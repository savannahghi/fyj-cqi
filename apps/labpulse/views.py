import math
from datetime import datetime

import numpy as np
import pandas as pd
import pytz
from datetime import timezone, timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models.functions import Lower
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from apps.cqi.models import Facilities, Sub_counties, Counties
from apps.cqi.views import bar_chart
from apps.data_analysis.views import get_key_from_session_names
from apps.dqa.models import UpdateButtonSettings
# from apps.dqa.views import disable_update_buttons
from apps.labpulse.filters import Cd4trakerFilter
from apps.labpulse.forms import Cd4trakerForm, Cd4TestingLabsForm, Cd4TestingLabForm
from apps.labpulse.models import Cd4TestingLabs, Cd4traker


def disable_update_buttons(request, audit_team, relevant_date_field):
    ##############################################################
    # DISABLE UPDATE BUTTONS AFTER A SPECIFIED TIME AND DAYS AGO #
    ##############################################################
    local_tz = pytz.timezone("Africa/Nairobi")
    settings = UpdateButtonSettings.objects.first()
    disable_button = settings.disable_all_dqa_update_buttons
    # DISABLE ALL DQA UPDATE BUTTONS
    if disable_button:
        for data in audit_team:
            data.hide_update_button = True
    else:
        try:
            hide_button_time = settings.hide_button_time
            days_to_keep_enabled = settings.days_to_keep_update_button_enabled
            now = timezone.now().astimezone(local_tz)
            enabled_datetime = now - timedelta(days=days_to_keep_enabled)
            for data in audit_team:
                try:
                    relevant_date = getattr(data, relevant_date_field).astimezone(local_tz).date()
                except AttributeError:
                    relevant_date = getattr(data, relevant_date_field).astimezone(local_tz).date()
                hide_button_datetime = timezone.make_aware(datetime.combine(relevant_date, hide_button_time))
                if relevant_date == now.date() and now >= hide_button_datetime:
                    data.hide_update_button = True
                elif relevant_date >= enabled_datetime.date():
                    data.hide_update_button = False
                elif now >= hide_button_datetime:
                    data.hide_update_button = True
                else:
                    data.hide_update_button = False
        except AttributeError:
            messages.info(request,
                          "You have not yet set the time to disable the DQA update button. Please click on the 'Change "
                          "DQA Update Time' button on the left navigation bar to set the time or contact an "
                          "administrator to set it for you.")
    return redirect(request.path_info)


# Create your views here.
@login_required(login_url='login')
def choose_testing_lab(request):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    cd4_testing_lab_form = Cd4TestingLabsForm(request.POST or None)
    if request.method == "POST":
        if cd4_testing_lab_form.is_valid():
            testing_lab_name = cd4_testing_lab_form.cleaned_data['testing_lab_name']
            # Generate the URL for the redirect
            url = reverse('add_cd4_count',
                          kwargs={
                              'pk_lab': testing_lab_name.id})

            return redirect(url)
    context = {
        "cd4_testing_lab_form": cd4_testing_lab_form,
        "title": "CD4 TRACKER"
    }
    return render(request, 'lab_pulse/add_cd4_data.html', context)


@login_required(login_url='login')
def add_cd4_count(request, pk_lab):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    form = Cd4trakerForm(request.POST or None)
    selected_lab, created = Cd4TestingLabs.objects.get_or_create(id=pk_lab)

    template_name = 'lab_pulse/add_cd4_data.html'
    context = {
        "form": form,
        "title": f"Add CD4 Results for {selected_lab.testing_lab_name.title()}",
    }

    if request.method == "POST":
        if form.is_valid():
            post = form.save(commit=False)
            received_status = form.cleaned_data['received_status']
            reason_for_rejection = form.cleaned_data['reason_for_rejection']
            date_of_collection = form.cleaned_data['date_of_collection']
            date_sample_received = form.cleaned_data['date_sample_received']
            date_of_testing = form.cleaned_data['date_of_testing']
            cd4_count_results = form.cleaned_data['cd4_count_results']
            serum_crag_results = form.cleaned_data['serum_crag_results']
            reason_for_no_serum_crag = form.cleaned_data['reason_for_no_serum_crag']

            if date_of_collection > date_sample_received:
                error_message = f"Collection date is greater than Receipt date!"
                form.add_error('date_of_collection', error_message)
                form.add_error('date_sample_received', error_message)
                return render(request, template_name, context)

            if received_status == 'Rejected':
                if not reason_for_rejection:
                    error_message = f"Please specify the reason for rejection."
                    form.add_error('reason_for_rejection', error_message)
                    return render(request, template_name, context)
                if date_of_testing or cd4_count_results or serum_crag_results or reason_for_no_serum_crag:
                    error_message = "All fields should be empty when the status is 'Rejected'."
                    if date_of_testing:
                        form.add_error('date_of_testing', error_message)
                    if cd4_count_results:
                        form.add_error('cd4_count_results', error_message)
                    if serum_crag_results:
                        form.add_error('serum_crag_results', error_message)
                    if reason_for_no_serum_crag:
                        form.add_error('reason_for_no_serum_crag', error_message)
                    return render(request, template_name, context)

            if received_status == "Accepted":
                if reason_for_rejection:
                    error_message = f"Check if this information is correct"
                    form.add_error('received_status', error_message)
                    form.add_error('reason_for_rejection', error_message)
                    return render(request, template_name, context)

                if not date_of_testing:
                    error_message = f"Provide Testing date"
                    form.add_error('received_status', error_message)
                    form.add_error('date_of_testing', error_message)
                    return render(request, template_name, context)

                if date_of_testing < date_of_collection:
                    error_message = f"Testing date is less than Collection date!"
                    form.add_error('date_of_testing', error_message)
                    form.add_error('date_of_collection', error_message)
                    return render(request, template_name, context)
                if date_of_testing < date_sample_received:
                    error_message = f"Testing date is less than Receipt date!"
                    form.add_error('date_of_testing', error_message)
                    form.add_error('date_sample_received', error_message)
                    return render(request, template_name, context)

                # Check date fields
                today = timezone.now().date()
                if date_of_testing > today:
                    form.add_error('date_of_testing', "Date of testing cannot be in the future.")
                if date_of_collection > today:
                    form.add_error('date_of_collection', "Date of collection cannot be in the future.")
                if date_sample_received > today:
                    form.add_error('date_sample_received', "Date of sample received cannot be in the future.")

                if form.errors:
                    # If there are any errors, return the form with the error messages
                    return render(request, template_name, context)

                if not cd4_count_results:
                    error_message = f"Provide CD4 count results"
                    form.add_error('received_status', error_message)
                    form.add_error('cd4_count_results', error_message)
                    return render(request, template_name, context)

                if cd4_count_results <= 200 and not serum_crag_results and not reason_for_no_serum_crag:
                    error_message = f"Select a reason why serum CRAG was not done"
                    form.add_error('reason_for_no_serum_crag', error_message)
                    form.add_error('cd4_count_results', error_message)
                    form.add_error('serum_crag_results', error_message)
                    return render(request, template_name, context)

                if cd4_count_results > 200 and not serum_crag_results and reason_for_no_serum_crag:
                    error_message = f"Check if the information is correct"
                    form.add_error('reason_for_no_serum_crag', error_message)
                    form.add_error('cd4_count_results', error_message)
                    form.add_error('serum_crag_results', error_message)
                    return render(request, template_name, context)

                if serum_crag_results and reason_for_no_serum_crag:
                    error_message = f"Check if the information is correct"
                    form.add_error('reason_for_no_serum_crag', error_message)
                    form.add_error('serum_crag_results', error_message)
                    return render(request, template_name, context)

            selected_facility = form.cleaned_data['facility_name']

            facility_id = Facilities.objects.get(name=selected_facility)
            # https://stackoverflow.com/questions/14820579/how-to-query-directly-the-table-created-by-django-for-a-manytomany-relation
            all_subcounties = Sub_counties.facilities.through.objects.all()
            all_counties = Sub_counties.counties.through.objects.all()
            # loop
            sub_county_list = []
            for sub_county in all_subcounties:
                if facility_id.id == sub_county.facilities_id:
                    # assign an instance to sub_county
                    post.sub_county = Sub_counties(id=sub_county.sub_counties_id)
                    sub_county_list.append(sub_county.sub_counties_id)
            for county in all_counties:
                if sub_county_list[0] == county.sub_counties_id:
                    post.county = Counties.objects.get(id=county.counties_id)

            facility_name = Facilities.objects.filter(name=selected_facility).first()
            post.facility_name = facility_name
            post.testing_laboratory = Cd4TestingLabs.objects.filter(testing_lab_name=selected_lab).first()
            post.save()
            messages.error(request, "Record saved successfully!")
            # Generate the URL for the redirect
            url = reverse('add_cd4_count', kwargs={'pk_lab': pk_lab})
            return redirect(url)
        else:
            messages.error(request, f"Record already exists.")
            render(request, template_name, context)

    context = {
        "form": form,
        "title": f"Add CD4 Results for {selected_lab.testing_lab_name.title()}",
    }
    return render(request, 'lab_pulse/add_cd4_data.html', context)


@login_required(login_url='login')
def update_cd4_results(request, pk):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    item = Cd4traker.objects.get(id=pk)
    if request.method == "POST":
        form = Cd4trakerForm(request.POST, instance=item)
        if form.is_valid():
            context = {
                "form": form,
                "title": "Update Results",
            }
            template_name = 'lab_pulse/add_cd4_data.html'
            post = form.save(commit=False)
            received_status = form.cleaned_data['received_status']
            reason_for_rejection = form.cleaned_data['reason_for_rejection']
            date_of_collection = form.cleaned_data['date_of_collection']
            date_sample_received = form.cleaned_data['date_sample_received']
            date_of_testing = form.cleaned_data['date_of_testing']
            cd4_count_results = form.cleaned_data['cd4_count_results']
            serum_crag_results = form.cleaned_data['serum_crag_results']
            reason_for_no_serum_crag = form.cleaned_data['reason_for_no_serum_crag']
            facility_name = form.cleaned_data['facility_name']

            if date_of_collection > date_sample_received:
                error_message = f"Collection date is greater than Receipt date!"
                form.add_error('date_of_collection', error_message)
                form.add_error('date_sample_received', error_message)
                return render(request, template_name, context)

            if received_status == 'Rejected':
                if not reason_for_rejection:
                    error_message = f"Please specify the reason for rejection."
                    form.add_error('reason_for_rejection', error_message)
                    return render(request, template_name, context)
                if date_of_testing or cd4_count_results or serum_crag_results or reason_for_no_serum_crag:
                    error_message = "All fields should be empty when the status is 'Rejected'."
                    if date_of_testing:
                        form.add_error('date_of_testing', error_message)
                    if cd4_count_results:
                        form.add_error('cd4_count_results', error_message)
                    if serum_crag_results:
                        form.add_error('serum_crag_results', error_message)
                    if reason_for_no_serum_crag:
                        form.add_error('reason_for_no_serum_crag', error_message)
                    return render(request, template_name, context)

            if received_status == "Accepted":
                if reason_for_rejection:
                    error_message = f"Check if this information is correct"
                    form.add_error('received_status', error_message)
                    form.add_error('reason_for_rejection', error_message)
                    return render(request, template_name, context)

                if not date_of_testing:
                    error_message = f"Provide Testing date"
                    form.add_error('received_status', error_message)
                    form.add_error('date_of_testing', error_message)
                    return render(request, template_name, context)

                if date_of_testing < date_of_collection:
                    error_message = f"Testing date is less than Collection date!"
                    form.add_error('date_of_testing', error_message)
                    form.add_error('date_of_collection', error_message)
                    return render(request, template_name, context)
                if date_of_testing < date_sample_received:
                    error_message = f"Testing date is less than Receipt date!"
                    form.add_error('date_of_testing', error_message)
                    form.add_error('date_sample_received', error_message)
                    return render(request, template_name, context)

                # Check date fields
                today = timezone.now().date()
                if date_of_testing > today:
                    form.add_error('date_of_testing', "Date of testing cannot be in the future.")
                if date_of_collection > today:
                    form.add_error('date_of_collection', "Date of collection cannot be in the future.")
                if date_sample_received > today:
                    form.add_error('date_sample_received', "Date of sample received cannot be in the future.")

                if form.errors:
                    # If there are any errors, return the form with the error messages
                    return render(request, template_name, context)

                if not cd4_count_results:
                    error_message = f"Provide CD4 count results"
                    form.add_error('received_status', error_message)
                    form.add_error('cd4_count_results', error_message)
                    return render(request, template_name, context)

                if cd4_count_results <= 200 and not serum_crag_results and not reason_for_no_serum_crag:
                    error_message = f"Select a reason why serum CRAG was not done"
                    form.add_error('reason_for_no_serum_crag', error_message)
                    form.add_error('cd4_count_results', error_message)
                    form.add_error('serum_crag_results', error_message)
                    return render(request, template_name, context)

                if cd4_count_results > 200 and not serum_crag_results and reason_for_no_serum_crag:
                    error_message = f"Check if the information is correct"
                    form.add_error('reason_for_no_serum_crag', error_message)
                    form.add_error('cd4_count_results', error_message)
                    form.add_error('serum_crag_results', error_message)
                    return render(request, template_name, context)

                if serum_crag_results and reason_for_no_serum_crag:
                    error_message = f"Check if the information is correct"
                    form.add_error('reason_for_no_serum_crag', error_message)
                    form.add_error('serum_crag_results', error_message)
                    return render(request, template_name, context)

            facility_id = Facilities.objects.get(name=facility_name)
            # https://stackoverflow.com/questions/14820579/how-to-query-directly-the-table-created-by-django-for-a-manytomany-relation
            all_subcounties = Sub_counties.facilities.through.objects.all()
            all_counties = Sub_counties.counties.through.objects.all()
            # loop
            sub_county_list = []
            for sub_county in all_subcounties:
                if facility_id.id == sub_county.facilities_id:
                    # assign an instance to sub_county
                    post.sub_county = Sub_counties(id=sub_county.sub_counties_id)
                    sub_county_list.append(sub_county.sub_counties_id)
            for county in all_counties:
                if sub_county_list[0] == county.sub_counties_id:
                    post.county = Counties.objects.get(id=county.counties_id)
            post.save()
            messages.error(request, "Record updated successfully!")
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = Cd4trakerForm(instance=item)
    context = {
        "form": form,
        "title": "Update Results",
    }
    return render(request, 'lab_pulse/update results.html', context)


def pagination_(request, item_list, record_count=None):
    page = request.GET.get('page', 1)
    record_count = request.GET.get('record_count', '50')

    if record_count == 'all':
        return item_list
    else:
        paginator = Paginator(item_list, int(record_count))
        try:
            items = paginator.page(page)
        except PageNotAnInteger:
            items = paginator.page(1)
        except EmptyPage:
            items = paginator.page(paginator.num_pages)
        return items


@login_required(login_url='login')
def show_results(request):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
        # record_count = int(request.GET.get('record_count', 10))  # Get the selected record count (default: 10)
        record_count = request.GET.get('record_count', '50')
        if record_count == 'all':
            record_count = 'all'  # Preserve the 'all' value if selected
        else:
            record_count = int(record_count)  # Convert to integer if a specific value is selected
    else:
        record_count = 50  # Default record count if no selection is made
    cd4_summary_fig = None
    cd4_testing_lab_fig = None
    crag_testing_lab_fig = None
    age_distribution_fig = None
    rejection_summary_fig = None
    crag_positivity_fig = None
    facility_crag_positive_fig = None
    list_of_projects_fac = pd.DataFrame()
    crag_pos_df = pd.DataFrame()
    missing_df = pd.DataFrame()
    rejected_df = pd.DataFrame()
    cd4_df = pd.DataFrame()
    crag_df = pd.DataFrame()
    crag_positivity_df = pd.DataFrame()
    facility_positive_count = pd.DataFrame()
    cd4_results = Cd4traker.objects.all()

    qi_list = Cd4traker.objects.all().order_by('-date_dispatched')
    my_filters = Cd4trakerFilter(request.GET, queryset=qi_list)
    qi_lists = my_filters.qs

    qi_list = pagination_(request, qi_lists, record_count)
    ######################
    # Hide update button #
    ######################
    if qi_list:
        disable_update_buttons(request, qi_list, 'date_dispatched')

    if qi_list:
        list_of_projects = [
            {'County': x.county.county_name,
             'Sub-county': x.sub_county.sub_counties,
             'Facility': x.facility_name.name,
             'MFL CODE': x.facility_name.mfl_code,
             'CCC NO.': x.patient_unique_no,
             'Age': x.age,
             'Sex': x.sex,
             'Collection Date': x.date_of_collection,
             'Testing date': x.date_of_testing,
             'Date Dispatch': x.date_dispatched,
             'CD4 Count': x.cd4_count_results,
             'Serum Crag': x.serum_crag_results,
             'Received status': x.received_status,
             'Rejection reason': x.reason_for_rejection,
             'Testing Laboratory': x.testing_laboratory.testing_lab_name,
             } for x in qi_list
        ]
        # convert data from database to a dataframe
        list_of_projects = pd.DataFrame(list_of_projects)
        list_of_projects_fac = list_of_projects.copy()

        # Convert Timestamp objects to strings
        list_of_projects_fac = list_of_projects_fac.sort_values('Collection Date').reset_index(drop=True)
        list_of_projects_fac['Testing date'] = pd.to_datetime(list_of_projects_fac['Testing date']).dt.date
        list_of_projects_fac['Collection Date'] = pd.to_datetime(list_of_projects_fac['Collection Date']).dt.date
        list_of_projects_fac['Date Dispatch'] = pd.to_datetime(list_of_projects_fac['Date Dispatch']).dt.date
        list_of_projects_fac['Collection Date'] = list_of_projects_fac['Collection Date'].astype(str)
        list_of_projects_fac['Testing date'] = list_of_projects_fac['Testing date'].replace(np.datetime64('NaT'), '')
        list_of_projects_fac['Testing date'] = list_of_projects_fac['Testing date'].astype(str)
        list_of_projects_fac['Date Dispatch'] = list_of_projects_fac['Date Dispatch'].astype(str)
        list_of_projects_fac.index = range(1, len(list_of_projects_fac) + 1)
        max_date = list_of_projects_fac['Collection Date'].max()
        min_date = list_of_projects_fac['Collection Date'].min()
        missing_df = list_of_projects_fac.loc[
            (list_of_projects_fac['CD4 Count'] < 200) & (list_of_projects_fac['Serum Crag'].isna())]
        crag_pos_df = list_of_projects_fac.loc[(list_of_projects_fac['Serum Crag'] == "Positive")]
        rejected_df = list_of_projects_fac.loc[(list_of_projects_fac['Received status'] == "Rejected")]

        # Create the summary dataframe
        summary_df = pd.DataFrame({
            'Total CD4 Processed': [list_of_projects_fac.shape[0]],
            'CD4 Count >=200': [(list_of_projects_fac['CD4 Count'] >= 200).sum()],
            'CD4 Count < 200': [(list_of_projects_fac['CD4 Count'] < 200).sum()],
            'Total CRAG Processed': [list_of_projects_fac['Serum Crag'].notna().sum()],
            'Negative CRAG': [(list_of_projects_fac['Serum Crag'] == 'Negative').sum()],
            'Positive CRAG': [(list_of_projects_fac['Serum Crag'] == 'Positive').sum()],
            'Missing CRAG': [
                (list_of_projects_fac.loc[list_of_projects_fac['CD4 Count'] < 200, 'Serum Crag'].isna()).sum()],
            'Rejected samples': [(list_of_projects_fac['Received status'] == 'Rejected').sum()],
        })

        # Display the summary dataframe
        summary_df = summary_df.T.reset_index()
        summary_df.columns = ['variables', 'values']
        cd4_summary_fig = bar_chart(summary_df, "variables", "values",
                                    f"Summary of CD4 Records and Serum CRAG Results between {min_date} and {max_date} ")

        # Group the data by testing laboratory and calculate the counts
        summary_df = list_of_projects_fac.groupby('Testing Laboratory').agg({
            'CD4 Count': 'count',
            'Serum Crag': lambda x: x.count() if x.notnull().any() else 0
        }).reset_index()

        # Rename the columns
        summary_df.rename(columns={'CD4 Count': 'Total CD4 Count', 'Serum Crag': 'Total CRAG Reports'}, inplace=True)

        # Sort the dataframe by testing laboratory name
        summary_df.sort_values('Testing Laboratory', inplace=True)

        # Reset the index
        summary_df.reset_index(drop=True, inplace=True)

        summary_df = pd.melt(summary_df, id_vars="Testing Laboratory",
                             value_vars=['Total CD4 Count', 'Total CRAG Reports'],
                             var_name="Test done", value_name='values')

        cd4_df = summary_df[summary_df['Test done'] == "Total CD4 Count"].sort_values("values").fillna(0)
        cd4_df=cd4_df[cd4_df['values']!=0]
        crag_df = summary_df[summary_df['Test done'] == "Total CRAG Reports"].sort_values("values").fillna(0)
        crag_df=crag_df[crag_df['values']!=0]
        crag_testing_lab_fig = bar_chart(crag_df, "Testing Laboratory", "values",
                                         "Number of CRAG Reports Processed by Testing Laboratory")
        cd4_testing_lab_fig = bar_chart(cd4_df, "Testing Laboratory", "values",
                                        "Number of CD4 Reports Processed by Testing Laboratory")

        age_bins = [0, 1, 4, 9, 14, 19, 24, 29, 34, 39, 44, 49, 54, 59, 64, 150]
        age_labels = ['<1', '1-4.', '5-9', '10-14.', '15-19', '20-24', '25-29', '30-34', '35-39', '40-44', '45-49',
                      '50-54', '55-59', '60-64', '65+']

        list_of_projects_fac['Age Group'] = pd.cut(list_of_projects_fac['Age'], bins=age_bins, labels=age_labels)

        age_sex_df = list_of_projects_fac.groupby(['Age Group', 'Sex']).size().unstack().reset_index()
        age_sex_df = pd.melt(age_sex_df, id_vars="Age Group",
                             value_vars=list(age_sex_df.columns[1:]),
                             var_name="Sex", value_name='# of sample processed')

        age_distribution_fig = bar_chart(age_sex_df, "Age Group", "# of sample processed",
                                         "CD4 Count Distribution by Age Band", color="Sex")

        ###################################
        # REJECTED SAMPLES
        ###################################
        # Get the unique rejection reasons excluding NaN
        rejection_reasons = list_of_projects_fac['Rejection reason'].unique()
        rejection_reasons = rejection_reasons[~pd.isnull(rejection_reasons)]

        # Create the summary dataframe
        rejection_summary_df = pd.DataFrame({
            'Reasons for sample rejection': rejection_reasons,
            'Number rejected': [(list_of_projects_fac['Rejection reason'] == reason).sum() for reason in
                                rejection_reasons]
        }).sort_values("Number rejected")
        total = rejection_summary_df['Number rejected'].sum()
        rejection_summary_fig = bar_chart(rejection_summary_df, "Reasons for sample rejection", "Number rejected",
                                          f"Summary of Reasons for Sample Rejection N={total}")

        ###########################
        # SERUM CRAG POSITIVITY
        ###########################
        # Filter the DataFrame for rows with valid serum crag results
        filtered_df = list_of_projects_fac[list_of_projects_fac['Serum Crag'].notna()]

        # Calculate the number of serum crag tests done
        num_tests_done = len(filtered_df)

        # Calculate the number of samples positive for serum crag
        num_samples_positive = (filtered_df['Serum Crag'] == 'Positive').sum()
        num_samples_negative = (filtered_df['Serum Crag'] == 'Negative').sum()

        # Calculate the serum crag positivity
        serum_crag_positivity = num_samples_positive / num_tests_done * 100

        # Create the new DataFrame
        crag_positivity_df = pd.DataFrame({
            'Number of Serum CRAG Tests Done': [num_tests_done],
            'Number of Samples Positive': [num_samples_positive],
            'Number of Samples Negative': [num_samples_negative],
            'Serum CRAG Positivity (%)': [serum_crag_positivity]
        })
        crag_positivity_df = crag_positivity_df.T.reset_index().fillna(0)
        crag_positivity_df.columns = ['variables', 'values']
        crag_positivity_df=crag_positivity_df[crag_positivity_df['values']!=0]
        crag_positivity_fig = bar_chart(crag_positivity_df, "variables", "values",
                                        f"Serum CRAG Testing Results", color='variables')
        ###############################
        # FACILITY WITH POSITIVE CRAG #
        ###############################
        # Filter the DataFrame for rows where Serum Crag is positive
        positive_crag_df = list_of_projects_fac[list_of_projects_fac['Serum Crag'] == 'Positive']

        # Group by Facility and count the number of positive serum CRAG results
        facility_positive_count = positive_crag_df.groupby('Facility')['Serum Crag'].count().reset_index().fillna(0)

        # Rename the column for clarity
        facility_positive_count.columns = ['Facilities', 'Number of Positive Serum CRAG']
        facility_positive_count = facility_positive_count.sort_values("Number of Positive Serum CRAG", ascending=False)
        facility_positive_count=facility_positive_count[facility_positive_count['Number of Positive Serum CRAG']!=0]
        # top twenty facilities
        if facility_positive_count.shape[0] > 20:
            facility_positive_count = facility_positive_count.head(20)
            facility_crag_positive_fig = bar_chart(facility_positive_count, "Facilities",
                                                   "Number of Positive Serum CRAG",
                                                   f"Top Twenty Facilities with Positive Serum CRAG Results")
        else:
            facility_crag_positive_fig = bar_chart(facility_positive_count, "Facilities",
                                                   "Number of Positive Serum CRAG",
                                                   f"Number of Positive Serum CRAG Results by Facility")

    request.session['list_of_projects_fac'] = list_of_projects_fac.to_dict()

    if missing_df.shape[0] > 0:
        request.session['missing_df'] = missing_df.to_dict()
    else:
        if "missing_df" in request.session:
            del request.session['missing_df']
    if crag_pos_df.shape[0] > 0:
        request.session['crag_pos_df'] = crag_pos_df.to_dict()
    else:
        if "crag_pos_df" in request.session:
            del request.session['crag_pos_df']

    if rejected_df.shape[0] > 0:
        request.session['rejected_df'] = rejected_df.to_dict()
    else:
        if "rejected_df" in request.session:
            del request.session['rejected_df']
    # Convert dict_items into a list
    dictionary = get_key_from_session_names(request)
    # list_of_projects_fac['Facility'] = list_of_projects_fac['facility'].astype(str).str.split(" ").str[0]
    context = {
        "title": "Results",
        "cd4_results": cd4_results,
        "dictionary": dictionary,
        "my_filters": my_filters, "qi_list": qi_list, "qi_lists": qi_lists,
        "cd4_summary_fig": cd4_summary_fig,
        "crag_testing_lab_fig": crag_testing_lab_fig,
        "cd4_testing_lab_fig": cd4_testing_lab_fig,
        "age_distribution_fig": age_distribution_fig,
        "rejection_summary_fig": rejection_summary_fig,
        "crag_positivity_fig": crag_positivity_fig,
        "facility_crag_positive_fig": facility_crag_positive_fig,
        "cd4_df":cd4_df,"crag_df":crag_df,"crag_positivity_df":crag_positivity_df,
        "facility_positive_count":facility_positive_count
    }
    return render(request, 'lab_pulse/show results.html', context)


def generate_report(request, pdf, name, mfl_code, date_collection, date_testing, date_dispatch, unique_no, age,
                    cd4_count, crag, sex, reason_for_rejection,testing_laboratory, y):
    # Change page size if needed
    if y < 0:
        pdf.showPage()
        y = 680  # Reset y value for the new page
        pdf.translate(inch, inch)

    pdf.setFont("Courier-Bold", 18)
    # Write the facility name in the top left corner of the page
    pdf.drawString(180, y + 10, "CD4 COUNT REPORT")
    pdf.setDash(1, 0)  # Reset the line style
    pdf.line(x1=10, y1=y, x2=500, y2=y)
    # Facility info
    pdf.setFont("Helvetica", 12)
    pdf.drawString(10, y - 20, f"Facility: {name}")
    pdf.drawString(10, y - 40, f"MFL Code: {mfl_code}")
    pdf.drawString(10, y - 60, f"Sex: {sex}")

    y -= 140
    # Rectangles
    pdf.rect(x=10, y=y, width=490, height=70, stroke=1, fill=0)
    pdf.rect(x=10, y=y, width=70, height=70, stroke=1, fill=0)
    pdf.rect(x=10, y=y, width=135, height=70, stroke=1, fill=0)
    pdf.rect(x=10, y=y, width=210, height=70, stroke=1, fill=0)
    pdf.rect(x=10, y=y, width=280, height=70, stroke=1, fill=0)
    pdf.rect(x=10, y=y, width=350, height=70, stroke=1, fill=0)
    pdf.rect(x=10, y=y, width=420, height=70, stroke=1, fill=0)

    pdf.rect(x=10, y=y, width=490, height=50, stroke=1, fill=0)
    pdf.setFont("Helvetica-Bold", 7)

    y_position = y + 53
    pdf.drawString(12, y_position, "Patient Unique No.")
    pdf.drawString(110, y_position, "Age")
    pdf.drawString(165, y_position, "CD4 COUNT")
    pdf.drawString(235, y_position, "SERUM CRAG")
    pdf.drawString(305, y_position, "Collection Date")
    pdf.drawString(375, y_position, "Testing Date")
    pdf.drawString(435, y_position, "Dispatch Date")

    pdf.setFont("Helvetica", 7)
    y_position = y + 24
    pdf.drawString(110, y_position, f"{age}")
    if math.isnan(cd4_count):
        pdf.setFont("Helvetica-Bold", 7)
        pdf.setFillColor(colors.red)
        pdf.drawString(165, y_position, "Rejected")
        pdf.setFont("Helvetica", 3)
        pdf.drawString(145, y_position - 10, f"(Reason: {reason_for_rejection})")
    elif int(cd4_count) <= 200:
        pdf.setFont("Helvetica-Bold", 7)
        pdf.drawString(165, y_position, str(int(cd4_count)))
    else:
        pdf.setFont("Helvetica", 7)
        pdf.drawString(165, y_position, str(int(cd4_count)))
    pdf.setFont("Helvetica", 7)
    if crag is not None and "pos" in crag.lower():
        pdf.setFont("Helvetica-Bold", 7)
        pdf.setFillColor(colors.red)
        pdf.drawString(235, y_position, f"{crag}")
    elif crag is None and cd4_count <= 200:
        pdf.setFont("Helvetica-Bold", 7)
        pdf.setFillColor(colors.red)
        pdf.drawString(235, y_position, f"Missing")
    else:
        pdf.setFont("Helvetica", 7)
        if crag is None:
            pdf.drawString(235, y_position, "")
        else:
            pdf.drawString(235, y_position, f"{crag}")
    pdf.setFont("Helvetica", 7)
    pdf.setFillColor(colors.black)
    pdf.drawString(305, y_position, f"{date_collection}")
    pdf.drawString(375, y_position, f"{date_testing}")
    pdf.drawString(435, y_position, f"{date_dispatch}")

    pdf.drawString(22, y_position, f"{unique_no}")
    y -= 50

    pdf.setFont("Helvetica", 4)
    pdf.setFillColor(colors.grey)
    pdf.drawString((letter[0] / 10), y + 0.2 * inch,
                   f"Testing laboratory : {testing_laboratory}")
    if y > 30:
        pdf.setDash(1, 2)  # Reset the line style
        pdf.line(x1=10, y1=y, x2=500, y2=y)
        pdf.setFont("Helvetica", 4)
        pdf.setFillColor(colors.grey)
        pdf.drawString((letter[0] / 3) + 30, y + 0.2 * inch,
                       f"Report generated by: {request.user}    Time: {datetime.now()}")
    else:
        pdf.setFont("Helvetica", 4)
        pdf.setFillColor(colors.grey)
        pdf.drawString((letter[0] / 3) + 30, y + 0.2 * inch,
                       f"Report generated by: {request.user}    Time: {datetime.now()}")

    pdf.setFont("Helvetica", 7)
    pdf.setFillColor(colors.black)

    # Add some space for the next report
    y -= 50

    return y


class GeneratePDF(View):
    def get(self, request):
        if request.user.is_authenticated and not request.user.first_name:
            return redirect("profile")

        # Retrieve the serialized DataFrame from the session
        list_of_projects_fac_dict = request.session.get('list_of_projects_fac', {})

        # Convert the dictionary back to a DataFrame
        list_of_projects_fac = pd.DataFrame.from_dict(list_of_projects_fac_dict)

        # Create a new PDF object using ReportLab
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'filename="CD4 Count Report.pdf"'
        pdf = canvas.Canvas(response, pagesize=letter)

        y = 680

        # Create a PDF canvas
        pdf.translate(inch, inch)
        client_timezone = timezone.get_current_timezone()

        # Generate reports
        for index, data in list_of_projects_fac.iterrows():
            name = data['Facility']
            mfl_code = data['MFL CODE']
            date_collection = data['Collection Date']
            date_testing = data['Testing date']
            date_dispatch = data['Date Dispatch']
            unique_no = data['CCC NO.']
            age = data['Age']
            sex = data['Sex']
            cd4_count = data['CD4 Count']
            crag = data['Serum Crag']
            reason_for_rejection = data['Rejection reason']
            testing_laboratory = data['Testing Laboratory']
            y = generate_report(request, pdf, name, mfl_code, date_collection, date_testing, date_dispatch,
                                unique_no, age, cd4_count, crag, sex, reason_for_rejection,testing_laboratory, y)

        pdf.save()
        return response


@login_required(login_url='login')
def add_testing_lab(request):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    form = Cd4TestingLabForm(request.POST or None)
    if form.is_valid():
        testing_lab_name = form.cleaned_data['testing_lab_name']

        # Check for duplicate testing_lab_name (case-insensitive)
        existing_lab = Cd4TestingLabs.objects.annotate(lower_name=Lower('testing_lab_name')).filter(
            lower_name=testing_lab_name.lower())
        if existing_lab.exists():
            form.add_error('testing_lab_name', 'A CD4 Testing Lab with this name already exists.')
        else:
            form.save()
            messages.error(request, "Record saved successfully!")
            return redirect("choose_testing_lab")
    context = {
        "form": form,
        "title": f"Add CD4 Testing Lab",
    }
    return render(request, 'lab_pulse/add_cd4_data.html', context)
