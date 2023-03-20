import ast

import matplotlib
from django.core.exceptions import ValidationError
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.platypus import TableStyle, Table, Paragraph

matplotlib.use('Agg')
matplotlib.rcParams['agg.path.chunksize'] = 10000

from io import BytesIO
import json
from datetime import timezone, datetime
import seaborn as sns
import matplotlib.pyplot as plt

from django.db.models import Case, When, IntegerField
from django.forms import modelformset_factory
from django.urls import reverse
from django.utils import timezone

import pandas as pd
from django.views import View
from plotly.offline import plot
import plotly.express as px
import plotly.graph_objs as go
import plotly.offline as opy

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction, DatabaseError
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render, redirect

# Create your views here.
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from apps.dqa.form import DataVerificationForm, PeriodForm, QuarterSelectionForm, YearSelectionForm, \
    FacilitySelectionForm, DQAWorkPlanForm, SystemAssessmentForm, DateSelectionForm, AuditTeamForm
from apps.dqa.models import DataVerification, Period, Indicators, FyjPerformance, DQAWorkPlan, SystemAssessment, \
    AuditTeam
from apps.cqi.views import bar_chart
from apps.cqi.models import Facilities


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
        # Read the data from the Excel file into a pandas DataFrame
        keyword = "perf"
        xls_file = pd.ExcelFile(file)
        sheet_names = [sheet for sheet in xls_file.sheet_names if keyword.upper() in sheet.upper()]
        if sheet_names:
            dfs = pd.read_excel(file, sheet_name=sheet_names)
            df = pd.concat([df.assign(sheet_name=name) for name, df in dfs.items()])
            df = df[list(df.columns[:35])]
            try:
                with transaction.atomic():
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
            except IntegrityError:
                quarter_year = row[df.columns[2]]
                messages.error(request, f"Data for  {quarter_year} already exists.")

            else:
                # Notify the user that the data is incorrect
                messages.error(request, f'Kindly confirm if {file} has all data columns.The file has'
                                        f'{len(df.columns)} columns')
                redirect('load_data')
        else:
            # Notify the user that the data already exists
            messages.error(request, f"Uploaded file does not have a sheet named 'performance'.")
            redirect('load_data')

        # return redirect('show_data_verification')
    return render(request, 'dqa/upload.html')


def calculate_averages(system_assessments, description_list):
    list_of_projects = [
        {'description': x.description,
         'calculations': x.calculations,
         'quarter_id': x.quarter_year_id,
         'facility_id': x.facility_name_id,
         } for x in system_assessments
    ]
    # convert data from database to a dataframe
    df = pd.DataFrame(list_of_projects)

    # Slice the dataframe by description
    df_list = [df[df['description'].isin(description_list[:5])],
               df[df['description'].isin(description_list[5:12])],
               df[df['description'].isin(description_list[12:17])],
               df[df['description'].isin(description_list[17:21])],
               df[df['description'].isin(description_list[21:])]]

    # Calculate the average of the calculations column for each dataframe
    values = []
    expected_counts = []
    for i in range(len(df_list)):
        cal_values = df_list[i]['calculations'].dropna()
        num_values = cal_values.count()
        avg_calc = cal_values.mean()
        values.append(round(avg_calc, 2))
        expected_counts.append(num_values * 3)

    keys = ["average_calculations_5", "average_calculations_5_12", "average_calculations_12_17",
            "average_calculations_17_21", "average_calculations_21_25"]

    average_dictionary = dict(zip(keys, values))
    expected_counts_dictionary = dict(zip(keys, expected_counts))
    return average_dictionary, expected_counts_dictionary


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
    forms = DataVerificationForm()
    selected_year = "2021"
    year_suffix = selected_year[-2:]

    if quarter_form.is_valid() and year_form.is_valid():
        selected_quarter = quarter_form.cleaned_data['quarter']
        request.session['selected_quarter'] = selected_quarter

        selected_year = year_form.cleaned_data['year']
        request.session['selected_year'] = selected_year

        selected_year = int(selected_year)
        if selected_quarter == "Qtr1":
            selected_year -= 1
            year_suffix = str(selected_year)[-2:]
        else:
            year_suffix = str(selected_year)[-2:]
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
            selected_facility = form.cleaned_data['facility_name']

            # Try to save the form data
            try:
                with transaction.atomic():
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
                    # return redirect("show_data_verification")
                    return HttpResponseRedirect(request.path_info)

            # Handle the IntegrityError exception
            except IntegrityError as e:
                # Notify the user that the data already exists
                messages.error(request, f'Data for {selected_facility}, {request.session["selected_quarter"]}, '
                                        f'{selected_indicator} '
                                        f'already exists!')
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
    selected_facility = None
    request.session['selected_year_'] = ""

    if form.is_valid() and year_form.is_valid() and facility_form.is_valid():
        selected_quarter = form.cleaned_data['quarter']
        selected_year = year_form.cleaned_data['year']
        request.session['selected_year_'] = selected_year
        selected_facility = facility_form.cleaned_data['name']
        year_suffix = selected_year[-2:]
        selected_year = int(selected_year)
        if selected_quarter == "Qtr1":
            selected_year -= 1
            year_suffix = str(selected_year)[-2:]
        else:
            year_suffix = str(selected_year)[-2:]
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
    selected_year = request.session['selected_year_']
    year_suffix = selected_year[-2:]
    quarter_year = f"{selected_quarter}-{year_suffix}"
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
    quarters = None
    item = DataVerification.objects.get(id=pk)
    if request.method == "POST":
        form = DataVerificationForm(request.POST, instance=item)
        if form.is_valid():
            # Get the selected indicator and facility name from the form data
            selected_indicator = form.cleaned_data['indicator']
            selected_quarter = item.quarter_year.quarter
            selected_quarter_year = item.quarter_year.id
            selected_year = item.quarter_year.year
            selected_facility = form.cleaned_data['facility_name']

            form.save()
            # Get the saved data for the selected quarter, year, and facility name
            data_verification = DataVerification.objects.filter(
                quarter_year__quarter=selected_quarter,
                quarter_year__year=selected_year,
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
        year_suffix = quarter_year[-2:]
        selected_quarter = quarter_year[:4]
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
    return plot(fig, include_plotlyjs=False, output_type="div")


def bar_chart_report(df, x_axis, y_axis,indy=None, quarter=None):
    image = None
    fig, ax = plt.subplots(figsize=(8, 5))

    sns.barplot(x=x_axis, y=y_axis, data=df, palette={
        'Source': '#5B9BD5',
        'MOH 731': '#ED7D31',
        'KHIS': '#A5A5A5',
        'DATIM': '#FFC000',
    })

    ax.set_xlabel(x_axis, fontsize=10)
    ax.set_ylabel(y_axis, fontsize=10)

    if indy is not None:
        ax.set_title(f"{indy} {quarter}", fontsize=14, fontweight='bold')

    ax.tick_params(labelsize=10)
    sns.despine()

    plt.tight_layout()

    # Add labels to the bars
    for i, val in enumerate(df[y_axis]):
        ax.text(i, val, int(val), horizontalalignment='center', fontsize=10, fontweight='bold')

    if indy is not None:
        # # create the full path for the file
        # file_path = os.path.join(settings.MEDIA_ROOT, f'{indy}.png')
        # facility_mfl = selected_facility.mfl_code
        # date_str = datetime.now().strftime("%Y-%m-%d")  # Get current date and time as string
        # chart_name = f"{indy}_{facility_mfl}_{date_str}.png"  # Combine facility name, date/time, and random UUID to create a unique file name
        # file_path = os.path.join(settings.MEDIA_ROOT, chart_name)  # create the full path for the file
        #
        # # Create the media directory if it doesn't exist
        # if not os.path.exists(settings.MEDIA_ROOT):
        #     os.makedirs(settings.MEDIA_ROOT)
        #
        # # save the file
        # fig.savefig(file_path, dpi=150, bbox_inches='tight', pad_inches=0.2)
        # Draw the chart onto the PDF using ReportLab

        # Save the PNG image to a buffer instead of a file
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight', pad_inches=0.2)
        buffer.seek(0)
        image = ImageReader(buffer)
        # pdf.drawImage(image=image, x=100, y=100, width=300, height=300)
        plt.close()  # close the current figure

    # return fig, chart_name
    return image


# def bar_chart_report(df, x_axis, y_axis, indy=None, quarter=None):
#     fig, ax = plt.subplots(figsize=(8, 5))
#
#     sns.barplot(x=x_axis, y=y_axis, data=df, palette={
#         'Source': '#5B9BD5',
#         'MOH 731': '#ED7D31',
#         'KHIS': '#A5A5A5',
#         'DATIM': '#FFC000',
#     })
#
#     ax.set_xlabel(x_axis, fontsize=10)
#     ax.set_ylabel(y_axis, fontsize=10)
#
#     if indy is not None:
#         ax.set_title(f"{indy} {quarter}", fontsize=14, fontweight='bold')
#
#     ax.tick_params(labelsize=10)
#     # Manually set the visibility of spines to False
#     for spine in ax.spines.values():
#         spine.set_visible(False)
#
#     plt.tight_layout()
#
#     # Add labels to the bars
#     for i, val in enumerate(df[y_axis]):
#         ax.text(i, val, int(val), horizontalalignment='center', fontsize=10, fontweight='bold')
#
#     # Draw the figure before saving
#     fig.canvas.draw()
#
#     # Save the figure as a bytes object instead of a file
#     bytes_io = BytesIO()
#     fig.savefig(bytes_io, format='png', dpi=150, bbox_inches='tight', pad_inches=0.2)
#     bytes_io.seek(0)
#     image_bytes = bytes_io.getvalue()
#
#     # Close the figure to free up memory
#     plt.close(fig)
#
#     return image_bytes


# def generate_pdf(request):
#     # Get data for rendering the HTML template here...
#
#     # Render the HTML template
#     template = get_template('my_template.html')
#     html = template.render({
#         'dqa': dqa,
#         'average_dictionary': average_dictionary,
#         'quarter_year': quarter_year,
#         'dicts': dicts,
#         'selected_facility': selected_facility,
#     })
#
#     # Generate PDF using ReportLab
#     pdf_file = BytesIO()
#     pisa.CreatePDF(BytesIO(html.encode("UTF-8")), pdf_file)
#
#     # Create a response object with the PDF file
#     response = HttpResponse(content_type='application/pdf')
#     response['Content-Disposition'] = 'attachment; filename="my_report.pdf"'
#     response.write(pdf_file.getvalue())
#
#     return response


def polar_chart_report(df, selected_facility, quarter_year):
    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111, projection='polar')
    sns.lineplot(x='category', y='value', data=df, sort=False, linewidth=2, color='green', marker='o',
                 markersize=10, ax=ax)
    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)
    ax.set_ylim(0, 5)

    plt.title(f"System Assessment Averages for {selected_facility} ({quarter_year})", y=1.15, fontsize=12)
    plt.tight_layout()

    # Draw the figure before saving
    fig.canvas.draw()

    # Save the PNG image to a buffer instead of a file
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight', pad_inches=0.2)
    buffer.seek(0)
    png_data = buffer.read()
    buffer.close()

    return png_data


def add_footer(canvas, user):
    # draw the footer text at the bottom of the page
    canvas.setFont("Helvetica", 4)
    canvas.setFillColor(colors.grey)
    canvas.drawString(letter[0] / 2, 0.5 * inch, f"Report generated by : {user}    Time: {datetime.now()}")


def create_polar(df, pdf, selected_facility, quarter_year):
    fig = plt.figure(figsize=(8, 8))
    ax = fig.add_subplot(111, projection='polar')
    sns.lineplot(x='category', y='value', data=df, sort=False, linewidth=2, color='green', marker='o',
                 markersize=10, ax=ax)
    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)
    ax.set_ylim(0, 5)

    plt.title(f"System Assessment Averages for {selected_facility} ({quarter_year})", y=1.15, fontsize=12)
    plt.tight_layout()

    # Draw the chart onto the PDF using ReportLab
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight', pad_inches=0.2)
    buffer.seek(0)
    image = ImageReader(buffer)
    pdf.drawImage(image=image, x=100, y=100, width=300, height=300)
    plt.close()  # close the current figure


class GeneratePDF(View):
    def get(self, request):
        # Retrieve the selected facility from the session and convert it back to a dictionary
        selected_facility_json = request.session.get('selected_facility')
        selected_facility_dict = json.loads(selected_facility_json)

        # Create a Facility object from the dictionary
        selected_facility = Facilities.objects.get(id=selected_facility_dict['id'])

        quarter_year = request.session['quarter_year']

        description_list = [
            "There is a documented structure/chart that clearly identifies positions that have data management "
            "responsibilities at the Facility.",
            "Positions dedicated to M&E and data management systems in the facility are filled.",
            "There is a training plan which includes staff involved in data-collection and reporting at all levels in the "
            "reporting process.",
            "All relevant staff have received training on the data management processes and tools.",
            "There is a designated staff responsible for reviewing the quality of data (i.e., accuracy, completeness and "
            "timeliness) before submission to the Sub County.",
            "The facility has data quality SOPs for monthly reporting processes and quality checks",
            "The facility conducts internal data quality checks and validation before submission of reports",
            "The facility has conducted a data quality audit in the last 6 months",
            "There is a documented data improvement action plan? Verify by seeing",
            "Feedback is systematically provided to the facility on the quality of their reporting (i.e., accuracy, "
            "completeness and timeliness).",
            "The facility regularly reviews data to inform decision making (Ask for evidence e.g.meeting minutes, "
            "MDT feedback data template",
            "The facility is aware of their yearly targets and are monitoring monthly performance using wall charts",
            "The facility has been provided with indicator definitions reference guides for both MOH and MER 2.6 "
            "indicators.",
            "The facility staff are very clear on what they are supposed to report on.",
            "The facility staff are very clear on how (e.g., in what specific format) reports are to be submitted.",
            "The facility staff are very clear on to whom the reports should be submitted.",
            "The facility staff are very clear on when the reports are due.",
            "The facility has the latest versions of source documents (registers) and aggregation tool (MOH 731)",
            "Clear instructions have been provided to the facility on how to complete the data collection and reporting "
            "forms/tools.",
            "The facility has the revised HTS register in all service delivery points and a clear inventory is available "
            "detailing the number of HTS registers in use by service delivery point",
            "HIV client files are well organised and stored in a secure location",
            "Do you use your EMR to generate reports?",
            "There is a clearly documented and actively implemented database administration procedure in place. This "
            "includes backup/recovery procedures, security admininstration, and user administration.",
            "The facility carries out daily back up of EMR data (Ask to see the back up for the day of the DQA)",
            "The facility has conducted an RDQA of the EMR system in the last 3 months with documented action points,"
            "What is your main challenge regarding data management and reporting?"]

        dicts = {}
        dqa = None
        average_dictionary = None
        df = None

        name = None
        mfl_code = None
        date = None
        site_avg = None
        polar_chart = ""
        charts = []

        # if "submit_data" in request.POST:
        dqa = DataVerification.objects.filter(facility_name__mfl_code=selected_facility.mfl_code,
                                              quarter_year__quarter_year=quarter_year)
        fyj_perf = FyjPerformance.objects.filter(mfl_code=selected_facility.mfl_code,
                                                 quarter_year=quarter_year).values()
        if dqa:
            # loop through both models QI_Projects and Program_qi_projects using two separate lists
            dqa_df = [
                {'indicator': x.indicator,
                 'facility': x.facility_name.name,
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
                                                              "Gend_GBV_Physical and Emotional")
            dqa_df['indicator'] = dqa_df['indicator'].replace("Cervical Cancer Screening (Women on ART)",
                                                              "Number Screened for Cervical Cancer")
            dqa_df['indicator'] = dqa_df['indicator'].replace("New & Relapse TB_Cases", "New & Relapse TB cases")
            dqa_df['indicator'] = dqa_df['indicator'].replace('Maternal HAART Total ', "Maternal HAART Total")
            if dqa_df.empty:
                messages.info(request, f"A few DQA indicators for {selected_facility} have been capture but not "
                                       f"enough for data visualization")
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
                             "gbv_emotional_physical": "Gend_GBV_Physical and Emotional",
                             "cx_ca": "Number Screened for Cervical Cancer",
                             "tb_stat_d": "New & Relapse TB cases", "ipt": "Number Starting IPT Total"})

                indicators_to_use_perf = ['mfl_code', 'quarter_year', "Number initiated on PrEP",
                                          'Maternal HAART Total', 'Number Tested Positive Total',
                                          'Total Positive (PMTCT)', 'Number Starting ART Total',
                                          'New & Relapse TB cases', 'Number Starting IPT Total',
                                          'Number Current on ART Total', "Gend_GBV Sexual Violence",
                                          'Gend_GBV_Physical and Emotional', 'Number Screened for Cervical Cancer',
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
            charts = []
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
                # fig, chart_name = bar_chart_report(merged_df_viz, "data sources", "performance", selected_facility,
                #                                    indy=indy, quarter=quarter)
                image = bar_chart_report(merged_df_viz, "data sources", "performance", indy=indy, quarter=quarter)
                charts.append(image)

            # retrieves a queryset of SystemAssessment objects that have the specified quarter_year and facility_name.
            system_assessments = SystemAssessment.objects.filter(
                quarter_year__quarter_year=quarter_year,
                facility_name=selected_facility
            )
            # if system_assessments:
            average_dictionary, expected_counts_dictionary = calculate_averages(system_assessments,
                                                                                description_list)
            site_avg = round(sum(average_dictionary.values()) / len(average_dictionary), 2)

            data = [
                {
                    'category': 'M&E Structure, Functions and Capabilities',
                    'value': average_dictionary['average_calculations_5']
                },
                {
                    'category': 'Data Management Processes',
                    'value': average_dictionary['average_calculations_5_12']
                },
                {
                    'category': 'Indicator Definitions and Reporting Guidelines',
                    'value': average_dictionary['average_calculations_12_17']
                },
                {
                    'category': 'Data-collection and Reporting Forms / Tools',
                    'value': average_dictionary['average_calculations_17_21']
                },
                {
                    'category': 'EMR Systems',
                    'value': average_dictionary['average_calculations_21_25']
                }
            ]
            df = pd.DataFrame(data)
            # fig = plt.figure(figsize=(8, 8))
            # ax = fig.add_subplot(111, projection='polar')
            # sns.lineplot(x='category', y='value', data=df, sort=False, linewidth=2, color='green', marker='o',
            #              markersize=10, ax=ax)
            # ax.set_theta_zero_location('N')
            # ax.set_theta_direction(-1)
            # ax.set_ylim(0, 5)
            #
            # plt.title(f"System Assessment Averages for {selected_facility} ({quarter_year})", y=1.15, fontsize=12)
            # plt.tight_layout()
            #
            # facility_mfl = selected_facility.mfl_code
            # date_str = datetime.now().strftime("%Y-%m-%d")  # Get current date and time as string
            # polar_chart = f"polar_chart_{facility_mfl}_{date_str}.png"
            # file_path = os.path.join(settings.MEDIA_ROOT, polar_chart)  # create the full path for the file
            #
            # # save the file
            # plt.savefig(file_path, dpi=150, bbox_inches='tight', pad_inches=0.2)
            # plt.close()  # close the current figure

        # Create a new PDF object using ReportLab
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'filename="dqa summary.pdf"'
        pdf = canvas.Canvas(response, pagesize=letter)

        # Write some content to the PDF
        for data in dqa:
            name = data.facility_name.name
            mfl_code = data.facility_name.mfl_code
            # date = data.date_modified.strftime('%B %d, %Y, %I:%M %p')
            # Convert datetime object to the client's timezone
            client_timezone = timezone.get_current_timezone()
            date = data.date_modified.astimezone(client_timezone).strftime('%B %d, %Y, %I:%M %p')

        period = quarter_year
        avg_me = average_dictionary['average_calculations_5']
        avg_data_mnx = average_dictionary['average_calculations_5_12']
        avg_indicator = average_dictionary['average_calculations_12_17']
        avg_data_collect = average_dictionary['average_calculations_17_21']
        avg_emr = average_dictionary['average_calculations_21_25']

        # change page size
        pdf.translate(inch, inch)
        pdf.setFont("Courier-Bold", 18)
        # write the facility name in the top left corner of the page
        pdf.drawString(180, 650, "DQA SUMMARY")
        y = 640
        pdf.line(x1=10, y1=y, x2=500, y2=y)
        # facility info
        pdf.setFont("Helvetica", 12)
        pdf.drawString(10, 620, f"Facility: {name}")
        pdf.drawString(10, 600, f"MFL Code: {mfl_code}")
        pdf.drawString(10, 580, f"Date Of Audit: {date}")
        pdf.drawString(10, 560, f"Review Period: {period}")
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(310, 625, f"COLOR CODE")
        pdf.drawString(420, 625, f"RANGE")
        # rectangles
        pdf.rect(x=300, y=550, width=200, height=70, stroke=1, fill=0)
        pdf.setFillColor(colors.green)
        pdf.rect(x=300, y=550, width=100, height=70, stroke=1, fill=1)
        pdf.setFillColor(colors.yellow)
        pdf.rect(x=300, y=550, width=100, height=46, stroke=1, fill=1)
        pdf.rect(x=300, y=550, width=200, height=46, stroke=1, fill=0)
        pdf.setFillColor(colors.red)
        pdf.rect(x=300, y=550, width=100, height=23, stroke=1, fill=1)
        pdf.rect(x=300, y=550, width=200, height=23, stroke=1, fill=0)

        # color codes
        pdf.setFont("Helvetica", 12)
        pdf.setFillColor(colors.black)
        pdf.drawString(310, 600, f"GREEN")
        pdf.drawString(310, 580, f"YELLOW")
        pdf.drawString(310, 560, f"RED")
        # Range
        pdf.drawString(420, 600, f">= 2.5")
        pdf.drawString(420, 580, f">= 1.5 - < 2.5")
        pdf.drawString(420, 560, f"< 1.5")
        # y=540
        # pdf.line(x1=10,y1=y,x2=500,y2=y)
        pdf.drawString(180, 520, "SYSTEMS ASSESSMENT RESULTS")

        # rectangles
        pdf.rect(x=10, y=440, width=490, height=70, stroke=1, fill=0)
        pdf.rect(x=10, y=440, width=70, height=70, stroke=1, fill=0)
        pdf.rect(x=10, y=440, width=140, height=70, stroke=1, fill=0)
        pdf.rect(x=10, y=440, width=210, height=70, stroke=1, fill=0)
        pdf.rect(x=10, y=440, width=280, height=70, stroke=1, fill=0)
        pdf.rect(x=10, y=440, width=350, height=70, stroke=1, fill=0)
        pdf.rect(x=10, y=440, width=420, height=70, stroke=1, fill=0)

        pdf.rect(x=10, y=440, width=490, height=20, stroke=1, fill=0)
        pdf.rect(x=10, y=440, width=490, height=50, stroke=1, fill=0)
        pdf.setFont("Helvetica", 7)
        pdf.drawString(12, 493, "SUMMARY TABLE")
        pdf.drawString(110, 493, "I")
        pdf.drawString(180, 493, "II")
        pdf.drawString(250, 493, "III")
        pdf.drawString(320, 493, "IV")
        pdf.drawString(390, 493, "V")

        pdf.drawString(12, 480, "Assessment of Data")
        pdf.drawString(83, 480, "M&E Structure")
        pdf.drawString(83, 472, "Functions and")
        pdf.drawString(83, 464, "Capabilities")

        pdf.drawString(153, 480, "Data")
        pdf.drawString(153, 472, "Management")
        pdf.drawString(153, 464, "Processes")

        pdf.drawString(223, 480, "Indicator Definitions")
        pdf.drawString(223, 472, "and Reporting ")
        pdf.drawString(223, 464, "Guidelines")

        pdf.drawString(293, 480, "Data-collection ")
        pdf.drawString(293, 472, "and Reporting ")
        pdf.drawString(293, 464, "Forms / Tools")

        pdf.drawString(363, 480, "EMR Systems")
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(433, 480, "Site Average")
        pdf.setFont("Helvetica", 7)

        pdf.drawString(12, 472, "Management and")
        pdf.drawString(12, 464, "Reporting Systems")
        pdf.drawString(12, 452, "Average")
        pdf.drawString(12, 443, "(per functional area)")

        pdf.drawString(110, 445, f"{avg_me}")
        pdf.drawString(180, 445, f"{avg_data_mnx}")
        pdf.drawString(250, 445, f"{avg_indicator}")
        pdf.drawString(320, 445, f"{avg_data_collect}")
        pdf.drawString(390, 445, f"{avg_emr}")
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(460, 445, f"{site_avg}")
        # create polar chart
        create_polar(df, pdf, selected_facility, quarter_year)
        pdf.setFont("Helvetica", 7)
        pdf.drawString(20, 0.75 * inch, "The DQA summary charts below are ordered from the indicators with the "
                                        "greatest discrepancies to the least.")
        pdf.saveState()
        add_footer(pdf, request.user)
        pdf.restoreState()
        pdf.setFont("Helvetica-Bold", 12)
        coordinates = [
            (70, 590), (325, 590),
            (70, 430), (325, 430),
            (70, 270), (325, 270),
            (70, 110), (325, 110),
            (70, 590), (325, 590),
            (70, 430), (325, 430),
        ]

        for i, image_path in enumerate(charts):
            if i % 8 == 0:  # start new page every 8 images
                pdf.showPage()
                # pdf.translate(inch, inch)
                pdf.drawString(280, 750, "DATA VERIFICATION")
                pdf.saveState()
                add_footer(pdf, request.user)
                pdf.restoreState()
            try:
                x, y = coordinates[i]
                pdf.drawImage(image=image_path, x=x, y=y, width=260, height=150)
            except IndexError:
                pass
        pdf.setFont("Helvetica", 12)
        pdf.setFillColor(colors.black)
        pdf.drawString(280, 400, f"AUDIT TEAM ")

        audit_team = AuditTeam.objects.filter(facility_name__id=selected_facility.id,
                                              quarter_year__quarter_year=quarter_year)

        # Create a list to hold the data for the table
        data = [['Name', 'Carder', 'Organization', 'Review Period']]
        # Loop through the audit_team queryset and append the required fields to the data list
        for audit in audit_team:
            data.append([audit.name, audit.carder, audit.organization,audit.quarter_year])

        # Define the table style
        table_style = TableStyle(
            [('BACKGROUND', (0, 0), (-1, 0), colors.grey), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
             ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica'),
             ('FONTSIZE', (0, 0), (-1, 0), 8), ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
             ('BACKGROUND', (0, 1), (-1, -1), colors.beige), ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
             ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'), ('FONTSIZE', (0, 1), (-1, -1), 8),
             ('BOTTOMPADDING', (0, 1), (-1, -1), 6), ('GRID', (0, 0), (-1, -1), .5, colors.black)])

        # Create the table object and apply the table style
        # Define the column widths
        widths = [124 for _ in range(4)]

        # Create the table object with the column widths
        table = Table(data, colWidths=widths)
        table.setStyle(table_style)

        # Define the initial position for the table
        x, y = 80, 390
        # Add the table to the PDF object
        table.wrapOn(pdf, 0, 0)
        table_height = table._height
        table.drawOn(pdf, x, y - table_height)
        # add the footer to each page of the document
        pdf.showPage()
        pdf.saveState()
        add_footer(pdf, request.user)
        pdf.restoreState()
        pdf.setFont("Helvetica", 12)
        pdf.setFillColor(colors.black)
        # add action plan
        pdf.drawString(280, 750, "ACTION PLAN")
        work_plan = DQAWorkPlan.objects.filter(facility_name__id=selected_facility.id,
                                               quarter_year__quarter_year=quarter_year)

        # Create a list to hold the data for the table
        data = [['Program Areas Reviewed', 'Strengths Identified', 'Gaps Identified', 'Recommendation',
                 'Individuals Responsible', 'Due complete by', 'Comments']]
        cell_style = ParagraphStyle(name='cell_style', fontSize=6, leading=7, wordWrap='CJK')
        for plan in work_plan:
            data.append([
                Paragraph(plan.program_areas_reviewed, cell_style),
                Paragraph(plan.strengths_identified, cell_style),
                Paragraph(plan.gaps_identified, cell_style),
                Paragraph(plan.recommendation, cell_style),
                Paragraph(plan.individuals_responsible, cell_style),
                plan.due_complete_by,
                Paragraph(plan.comments, cell_style),
            ])
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 5.5),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), .5, colors.black),
            ('VALIGN', (0, 1), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 2),  # Add top padding to cells
            ('PARAGRAPHALIGN', (0, 1), (-1, -1), 'LEFT'),  # Add paragraph alignment to cells
        ])

        # Create the table object and apply the table style
        # Define the column widths
        widths = [71, 71, 71, 81, 81, 51, 71]

        # Create the table object with the column widths
        table = Table(data, colWidths=widths)
        table.setStyle(table_style)

        # Define the initial position for the table
        x, y = 80, 740
        # Add the table to the PDF object
        table.wrapOn(pdf, 0, 0)
        table_height = table._height
        table.drawOn(pdf, x, y - table_height)
        pdf.save()
        return response


def dqa_summary(request):
    form = QuarterSelectionForm(request.POST or None)
    year_form = YearSelectionForm(request.POST or None)
    facility_form = FacilitySelectionForm(request.POST or None)
    plot_div = None

    selected_quarter = "Qtr1"
    year_suffix = "21"
    selected_facility = None
    average_dictionary = None
    site_avg = None
    audit_team = None

    if form.is_valid() and year_form.is_valid() and facility_form.is_valid():
        selected_quarter = form.cleaned_data['quarter']
        selected_year = year_form.cleaned_data['year']
        selected_facility = facility_form.cleaned_data['name']
        year_suffix = selected_year[-2:]
    quarter_year = f"{selected_quarter}-{year_suffix}"

    if selected_facility:
        selected_facility_dict = {
            'id': str(selected_facility.id),
            'name': selected_facility.name,
            # Add other fields as necessary
        }

        # Convert the dictionary to a JSON string
        selected_facility_json = json.dumps(selected_facility_dict)

        # Store the JSON string in the session
        request.session['selected_facility'] = selected_facility_json
        request.session['quarter_year'] = quarter_year

    description_list = [
        "There is a documented structure/chart that clearly identifies positions that have data management "
        "responsibilities at the Facility.",
        "Positions dedicated to M&E and data management systems in the facility are filled.",
        "There is a training plan which includes staff involved in data-collection and reporting at all levels in the "
        "reporting process.",
        "All relevant staff have received training on the data management processes and tools.",
        "There is a designated staff responsible for reviewing the quality of data (i.e., accuracy, completeness and "
        "timeliness) before submission to the Sub County.",
        "The facility has data quality SOPs for monthly reporting processes and quality checks",
        "The facility conducts internal data quality checks and validation before submission of reports",
        "The facility has conducted a data quality audit in the last 6 months",
        "There is a documented data improvement action plan? Verify by seeing",
        "Feedback is systematically provided to the facility on the quality of their reporting (i.e., accuracy, "
        "completeness and timeliness).",
        "The facility regularly reviews data to inform decision making (Ask for evidence e.g.meeting minutes, "
        "MDT feedback data template",
        "The facility is aware of their yearly targets and are monitoring monthly performance using wall charts",
        "The facility has been provided with indicator definitions reference guides for both MOH and MER 2.6 "
        "indicators.",
        "The facility staff are very clear on what they are supposed to report on.",
        "The facility staff are very clear on how (e.g., in what specific format) reports are to be submitted.",
        "The facility staff are very clear on to whom the reports should be submitted.",
        "The facility staff are very clear on when the reports are due.",
        "The facility has the latest versions of source documents (registers) and aggregation tool (MOH 731)",
        "Clear instructions have been provided to the facility on how to complete the data collection and reporting "
        "forms/tools.",
        "The facility has the revised HTS register in all service delivery points and a clear inventory is available "
        "detailing the number of HTS registers in use by service delivery point",
        "HIV client files are well organised and stored in a secure location",
        "Do you use your EMR to generate reports?",
        "There is a clearly documented and actively implemented database administration procedure in place. This "
        "includes backup/recovery procedures, security admininstration, and user administration.",
        "The facility carries out daily back up of EMR data (Ask to see the back up for the day of the DQA)",
        "The facility has conducted an RDQA of the EMR system in the last 3 months with documented action points,"
        "What is your main challenge regarding data management and reporting?"]

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
                 'facility': x.facility_name.name,
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
                                                              "Gend_GBV_Physical and Emotional")
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
                         "gbv_emotional_physical": "Gend_GBV_Physical and Emotional",
                         "cx_ca": "Number Screened for Cervical Cancer",
                         "tb_stat_d": "New & Relapse TB cases", "ipt": "Number Starting IPT Total"})

            indicators_to_use_perf = ['mfl_code', 'quarter_year', "Number initiated on PrEP",
                                      'Maternal HAART Total', 'Number Tested Positive Total',
                                      'Total Positive (PMTCT)', 'Number Starting ART Total',
                                      'New & Relapse TB cases', 'Number Starting IPT Total',
                                      'Number Current on ART Total', "Gend_GBV Sexual Violence",
                                      'Gend_GBV_Physical and Emotional', 'Number Screened for Cervical Cancer',
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

        # retrieves a queryset of SystemAssessment objects that have the specified quarter_year and facility_name.
        system_assessments = SystemAssessment.objects.filter(
            quarter_year__quarter_year=quarter_year,
            facility_name=selected_facility
        )
        if system_assessments:
            average_dictionary, expected_counts_dictionary = calculate_averages(system_assessments, description_list)
            site_avg = round(sum(average_dictionary.values()) / len(average_dictionary), 2)
            data = [
                go.Scatterpolar(
                    r=[average_dictionary['average_calculations_5'], average_dictionary['average_calculations_5_12'],
                       average_dictionary['average_calculations_12_17'],
                       average_dictionary['average_calculations_17_21'],
                       average_dictionary['average_calculations_21_25']],
                    theta=['M&E Structure, Functions and Capabilities', 'Data Management Processes',
                           'Indicator Definitions and Reporting Guidelines',
                           'Data-collection and Reporting Forms / Tools', 'EMR Systems'],
                    fill='toself'
                )
            ]

            layout = go.Layout(
                height=400,  # set the chart's height to 500 pixels
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 5]
                    )
                ),
                showlegend=False
            )

            fig = go.Figure(data=data, layout=layout)
            # set the chart title
            fig.update_layout(
                title={
                    'text': f"System Assessment Averages for {selected_facility} ({quarter_year})",
                    'y': 0.95,
                    'x': 0.5,
                    'xanchor': 'center',
                    'yanchor': 'top'
                },
            )

            plot_div = opy.plot(fig, auto_open=False, output_type='div')

        else:
            messages.info(request, f"No System assessment data for {selected_facility}")
        audit_team = AuditTeam.objects.filter(facility_name__id=selected_facility.id,
                                              quarter_year__quarter_year=quarter_year)
        if not audit_team:
            messages.info(request,
                          f"No audit team assigned for {selected_facility}  {quarter_year}. Please ensure that data"
                          f" verification and system assessment data has been entered before assigning an audit team. "
                          f"Once all data is verified, the 'Add audit team' button will be available on this page.")

    context = {
        "dicts": dicts,
        "dqa": dqa,
        'form': form,
        "year_form": year_form,
        "facility_form": facility_form,
        "selected_facility": selected_facility,
        "quarter_year": quarter_year,
        "plot_div": plot_div,
        "average_dictionary": average_dictionary,
        "site_avg": site_avg,
        "audit_team": audit_team,
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
        'facility': facility.facility_name.name,
        'mfl_code': facility.facility_name.mfl_code,
        'date_modified': facility.date_modified,
    }

    return render(request, 'dqa/add_qi_manager.html', context)


def show_dqa_work_plan(request):
    form = QuarterSelectionForm(request.POST or None)
    year_form = YearSelectionForm(request.POST or None)
    facility_form = FacilitySelectionForm(request.POST or None)
    selected_facility = None
    work_plan = None
    quarter_year = None

    if form.is_valid() and year_form.is_valid() and facility_form.is_valid():
        selected_quarter = form.cleaned_data['quarter']
        selected_year = year_form.cleaned_data['year']
        selected_facility = facility_form.cleaned_data['name']
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


def add_system_verification(request):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    quarter_form = QuarterSelectionForm(request.POST or None)
    year_form = YearSelectionForm(request.POST or None)
    facility_form = FacilitySelectionForm(request.POST or None)
    date_form = DateSelectionForm(request.POST or None)
    descriptions = [
        "There is a documented structure/chart that clearly identifies positions that have data management "
        "responsibilities at the Facility.",
        "Positions dedicated to M&E and data management systems in the facility are filled.",
        "There is a training plan which includes staff involved in data-collection and reporting at all levels in the "
        "reporting process.",
        "All relevant staff have received training on the data management processes and tools.",
        "There is a designated staff responsible for reviewing the quality of data (i.e., accuracy, completeness and "
        "timeliness) before submission to the Sub County.",
        "The facility has data quality SOPs for monthly reporting processes and quality checks",
        "The facility conducts internal data quality checks and validation before submission of reports",
        "The facility has conducted a data quality audit in the last 6 months",
        "There is a documented data improvement action plan? Verify by seeing",
        "Feedback is systematically provided to the facility on the quality of their reporting (i.e., accuracy, "
        "completeness and timeliness).",
        "The facility regularly reviews data to inform decision making (Ask for evidence e.g.meeting minutes, "
        "MDT feedback data template",
        "The facility is aware of their yearly targets and are monitoring monthly performance using wall charts",
        "The facility has been provided with indicator definitions reference guides for both MOH and MER 2.6 "
        "indicators.",
        "The facility staff are very clear on what they are supposed to report on.",
        "The facility staff are very clear on how (e.g., in what specific format) reports are to be submitted.",
        "The facility staff are very clear on to whom the reports should be submitted.",
        "The facility staff are very clear on when the reports are due.",
        "The facility has the latest versions of source documents (registers) and aggregation tool (MOH 731)",
        "Clear instructions have been provided to the facility on how to complete the data collection and reporting "
        "forms/tools.",
        "The facility has the revised HTS register in all service delivery points and a clear inventory is available "
        "detailing the number of HTS registers in use by service delivery point",
        "HIV client files are well organised and stored in a secure location",
        "Do you use your EMR to generate reports?",
        "There is a clearly documented and actively implemented database administration procedure in place. This "
        "includes backup/recovery procedures, security admininstration, and user administration.",
        "The facility carries out daily back up of EMR data (Ask to see the back up for the day of the DQA)",
        "The facility has conducted an RDQA of the EMR system in the last 3 months with documented action points,"
        "What is your main challenge regarding data management and reporting?"]
    initial_data = [{'description': description} for description in descriptions]

    SystemAssessmentFormSet = modelformset_factory(
        SystemAssessment,
        form=SystemAssessmentForm,
        extra=25

    )
    formset = SystemAssessmentFormSet(queryset=SystemAssessment.objects.none(), initial=initial_data)
    if request.method == "POST":
        formset = SystemAssessmentFormSet(request.POST, initial=initial_data)
        if formset.is_valid() and quarter_form.is_valid() and year_form.is_valid() and date_form.is_valid() and facility_form.is_valid():
            selected_quarter = quarter_form.cleaned_data['quarter']
            selected_facility = facility_form.cleaned_data['name']
            selected_year = year_form.cleaned_data['year']
            selected_date = date_form.cleaned_data['date']
            instances = formset.save(commit=False)
            # Check if all forms in formset are filled
            if not all([form.has_changed() for form in formset.forms]):
                messages.error(request, "Please fill all rows before saving.")
            else:
                try:
                    with transaction.atomic():
                        for form, instance in zip(formset.forms, instances):
                            # Set instance fields from form data
                            instance.dropdown_option = form.cleaned_data['dropdown_option']
                            instance.auditor_note = form.cleaned_data['auditor_note']
                            instance.supporting_documentation_required = form.cleaned_data[
                                'supporting_documentation_required']
                            instance.dqa_date = selected_date
                            instance.created_by = request.user
                            if instance.dropdown_option == 'Yes':
                                instance.calculations = 3
                            elif instance.dropdown_option == 'Partly':
                                instance.calculations = 2
                            elif instance.dropdown_option == 'No':
                                instance.calculations = 1
                            elif instance.dropdown_option == 'N/A':
                                instance.calculations = None
                            # Get or create the Facility instance
                            facility, created = Facilities.objects.get_or_create(name=selected_facility)
                            instance.facility_name = facility
                            # Get or create the Period instance
                            period, created = Period.objects.get_or_create(quarter=selected_quarter, year=selected_year)
                            instance.quarter_year = period
                            instance.save()
                        messages.success(request, "Successfully saved to the database!")
                except DatabaseError:
                    messages.error(request,
                                   "Database Error: An error occurred while saving to the database. Data already "
                                   "exists!")

    context = {
        "formset": formset,
        "quarter_form": quarter_form,
        "year_form": year_form,
        "facility_form": facility_form,
        "date_form": date_form,
    }
    return render(request, 'dqa/add_system_assessment.html', context)


def system_assessment_table(request):
    # Get the query parameters from the URL
    quarter_form_initial = request.GET.get('quarter_form')
    year_form_initial = request.GET.get('year_form')
    facility_form_initial = request.GET.get('facility_form')

    # Parse the string values into dictionary objects
    quarter_form_initial = ast.literal_eval(quarter_form_initial) if quarter_form_initial else {}
    year_form_initial = ast.literal_eval(year_form_initial) if year_form_initial else {}
    facility_form_initial = ast.literal_eval(facility_form_initial) if facility_form_initial else {}

    quarter_form = QuarterSelectionForm(request.POST or None, initial=quarter_form_initial)
    year_form = YearSelectionForm(request.POST or None, initial=year_form_initial)
    facility_form = FacilitySelectionForm(request.POST or None, initial=facility_form_initial)

    date_form = DateSelectionForm(request.POST or None)
    system_assessments = None
    average_dictionary = None
    expected_counts_dictionary = None
    description_list = [
        "There is a documented structure/chart that clearly identifies positions that have data management "
        "responsibilities at the Facility.",
        "Positions dedicated to M&E and data management systems in the facility are filled.",
        "There is a training plan which includes staff involved in data-collection and reporting at all levels in the "
        "reporting process.",
        "All relevant staff have received training on the data management processes and tools.",
        "There is a designated staff responsible for reviewing the quality of data (i.e., accuracy, completeness and "
        "timeliness) before submission to the Sub County.",
        "The facility has data quality SOPs for monthly reporting processes and quality checks",
        "The facility conducts internal data quality checks and validation before submission of reports",
        "The facility has conducted a data quality audit in the last 6 months",
        "There is a documented data improvement action plan? Verify by seeing",
        "Feedback is systematically provided to the facility on the quality of their reporting (i.e., accuracy, "
        "completeness and timeliness).",
        "The facility regularly reviews data to inform decision making (Ask for evidence e.g.meeting minutes, "
        "MDT feedback data template",
        "The facility is aware of their yearly targets and are monitoring monthly performance using wall charts",
        "The facility has been provided with indicator definitions reference guides for both MOH and MER 2.6 "
        "indicators.",
        "The facility staff are very clear on what they are supposed to report on.",
        "The facility staff are very clear on how (e.g., in what specific format) reports are to be submitted.",
        "The facility staff are very clear on to whom the reports should be submitted.",
        "The facility staff are very clear on when the reports are due.",
        "The facility has the latest versions of source documents (registers) and aggregation tool (MOH 731)",
        "Clear instructions have been provided to the facility on how to complete the data collection and reporting "
        "forms/tools.",
        "The facility has the revised HTS register in all service delivery points and a clear inventory is available "
        "detailing the number of HTS registers in use by service delivery point",
        "HIV client files are well organised and stored in a secure location",
        "Do you use your EMR to generate reports?",
        "There is a clearly documented and actively implemented database administration procedure in place. This "
        "includes backup/recovery procedures, security admininstration, and user administration.",
        "The facility carries out daily back up of EMR data (Ask to see the back up for the day of the DQA)",
        "The facility has conducted an RDQA of the EMR system in the last 3 months with documented action points,"
        "What is your main challenge regarding data management and reporting?"]

    if quarter_form.is_valid() and year_form.is_valid() and facility_form.is_valid():
        selected_quarter = quarter_form.cleaned_data['quarter']
        selected_facility = facility_form.cleaned_data['name']
        selected_year = year_form.cleaned_data['year']

        year_suffix = selected_year[-2:]
        quarter_year = f"{selected_quarter}-{year_suffix}"
        # retrieves a queryset of SystemAssessment objects that have the specified quarter_year and facility_name.
        system_assessments = SystemAssessment.objects.filter(
            quarter_year__quarter_year=quarter_year,
            facility_name=selected_facility
        ).order_by(
            Case(
                *[When(description=d, then=pos) for pos, d in enumerate(description_list)],
                output_field=IntegerField()
            )
        )
        if system_assessments:
            average_dictionary, expected_counts_dictionary = calculate_averages(system_assessments, description_list)

        if not system_assessments:
            messages.error(request, f"System assessment data was not found for {selected_facility} ({quarter_year})")

    if quarter_form_initial:
        # retrieves a queryset of SystemAssessment objects that have the specified quarter_year and facility_name.
        system_assessments = SystemAssessment.objects.filter(
            quarter_year__quarter_year=quarter_form_initial['quarter'],
            facility_name=Facilities.objects.get(name=facility_form_initial["name"])
        ).order_by(
            Case(
                *[When(description=d, then=pos) for pos, d in enumerate(description_list)],
                output_field=IntegerField()
            )
        )
        if system_assessments:
            average_dictionary, expected_counts_dictionary = calculate_averages(system_assessments, description_list)

    context = {
        "quarter_form": quarter_form,
        "year_form": year_form,
        "facility_form": facility_form,
        "date_form": date_form,
        'system_assessments': system_assessments,
        "average_dictionary": average_dictionary,
        "expected_counts_dictionary": expected_counts_dictionary,
    }
    return render(request, 'dqa/show_system_assessment.html', context)


def instructions(request):
    return render(request, 'dqa/instructions.html')


@login_required(login_url='login')
def update_system_assessment(request, pk):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    item = SystemAssessment.objects.get(id=pk)
    if request.method == "POST":
        form = SystemAssessmentForm(request.POST, instance=item)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.dropdown_option = form.cleaned_data['dropdown_option']
            instance.auditor_note = form.cleaned_data['auditor_note']
            instance.supporting_documentation_required = form.cleaned_data[
                'supporting_documentation_required']
            instance.dqa_date = item.dqa_date
            instance.created_by = request.user
            if instance.dropdown_option == 'Yes':
                instance.calculations = 3
            elif instance.dropdown_option == 'Partly':
                instance.calculations = 2
            elif instance.dropdown_option == 'No':
                instance.calculations = 1
            elif instance.dropdown_option == 'N/A':
                instance.calculations = None
            # Get or create the Facility instance
            instance.facility_name = item.facility_name
            # Get the Period instance
            instance.quarter_year = item.quarter_year
            instance.save()
            # Set the initial values for the forms
            quarter_form_initial = {'quarter': item.quarter_year.quarter_year}
            year_form_initial = {'year': item.quarter_year.year}
            facility_form_initial = {"name": item.facility_name.name}

            messages.success(request, "Record successfully updated!")
            # Redirect to the system assessment table view with the initial values for the forms
            url = reverse('system_assessment_table')
            url = f'{url}?quarter_form={quarter_form_initial}&year_form={year_form_initial}&facility_form={facility_form_initial}'
            return redirect(url)
            # return HttpResponseRedirect(request.session['page_from'])
    else:
        form = SystemAssessmentForm(instance=item)
    context = {
        "form": form,
        "title": "update"
    }
    return render(request, 'dqa/update_system_assessment.html', context)


@login_required(login_url='login')
def update_dqa_workplan(request, pk):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    item = DQAWorkPlan.objects.get(id=pk)
    today = timezone.now().date()
    if request.method == "POST":
        form = DQAWorkPlanForm(request.POST, instance=item)
        if form.is_valid():
            dqa_work_plan = form.save(commit=False)
            dqa_work_plan.facility_name = item.facility_name
            dqa_work_plan.quarter_year = item.quarter_year
            dqa_work_plan.created_by = request.user
            dqa_work_plan.progress = (dqa_work_plan.due_complete_by - today).days
            dqa_work_plan.timeframe = (dqa_work_plan.due_complete_by - dqa_work_plan.dqa_date).days
            dqa_work_plan.save()
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = DQAWorkPlanForm(instance=item)
    context = {
        "form": form,
        'title': 'Update DQA Work Plan',
        'facility': item.facility_name.name,
        'mfl_code': item.facility_name.mfl_code,
        'date_modified': item.updated_at,
    }
    return render(request, 'dqa/add_qi_manager.html', context)


def add_audit_team(request, pk, quarter_year):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    if request.method == 'POST':
        form = AuditTeamForm(request.POST)
        if form.is_valid():
            try:
                post = form.save(commit=False)
                post.facility_name = Facilities.objects.get(id=pk)
                post.quarter_year = Period.objects.get(quarter_year=quarter_year)
                post.save()
                return HttpResponseRedirect(request.path_info)
            except ValidationError as e:
                error_msg = str(e)
                error_msg = error_msg[1:-1]  # remove the first and last characters (brackets)
                messages.error(request, error_msg)
    else:
        form = AuditTeamForm()
    audit_team = AuditTeam.objects.filter(facility_name__id=pk, quarter_year__quarter_year=quarter_year)

    context = {
        "form": form,
        "title": "audit team",
        "audit_team": audit_team,
        "quarter_year": quarter_year,
    }
    return render(request, 'dqa/add_period.html', context)


@login_required(login_url='login')
def update_audit_team(request, pk):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    item = AuditTeam.objects.get(id=pk)
    if request.method == "POST":
        form = AuditTeamForm(request.POST, instance=item)
        if form.is_valid():
            audit_team = form.save(commit=False)
            audit_team.facility_name = item.facility_name
            audit_team.quarter_year = item.quarter_year
            audit_team.save()
            # return HttpResponseRedirect(request.session['page_from'])
            # Set the initial values for the forms
            quarter_form_initial = {'quarter': item.quarter_year.quarter_year}
            year_form_initial = {'year': item.quarter_year.year}
            facility_form_initial = {"name": item.facility_name.name}

            messages.success(request, "Record successfully updated!")
            # Redirect to the system assessment table view with the initial values for the forms
            url = reverse('show_audit_team')
            url = f'{url}?quarter_form={quarter_form_initial}&year_form={year_form_initial}&facility_form={facility_form_initial}'
            return redirect(url)
    else:
        form = AuditTeamForm(instance=item)
    context = {
        "form": form,
        'title': 'update audit team',
        'facility': item.facility_name.name,
        'mfl_code': item.facility_name.mfl_code,
        'date_modified': item.updated_at,
    }
    return render(request, 'dqa/add_period.html', context)


@login_required(login_url='login')
def show_audit_team(request):
    # Get the query parameters from the URL
    quarter_form_initial = request.GET.get('quarter_form')
    year_form_initial = request.GET.get('year_form')
    facility_form_initial = request.GET.get('facility_form')

    # Parse the string values into dictionary objects
    quarter_form_initial = ast.literal_eval(quarter_form_initial) if quarter_form_initial else {}
    year_form_initial = ast.literal_eval(year_form_initial) if year_form_initial else {}
    facility_form_initial = ast.literal_eval(facility_form_initial) if facility_form_initial else {}

    form = QuarterSelectionForm(request.POST or None, initial=quarter_form_initial)
    year_form = YearSelectionForm(request.POST or None, initial=year_form_initial)
    facility_form = FacilitySelectionForm(request.POST or None, initial=facility_form_initial)

    audit_team = None
    quarter_year = None

    if form.is_valid() and year_form.is_valid() and facility_form.is_valid():
        selected_quarter = form.cleaned_data['quarter']
        selected_year = year_form.cleaned_data['year']
        selected_facility = facility_form.cleaned_data['name']
        year_suffix = selected_year[-2:]
        quarter_year = f"{selected_quarter}-{year_suffix}"
        audit_team = AuditTeam.objects.filter(facility_name__id=selected_facility.id,
                                              quarter_year__quarter_year=quarter_year)
    elif facility_form_initial:
        selected_quarter = quarter_form_initial['quarter']
        selected_facility = facility_form_initial['name']
        audit_team = AuditTeam.objects.filter(facility_name=Facilities.objects.get(name=selected_facility),
                                              quarter_year__quarter_year=selected_quarter)

    context = {
        "audit_team": audit_team,
        'form': form,
        "year_form": year_form,
        "facility_form": facility_form,
        'title': 'show team',
        "quarter_year": quarter_year,
    }
    return render(request, 'dqa/add_period.html', context)
