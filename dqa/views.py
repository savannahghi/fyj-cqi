from datetime import timezone

from django.forms import modelformset_factory
from django.utils import timezone

import pandas as pd
import plotly.express as px
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Count
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect

# Create your views here.
from django.views.generic import ListView

from dqa.form import DataVerificationForm, PeriodForm, QuarterSelectionForm, YearSelectionForm, FacilitySelectionForm, \
    DQAWorkPlanForm, SystemAssessmentForm, DateSelectionForm
from dqa.models import DataVerification, Period, Indicators, FyjPerformance, DQAWorkPlan, SystemAssessment
from project.models import Facilities
from project.views import bar_chart


def load_system_data(request):
    if request.method == 'POST':
        file = request.FILES['file']
        df = pd.read_excel(file, usecols=[0])
        for index, row in df.iterrows():
            instance = SystemAssessment(description=row[0])
            instance.save()

        # Code to load data from Excel file and save it to MyModel
        return render(request, 'dqa/upload.html', {'success': True})
    else:
        return render(request, 'dqa/upload.html')


def load_data(request):
    if request.method == 'POST':
        file = request.FILES['file']
        # Read the data from the excel file into a pandas DataFrame
        keyword = "perf"
        xls_file = pd.ExcelFile(file)
        sheet_names = [sheet for sheet in xls_file.sheet_names if keyword.upper() in sheet.upper()]
        if sheet_names:
            dfs = pd.read_excel(file, sheet_name=sheet_names)
            df = pd.concat([df.assign(sheet_name=name) for name, df in dfs.items()])
            df = df[list(df.columns[:35])]
            # except:
            #     df = pd.read_excel(file)
            # except:
            #     df = pd.read_csv(file)

            if len(df.columns) == 35:
                df.fillna(0, inplace=True)
                process_cols = [col for col in df.columns if col not in [df.columns[1], df.columns[2]]]
                for col in process_cols:
                    df[col] = df[col].astype(int)
                df[df.columns[1]] = df[df.columns[1]].astype(str)
                df[df.columns[2]] = df[df.columns[2]].astype(str)

                # Iterate over each row in the DataFrame
                for index, row in df.iterrows():
                    performance = FyjPerformance()
                    performance.mfl_code = row[df.columns[0]]
                    performance.facility = row[df.columns[1]]
                    performance.month = row[df.columns[2]]
                    performance.tst_p = row[df.columns[3]]
                    performance.tst_a = row[df.columns[4]]
                    performance.tst_t = row[df.columns[5]]
                    performance.tst_pos_p = row[df.columns[6]]
                    performance.tst_pos_a = row[df.columns[7]]
                    performance.tst_pos_t = row[df.columns[8]]
                    performance.tx_new_p = row[df.columns[9]]
                    performance.tx_new_a = row[df.columns[10]]
                    performance.tx_new_t = row[df.columns[11]]
                    performance.tx_curr_p = row[df.columns[12]]
                    performance.tx_curr_a = row[df.columns[13]]
                    performance.tx_curr_t = row[df.columns[14]]
                    performance.pmtct_stat_d = row[df.columns[15]]
                    performance.pmtct_stat_n = row[df.columns[16]]
                    performance.pmtct_pos = row[df.columns[17]]
                    performance.pmtct_arv = row[df.columns[18]]
                    performance.pmtct_inf_arv = row[df.columns[19]]
                    performance.pmtct_eid = row[df.columns[20]]
                    performance.hei_pos = row[df.columns[21]]
                    performance.hei_pos_art = row[df.columns[22]]
                    performance.prep_new = row[df.columns[23]]
                    performance.gbv_sexual = row[df.columns[24]]
                    performance.gbv_emotional_physical = row[df.columns[25]]
                    performance.kp_anc = row[df.columns[26]]
                    performance.new_pos_anc = row[df.columns[27]]
                    performance.on_haart_anc = row[df.columns[28]]
                    performance.new_on_haart_anc = row[df.columns[29]]
                    performance.pos_l_d = row[df.columns[30]]
                    performance.pos_pnc = row[df.columns[31]]
                    performance.cx_ca = row[df.columns[32]]
                    performance.tb_stat_d = row[df.columns[33]]
                    performance.ipt = row[df.columns[34]]
                    performance.save()
                messages.error(request, f'Data successfully saved in the database!')
                return redirect('show_data_verification')
            else:
                # Notify the user that the data is incorrect
                messages.error(request, f'Kindly confirm if {file} has all data columns.The file has'
                                        f'{len(df.columns)} columns')
                print(df.columns)
                redirect('load_data')
        else:
            # Notify the user that the data already exists
            messages.error(request, f"Uploaded file does not have a sheet name performance.")
            redirect('load_data')

        # return redirect('show_data_verification')
    return render(request, 'dqa/upload.html')


def add_period(request):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    if request.method == 'POST':
        period_form = PeriodForm(request.POST)
        if period_form.is_valid():
            period_form.save()
            return HttpResponseRedirect(request.session['page_from'])
    else:
        period_form = PeriodForm()
    context = {
        "period_form": period_form,
    }
    return render(request, 'dqa/add_period.html', context)


def add_data_verification(request):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    quarter_form = QuarterSelectionForm(request.POST or None)
    year_form = YearSelectionForm(request.POST or None)
    form = DataVerificationForm()

    selected_quarter = "Qtr1"
    selected_year = "2021"
    year_suffix = selected_year[-2:]

    if quarter_form.is_valid() and year_form.is_valid():
        selected_quarter = quarter_form.cleaned_data['quarter']
        request.session['selected_quarter'] = selected_quarter

        selected_year = year_form.cleaned_data['year']
        request.session['selected_year'] = selected_year
        year_suffix = selected_year[-2:]
        quarters = {
            selected_quarter: [
                f'Oct-{year_suffix}', f'Nov-{year_suffix}', f'Dec-{year_suffix}'
            ] if selected_quarter == 'Qtr1' else [
                f'Jan-{year_suffix}', f'Feb-{year_suffix}', f'Mar-{year_suffix}'
            ] if selected_quarter == 'Qtr2' else [
                f'Apr-{year_suffix}', f'May-{year_suffix}', f'Jun-{year_suffix}'
            ] if selected_quarter == 'Qtr3' else [
                f'Jul-{year_suffix}', f'Aug-{year_suffix}', f'Sep-{year_suffix}'
            ]
        }
    else:
        quarters = {
            "Qtr2": [f'January-{year_suffix}', f'Feb-{year_suffix}', f'Mar-{year_suffix}']
        }

    # if request.method == "POST":

    # Check if the request method is POST and the submit_data button was pressed
    if 'submit_data' in request.POST:
        # Create an instance of the DataVerificationForm with the submitted data
        form = DataVerificationForm(request.POST)

        # Check if the form data is valid
        if form.is_valid():
            # Get the selected indicator and facility name from the form data
            selected_indicator = form.cleaned_data['indicator']
            # print("selected_indicator:::::::::::::::::::::::::::::::")
            # print(selected_indicator)
            selected_facility = form.cleaned_data['facility_name']

            # Try to save the form data
            try:
                # Get the instance of the form data but don't commit it yet
                post = form.save(commit=False)

                # Set the user who created the data
                post.created_by = request.user

                # Get or create the period instance
                period, created = Period.objects.get_or_create(quarter=request.session['selected_quarter'],
                                                               year=request.session['selected_year'])

                # Set the quarter_year field of the form data
                post.quarter_year = period

                # Save the form data
                post.save()
                # Get the saved data for the selected quarter, year, and facility name
                data_verification = DataVerification.objects.filter(
                    quarter_year__quarter=request.session['selected_quarter'],
                    quarter_year__year=request.session['selected_year'],
                    facility_name=selected_facility,
                )
                if data_verification:
                    # Check if the 'Number tested Positive aged 15+ years' and 'Number tested Positive aged <15
                    # years' are saved in the database
                    positive_15_plus = data_verification.filter(indicator='Number tested Positive aged 15+ years')
                    positive_less_15 = data_verification.filter(indicator='Number tested Positive aged <15 years')

                    # If both values are saved in the database, calculate the sum
                    if positive_15_plus and positive_less_15:

                        field_1 = 0
                        field_2 = 0
                        field_3 = 0
                        total_source = 0
                        field_5 = 0
                        field_6 = 0
                        field_7 = 0
                        total_731moh = 0
                        field_9 = 0
                        field_10 = 0
                        field_11 = 0
                        total_khis = 0

                        #  returns a new queryset containing all the elements from both querysets.
                        combined_queryset = positive_less_15 | positive_15_plus

                        for data in combined_queryset:
                            field_1 += int(data.field_1)
                            field_2 += int(data.field_2)
                            field_3 += int(data.field_3)
                            total_source += int(data.total_source)
                            field_5 += int(data.field_5)
                            field_6 += int(data.field_6)
                            field_7 += int(data.field_7)
                            total_731moh += int(data.total_731moh)
                            field_9 += int(data.field_9)
                            field_10 += int(data.field_10)
                            field_11 += int(data.field_11)
                            total_khis += int(data.total_khis)

                        try:
                            DataVerification.objects.create(indicator='Number tested Positive _Total',
                                                            field_1=field_1,
                                                            field_2=field_2,
                                                            field_3=field_3,
                                                            total_source=total_source,
                                                            field_5=field_5,
                                                            field_6=field_6,
                                                            field_7=field_7,
                                                            total_731moh=total_731moh,
                                                            field_9=field_9,
                                                            field_10=field_10,
                                                            field_11=field_11,
                                                            total_khis=total_khis,
                                                            created_by=request.user,
                                                            quarter_year=period,
                                                            facility_name=selected_facility)
                        except IntegrityError:
                            # handle the scenario where a duplicate instance is trying to be created
                            # for example, return an error message to the user
                            pass

                    # Check if the 'Number tested Positive aged 15+ years' and 'Number tested Positive aged <15
                    # years' are saved in the database
                    infant_anc = data_verification.filter(indicator='Infant ARV Prophyl_ANC')
                    infant_ld = data_verification.filter(indicator='Infant ARV Prophyl_L&D')
                    infant_pnc = data_verification.filter(indicator='Infant ARV Prophyl_PNC<= 6 weeks')

                    # # If both values are saved in the database, calculate the sum
                    if infant_anc and infant_ld and infant_pnc:

                        field_1 = 0
                        field_2 = 0
                        field_3 = 0
                        total_source = 0
                        field_5 = 0
                        field_6 = 0
                        field_7 = 0
                        total_731moh = 0
                        field_9 = 0
                        field_10 = 0
                        field_11 = 0
                        total_khis = 0
                        #  returns a new queryset containing all the elements from both querysets.
                        combined_queryset = infant_anc | infant_ld | infant_pnc

                        for data in combined_queryset:
                            field_1 += int(data.field_1)
                            field_2 += int(data.field_2)
                            field_3 += int(data.field_3)
                            total_source += int(data.total_source)
                            field_5 += int(data.field_5)
                            field_6 += int(data.field_6)
                            field_7 += int(data.field_7)
                            total_731moh += int(data.total_731moh)
                            field_9 += int(data.field_9)
                            field_10 += int(data.field_10)
                            field_11 += int(data.field_11)
                            total_khis += int(data.total_khis)

                        try:
                            DataVerification.objects.create(indicator='Total Infant prophylaxis',
                                                            field_1=field_1,
                                                            field_2=field_2,
                                                            field_3=field_3,
                                                            total_source=total_source,
                                                            field_5=field_5,
                                                            field_6=field_6,
                                                            field_7=field_7,
                                                            total_731moh=total_731moh,
                                                            field_9=field_9,
                                                            field_10=field_10,
                                                            field_11=field_11,
                                                            total_khis=total_khis,
                                                            created_by=request.user,
                                                            quarter_year=period,
                                                            facility_name=selected_facility)
                        except IntegrityError:
                            # handle the scenario where a duplicate instance is trying to be created
                            # for example, return an error message to the user
                            pass

                    # Check if the 'Number tested Positive aged 15+ years' and 'Number tested Positive aged <15
                    # years' are saved in the database
                    kp_anc = data_verification.filter(indicator='On HAART at 1st ANC')
                    new_art_anc = data_verification.filter(indicator='Start HAART ANC')
                    new_art_ld = data_verification.filter(indicator='Start HAART_L&D')
                    new_art_pnc = data_verification.filter(indicator='Start HAART_PNC<= 6 weeks')

                    # # If both values are saved in the database, calculate the sum
                    if kp_anc and new_art_anc and new_art_ld and new_art_pnc:

                        field_1 = 0
                        field_2 = 0
                        field_3 = 0
                        total_source = 0
                        field_5 = 0
                        field_6 = 0
                        field_7 = 0
                        total_731moh = 0
                        field_9 = 0
                        field_10 = 0
                        field_11 = 0
                        total_khis = 0

                        #  returns a new queryset containing all the elements from both querysets.
                        combined_queryset = kp_anc | new_art_anc | new_art_ld | new_art_pnc

                        for data in combined_queryset:
                            field_1 += int(data.field_1)
                            field_2 += int(data.field_2)
                            field_3 += int(data.field_3)
                            total_source += int(data.total_source)
                            field_5 += int(data.field_5)
                            field_6 += int(data.field_6)
                            field_7 += int(data.field_7)
                            total_731moh += int(data.total_731moh)
                            field_9 += int(data.field_9)
                            field_10 += int(data.field_10)
                            field_11 += int(data.field_11)
                            total_khis += int(data.total_khis)
                        try:
                            DataVerification.objects.create(indicator='Maternal HAART Total ',
                                                            field_1=field_1,
                                                            field_2=field_2,
                                                            field_3=field_3,
                                                            total_source=total_source,
                                                            field_5=field_5,
                                                            field_6=field_6,
                                                            field_7=field_7,
                                                            total_731moh=total_731moh,
                                                            field_9=field_9,
                                                            field_10=field_10,
                                                            field_11=field_11,
                                                            total_khis=total_khis,
                                                            created_by=request.user,
                                                            quarter_year=period,
                                                            facility_name=selected_facility)
                        except IntegrityError:
                            # handle the scenario where a duplicate instance is trying to be created
                            # for example, return an error message to the user
                            pass

                    # Check if the 'Number tested Positive aged 15+ years' and 'Number tested Positive aged <15
                    # years' are saved in the database
                    tx_new_less_15 = data_verification.filter(
                        indicator='Under 15yrs Starting on ART')
                    tx_new_above_15 = data_verification.filter(
                        indicator='Above 15yrs Starting on ART ')

                    # If both values are saved in the database, calculate the sum
                    if tx_new_above_15 and tx_new_less_15:

                        field_1 = 0
                        field_2 = 0
                        field_3 = 0
                        total_source = 0
                        field_5 = 0
                        field_6 = 0
                        field_7 = 0
                        total_731moh = 0
                        field_9 = 0
                        field_10 = 0
                        field_11 = 0
                        total_khis = 0

                        #  returns a new queryset containing all the elements from both querysets.
                        combined_queryset = tx_new_less_15 | tx_new_above_15

                        for data in combined_queryset:
                            field_1 += int(data.field_1)
                            field_2 += int(data.field_2)
                            field_3 += int(data.field_3)
                            total_source += int(data.total_source)
                            field_5 += int(data.field_5)
                            field_6 += int(data.field_6)
                            field_7 += int(data.field_7)
                            total_731moh += int(data.total_731moh)
                            field_9 += int(data.field_9)
                            field_10 += int(data.field_10)
                            field_11 += int(data.field_11)
                            total_khis += int(data.total_khis)

                        try:
                            DataVerification.objects.create(indicator='Number of adults and children starting ART',
                                                            field_1=field_1,
                                                            field_2=field_2,
                                                            field_3=field_3,
                                                            total_source=total_source,
                                                            field_5=field_5,
                                                            field_6=field_6,
                                                            field_7=field_7,
                                                            total_731moh=total_731moh,
                                                            field_9=field_9,
                                                            field_10=field_10,
                                                            field_11=field_11,
                                                            total_khis=total_khis,
                                                            created_by=request.user,
                                                            quarter_year=period,
                                                            facility_name=selected_facility)
                        except IntegrityError:
                            # handle the scenario where a duplicate instance is trying to be created
                            # for example, return an error message to the user
                            pass

                    # Check if the 'Number tested Positive aged 15+ years' and 'Number tested Positive aged <15
                    # years' are saved in the database
                    tx_curr_less_15 = data_verification.filter(
                        indicator='Currently on ART <15Years')
                    tx_curr_above_15 = data_verification.filter(
                        indicator='Currently on ART 15+ years')

                    # If both values are saved in the database, calculate the sum
                    if tx_curr_above_15 and tx_curr_less_15:

                        field_1 = 0
                        field_2 = 0
                        field_3 = 0
                        total_source = 0
                        field_5 = 0
                        field_6 = 0
                        field_7 = 0
                        total_731moh = 0
                        field_9 = 0
                        field_10 = 0
                        field_11 = 0
                        total_khis = 0

                        #  returns a new queryset containing all the elements from both querysets.
                        combined_queryset = tx_curr_less_15 | tx_curr_above_15

                        for data in combined_queryset:
                            field_1 += int(data.field_1)
                            field_2 += int(data.field_2)
                            field_3 += int(data.field_3)
                            total_source += int(data.total_source)
                            field_5 += int(data.field_5)
                            field_6 += int(data.field_6)
                            field_7 += int(data.field_7)
                            total_731moh += int(data.total_731moh)
                            field_9 += int(data.field_9)
                            field_10 += int(data.field_10)
                            field_11 += int(data.field_11)
                            total_khis += int(data.total_khis)

                        try:
                            DataVerification.objects.create(
                                indicator='Number of adults and children Currently on ART',
                                field_1=field_1,
                                field_2=field_2,
                                field_3=field_3,
                                total_source=total_source,
                                field_5=field_5,
                                field_6=field_6,
                                field_7=field_7,
                                total_731moh=total_731moh,
                                field_9=field_9,
                                field_10=field_10,
                                field_11=field_11,
                                total_khis=total_khis,
                                created_by=request.user,
                                quarter_year=period,
                                facility_name=selected_facility)
                        except IntegrityError:
                            # handle the scenario where a duplicate instance is trying to be created
                            # for example, return an error message to the user
                            pass

                    # Check if the 'Number tested Positive aged 15+ years' and 'Number tested Positive aged <15
                    # years' are saved in the database
                    kp_anc_pos = data_verification.filter(indicator='Known Positive at 1st ANC')
                    pos_anc = data_verification.filter(indicator='Positive Results_ANC')
                    pos_ld = data_verification.filter(indicator='Positive Results_L&D')
                    pos_pnc = data_verification.filter(indicator='Positive Results_PNC<=6 weeks')

                    # # If both values are saved in the database, calculate the sum
                    if kp_anc_pos and pos_anc and pos_ld and pos_pnc:

                        field_1 = 0
                        field_2 = 0
                        field_3 = 0
                        total_source = 0
                        field_5 = 0
                        field_6 = 0
                        field_7 = 0
                        total_731moh = 0
                        field_9 = 0
                        field_10 = 0
                        field_11 = 0
                        total_khis = 0

                        #  returns a new queryset containing all the elements from both querysets.
                        combined_queryset = kp_anc_pos | pos_anc | pos_ld | pos_pnc

                        for data in combined_queryset:
                            field_1 += int(data.field_1)
                            field_2 += int(data.field_2)
                            field_3 += int(data.field_3)
                            total_source += int(data.total_source)
                            field_5 += int(data.field_5)
                            field_6 += int(data.field_6)
                            field_7 += int(data.field_7)
                            total_731moh += int(data.total_731moh)
                            field_9 += int(data.field_9)
                            field_10 += int(data.field_10)
                            field_11 += int(data.field_11)
                            total_khis += int(data.total_khis)
                        try:
                            DataVerification.objects.create(indicator='Total Positive (PMTCT)',
                                                            field_1=field_1,
                                                            field_2=field_2,
                                                            field_3=field_3,
                                                            total_source=total_source,
                                                            field_5=field_5,
                                                            field_6=field_6,
                                                            field_7=field_7,
                                                            total_731moh=total_731moh,
                                                            field_9=field_9,
                                                            field_10=field_10,
                                                            field_11=field_11,
                                                            total_khis=total_khis,
                                                            created_by=request.user,
                                                            quarter_year=period,
                                                            facility_name=selected_facility)
                        except IntegrityError:
                            # handle the scenario where a duplicate instance is trying to be created
                            # for example, return an error message to the user
                            pass

                # Redirect the user to the show_data_verification view
                return redirect("show_data_verification")

            # Handle the IntegrityError exception
            except IntegrityError as e:
                # Notify the user that the data already exists
                messages.error(request, f'Data for {selected_facility}, {request.session["selected_quarter"]}, '
                                        f'{selected_indicator} '
                                        f'already exists.')
        # If the form data is not valid
        else:
            # Create a new instance of the DataVerificationForm with the invalid data
            form = DataVerificationForm(request.POST)
    # If the request method is not POST or the submit_data button was not pressed
    else:
        # Create an empty instance of the DataVerificationForm
        form = DataVerificationForm()
        forms = form

    # convert a form into a list to allow slicing
    form = list(form)
    # Create the context for the template
    context = {
        "form": form,
        "forms": forms,
        "quarters": quarters,
        "quarter_form": quarter_form,
        "year_form": year_form,
        "year_suffix": year_suffix
    }

    # Render the template with the context
    return render(request, 'dqa/add_data_verification.html', context)


def show_data_verification(request):
    form = QuarterSelectionForm(request.POST or None)
    year_form = YearSelectionForm(request.POST or None)
    facility_form = FacilitySelectionForm(request.POST or None)

    selected_quarter = "Qtr1"
    selected_year = "2021"
    year_suffix = "21"
    selected_facility = None

    if form.is_valid() and year_form.is_valid() and facility_form.is_valid():
        selected_quarter = form.cleaned_data['quarter']
        selected_year = year_form.cleaned_data['year']
        selected_facility = facility_form.cleaned_data['facilities']
        print("selected_facility.mfl_code:::::::::::::::")
        print(selected_facility.mfl_code)
        year_suffix = selected_year[-2:]
        quarters = {
            selected_quarter: [
                f'Oct-{year_suffix}', f'Nov-{year_suffix}', f'Dec-{year_suffix}', 'Total'
            ] if selected_quarter == 'Qtr1' else [
                f'Jan-{year_suffix}', f'Feb-{year_suffix}', f'Mar-{year_suffix}', 'Total'
            ] if selected_quarter == 'Qtr2' else [
                f'Apr-{year_suffix}', f'May-{year_suffix}', f'Jun-{year_suffix}', 'Total'
            ] if selected_quarter == 'Qtr3' else [
                f'Jul-{year_suffix}', f'Aug-{year_suffix}', f'Sep-{year_suffix}', 'Total'
            ]
        }
    else:
        quarters = {}

    quarter_year = f"{selected_quarter}-{year_suffix}"
    print(selected_quarter)
    print(selected_year)
    print(selected_facility)
    data_verification = DataVerification.objects.filter(quarter_year__quarter=selected_quarter,
                                                        quarter_year__year=selected_year,
                                                        facility_name=selected_facility,
                                                        )
    # Get the Indicator choices in the order specified in the list
    indicator_choices = [choice[0] for choice in Indicators.INDICATOR_CHOICES]
    available_indicators = [i.indicator for i in data_verification]

    prevention = ['PrEP_New', 'Starting_TPT', 'GBV_Sexual violence', 'GBV_Emotional and /Physical Violence',
                  'Cervical Cancer Screening (Women on ART)']
    hts = ['Total tested ', 'Number tested Positive aged <15 years', 'Number tested Positive aged 15+ years',
           'Number tested Positive _Total']
    pmtct = ['Known Positive at 1st ANC', 'Positive Results_ANC', 'On HAART at 1st ANC', 'Start HAART ANC',
             'Infant ARV Prophyl_ANC', 'Positive Results_L&D', 'Start HAART_L&D', 'Infant ARV Prophyl_L&D',
             'Positive Results_PNC<=6 weeks', 'Start HAART_PNC<= 6 weeks', 'Infant ARV Prophyl_PNC<= 6 weeks',
             'Total Positive (PMTCT)', 'Maternal HAART Total ', 'Total Infant prophylaxis']
    care_rx = ['Under 15yrs Starting on ART', 'Above 15yrs Starting on ART ',
               'Number of adults and children starting ART', 'New & Relapse TB_Cases', 'Currently on ART <15Years',
               'Currently on ART 15+ years', 'Number of adults and children Currently on ART']

    program_accessed = []
    for indy in available_indicators:
        if indy in prevention:
            if "Prevention" not in program_accessed:
                program_accessed.append("Prevention")
        elif indy in hts:
            if "HTS" not in program_accessed:
                program_accessed.append("HTS")
        elif indy in pmtct:
            if "PMTCT" not in program_accessed:
                program_accessed.append("PMTCT")
        elif indy in care_rx:
            if "CARE & RX" not in program_accessed:
                program_accessed.append("CARE & RX")
    # Sort the data_verification objects based on the order of the indicator choices
    sorted_data_verification = sorted(data_verification, key=lambda x: indicator_choices.index(x.indicator))
    if data_verification:
        if data_verification.count() < 30:
            # TODO: THIS MESSAGE SHOULD BE ONLY WHEN DATA NEEDED FOR VISUALIZATION IS NOT ENTERED.
            messages.error(request, f"Only {data_verification.count()} DQA indicators for {selected_facility} "
                                    f"({quarter_year}) have been recorded so far. To ensure proper data visualization,"
                                    f" it is important to capture at least 30 indicators.")

    if not data_verification:
        if selected_facility:
            messages.error(request,
                           f"No DQA data was found in the database for {selected_facility} {selected_quarter}-FY{year_suffix}.")

    try:
        fyj_performance = FyjPerformance.objects.filter(mfl_code=selected_facility.mfl_code,
                                                        quarter_year=quarter_year
                                                        )
    except:
        fyj_performance = None
    context = {
        'form': form,
        "year_form": year_form,
        "facility_form": facility_form,
        "quarters": quarters,
        "selected_year": year_suffix,
        'data_verification': sorted_data_verification,
        "program_accessed": program_accessed,
        "fyj_performance": fyj_performance,
    }
    return render(request, 'dqa/show data verification.html', context)


@login_required(login_url='login')
def update_data_verification(request, pk):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    item = DataVerification.objects.get(id=pk)
    if request.method == "POST":
        form = DataVerificationForm(request.POST, instance=item)
        if form.is_valid():
            # Get the selected indicator and facility name from the form data
            selected_indicator = form.cleaned_data['indicator']
            selected_quarter = item.quarter_year.quarter
            selected_quarter_year = item.quarter_year.id
            selected_year = item.quarter_year.year
            print("selected_quarter_year:::::::::::::::::::::::::::::::")
            print(selected_quarter_year)
            selected_facility = form.cleaned_data['facility_name']
            print(selected_facility)

            form.save()
            # Get the saved data for the selected quarter, year, and facility name
            data_verification = DataVerification.objects.filter(
                quarter_year__quarter=selected_quarter,
                quarter_year__year=selected_year,
                facility_name=selected_facility,
            )
            for i in data_verification:
                print(i.indicator)
            if data_verification:
                # Check if the 'Number tested Positive aged 15+ years' and 'Number tested Positive aged <15
                # years' are saved in the database
                positive_15_plus = data_verification.filter(indicator='Number tested Positive aged 15+ years')
                positive_less_15 = data_verification.filter(indicator='Number tested Positive aged <15 years')

                # If both values are saved in the database, calculate the sum
                if positive_15_plus and positive_less_15:

                    field_1 = 0
                    field_2 = 0
                    field_3 = 0
                    total_source = 0
                    field_5 = 0
                    field_6 = 0
                    field_7 = 0
                    total_731moh = 0
                    field_9 = 0
                    field_10 = 0
                    field_11 = 0
                    total_khis = 0

                    #  returns a new queryset containing all the elements from both querysets.
                    combined_queryset = positive_less_15 | positive_15_plus

                    for data in combined_queryset:
                        field_1 += int(data.field_1)
                        field_2 += int(data.field_2)
                        field_3 += int(data.field_3)
                        total_source += int(data.total_source)
                        field_5 += int(data.field_5)
                        field_6 += int(data.field_6)
                        field_7 += int(data.field_7)
                        total_731moh += int(data.total_731moh)
                        field_9 += int(data.field_9)
                        field_10 += int(data.field_10)
                        field_11 += int(data.field_11)
                        total_khis += int(data.total_khis)

                    # try:
                    DataVerification.objects.update_or_create(
                        indicator='Number tested Positive _Total',
                        quarter_year_id=selected_quarter_year,
                        facility_name=selected_facility,
                        defaults={
                            'indicator': 'Number tested Positive _Total',
                            'field_1': field_1,
                            'field_2': field_2,
                            'field_3': field_3,
                            'total_source': total_source,
                            'field_5': field_5,
                            'field_6': field_6,
                            'field_7': field_7,
                            'total_731moh': total_731moh,
                            'field_9': field_9,
                            'field_10': field_10,
                            'field_11': field_11,
                            'total_khis': total_khis,
                            'created_by': request.user,
                        }
                    )

                # Check if the 'Number tested Positive aged 15+ years' and 'Number tested Positive aged <15
                # years' are saved in the database
                infant_anc = data_verification.filter(indicator='Infant ARV Prophyl_ANC')
                infant_ld = data_verification.filter(indicator='Infant ARV Prophyl_L&D')
                infant_pnc = data_verification.filter(indicator='Infant ARV Prophyl_PNC<= 6 weeks')

                # # If both values are saved in the database, calculate the sum
                if infant_anc and infant_ld and infant_pnc:

                    field_1 = 0
                    field_2 = 0
                    field_3 = 0
                    total_source = 0
                    field_5 = 0
                    field_6 = 0
                    field_7 = 0
                    total_731moh = 0
                    field_9 = 0
                    field_10 = 0
                    field_11 = 0
                    total_khis = 0
                    #  returns a new queryset containing all the elements from both querysets.
                    combined_queryset = infant_anc | infant_ld | infant_pnc

                    for data in combined_queryset:
                        field_1 += int(data.field_1)
                        field_2 += int(data.field_2)
                        field_3 += int(data.field_3)
                        total_source += int(data.total_source)
                        field_5 += int(data.field_5)
                        field_6 += int(data.field_6)
                        field_7 += int(data.field_7)
                        total_731moh += int(data.total_731moh)
                        field_9 += int(data.field_9)
                        field_10 += int(data.field_10)
                        field_11 += int(data.field_11)
                        total_khis += int(data.total_khis)

                    DataVerification.objects.update_or_create(
                        indicator='Total Infant prophylaxis',
                        quarter_year_id=selected_quarter_year,
                        facility_name=selected_facility,
                        defaults={
                            'indicator': 'Total Infant prophylaxis',
                            'field_1': field_1,
                            'field_2': field_2,
                            'field_3': field_3,
                            'total_source': total_source,
                            'field_5': field_5,
                            'field_6': field_6,
                            'field_7': field_7,
                            'total_731moh': total_731moh,
                            'field_9': field_9,
                            'field_10': field_10,
                            'field_11': field_11,
                            'total_khis': total_khis,
                            'created_by': request.user,
                        }
                    )

                # Check if the 'Number tested Positive aged 15+ years' and 'Number tested Positive aged <15
                # years' are saved in the database
                kp_anc = data_verification.filter(indicator='On HAART at 1st ANC')
                new_art_anc = data_verification.filter(indicator='Start HAART ANC')
                new_art_ld = data_verification.filter(indicator='Start HAART_L&D')
                new_art_pnc = data_verification.filter(indicator='Start HAART_PNC<= 6 weeks')

                # # If both values are saved in the database, calculate the sum
                if kp_anc and new_art_anc and new_art_ld and new_art_pnc:

                    field_1 = 0
                    field_2 = 0
                    field_3 = 0
                    total_source = 0
                    field_5 = 0
                    field_6 = 0
                    field_7 = 0
                    total_731moh = 0
                    field_9 = 0
                    field_10 = 0
                    field_11 = 0
                    total_khis = 0

                    #  returns a new queryset containing all the elements from both querysets.
                    combined_queryset = kp_anc | new_art_anc | new_art_ld | new_art_pnc

                    for data in combined_queryset:
                        field_1 += int(data.field_1)
                        field_2 += int(data.field_2)
                        field_3 += int(data.field_3)
                        total_source += int(data.total_source)
                        field_5 += int(data.field_5)
                        field_6 += int(data.field_6)
                        field_7 += int(data.field_7)
                        total_731moh += int(data.total_731moh)
                        field_9 += int(data.field_9)
                        field_10 += int(data.field_10)
                        field_11 += int(data.field_11)
                        total_khis += int(data.total_khis)
                    DataVerification.objects.update_or_create(
                        indicator='Maternal HAART Total ',
                        quarter_year_id=selected_quarter_year,
                        facility_name=selected_facility,
                        defaults={
                            'indicator': 'Maternal HAART Total ',
                            'field_1': field_1,
                            'field_2': field_2,
                            'field_3': field_3,
                            'total_source': total_source,
                            'field_5': field_5,
                            'field_6': field_6,
                            'field_7': field_7,
                            'total_731moh': total_731moh,
                            'field_9': field_9,
                            'field_10': field_10,
                            'field_11': field_11,
                            'total_khis': total_khis,
                            'created_by': request.user,
                        }
                    )

                # Check if the 'Number tested Positive aged 15+ years' and 'Number tested Positive aged <15
                # years' are saved in the database
                tx_new_less_15 = data_verification.filter(
                    indicator='Under 15yrs Starting on ART')
                tx_new_above_15 = data_verification.filter(
                    indicator='Above 15yrs Starting on ART ')

                # If both values are saved in the database, calculate the sum
                if tx_new_above_15 and tx_new_less_15:

                    field_1 = 0
                    field_2 = 0
                    field_3 = 0
                    total_source = 0
                    field_5 = 0
                    field_6 = 0
                    field_7 = 0
                    total_731moh = 0
                    field_9 = 0
                    field_10 = 0
                    field_11 = 0
                    total_khis = 0

                    #  returns a new queryset containing all the elements from both querysets.
                    combined_queryset = tx_new_less_15 | tx_new_above_15

                    for data in combined_queryset:
                        field_1 += int(data.field_1)
                        field_2 += int(data.field_2)
                        field_3 += int(data.field_3)
                        total_source += int(data.total_source)
                        field_5 += int(data.field_5)
                        field_6 += int(data.field_6)
                        field_7 += int(data.field_7)
                        total_731moh += int(data.total_731moh)
                        field_9 += int(data.field_9)
                        field_10 += int(data.field_10)
                        field_11 += int(data.field_11)
                        total_khis += int(data.total_khis)

                    DataVerification.objects.update_or_create(
                        indicator='Number of adults and children starting ART',
                        quarter_year_id=selected_quarter_year,
                        facility_name=selected_facility,
                        defaults={
                            'indicator': 'Number of adults and children starting ART',
                            'field_1': field_1,
                            'field_2': field_2,
                            'field_3': field_3,
                            'total_source': total_source,
                            'field_5': field_5,
                            'field_6': field_6,
                            'field_7': field_7,
                            'total_731moh': total_731moh,
                            'field_9': field_9,
                            'field_10': field_10,
                            'field_11': field_11,
                            'total_khis': total_khis,
                            'created_by': request.user,
                        }
                    )

                # Check if the 'Number tested Positive aged 15+ years' and 'Number tested Positive aged <15
                # years' are saved in the database
                tx_curr_less_15 = data_verification.filter(
                    indicator='Currently on ART <15Years')
                tx_curr_above_15 = data_verification.filter(
                    indicator='Currently on ART 15+ years')

                # If both values are saved in the database, calculate the sum
                if tx_curr_above_15 and tx_curr_less_15:

                    field_1 = 0
                    field_2 = 0
                    field_3 = 0
                    total_source = 0
                    field_5 = 0
                    field_6 = 0
                    field_7 = 0
                    total_731moh = 0
                    field_9 = 0
                    field_10 = 0
                    field_11 = 0
                    total_khis = 0

                    #  returns a new queryset containing all the elements from both querysets.
                    combined_queryset = tx_curr_less_15 | tx_curr_above_15

                    for data in combined_queryset:
                        field_1 += int(data.field_1)
                        field_2 += int(data.field_2)
                        field_3 += int(data.field_3)
                        total_source += int(data.total_source)
                        field_5 += int(data.field_5)
                        field_6 += int(data.field_6)
                        field_7 += int(data.field_7)
                        total_731moh += int(data.total_731moh)
                        field_9 += int(data.field_9)
                        field_10 += int(data.field_10)
                        field_11 += int(data.field_11)
                        total_khis += int(data.total_khis)

                    DataVerification.objects.update_or_create(
                        indicator='Number of adults and children Currently on ART',
                        quarter_year_id=selected_quarter_year,
                        facility_name=selected_facility,
                        defaults={
                            'indicator': 'Number of adults and children Currently on ART',
                            'field_1': field_1,
                            'field_2': field_2,
                            'field_3': field_3,
                            'total_source': total_source,
                            'field_5': field_5,
                            'field_6': field_6,
                            'field_7': field_7,
                            'total_731moh': total_731moh,
                            'field_9': field_9,
                            'field_10': field_10,
                            'field_11': field_11,
                            'total_khis': total_khis,
                            'created_by': request.user,
                        }
                    )

                # Check if the 'Number tested Positive aged 15+ years' and 'Number tested Positive aged <15
                # years' are saved in the database
                kp_anc_pos = data_verification.filter(indicator='Known Positive at 1st ANC')
                pos_anc = data_verification.filter(indicator='Positive Results_ANC')
                pos_ld = data_verification.filter(indicator='Positive Results_L&D')
                pos_pnc = data_verification.filter(indicator='Positive Results_PNC<=6 weeks')

                # # If both values are saved in the database, calculate the sum
                if kp_anc_pos and pos_anc and pos_ld and pos_pnc:

                    field_1 = 0
                    field_2 = 0
                    field_3 = 0
                    total_source = 0
                    field_5 = 0
                    field_6 = 0
                    field_7 = 0
                    total_731moh = 0
                    field_9 = 0
                    field_10 = 0
                    field_11 = 0
                    total_khis = 0

                    #  returns a new queryset containing all the elements from both querysets.
                    combined_queryset = kp_anc_pos | pos_anc | pos_ld | pos_pnc

                    for data in combined_queryset:
                        field_1 += int(data.field_1)
                        field_2 += int(data.field_2)
                        field_3 += int(data.field_3)
                        total_source += int(data.total_source)
                        field_5 += int(data.field_5)
                        field_6 += int(data.field_6)
                        field_7 += int(data.field_7)
                        total_731moh += int(data.total_731moh)
                        field_9 += int(data.field_9)
                        field_10 += int(data.field_10)
                        field_11 += int(data.field_11)
                        total_khis += int(data.total_khis)
                    DataVerification.objects.update_or_create(
                        indicator='Total Positive (PMTCT)',
                        quarter_year_id=selected_quarter_year,
                        facility_name=selected_facility,
                        defaults={
                            'indicator': 'Total Positive (PMTCT)',
                            'field_1': field_1,
                            'field_2': field_2,
                            'field_3': field_3,
                            'total_source': total_source,
                            'field_5': field_5,
                            'field_6': field_6,
                            'field_7': field_7,
                            'total_731moh': total_731moh,
                            'field_9': field_9,
                            'field_10': field_10,
                            'field_11': field_11,
                            'total_khis': total_khis,
                            'created_by': request.user,
                        }
                    )
            # TODO: AFTER UPDATE, USER SHOULD BE TAKEN BACK TO THE PAGE THEY WERE FROM WITH DATA ALREADY LOADED
            return HttpResponseRedirect(request.session['page_from'])
    else:
        quarter_year = item.quarter_year.quarter_year
        print("item::::::::::::::::::::")
        print(quarter_year)
        year_suffix = quarter_year[-2:]
        selected_quarter = quarter_year[:4]
        print(selected_quarter)
        print(year_suffix)
        quarters = {
            selected_quarter: [
                f'Oct-{year_suffix}', f'Nov-{year_suffix}', f'Dec-{year_suffix}'
            ] if selected_quarter == 'Qtr1' else [
                f'Jan-{year_suffix}', f'Feb-{year_suffix}', f'Mar-{year_suffix}'
            ] if selected_quarter == 'Qtr2' else [
                f'Apr-{year_suffix}', f'May-{year_suffix}', f'Jun-{year_suffix}'
            ] if selected_quarter == 'Qtr3' else [
                f'Jul-{year_suffix}', f'Aug-{year_suffix}', f'Sep-{year_suffix}'
            ]
        }
        form = DataVerificationForm(instance=item)
    context = {
        "form": form,
        "title": "Update DQA data",
        "quarters": quarters,
    }
    return render(request, 'dqa/update_data_verification.html', context)


@login_required(login_url='login')
def delete_data_verification(request, pk):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    item = DataVerification.objects.get(id=pk)
    if request.method == "POST":
        item.delete()

        return HttpResponseRedirect(request.session['page_from'])
    context = {
        "test_of_changes": item
    }
    return render(request, 'project/delete_test_of_change.html', context)


def bar_chart(df, x_axis, y_axis, title=None):
    # df[x_axis]=df[x_axis].str.split(" ").str[0]

    fig = px.bar(df, x=x_axis, y=y_axis, text=y_axis, title=title, height=200,
                 color=x_axis,
                 category_orders={
                     x_axis: ['Source', 'MOH 731', 'KHIS', 'DATIM']},
                 color_discrete_map={'Source': '#5B9BD5',
                                     'MOH 731': '#ED7D31',
                                     'KHIS': '#A5A5A5',
                                     'DATIM': '#FFC000',
                                     }
                 )

    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)

    fig.update_layout({
        'plot_bgcolor': 'rgba(0, 0, 0, 0)',
        'paper_bgcolor': 'rgba(0, 0, 0, 0)',
    })
    # Set the font size of the x-axis and y-axis labels
    fig.update_layout(
        xaxis=dict(
            tickfont=dict(
                size=7
            ),
            title_font=dict(
                size=7
            )
        ),
        yaxis=dict(
            title_font=dict(
                size=7
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
        ,
        font=dict(
            family="Courier New, monospace",
            size=12,
            color="RebeccaPurple"
        )
    )

    fig.update_layout(showlegend=False)
    return fig.to_html()


def dqa_summary(request):
    form = QuarterSelectionForm(request.POST or None)
    year_form = YearSelectionForm(request.POST or None)
    facility_form = FacilitySelectionForm(request.POST or None)

    selected_quarter = "Qtr1"
    selected_year = "2021"
    year_suffix = "21"
    selected_facility = None

    if form.is_valid() and year_form.is_valid() and facility_form.is_valid():
        selected_quarter = form.cleaned_data['quarter']
        selected_year = year_form.cleaned_data['year']
        selected_facility = facility_form.cleaned_data['facilities']
        print("selected_facility.mfl_code:::::::::::::::")
        print(selected_facility.mfl_code)
        year_suffix = selected_year[-2:]
    #     quarters = {
    #         selected_quarter: [
    #             f'Oct-{year_suffix}', f'Nov-{year_suffix}', f'Dec-{year_suffix}', 'Total'
    #         ] if selected_quarter == 'Qtr1' else [
    #             f'Jan-{year_suffix}', f'Feb-{year_suffix}', f'Mar-{year_suffix}', 'Total'
    #         ] if selected_quarter == 'Qtr2' else [
    #             f'Apr-{year_suffix}', f'May-{year_suffix}', f'Jun-{year_suffix}', 'Total'
    #         ] if selected_quarter == 'Qtr3' else [
    #             f'Jul-{year_suffix}', f'Aug-{year_suffix}', f'Sep-{year_suffix}', 'Total'
    #         ]
    #     }
    # else:
    #     quarters = {}

    quarter_year = f"{selected_quarter}-{year_suffix}"

    dicts = {}
    dqa = None

    if "submit_data" in request.POST:
        dqa = DataVerification.objects.filter(facility_name__mfl_code=selected_facility.mfl_code,
                                              quarter_year__quarter_year=quarter_year)
        fyj_perf = FyjPerformance.objects.filter(mfl_code=selected_facility.mfl_code,
                                                 quarter_year=quarter_year).values()
        if dqa:
            # loop through both models QI_Projects and Program_qi_projects using two separate lists
            dqa_df = [
                {'indicator': x.indicator,
                 'facility': x.facility_name.facilities,
                 'mfl_code': x.facility_name.mfl_code,
                 'Source': x.total_source,
                 "MOH 731": x.total_731moh,
                 "KHIS": x.total_khis,
                 "quarter_year": x.quarter_year.quarter_year,
                 } for x in dqa
            ]
            # Finally, you can create a dataframe from this list of dictionaries.
            dqa_df = pd.DataFrame(dqa_df)
            indicators_to_use = ['Total Infant prophylaxis', 'Maternal HAART Total ', 'Number tested Positive _Total',
                                 'Total Positive (PMTCT)', 'Number of adults and children starting ART', 'Starting_TPT',
                                 'New & Relapse TB_Cases', 'Number of adults and children Currently on ART', 'PrEP_New',
                                 'GBV_Sexual violence', 'GBV_Emotional and /Physical Violence',
                                 'Cervical Cancer Screening (Women on ART)'

                                 ]
            dqa_df = dqa_df[dqa_df['indicator'].isin(indicators_to_use)]

            dqa_df['indicator'] = dqa_df['indicator'].replace("Number of adults and children Currently on ART",
                                                              "Number Current on ART Total")
            dqa_df['indicator'] = dqa_df['indicator'].replace("Number of adults and children starting ART",
                                                              "Number Starting ART Total")
            dqa_df['indicator'] = dqa_df['indicator'].replace("Number tested Positive _Total",
                                                              "Number Tested Positive Total")
            dqa_df['indicator'] = dqa_df['indicator'].replace("Starting_TPT", "Number Starting IPT Total")
            dqa_df['indicator'] = dqa_df['indicator'].replace("PrEP_New", "Number initiated on PrEP")
            dqa_df['indicator'] = dqa_df['indicator'].replace("GBV_Sexual violence", "Gend_GBV Sexual Violence")
            dqa_df['indicator'] = dqa_df['indicator'].replace("GBV_Emotional and /Physical Violence",
                                                              "Gend_GBV_Physical and /Emotional")
            dqa_df['indicator'] = dqa_df['indicator'].replace("Cervical Cancer Screening (Women on ART)",
                                                              "Number Screened for Cervical Cancer")
            dqa_df['indicator'] = dqa_df['indicator'].replace("New & Relapse TB_Cases", "New & Relapse TB cases")
            dqa_df['indicator'] = dqa_df['indicator'].replace('Maternal HAART Total ', "Maternal HAART Total")
            if dqa_df.empty:
                messages.info(request, f"A few DQA indicators for {selected_facility} have been capture but not "
                                       f"enough for data visualization")
        else:
            dqa_df = pd.DataFrame(columns=['indicator', 'facility', 'mfl_code', 'Source', 'MOH 731', 'KHIS',
                                           'quarter_year'])
            messages.info(request, f"No DQA data for {selected_facility}")
        if fyj_perf:
            fyj_perf_df = pd.DataFrame(list(fyj_perf))
            for col in fyj_perf_df.columns[4:-1]:
                fyj_perf_df[col] = fyj_perf_df[col].astype(int)
            fyj_perf_df['Maternal HAART Total'] = fyj_perf_df['on_haart_anc'] + fyj_perf_df['new_on_haart_anc']
            fyj_perf_df['Total Positive (PMTCT)'] = fyj_perf_df['kp_anc'] + fyj_perf_df['new_pos_anc']
            fyj_perf_df['Number Tested Positive Total'] = fyj_perf_df['tst_pos_p'] + fyj_perf_df['tst_pos_a']
            fyj_perf_df['Number Starting ART Total'] = fyj_perf_df['tx_new_p'] + fyj_perf_df['tx_new_a']
            fyj_perf_df['Number Current on ART Total'] = fyj_perf_df['tx_curr_p'] + fyj_perf_df['tx_curr_a']
            fyj_perf_df['Total Infant prophylaxis'] = 0

            fyj_perf_df = fyj_perf_df.rename(
                columns={"prep_new": "Number initiated on PrEP", "gbv_sexual": "Gend_GBV Sexual Violence",
                         "gbv_emotional_physical": "Gend_GBV_Physical and /Emotional",
                         "cx_ca": "Number Screened for Cervical Cancer",
                         "tb_stat_d": "New & Relapse TB cases", "ipt": "Number Starting IPT Total"})

            indicators_to_use_perf = ['mfl_code', 'quarter_year', "Number initiated on PrEP",
                                      'Maternal HAART Total', 'Number Tested Positive Total',
                                      'Total Positive (PMTCT)', 'Number Starting ART Total',
                                      'New & Relapse TB cases', 'Number Starting IPT Total',
                                      'Number Current on ART Total', "Gend_GBV Sexual Violence",
                                      'Gend_GBV_Physical and /Emotional', 'Number Screened for Cervical Cancer',
                                      'Total Infant prophylaxis'

                                      ]
            fyj_perf_df = fyj_perf_df[indicators_to_use_perf]

            fyj_perf_df = pd.melt(fyj_perf_df, id_vars=['mfl_code', 'quarter_year'],
                                  value_vars=list(fyj_perf_df.columns[2:]),
                                  var_name='indicator', value_name='DATIM')
            if dqa_df.empty:
                messages.info(request, f"A few DATIM indicators for {selected_facility} have been capture but not "
                                       f"enough for data visualization")


        else:
            fyj_perf_df = pd.DataFrame(columns=['mfl_code', 'quarter_year', 'indicator', 'DATIM'])
            messages.info(request, f"No DATIM data for {selected_facility}!")

        merged_df = dqa_df.merge(fyj_perf_df, on=['mfl_code', 'quarter_year', 'indicator'], how='right')

        merged_df = merged_df[
            ['mfl_code', 'facility', 'indicator', 'quarter_year', 'Source', 'MOH 731', 'KHIS', 'DATIM']]
        merged_df = pd.melt(merged_df, id_vars=['mfl_code', 'facility', 'indicator', 'quarter_year'],
                            value_vars=list(merged_df.columns[4:]),
                            var_name='data sources', value_name='performance')

        merged_df['performance'] = merged_df['performance'].fillna(0)
        merged_df['performance'] = merged_df['performance'].astype(int)
        # merged_df = merged_df.sort_values('indicator')
        # print(merged_df)
        # dicts = {}
        #
        # for indy in merged_df['indicator'].unique():
        #     merged_df_viz = merged_df[merged_df['indicator'] == indy]
        #     # print(merged_df_viz)
        #     quarter = merged_df_viz['quarter_year'].unique()[0]
        #     dicts[f"{indy} ({quarter})"] = bar_chart(merged_df_viz, "data sources", "performance")

        # Define a new DataFrame object by grouping the 'merged_df' DataFrame by 'indicator' column and calculating
        # the standard deviation of 'performance' column. The idea is to have the indicator with the greatest
        # disparities in the performance column come first.
        grouped = merged_df.groupby("indicator")["performance"].std().reset_index()
        # Sort the 'grouped' DataFrame in descending order based on 'performance' column
        grouped = grouped.sort_values("performance", ascending=False)
        # Extract the 'indicator' column from the sorted 'grouped' DataFrame and assign it to a new variable called
        # 'grouped'
        grouped = grouped["indicator"]
        # Create an empty dictionary object to store the bar charts for each 'indicator' in 'grouped'
        dicts = {}
        # Loop through each 'indicator' in 'grouped'
        for indy in grouped:
            # Create a new DataFrame object called 'merged_df_viz' containing only the rows where 'indicator' column
            # matches the current 'indy' value
            merged_df_viz = merged_df[merged_df['indicator'] == indy]
            # Extract the unique value from the 'quarter_year' column in 'merged_df_viz' and assign it to a variable
            # called 'quarter'
            quarter = merged_df_viz['quarter_year'].unique()[0]
            # Create a new key-value pair in the 'dicts' dictionary, where the key is a string containing the 'indy'
            # value and the 'quarter' value, and the value is a bar chart object created using the 'merged_df_viz'
            # DataFrame
            dicts[f"{indy} ({quarter})"] = bar_chart(merged_df_viz, "data sources", "performance")

    context = {
        "dicts": dicts,
        "dqa": dqa,
        'form': form,
        "year_form": year_form,
        "facility_form": facility_form,
        "selected_facility": selected_facility,
        "quarter_year": quarter_year,
    }
    return render(request, 'dqa/dqa_summary.html', context)


def dqa_work_plan_create(request, pk, quarter_year):
    facility = DataVerification.objects.filter(facility_name_id=pk,
                                               quarter_year__quarter_year=quarter_year
                                               ).order_by('-date_modified').first()
    today = timezone.now().date()

    if request.method == 'POST':
        form = DQAWorkPlanForm(request.POST)
        if form.is_valid():
            dqa_work_plan = form.save(commit=False)
            dqa_work_plan.facility_name = facility.facility_name
            dqa_work_plan.quarter_year = facility.quarter_year
            dqa_work_plan.created_by = request.user
            dqa_work_plan.progress = (dqa_work_plan.due_complete_by - today).days
            dqa_work_plan.timeframe = (dqa_work_plan.due_complete_by - dqa_work_plan.dqa_date).days
            dqa_work_plan.save()
            return redirect('show_dqa_work_plan')
    else:
        form = DQAWorkPlanForm()

    context = {
        'form': form,
        'title': 'Add DQA Work Plan',
        'facility': facility.facility_name,
        'mfl_code': facility.facility_name.mfl_code,
        'date_modified': facility.date_modified,
    }

    return render(request, 'project/add_qi_manager.html', context)


def show_dqa_work_plan(request):
    form = QuarterSelectionForm(request.POST or None)
    year_form = YearSelectionForm(request.POST or None)
    facility_form = FacilitySelectionForm(request.POST or None)

    selected_quarter = "Qtr1"
    selected_year = "2021"
    year_suffix = "21"
    selected_facility = None
    work_plan = None

    if form.is_valid() and year_form.is_valid() and facility_form.is_valid():
        selected_quarter = form.cleaned_data['quarter']
        selected_year = year_form.cleaned_data['year']
        selected_facility = facility_form.cleaned_data['facilities']
        year_suffix = selected_year[-2:]
        quarter_year = f"{selected_quarter}-{year_suffix}"

    if "submit_data" in request.POST:
        work_plan = DQAWorkPlan.objects.filter(facility_name_id=selected_facility.id,
                                               quarter_year__quarter_year=quarter_year
                                               )
        if not work_plan:
            messages.error(request, f"No work plan for {selected_facility} ({quarter_year}) found.")
    context = {
        "work_plan": work_plan,
        'form': form,
        "year_form": year_form,
        "facility_form": facility_form,
    }
    return render(request, 'dqa/dqa_work_plan_list.html', context)


# @login_required(login_url='login')
# def add_dqa_action_plan(request, pk):
#     # facility_project = QI_Projects.objects.get(id=pk)
#
#     try:
#         facility_project = get_object_or_404(QI_Projects, id=pk)
#         qi_project = QI_Projects.objects.get(id=pk)
#         facility = facility_project.facility_name
#         qi_team_members = Qi_team_members.objects.filter(qi_project=facility_project)
#         level = "facility"
#     except:
#         facility_project = get_object_or_404(Program_qi_projects, id=pk)
#         qi_project = Program_qi_projects.objects.get(id=pk)
#         facility = facility_project.program
#         qi_team_members = Qi_team_members.objects.filter(program_qi_project=facility_project)
#         level = "program"
#
#     qi_projects = facility_project
#
#     today = timezone.now().date()
#     # check the page user is from
#     if request.method == "GET":
#         request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
#
#     if request.method == "POST":
#         form = ActionPlanForm(facility, qi_projects, request.POST)
#         if form.is_valid():
#             # form.save()
#             post = form.save(commit=False)
#             if level == "facility":
#                 post.facility = Facilities.objects.get(id=facility_project.facility_name_id)
#                 post.qi_project = qi_project
#                 post.program = None
#             elif level == "program":
#                 post.facility = None
#                 post.program = Program.objects.get(id=facility_project.program_id)
#                 post.program_qi_project = qi_project
#
#             post.created_by = request.user
#             #
#             post.progress = (post.due_date - today).days
#             post.timeframe = (post.due_date - post.start_date).days
#             post.save()
#
#             # Save many-to-many relationships
#             form.save_m2m()
#             # redirect back to the page the user was from after saving the form
#             return HttpResponseRedirect(request.session['page_from'])
#     else:
#         form = ActionPlanForm(facility, qi_projects)
#     context = {"form": form,
#                "title": "Add Action Plan",
#                "qi_team_members": qi_team_members,
#                "qi_project": qi_project,
#                "level": level
#                }
#     return render(request, "project/add_qi_manager.html", context)


def add_system_verification(request):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    quarter_form = QuarterSelectionForm(request.POST or None)
    year_form = YearSelectionForm(request.POST or None)
    form = SystemAssessmentForm()
    system_assessments = SystemAssessment.objects.all()
    facility_form = FacilitySelectionForm(request.POST or None)
    date_form = DateSelectionForm(request.POST or None)
    SystemAssessmentFormSet = modelformset_factory(SystemAssessment, fields=(
        'dropdown_option', 'auditor_note','facility_name',
        'supporting_documentation_required'), extra=0)




    selected_quarter = "Qtr1"
    selected_year = "2021"
    year_suffix = selected_year[-2:]

    if quarter_form.is_valid() and year_form.is_valid():
        selected_quarter = quarter_form.cleaned_data['quarter']
        request.session['selected_quarter'] = selected_quarter

        selected_year = year_form.cleaned_data['year']
        request.session['selected_year'] = selected_year
        year_suffix = selected_year[-2:]
        quarters = {
            selected_quarter: [
                f'Oct-{year_suffix}', f'Nov-{year_suffix}', f'Dec-{year_suffix}'
            ] if selected_quarter == 'Qtr1' else [
                f'Jan-{year_suffix}', f'Feb-{year_suffix}', f'Mar-{year_suffix}'
            ] if selected_quarter == 'Qtr2' else [
                f'Apr-{year_suffix}', f'May-{year_suffix}', f'Jun-{year_suffix}'
            ] if selected_quarter == 'Qtr3' else [
                f'Jul-{year_suffix}', f'Aug-{year_suffix}', f'Sep-{year_suffix}'
            ]
        }
    else:
        quarters = {
            "Qtr2": [f'January-{year_suffix}', f'Feb-{year_suffix}', f'Mar-{year_suffix}']
        }

    # if request.method == "POST":

    # Check if the request method is POST and the submit_data button was pressed
    if 'submit_data' in request.POST:
        # Create an instance of the DataVerificationForm with the submitted data
        # form = SystemAssessmentForm(request.POST)
        form = SystemAssessmentFormSet(request.POST)
        form.save()

    # If the request method is not POST or the submit_data button was not pressed
    else:
        # Create an empty instance of the DataVerificationForm
        # form = SystemAssessmentForm()
        formset = SystemAssessmentFormSet(queryset=system_assessments)
        forms = formset

    # convert a form into a list to allow slicing
    form = list(form)
    # Create the context for the template
    context = {
        "form": form,
        "forms": formset,
        "quarters": quarters,
        "quarter_form": quarter_form,
        "year_form": year_form,
        "year_suffix": year_suffix,
        "system_assessments": system_assessments,
        "facility_form":facility_form,
        "date_form":date_form,
    }

    # Render the template with the context
    return render(request, 'dqa/add_system_assessment.html', context)


