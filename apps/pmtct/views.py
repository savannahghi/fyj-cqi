from itertools import chain
import pandas as pd
import plotly.express as px
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction, DatabaseError, IntegrityError
from django.db.models import Q
from django.db.models.expressions import When, Case
from django.forms import modelformset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect

# Create your views here.
from apps.pmtct.form import PatientDetailsForm, RiskCategorizationForm, RiskCategorizationTrialForm
from apps.pmtct.models import PatientDetails, RiskCategorization, RiskCategorizationTrial

from datetime import datetime, timedelta

from apps.pmtct.filters import PatientDetailsFilter


def show_stability(stability_df, num_patients_not_in_data_info=None):
    # Create a dictionary to store the risk level for each patient
    risk_dict = {}

    # Iterate over each unique patient and check for any 'Y' values in the columns after the second one
    for patient, group in stability_df.groupby('pmtct_mother'):
        if 'Y' in group.iloc[:, 1:].values:
            risk_dict[patient] = "HIGH RISK"
        else:
            risk_dict[patient] = "STABLE"

    # Convert the dictionary to a DataFrame and count the number of patients for each risk level
    risk_df = pd.DataFrame.from_dict(risk_dict, orient='index', columns=['Risk categorization'])
    d = {"Not categorized": num_patients_not_in_data_info}
    not_cat_df = pd.DataFrame(d.items(), columns=['Risk categorization', 'Number of patients'])

    grouped = risk_df['Risk categorization'].value_counts().reset_index().rename(
        columns={'index': 'Risk categorization', 'Risk categorization': 'Number of patients'})
    grouped = pd.concat([grouped, not_cat_df])

    # Add a row for the total number of patients and sort the DataFrame by the number of patients in descending
    # order
    grouped.loc[len(grouped)] = ['Total Categorized', len(risk_df)]
    # calculate the sum of patients in the not categorized and total categorized groups
    sum_not_categorized = grouped.loc[grouped['Risk categorization'] == 'Not categorized', 'Number of patients'].sum()
    sum_total_categorized = grouped.loc[
        grouped['Risk categorization'] == 'Total Categorized', 'Number of patients'].sum()

    # create a new dataframe with the total row
    total_row = {'Risk categorization': 'Total pts', 'Number of patients': sum_not_categorized + sum_total_categorized}
    df_total = pd.DataFrame(total_row, index=[len(grouped)])
    grouped = pd.concat([grouped, df_total])
    grouped = grouped.sort_values('Number of patients', ascending=False)
    total_patients = len(risk_df)
    grouped['Percentage'] = round((grouped['Number of patients'] / total_patients) * 100, 1)
    # Get the value for "STABLE" and calculate its percentage
    try:
        stable_count = grouped.loc[grouped['Risk categorization'] == 'STABLE', 'Number of patients'].iloc[0]
        stable_percent = round((stable_count / len(risk_df)) * 100, 1)
    except IndexError:
        stable_percent = 0

    # Get the value for "HIGH RISK" and calculate its percentage
    try:
        high_risk_count = grouped.loc[grouped['Risk categorization'] == 'HIGH RISK', 'Number of patients'].iloc[0]
        high_risk_percent = round((high_risk_count / len(risk_df)) * 100, 1)
    except IndexError:
        high_risk_percent = 0

    # Define a dictionary for the colors to use in the plot and create the plot using Plotly Express
    color_dict = {'Total Categorized': "blue", "STABLE": "green", "HIGH RISK": "red"}
    fig = px.bar(grouped, x="Risk categorization", y="Number of patients", text='Number of patients',
                 color="Risk categorization", color_discrete_map=color_dict,
                 title=F"High risk vs Stable N= {len(stability_df)}  (Stable = {stable_percent}% High risk = "
                       F"{high_risk_percent}%)", height=350)
    fig.update_layout(legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    ))
    # Set the font size of the x-axis and y-axis labels
    fig.update_layout(
        xaxis=dict(
            tickfont=dict(
                size=10
            ),
            title_font=dict(
                size=10
            )
        ),
        yaxis=dict(
            title_font=dict(
                size=10
            )
        ),
        legend=dict(
            font=dict(
                size=10
            )
        ),
        title=dict(
            # text="My Line Chart",
            font=dict(
                size=12
            )
        )
    )
    fig.update_layout(
        hoverlabel=dict(
            # bgcolor="white",
            font_size=9,
            font_family="Rockwell"
        )
    )
    chart_html = fig.to_html()
    return chart_html


def add_patient_details(request):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    if request.method == 'POST':
        form = PatientDetailsForm(request.POST)
        if form.is_valid():
            # Calculate age based on date of birth
            date_of_birth = form.cleaned_data['date_of_birth']
            today = datetime.today()
            age = today.year - date_of_birth.year - (
                    (today.month, today.day) < (date_of_birth.month, date_of_birth.day))

            # Save age to the model instance
            patient_details = form.save(commit=False)
            patient_details.age = age
            # save edd
            lmp = patient_details.lmp
            edd = lmp + timedelta(days=280)
            patient_details.edd = edd
            # save GBA
            patient_details.gestation_by_age = (datetime.now().date() - patient_details.lmp).days // 7
            lmp = patient_details.lmp

            date_enrolled_anc = patient_details.date_enrolled_anc.date()
            if date_enrolled_anc < lmp:
                form.add_error('date_enrolled_anc', 'Date enrolled ANC cannot be less than LMP.')
                return render(request, 'pmtct/add_patient_details.html', {'form': form})
            if patient_details.on_art == 'Yes' and not patient_details.date_started_on_art:
                form.add_error('date_started_on_art', 'Date started on ART is required if the patient is on ART.')
                return render(request, 'pmtct/add_patient_details.html', {'form': form})

            patient_details.save()
            return redirect("show_patient_details")

            # return HttpResponseRedirect(request.session['page_from'])
    else:
        form = PatientDetailsForm()
    context = {
        "form": form,
    }
    return render(request, 'pmtct/add_patient_details.html', context)


def show_patient_details(request):
    patient_filter = PatientDetailsFilter(request.GET, queryset=PatientDetails.objects.all().order_by('edd'))
    filtered_patients = patient_filter.qs.values_list('id', flat=True)
    data_infos = RiskCategorizationTrial.objects.filter(pmtct_mother_id__in=filtered_patients)
    data_info = data_infos.values_list('pmtct_mother_id', flat=True)

    data_info_ids = set(data_infos.values_list('pmtct_mother_id', flat=True))

    all_patient_ids = set(filtered_patients)
    not_in_data_info_ids = all_patient_ids - data_info_ids

    num_patients_not_in_data_info = len(not_in_data_info_ids)
    stability_df = [
        {'pmtct_mother': x.pmtct_mother.id,
         'baseline_assessment': x.baseline_assessment,
         'early_anc': x.early_anc,
         'mid_anc': x.mid_anc,
         "late_gestation": x.late_gestation,
         "six_weeks_assessment": x.six_weeks_assessment,
         "fourteen_weeks_assessment": x.fourteen_weeks_assessment,
         "six_month_assessment": x.six_month_assessment,
         "nine_month_assessment": x.nine_month_assessment,
         "twelve_month_assessment": x.twelve_month_assessment,
         "eighteen_month_assessment": x.eighteen_month_assessment,
         "twenty_four_month_assessment": x.twenty_four_month_assessment,
         } for x in data_infos
    ]
    stability_df = pd.DataFrame(stability_df)
    if stability_df.shape[0] > 0:
        chart_html = show_stability(stability_df, num_patients_not_in_data_info)
    else:
        chart_html = None

    # Filter the model to get objects where the risk category is "HIGH RISK"
    high_risk_objects = data_infos.filter(
        Q(baseline_assessment='Y') | Q(early_anc='Y') | Q(mid_anc='Y') | Q(late_gestation='Y') |
        Q(six_weeks_assessment='Y') | Q(fourteen_weeks_assessment='Y') | Q(six_month_assessment='Y') |
        Q(nine_month_assessment='Y') | Q(twelve_month_assessment='Y') | Q(eighteen_month_assessment='Y')
    )

    # Retrieve the pmtct_mother_id field from the high risk objects
    high_risk_pmtct_mother_ids = [obj.pmtct_mother_id for obj in high_risk_objects]
    print("pmtct_mother_ids::::::::::::::::::::::::::::::::::::::::::::::::::::::::::")
    print(high_risk_pmtct_mother_ids)
    context = {
        "filter": patient_filter,
        "risk_categorization_data": data_info,
        "chart_html": chart_html,
        "high_risk_pmtct_mother_ids":high_risk_pmtct_mother_ids,
        "high_risk_objects":high_risk_objects


    }
    return render(request, 'pmtct/show_patient_data.html', context)


def try_adding_details(request, pk):
    patient = PatientDetails.objects.filter(id=pk)
    context = {
        "filter": patient,
    }
    return render(request, 'pmtct/add_client_characterisation.html', context)


def validate_choice_fields(formset):
    for form in formset.forms:
        if all(field == '-' for field in form.cleaned_data.values()):
            raise ValidationError("Please fill in at least one choice field.")


def add_client_characteristics(request, pk):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    patient_info = PatientDetails.objects.get(id=pk)
    data_info = RiskCategorization.objects.filter(pmtct_mother_id=pk).first()

    pt_details_form = PatientDetailsForm(request.POST or None)
    client_characteristics = [
        "Is the client a newly HIV Positive (<3mnths)",
        "Is the client an adolescent <19 years of age?",
        "Is the client an adolescent @ School>20yrs",
        "Is the client’s current VL >200 copies/ml",
        "Client has poor adherence : Delayed ART",
        "Client has poor adherence : Missed >1 clinic appointments in the last scheduled 3 visits",
        "Client has poor adherence : LTFU/IIT",
        "Client has poor adherence : Declined ART",
        "Client has poor adherence : Missed ART doses",
        "The client NOT disclosed to partner",
        "Does the client have any social family issues and/or severe poverty that could hinder optimal adherence or "
        "other related issues",
        "Is the client experiencing intimate partner violence or at risk of intimate partner violence?",
        "Does the client have active comorbidities? TB, DM, OIs, painful, swollen/cracked nipples, etc.",
        "Is the client a lost to follow up/IIT who has returned to care",
        "Client has malnourished HEI; SAM, MAM.",
        "Does the client have a mental disability or require close care? Use PHQ9 to assess"
    ]
    # initialize data and make pmtct_mother not required in the RiskCategorizationForm
    initial_data = [{'client_characteristics': client_characteristic, 'pmtct_mother': patient_info.id} for
                    client_characteristic in
                    client_characteristics]

    RiskCategorizationFormSet = modelformset_factory(
        RiskCategorization,
        form=RiskCategorizationForm,
        extra=16

    )
    formset = RiskCategorizationFormSet(queryset=RiskCategorization.objects.none(), initial=initial_data)
    if request.method == "POST":
        # manipulate request.post data before passing it to the RiskCategorizationFormSet constructor
        post_data = request.POST.copy()
        for key, value in post_data.items():
            if value == '':
                post_data[key] = '-'
        formset = RiskCategorizationFormSet(post_data, initial=initial_data)
        if formset.is_valid():
            try:
                with transaction.atomic():
                    for form in formset:
                        instance = form.save(commit=False)
                        instance.created_by = request.user
                        instance.pmtct_mother = patient_info
                        instance.save()
                        messages.success(request, 'Risk Categorization data has been saved successfully.')
                return redirect("add_client_characteristics", pk=patient_info.id)
            except DatabaseError:
                messages.error(request,
                               "Database Error: An error occurred while saving data to the database. Data already "
                               "exists!")
            except ValidationError as e:
                messages.error(request, str(e))
    context = {
        "formset": formset,
        "pt_details_form": pt_details_form,
        "patient": patient_info,
        "data_info": data_info,
    }
    return render(request, 'pmtct/add_client_characterisation.html', context)


def show_client_characterisation(request, pk):
    data_info = RiskCategorization.objects.filter(pmtct_mother_id=pk)
    patient_info = PatientDetails.objects.get(id=pk)

    # pt_details_form = PatientDetailsForm(request.POST or None)
    client_characteristics = [
        "Is the client a newly HIV Positive (<3mnths)",
        "Is the client an adolescent <19 years of age?",
        "Is the client an adolescent @ School>20yrs",
        "Is the client’s current VL >200 copies/ml",
        "Client has poor adherence : Delayed ART",
        "Client has poor adherence : Missed >1 clinic appointments in the last scheduled 3 visits",
        "Client has poor adherence : LTFU/IIT",
        "Client has poor adherence : Declined ART",
        "Client has poor adherence : Missed ART doses",
        "The client NOT disclosed to partner",
        "Does the client have any social family issues and/or severe poverty that could hinder optimal adherence or "
        "other related issues",
        "Is the client experiencing intimate partner violence or at risk of intimate partner violence?",
        "Does the client have active comorbidities? TB, DM, OIs, painful, swollen/cracked nipples, etc.",
        "Is the client a lost to follow up/IIT who has returned to care",
        "Client has malnourished HEI; SAM, MAM.",
        "Does the client have a mental disability or require close care? Use PHQ9 to assess"
    ]
    # initialize data and make pmtct_mother not required in the RiskCategorizationForm
    initial_data = [{'client_characteristics': client_characteristic, 'pmtct_mother': patient_info.id} for
                    client_characteristic in
                    client_characteristics]

    RiskCategorizationFormSet = modelformset_factory(
        RiskCategorization,
        form=RiskCategorizationForm,
        extra=16

    )
    formset = RiskCategorizationFormSet(queryset=RiskCategorization.objects.none(), initial=initial_data)

    context = {
        "data_info": data_info,
        "patient": patient_info,
        "formset": formset,
    }
    return render(request, 'pmtct/show_client_characterisation.html', context)


def update_client_characteristics(request, pk):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    patient_info = RiskCategorization.objects.filter(pmtct_mother_id=pk).first()
    patient_infos = RiskCategorization.objects.filter(pmtct_mother_id=pk).order_by('id')

    pt_details_form = PatientDetailsForm(request.POST or None)

    client_characteristics = [
        "Is the client a newly HIV Positive (<3mnths)",
        "Is the client an adolescent <19 years of age?",
        "Is the client an adolescent @ School>20yrs",
        "Is the client’s current VL >200 copies/ml",
        "Client has poor adherence : Delayed ART",
        "Client has poor adherence : Missed >1 clinic appointments in the last scheduled 3 visits",
        "Client has poor adherence : LTFU/IIT",
        "Client has poor adherence : Declined ART",
        "Client has poor adherence : Missed ART doses",
        "The client NOT disclosed to partner",
        "Does the client have any social family issues and/or severe poverty that could hinder optimal adherence or "
        "other related issues",
        "Is the client experiencing intimate partner violence or at risk of intimate partner violence?",
        "Does the client have active comorbidities? TB, DM, OIs, painful, swollen/cracked nipples, etc.",
        "Is the client a lost to follow up/IIT who has returned to care",
        "Client has malnourished HEI; SAM, MAM.",
        "Does the client have a mental disability or require close care? Use PHQ9 to assess"
    ]
    ids = [{'id': x.id} for x in patient_infos]
    # initialize data and make pmtct_mother not required in the RiskCategorizationForm
    initial_data = [{'client_characteristics': client_characteristic, 'pmtct_mother': patient_info.id} for
                    client_characteristic in client_characteristics]

    RiskCategorizationFormSet = modelformset_factory(
        RiskCategorization,
        form=RiskCategorizationForm,
        extra=0,

    )
    formset = RiskCategorizationFormSet(queryset=patient_infos)
    # Set the ID field of each form in the formset
    for form in formset:
        form.fields['id'].widget.attrs['value'] = form.instance.id

    if request.method == "POST":
        # manipulate request.post data before passing it to the RiskCategorizationFormSet constructor
        post_data = request.POST.copy()
        for key, value in post_data.items():
            if value == '':
                post_data[key] = '-'

        for i, item in enumerate(ids):
            key = f'form-{i}-id'
            if key in post_data and post_data[key][0] == '-':
                post_data[key] = item['id']

        formset = RiskCategorizationFormSet(post_data, initial=initial_data, queryset=patient_info)

        if formset.is_valid():
            formset.save()
    context = {
        "formset": formset,
        "pt_details_form": pt_details_form,
        "patient": patient_info,
    }
    return render(request, 'pmtct/add_client_characterisation.html', context)


def add_client_characteristics_trial(request, pk):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    patient_info = PatientDetails.objects.get(id=pk)

    # Order the queryset using the choice_indexes list
    data_info = RiskCategorizationTrial.objects.filter(pmtct_mother_id=pk).order_by(
        Case(*[When(client_characteristics=choice[1], then=index) for index, choice in
               enumerate(RiskCategorizationTrial.CLIENT_CATEGORIES)],
             default=len(RiskCategorizationTrial.CLIENT_CATEGORIES))
    )

    form = RiskCategorizationTrialForm()
    if request.method == "POST":
        form = RiskCategorizationTrialForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    post = form.save(commit=True)
                    post.created_by = request.user
                    post.pmtct_mother = patient_info
                    post.save()
                    messages.success(request, "The form has been submitted successfully.")
                    return HttpResponseRedirect(request.path_info)
            except IntegrityError as e:
                messages.error(request, "Data already exists.")
        else:
            messages.error(request, "There was an error with your submission. Please correct the errors below.")
            return HttpResponseRedirect(request.session['page_from'])

    choices = data_info.values_list('baseline_assessment', 'early_anc', 'mid_anc', 'late_gestation',
                                    'six_weeks_assessment', 'fourteen_weeks_assessment', 'six_month_assessment',
                                    'nine_month_assessment', 'twelve_month_assessment', 'eighteen_month_assessment',
                                    'twelve_month_assessment',
                                    )
    if "Y" in list(chain(*choices)):
        risk_category = "HIGH RISK"
    elif "N" in list(chain(*choices)):
        risk_category = "STABLE"
    else:
        risk_category = ""

    context = {
        "formset": form,
        "patient": patient_info,
        "data_info": data_info,
        "risk_category": risk_category,

    }
    return render(request, 'pmtct/add_client_characterisations.html', context)


def update_client_characteristics_trial(request, pk):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    data_info = RiskCategorizationTrial.objects.get(id=pk)
    patient_info = PatientDetails.objects.get(id=data_info.pmtct_mother_id)
    form = RiskCategorizationTrialForm(instance=data_info)
    if request.method == "POST":
        form = RiskCategorizationTrialForm(request.POST, instance=data_info)
        if form.is_valid():
            post = form.save(commit=False)
            post.pmtct_mother = patient_info
            post.save()
            messages.success(request, "The form has been submitted successfully.")
            return HttpResponseRedirect(request.session['page_from'])

    context = {
        "formset": form,
    }
    return render(request, 'pmtct/update_client_characterisations.html', context)
