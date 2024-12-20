import ast
import csv
import re
from collections import defaultdict
from statistics import mean

import matplotlib
import numpy as np
from django.apps import apps
from django.core.exceptions import ValidationError
from django.db.models.functions import Cast, Concat
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph, Table, TableStyle

from apps.labpulse.views import line_chart_median_mean

matplotlib.use('Agg')
matplotlib.rcParams['agg.path.chunksize'] = 10000

from io import BytesIO
import json
from datetime import timezone, timedelta
import seaborn as sns
import matplotlib.pyplot as plt

from django.db.models import Case, Count, Q, When, IntegerField, DateField, ExpressionWrapper, Value, CharField, Sum
from django.forms import modelform_factory, modelformset_factory
from django.urls import reverse

import pandas as pd

pd.options.mode.chained_assignment = None  # default='warn' Suppress pandas SettingWithCopyWarning
from django.views import View
from plotly.offline import plot
import plotly.express as px
import plotly.graph_objs as go
import plotly.offline as opy

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, connection, reset_queries, transaction, DatabaseError
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render, redirect

# Create your views here.
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from apps.dqa.form import BaseForm, CareTreatmentForm, CqiForm, DataVerificationForm, GbvForm, HtsForm, PeriodForm, \
    PharmacyForm, \
    PrepForm, \
    QuarterSelectionForm, TbForm, \
    VmmcForm, \
    YearSelectionForm, \
    FacilitySelectionForm, DQAWorkPlanForm, SystemAssessmentForm, DateSelectionForm, AuditTeamForm, \
    UpdateButtonSettingsForm, HubSelectionForm, SubcountySelectionForm, CountySelectionForm, ProgramSelectionForm
from apps.dqa.models import CareTreatment, Cqi, DataVerification, Gbv, Hts, Period, Indicators, FyjPerformance, \
    DQAWorkPlan, \
    Pharmacy, \
    Prep, SystemAssessment, \
    AuditTeam, KhisPerformance, TableNames, Tb, UpdateButtonSettings, Vmmc
# from apps.cqi.views import bar_chart
from apps.cqi.models import Counties, Facilities, Sub_counties

from datetime import datetime
import pytz
from django.utils import timezone


def disable_update_buttons(request, audit_team):
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
                    data_entry_date = data.date_created.astimezone(local_tz).date()
                except AttributeError:
                    data_entry_date = data.created_at.astimezone(local_tz).date()
                hide_button_datetime = timezone.make_aware(datetime.combine(data_entry_date, hide_button_time))
                if data_entry_date == now.date() and now >= hide_button_datetime:
                    data.hide_update_button = True
                elif data_entry_date >= enabled_datetime.date():
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


def calculate_progress(dqa_workplan_list):
    today = timezone.now().date()
    for workplan in dqa_workplan_list:
        workplan.progress = (workplan.due_complete_by - today).days


def export_dqa_work_plan_csv(request, quarter_year, selected_level):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{selected_level} {quarter_year} dqa_workplan.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'DQA Date', 'Facility Name', 'Quarter Year', 'Individuals Conducting DQA',
                     'Program Areas Reviewed', 'Strengths Identified', 'Gaps Identified', 'Recommendation',
                     '% Completed', 'Individuals Responsible', 'Due/Complete By', 'Comments',
                     'Created At', 'Updated At', 'Progress', 'Timeframe', 'Created By', 'Modified By'])

    work_plans = DQAWorkPlan.objects.all().values_list('id', 'dqa_date', 'facility_name__name',
                                                       'quarter_year__quarter_year', 'individuals_conducting_dqa',
                                                       'program_areas_reviewed', 'strengths_identified',
                                                       'gaps_identified', 'recommendation',
                                                       'percent_completed', 'individuals_responsible',
                                                       'due_complete_by', 'comments', 'created_at',
                                                       'updated_at', 'progress', 'timeframe', 'created_by__email',
                                                       'modified_by__email')

    for work_plan in work_plans:
        writer.writerow(work_plan)

    return response


def export_sqa_csv(request, quarter_year, selected_level):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{selected_level} {quarter_year} sqa_data.csv"'

    writer = csv.writer(response)
    writer.writerow(['DQA Date', 'County', 'Sub-County', 'Hub', 'Facility Name', 'Quarter Year',
                     'Program Areas Reviewed', 'Description', 'Probable Response',
                     'Verification', 'Numerator Description', 'Numerator',
                     'Denominator Description', 'Denominator', "Auditor's Note",
                     'Created At', 'Date Modified', 'Created By'])

    models_to_check = {
        "GBV": Gbv, "VMMC": Vmmc, "HTS": Hts, "PrEP": Prep, "TB": Tb,
        "CARE & RX": CareTreatment, "PHARMACY": Pharmacy, "CQI": Cqi,
    }

    for model_name, model in models_to_check.items():
        sqa_data = model.objects.all().values_list('dqa_date', 'county__county_name',
                                                   'sub_county__sub_counties', 'sub_county__hub__hub',
                                                   'facility_name__name', 'quarter_year__quarter_year',
                                                   'description', 'dropdown_option', 'verification',
                                                   'numerator_description', 'numerator',
                                                   'denominator_description', 'denominator',
                                                   'auditor_note', 'date_created',
                                                   'date_modified', 'created_by__email')
        for data in sqa_data:
            # Insert the model name into the appropriate position in the data
            row = list(data)
            row.insert(5, model_name)  # Index 5 is the position for 'Program Areas Reviewed'
            writer.writerow(row)

    return response


def khis_data_prep(df):
    df['month'] = pd.to_datetime(df['month'])
    df['month'] = df['month'].dt.strftime('%b %Y')

    df = df[['mfl', 'month', 'mois', 'facility', 'UniqID', 'PrEP_New_dhis', 'dhis_start_ipt_total', 'sGBV_Seen_dhis',
             'dhis_screen_cacx_new_f18', 'dhis_tested_9', 'dhis_tested_14m', 'dhis_tested_14f', 'dhis_tested_19m',
             'dhis_tested_19f', 'dhis_tested_24m', 'dhis_tested_24f', 'dhis_tested_25m', 'dhis_tested_25f',
             'dhis_pos_lt9', 'dhis_pos_14m', 'dhis_pos_14f', 'dhis_pos_19m', 'dhis_pos_19f', 'dhis_pos_24m',
             'dhis_pos_24f', 'dhis_pos_25m', 'dhis_pos_25f', 'known_pos_at_first_anc', 'pos_results_anc',
             'on_haart_at_first_anc', 'start_haart_anc', 'infant_arv_prophyl_anc', 'pos_results_LD', 'start_haart_LD',
             'infant_arv_prophyl_LD', 'pos_results_pnc_lt6wks', 'start_haart_pnc_lt6wks',
             'infant_arv_prophyl_lt8wks_pnc', 'dhis_start_art_lt1', 'dhis_start_art_9', 'dhis_start_art_14m',
             'dhis_start_art_14f', 'dhis_start_art_19m', 'dhis_start_art_19f', 'dhis_start_art_24m',
             'dhis_start_art_24f', 'dhis_start_art_25m', 'dhis_start_art_25f', 'dhis_tb_cases_new', 'dhis_on_art_lt1',
             'dhis_on_art_9', 'dhis_on_art_14m', 'dhis_on_art_14f', 'dhis_on_art_19m', 'dhis_on_art_19f',
             'dhis_on_art_24m', 'dhis_on_art_24f', 'dhis_on_art_25m', 'dhis_on_art_25f', 'kps_at_first_anc',
             'anc_initial_test', 'first_anc_visits', 'pos_pnc_gt6weeks_to_6_mon'
             ]]

    for i in df.columns[5:]:
        df[i] = df[i].astype(int)

    df['TX_New_p'] = df['dhis_start_art_lt1'] + df['dhis_start_art_9'] + df['dhis_start_art_14m'] + df[
        'dhis_start_art_14f']
    df['TX_New_a'] = df['dhis_start_art_19m'] + df['dhis_start_art_19f'] + df['dhis_start_art_24m'] + df[
        'dhis_start_art_24f'] + df['dhis_start_art_25m'] + df['dhis_start_art_25f']

    df['TX_New_t'] = df['dhis_start_art_lt1'] + df['dhis_start_art_9'] + df['dhis_start_art_14m'] + df[
        'dhis_start_art_14f'] + df['dhis_start_art_19m'] + df['dhis_start_art_19f'] + df['dhis_start_art_24m'] + df[
                         'dhis_start_art_24f'] + df['dhis_start_art_25m'] + df['dhis_start_art_25f']

    df['TX_Curr_p'] = df['dhis_on_art_lt1'] + df['dhis_on_art_9'] + df['dhis_on_art_14m'] + df['dhis_on_art_14f']
    df['TX_Curr_a'] = df['dhis_on_art_19m'] + df['dhis_on_art_19f'] + df['dhis_on_art_24m'] + df['dhis_on_art_24f'] + \
                      df['dhis_on_art_25m'] + df['dhis_on_art_25f']

    df['TX_Curr_t'] = df['dhis_on_art_lt1'] + df['dhis_on_art_9'] + df['dhis_on_art_14m'] + df['dhis_on_art_14f'] + df[
        'dhis_on_art_19m'] + df['dhis_on_art_19f'] + df['dhis_on_art_24m'] + df['dhis_on_art_24f'] + df[
                          'dhis_on_art_25m'] + df['dhis_on_art_25f']

    df['TST_t'] = df['dhis_tested_9'] + df['dhis_tested_14m'] + df['dhis_tested_14f'] + df['dhis_tested_19m'] + df[
        'dhis_tested_19f'] + df['dhis_tested_24m'] + df['dhis_tested_24f'] + df['dhis_tested_25m'] + df[
                      'dhis_tested_25f']

    df['TST_p'] = df['dhis_tested_9'] + df['dhis_tested_14m'] + df['dhis_tested_14f']

    df['TST_a'] = df['dhis_tested_19m'] + df['dhis_tested_19f'] + df['dhis_tested_24m'] + df['dhis_tested_24f'] + df[
        'dhis_tested_25m'] + df['dhis_tested_25f']

    df['TST_pos_p'] = df['dhis_pos_lt9'] + df['dhis_pos_14m'] + df['dhis_pos_14f']
    df['TST_pos_a'] = df['dhis_pos_19m'] + df['dhis_pos_19f'] + df['dhis_pos_24m'] + df['dhis_pos_24f'] + df[
        'dhis_pos_25m'] + df['dhis_pos_25f']

    df['TST_pos_t'] = df['dhis_pos_lt9'] + df['dhis_pos_14m'] + df['dhis_pos_14f'] + df['dhis_pos_19m'] + df[
        'dhis_pos_19f'] + df['dhis_pos_24m'] + df['dhis_pos_24f'] + df['dhis_pos_25m'] + df['dhis_pos_25f']

    df['PMTCT_STAT_N'] = df['kps_at_first_anc'] + df['anc_initial_test']
    df['PMTCT_STAT_D'] = df['first_anc_visits']
    df['PMTCT_Pos'] = df['kps_at_first_anc'] + df['pos_results_anc']
    df['PMTCT_ARV'] = df['start_haart_anc'] + df['on_haart_at_first_anc']
    df['PMTCT_INF_ARV'] = df['infant_arv_prophyl_anc'] + df['infant_arv_prophyl_lt8wks_pnc'] + df[
        'infant_arv_prophyl_LD']
    df['Pos_PNC'] = df['pos_results_pnc_lt6wks'] + df['pos_pnc_gt6weeks_to_6_mon']

    columns_to_drop = ['dhis_on_art_19m', 'dhis_on_art_19f', 'dhis_on_art_24m', 'dhis_on_art_24f', 'dhis_on_art_25m',
                       'dhis_on_art_25f', 'dhis_on_art_lt1', 'dhis_on_art_9', 'dhis_on_art_14m', 'dhis_on_art_14f',
                       'dhis_start_art_lt1', 'dhis_start_art_9', 'dhis_start_art_14m', 'dhis_start_art_14f',
                       'dhis_start_art_19m', 'dhis_start_art_19f', 'dhis_start_art_24m', 'dhis_start_art_24f',
                       'dhis_start_art_25m', 'dhis_start_art_25f', 'dhis_tested_9', 'dhis_tested_14m',
                       'dhis_tested_14f', 'dhis_tested_19m', 'dhis_tested_19f', 'dhis_tested_24m', 'dhis_tested_24f',
                       'dhis_tested_25m', 'dhis_tested_25f', 'dhis_pos_lt9', 'dhis_pos_14m', 'dhis_pos_14f',
                       'dhis_pos_19m', 'dhis_pos_19f', 'dhis_pos_24m', 'dhis_pos_24f', 'dhis_pos_25m', 'dhis_pos_25f',
                       'mois', 'UniqID', 'kps_at_first_anc', 'pos_pnc_gt6weeks_to_6_mon']

    df = df.drop(columns_to_drop, axis=1)

    df = df.rename(columns={
        'PrEP_New_dhis': 'PrEP_New', 'dhis_start_ipt_total': 'IPT', 'sGBV_Seen_dhis': 'GBV_Sexual',
        'dhis_screen_cacx_new_f18': 'CXCA', 'known_pos_at_first_anc': 'KP_ANC', 'pos_results_anc': 'Newpos_ANC',
        'on_haart_at_first_anc': 'on HAART _ANC', 'start_haart_anc': 'New on HAART_ANC', 'pos_results_LD': 'Pos_L&D',
        'start_haart_LD': 'haart_l_d', 'dhis_tb_cases_new': 'TB_STAT_D', "mfl": "MFL", "facility": "Facility",
        "month": "Month"
    })
    columns_to_use = ['MFL', 'Facility', 'Month', 'TST_p', 'TST_a', 'TST_t', 'TST_pos_p',
                      'TST_pos_a', 'TST_pos_t', 'TX_New_p', 'TX_New_a', 'TX_New_t',
                      'TX_Curr_p', 'TX_Curr_a', 'TX_Curr_t', 'PMTCT_STAT_D', 'PMTCT_STAT_N',
                      'PMTCT_Pos', 'PMTCT_ARV', 'PMTCT_INF_ARV',
                      'PrEP_New', 'GBV_Sexual', 'infant_arv_prophyl_anc',
                      'infant_arv_prophyl_LD', 'infant_arv_prophyl_lt8wks_pnc',
                      'haart_l_d',
                      'pos_results_pnc_lt6wks', 'start_haart_pnc_lt6wks',
                      'KP_ANC',
                      'Newpos_ANC', 'on HAART _ANC', 'New on HAART_ANC', 'Pos_L&D', 'Pos_PNC',
                      'CXCA', 'TB_STAT_D', 'IPT', 'anc_initial_test', 'first_anc_visits', ]
    df = df[columns_to_use]
    return df


@login_required(login_url='login')
def load_khis_data(request):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == 'POST' and "file" in request.FILES:
        file = request.FILES['file']
        # Read the data from the Excel file into a pandas DataFrame
        keyword = "his"
        keyword1 = "731"
        xls_file = pd.ExcelFile(file)
        sheet_names = [sheet for sheet in xls_file.sheet_names if
                       keyword.upper() in sheet.upper() or keyword1.upper() in sheet.upper()]
        if sheet_names:
            dfs = pd.read_excel(file, sheet_name=sheet_names)
            df = pd.concat([df.assign(sheet_name=name) for name, df in dfs.items()])
            df = khis_data_prep(df)
            try:
                with transaction.atomic():
                    if len(df.columns) == 39:
                        df.fillna(0, inplace=True)
                        process_cols = [col for col in df.columns if col not in [df.columns[1], df.columns[2]]]
                        for col in process_cols:
                            df[col] = df[col].astype(int)
                        df[df.columns[1]] = df[df.columns[1]].astype(str)
                        df[df.columns[2]] = df[df.columns[2]].astype(str)

                        # Iterate over each row in the DataFrame
                        for index, row in df.iterrows():
                            performance = KhisPerformance()
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
                            performance.prep_new = row[df.columns[20]]
                            performance.gbv_sexual = row[df.columns[21]]
                            performance.infant_arv_prophyl_anc = row[df.columns[22]]
                            performance.infant_arv_prophyl_l_d = row[df.columns[23]]
                            performance.infant_arv_prophyl_lt8wks_pnc = row[df.columns[24]]
                            performance.haart_l_d = row[df.columns[25]]
                            performance.pos_results_pnc_lt6wks = row[df.columns[26]]
                            performance.start_haart_pnc_lt6wks = row[df.columns[27]]
                            performance.kp_anc = row[df.columns[28]]
                            performance.new_pos_anc = row[df.columns[29]]
                            performance.on_haart_anc = row[df.columns[30]]
                            performance.new_on_haart_anc = row[df.columns[31]]
                            performance.pos_l_d = row[df.columns[32]]
                            performance.pos_pnc = row[df.columns[33]]
                            performance.cx_ca = row[df.columns[34]]
                            performance.tb_stat_d = row[df.columns[35]]
                            performance.ipt = row[df.columns[36]]
                            performance.anc_initial_test = row[df.columns[37]]
                            performance.first_anc_visits = row[df.columns[38]]
                            performance.save()
                        messages.error(request, f'Data successfully saved in the database!')
                        return redirect('show_data_verification')
                    else:
                        # Notify the user that the data is not correct
                        messages.error(request, f'Kindly confirm if {file} has all data columns.The file has'
                                                f'{len(df.columns)} columns')
                        redirect('load_data')
            except IntegrityError:
                month_list = ', '.join(str(month) for month in df['Month'].unique())
                error_msg = f"KHIS Data for {month_list} already exists."
                messages.error(request, error_msg)
        else:
            messages.error(request, f"Uploaded file does not have a sheet named 'KHIS or DHIS or MOH 731'.")
            redirect('load_khis_data')
    return render(request, 'dqa/upload.html')


@login_required(login_url='login')
def load_system_data(request):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == 'POST' and "file" in request.FILES:
        file = request.FILES['file']
        df = pd.read_excel(file, usecols=[0])
        for index, row in df.iterrows():
            instance = SystemAssessment(description=row[0])
            instance.save()

        # Code to load data from Excel file and save it to MyModel
        return render(request, 'dqa/upload.html', {'success': True})
    else:
        return render(request, 'dqa/upload.html')


@login_required(login_url='login')
def load_data(request):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == 'POST' and "file" in request.FILES:
        file = request.FILES['file']
        # Read the data from the Excel file into a pandas DataFrame
        keyword = "perf"
        xls_file = pd.ExcelFile(file)
        sheet_names = [sheet for sheet in xls_file.sheet_names if keyword.upper() in sheet.upper()]
        if sheet_names:
            dfs = pd.read_excel(file, sheet_name=sheet_names)
            df = pd.concat([df.assign(sheet_name=name) for name, df in dfs.items()])
            df.columns = df.columns.str.lower()
            facility_name_cols = [col for col in df.columns if "facility" in col]
            months_name_cols = [col for col in df.columns if "month" in col or "period" in col]
            mfl_codes_cols = [col for col in df.columns if "mfl" in col]
            df = df.rename(
                columns={
                    mfl_codes_cols[0]: "mfl",
                    facility_name_cols[0]: "facility",
                    months_name_cols[0]: "month"
                })

            columns_to_use = ['mfl', 'facility', 'month', 'tst_p', 'tst_a', 'tst_t', 'tst_pos_p',
                              'tst_pos_a', 'tst_pos_t', 'tx_new_p', 'tx_new_a', 'tx_new_t', 'tx_curr_p', 'tx_curr_a',
                              'tx_curr_t', 'pmtct_stat_d', 'pmtct_stat_n', 'pmtct_pos', 'pmtct_arv', 'pmtct_inf_arv',
                              'pmtct_eid', 'hei_pos', 'hei_pos art', 'prep_new', 'gbv_sexual', 'gbv emotional/phy',
                              'kp_anc', 'newpos_anc', 'on haart _anc', 'new on haart_anc', 'pos_l&d', 'pos_pnc',
                              'cxca', 'tb_stat_d', 'ipt', 'tb_prev_n', 'tx_ml', 'tx_rtt']

            df = df[columns_to_use]
            try:
                with transaction.atomic():
                    if len(df.columns) == 38:
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
                            performance.tb_prev_n = row[df.columns[35]]
                            performance.tx_ml = row[df.columns[36]]
                            performance.tx_rtt = row[df.columns[37]]
                            performance.save()
                        messages.error(request, f'Data successfully saved in the database!')
                        return redirect('show_data_verification')
            except IntegrityError:
                quarter_year = row[df.columns[2]]
                messages.error(request, f"Data for  {quarter_year} already exists.")
            except ValidationError:
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


@login_required(login_url='login')
def add_period(request):
    if not request.user.first_name:
        return redirect("profile")
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


@login_required(login_url='login')
def add_data_verification(request):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

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

    forms = DataVerificationForm()
    selected_year = "2021"
    year_suffix = selected_year[-2:]
    facility_obj = None

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
    elif quarter_form_initial:
        selected_quarter = quarter_form_initial['quarter']
        request.session['selected_quarter'] = selected_quarter

        selected_year = year_form_initial['year']
        request.session['selected_year'] = selected_year

        selected_facility = facility_form_initial['name']
        facility_obj = Facilities.objects.filter(name=selected_facility).first()

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
                            with transaction.atomic():

                                field_1 = 0
                                field_2 = 0
                                field_3 = 0
                                total_source = 0
                                field_5 = 0
                                field_6 = 0
                                field_7 = 0
                                total_731moh = 0

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
                            with transaction.atomic():
                                field_1 = 0
                                field_2 = 0
                                field_3 = 0
                                total_source = 0
                                field_5 = 0
                                field_6 = 0
                                field_7 = 0
                                total_731moh = 0

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
                            with transaction.atomic():
                                field_1 = 0
                                field_2 = 0
                                field_3 = 0
                                total_source = 0
                                field_5 = 0
                                field_6 = 0
                                field_7 = 0
                                total_731moh = 0

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
                            with transaction.atomic():
                                field_1 = 0
                                field_2 = 0
                                field_3 = 0
                                total_source = 0
                                field_5 = 0
                                field_6 = 0
                                field_7 = 0
                                total_731moh = 0

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

                                try:
                                    DataVerification.objects.create(
                                        indicator='Number of adults and children starting ART',
                                        field_1=field_1,
                                        field_2=field_2,
                                        field_3=field_3,
                                        total_source=total_source,
                                        field_5=field_5,
                                        field_6=field_6,
                                        field_7=field_7,
                                        total_731moh=total_731moh,
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
                            with transaction.atomic():
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
                                    # field_9 += int(data.field_9)
                                    # field_10 += int(data.field_10)
                                    # field_11 += int(data.field_11)
                                    # total_khis += int(data.total_khis)

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
                                        # field_9=field_9,
                                        # field_10=field_10,
                                        # field_11=field_11,
                                        # total_khis=total_khis,
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
                            with transaction.atomic():
                                field_1 = 0
                                field_2 = 0
                                field_3 = 0
                                total_source = 0
                                field_5 = 0
                                field_6 = 0
                                field_7 = 0
                                total_731moh = 0

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
                                                                    created_by=request.user,
                                                                    quarter_year=period,
                                                                    facility_name=selected_facility)
                                except IntegrityError:
                                    # handle the scenario where a duplicate instance is trying to be created
                                    # for example, return an error message to the user
                                    pass

                        # Redirect the user to the show_data_verification view
                        # return redirect("show_data_verification")
                        data_verification = DataVerification.objects.select_related('quarter_year').filter(
                            quarter_year__quarter=request.session['selected_quarter'],
                            quarter_year__year=request.session['selected_year'],
                            facility_name=selected_facility,
                        )

                        indicator_choices = [choice[0] for choice in Indicators.INDICATOR_CHOICES]
                        sorted_data_verification = sorted(data_verification,
                                                          key=lambda x: indicator_choices.index(x.indicator))

                        if data_verification:
                            remaining_indicators = set(indicator_choices) - {obj.indicator for obj in
                                                                             sorted_data_verification}
                            if remaining_indicators:
                                message = f"{len(remaining_indicators)} remaining indicators: {', '.join(remaining_indicators)}"
                                messages.error(request, message)
                            else:
                                messages.info(request, "All indicators have been recorded.")
                        # return HttpResponseRedirect(request.path_info)
                        # Set the initial values for the forms
                        quarter_form_initial = {'quarter': request.session['selected_quarter']}
                        year_form_initial = {'year': request.session['selected_year']}
                        facility_form_initial = {"name": selected_facility.name}

                        messages.success(request, "Record successfully saved!")
                        # Redirect to the system assessment table view with the initial values for the forms
                        url = reverse('add_data_verification')
                        url = f'{url}?quarter_form={quarter_form_initial}&year_form={year_form_initial}&facility_form={facility_form_initial}'
                        return redirect(url)

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
        forms = DataVerificationForm(initial={'facility_name': facility_obj})

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


@login_required(login_url='login')
def show_data_verification(request):
    if not request.user.first_name:
        return redirect("profile")

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

    selected_quarter = "Qtr1"
    selected_facility = None
    quarters = {}
    request.session['selected_year_'] = ""
    selected_quarter = "Qtr1"
    selected_year = "2021"
    if form.is_valid():
        selected_quarter = form.cleaned_data['quarter']

    if year_form.is_valid():
        selected_year = year_form.cleaned_data['year']

    facility_form = FacilitySelectionForm(request.POST or None,
                                          selected_year=selected_year,
                                          selected_quarter=selected_quarter,
                                          model_to_check=DataVerification)

    ##########################################
    # Show quarterly trends
    ##########################################
    quarterly_trend_fig = show_quarterly_trends(request, DataVerification, "Data Verification")
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
        if selected_quarter == 'Qtr1':
            quarters = {
                selected_quarter: [f'Oct-{year_suffix}', f'Nov-{year_suffix}', f'Dec-{year_suffix}', 'Total']
            }
        elif selected_quarter == 'Qtr2':
            quarters = {
                selected_quarter: [f'Jan-{year_suffix}', f'Feb-{year_suffix}', f'Mar-{year_suffix}', 'Total']
            }
        elif selected_quarter == 'Qtr3':
            quarters = {
                selected_quarter: [f'Apr-{year_suffix}', f'May-{year_suffix}', f'Jun-{year_suffix}', 'Total']
            }
        else:
            quarters = {
                selected_quarter: [f'Jul-{year_suffix}', f'Aug-{year_suffix}', f'Sep-{year_suffix}', 'Total']
            }


    # else:
    #     quarters = {}
    elif quarter_form_initial:
        selected_quarter = quarter_form_initial['quarter']
        selected_facility = facility_form_initial['name']

    try:
        selected_year = request.session['selected_year_']
        year_suffix = selected_year[-2:]
        quarter_year = f"{selected_quarter}-{year_suffix}"
        data_verification = DataVerification.objects.filter(quarter_year__quarter=selected_quarter,
                                                            quarter_year__year=selected_year,
                                                            facility_name=selected_facility,
                                                            )
    except ValidationError:
        selected_year = year_form_initial['year']
        # year_suffix = selected_year[-2:]
        selected_facility = Facilities.objects.get(name=selected_facility)
        quarter_year = selected_quarter
        data_verification = DataVerification.objects.filter(quarter_year__quarter_year=selected_quarter,
                                                            facility_name=selected_facility,
                                                            )
        selected_year = int(selected_year)
        if "Qtr1" in selected_quarter:
            selected_year -= 1
            year_suffix = str(selected_year)[-2:]
        else:
            year_suffix = str(selected_year)[-2:]
        quarters = {
            selected_quarter.split("-")[0]: [
                f'Oct-{year_suffix}', f'Nov-{year_suffix}', f'Dec-{year_suffix}', 'Total'
            ] if 'Qtr1' in selected_quarter else [
                f'Jan-{year_suffix}', f'Feb-{year_suffix}', f'Mar-{year_suffix}', 'Total'
            ] if 'Qtr2' in selected_quarter else [
                f'Apr-{year_suffix}', f'May-{year_suffix}', f'Jun-{year_suffix}', 'Total'
            ] if 'Qtr3' in selected_quarter else [
                f'Jul-{year_suffix}', f'Aug-{year_suffix}', f'Sep-{year_suffix}', 'Total'
            ]
        }
        if "Qtr1" in selected_quarter:
            selected_year += 1
            year_suffix = str(selected_year)[-2:]
        else:
            year_suffix = str(selected_year)[-2:]

    # Display data verification
    display_dicts = display_data_verification(request, data_verification, selected_facility, quarter_year, year_suffix,
                                              quarters)
    context = {"form": form, "year_form": year_form, "facility_form": facility_form,
               "quarterly_trend_fig": quarterly_trend_fig,
               } | display_dicts
    return render(request, 'dqa/show data verification.html', context)


@login_required(login_url='login')
def update_data_verification(request, pk):
    if not request.user.first_name:
        return redirect("profile")
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
                            'created_by': request.user,
                        }
                    )
            # TODO: AFTER UPDATE, USER SHOULD BE TAKEN BACK TO THE PAGE THEY WERE FROM WITH DATA ALREADY LOADED
            # return HttpResponseRedirect(request.session['page_from'])

            # Set the initial values for the forms
            quarter_form_initial = {'quarter': item.quarter_year.quarter_year}
            year_form_initial = {'year': item.quarter_year.year}
            facility_form_initial = {"name": item.facility_name.name}

            messages.success(request, "Record successfully updated!")
            # Redirect to the system assessment table view with the initial values for the forms
            url = reverse('show_data_verification')
            url = f'{url}?quarter_form={quarter_form_initial}&year_form={year_form_initial}&facility_form={facility_form_initial}'
            return redirect(url)
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
    if not request.user.first_name:
        return redirect("profile")
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


def bar_chart(df, x_axis, y_axis, title=None, has_khis_731_datim=False):
    if has_khis_731_datim:
        category_orders = {x_axis: ['Source', 'MOH 731', 'KHIS', 'DATIM']}
        color_discrete_map = {'Source': '#5B9BD5', 'MOH 731': '#ED7D31', 'KHIS': '#A5A5A5', 'DATIM': '#FFC000'}
    else:
        category_orders = {x_axis: ['Source', 'Monthly Report', 'JPHES']}
        color_discrete_map = {'Source': '#5B9BD5', 'Monthly Report': '#ED7D31', 'JPHES': '#FFC000'}
    fig = px.bar(df, x=x_axis, y=y_axis, text=y_axis, title=title, height=200,
                 color=x_axis, category_orders=category_orders, color_discrete_map=color_discrete_map
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


def bar_chart_report(df, x_axis, y_axis, indy=None, quarter=None):
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
        # Save the PNG image to a buffer instead of a file
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight', pad_inches=0.2)
        buffer.seek(0)
        image = ImageReader(buffer)
        plt.close()  # close the current figure
    return image


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


def write_sqa(pdf, request, selected_facility, quarter_year):
    # add the footer to each page of the document
    pdf.showPage()
    pdf.saveState()
    add_footer(pdf, request.user)
    pdf.restoreState()
    pdf.setFont("Helvetica", 12)
    pdf.setFillColor(colors.black)
    # add action plan
    pdf.drawString(200, 750, "Service Quality Assessment (SQA)")
    # Add color code key
    color_key_data = [
        ["Color Code:", "Green >= 2.5 ", "Yellow >= 1.5 to < 2.5", "Red < 1.5"]
    ]

    color_key_style = TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (1, 0), (1, 0), colors.green),
        ('BACKGROUND', (2, 0), (2, 0), colors.yellow),
        ('BACKGROUND', (3, 0), (3, 0), colors.red),
    ])

    color_key_table = Table(color_key_data, colWidths=[80, 80, 80, 80])
    color_key_table.setStyle(color_key_style)

    # Draw the color key table
    color_key_table.wrapOn(pdf, 0, 0)
    color_key_table.drawOn(pdf, 100, 720)  # Adjust position as needed

    sqa_models = [Gbv, Vmmc, Hts, Prep, Tb, CareTreatment, Pharmacy, Cqi]

    # Initialize an average dictionary
    averages = {}

    # Calculate averages for each model
    for model in sqa_models:
        sqa_plan = model.objects.filter(facility_name__id=selected_facility.id,
                                        quarter_year__quarter_year=quarter_year)

        # Filter out null or invalid calculations
        valid_calculations = []
        for plan in sqa_plan:
            try:
                valid_calculations.append(int(plan.calculations))
            except (ValueError, TypeError):
                continue

        # Compute the average if there are valid calculations
        if valid_calculations:
            averages[model.__name__.upper()] = mean(valid_calculations)
        else:
            averages[model.__name__.upper()] = "N/A"

    # Determine dynamic font size based on the number of columns
    num_columns = len(averages.keys()) + 1  # +1 for the "Model" column
    max_width = 496  # Total available width
    col_width = max_width / num_columns  # Divide width equally across columns

    # Adjust the font size dynamically based on column width
    base_font_size = max(5, min(8, int(col_width / 10)))  # Ensure font size is within a readable range

    # Prepare the average table data for horizontal orientation
    average_table_data = [["Functional area"] + list(averages.keys()),  # Model names as headers
                          ["Average Calculation"] + [
                              f"{avg:.2f}" if isinstance(avg, float) else avg for avg in averages.values()
                          ]]  # Corresponding average values

    # Create the average table object with adjusted column widths
    col_widths = [col_width for _ in range(num_columns)]
    # Initialize base styles for the average table
    average_table_style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),  # Header background
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), base_font_size),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, -1), base_font_size),
    ]

    # Add dynamic background colors for the average values
    for col_idx, avg in enumerate(averages.values(), start=1):  # Start at 1 to skip the "Model" column
        if isinstance(avg, (int, float)):
            # Determine background color based on the float value
            if avg >= 2.5:
                calc_bg_color = colors.green
            elif 1.5 <= avg < 2.5:
                calc_bg_color = colors.yellow
            else:
                calc_bg_color = colors.red

            # Add the background style for this cell
            average_table_style.append(('BACKGROUND', (col_idx, 1), (col_idx, 1), calc_bg_color))
    average_table = Table(average_table_data, colWidths=col_widths)
    average_table.setStyle(average_table_style)

    # Draw the average table
    average_table.wrapOn(pdf, 0, 0)
    average_table.drawOn(pdf, 80, 670)  # Adjust position as needed

    cell_style = ParagraphStyle(name='cell_style', fontSize=6, leading=7, wordWrap='CJK')

    # Define the initial position for the first table
    x, y = 80, 660

    for model in sqa_models:
        sqa_plan = model.objects.filter(facility_name__id=selected_facility.id,
                                        quarter_year__quarter_year=quarter_year)
        # Check if all calculations are null
        if not sqa_plan.exclude(Q(calculations__isnull=True)).exists():
            continue  # Skip this model and continue to the next one

        data = [[f'Description- {model.__name__.upper()}', 'Answer', 'Calculations', 'Auditors notes']]
        table_style = [
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
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('PARAGRAPHALIGN', (0, 1), (-1, -1), 'LEFT'),
        ]

        for plan in sqa_plan:
            data.append([
                Paragraph(plan.description or '', cell_style),
                Paragraph(plan.dropdown_option or '', cell_style),
                Paragraph(f"{plan.calculations or 'N/A'}", cell_style),
                Paragraph(plan.auditor_note or '', cell_style),
            ])

        # Define the column widths
        widths = [208, 40, 40, 208]
        # Apply conditional background colors for calculations
        for row_idx, plan in enumerate(sqa_plan, start=1):  # Start from the second row (row_idx 1)
            calc_bg_color = {
                3: colors.green,
                2: colors.yellow,
                1: colors.red,
            }.get(plan.calculations, colors.white)  # Default white if no match

            # Add a background style for the "Calculations" column of this specific row
            table_style.append(('BACKGROUND', (1, row_idx), (1, row_idx), calc_bg_color))
            table_style.append(('BACKGROUND', (2, row_idx), (2, row_idx), calc_bg_color))

        # Create the table object with the column widths
        table = Table(data, colWidths=widths)
        table.setStyle(TableStyle(table_style))

        # Calculate the table height
        w, h = table.wrapOn(pdf, 0, 0)

        # Check if there's enough space on the current page
        if y - h < 50:  # Assuming 50 as minimum space needed at bottom
            pdf.showPage()
            pdf.saveState()
            add_footer(pdf, request.user)
            pdf.restoreState()
            y = 740  # Reset y to top of new page

        # Draw the table
        table.drawOn(pdf, x, y - h)

        # Update y for the next table
        y = y - h - 20  # 20 is the space between tables


class GeneratePDF(View):
    def get(self, request):
        if request.user.is_authenticated and not request.user.first_name:
            return redirect("profile")
        # Retrieve the selected facility from the session and convert it back to a dictionary
        selected_facility_json = request.session.get('selected_facility')

        # Check if selected_facility_json is None
        if selected_facility_json is None:
            # Handle the case when selected_facility_json is None (perhaps redirect to an error page)
            return HttpResponse("Selected facility information not found.")
        # Attempt to load the JSON
        try:
            selected_facility_dict = json.loads(selected_facility_json)
        except json.JSONDecodeError as e:
            # Handle the case when JSON decoding fails (perhaps log the error)
            return HttpResponse(f"Error decoding JSON: {str(e)}")

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
        khis_perf = KhisPerformance.objects.filter(mfl_code=selected_facility.mfl_code,
                                                   quarter_year=quarter_year).values()
        if dqa:
            # loop through both models QI_Projects and Program_qi_projects using two separate lists
            dqa_df = [
                {'indicator': x.indicator,
                 'facility': x.facility_name.name,
                 'mfl_code': x.facility_name.mfl_code,
                 'Source': x.total_source,
                 "MOH 731": x.total_731moh,
                 "last month source": x.field_3,
                 "last month 731": x.field_7,
                 "quarter_year": x.quarter_year.quarter_year,
                 } for x in dqa
            ]
            # Finally, you can create a dataframe from this list of dictionaries.
            dqa_df = pd.DataFrame(dqa_df)
            indicators_to_use = ['Total Infant prophylaxis', 'Maternal HAART Total ', 'Number tested Positive _Total',
                                 'Total Positive (PMTCT)', 'Number of adults and children starting ART', 'Starting_TPT',
                                 'New & Relapse TB_Cases', 'Number of adults and children Currently on ART', 'PrEP_New',
                                 'GBV_Sexual violence', 'GBV_Emotional and /Physical Violence',
                                 'Cervical Cancer Screening (Women on ART)', 'TB_PREV_N', 'TX_ML', 'RTT'
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
            dqa_df['indicator'] = dqa_df['indicator'].replace('RTT', "TX_RTT")
            dqa_df['indicator'] = dqa_df['indicator'].replace('TB_PREV_N', "TB_PREV_N")

            quarterly_indicators = dqa_df[['indicator', 'facility', 'mfl_code',
                                           'quarter_year', 'last month source', 'last month 731']]

            indicators_to_use = ['TX_RTT', 'TX_ML', 'Number Current on ART Total']
            quarterly_indicators = quarterly_indicators[quarterly_indicators['indicator'].isin(indicators_to_use)]
            quarterly_indicators = quarterly_indicators.rename(columns={"last month source": "Source",
                                                                        "last month 731": "MOH 731"})
            # Replace TX_RTT and TX_ML with 0 in the MOH 731 column
            quarterly_indicators.loc[quarterly_indicators['indicator'] == 'TX_RTT', 'MOH 731'] = 0
            quarterly_indicators.loc[quarterly_indicators['indicator'] == 'TX_ML', 'MOH 731'] = 0

            dqa_df = dqa_df[~dqa_df['indicator'].isin(indicators_to_use)]
            del dqa_df['last month 731']
            del dqa_df['last month source']
            dqa_df = pd.concat([dqa_df, quarterly_indicators])
            if dqa_df.empty:
                messages.info(request, f"A few DQA indicators for {selected_facility} have been capture but not "
                                       f"enough for data visualization")
            if fyj_perf:
                fyj_perf_df = make_performance_df(fyj_perf, 'DATIM')
                if dqa_df.empty:
                    messages.info(request, f"A few DATIM indicators for {selected_facility} have been capture but not "
                                           f"enough for data visualization")


            else:
                fyj_perf_df = pd.DataFrame(columns=['mfl_code', 'quarter_year', 'indicator', 'DATIM'])
                messages.info(request, f"No DATIM data for {selected_facility} {quarter_year}!")

            merged_df = dqa_df.merge(fyj_perf_df, on=['mfl_code', 'quarter_year', 'indicator'], how='right')
            if khis_perf:
                khis_perf_df = make_performance_df(khis_perf, 'KHIS')

                tx_curr_khis = khis_perf_df[khis_perf_df['indicator'] == "Number Current on ART Total"]

                # apply the function to the 'date' column and store the result in a new column
                tx_curr_khis['month_number'] = tx_curr_khis['month'].apply(get_month_number)
                tx_curr_khis = tx_curr_khis.sort_values('month_number', ascending=False).head(1)
                del tx_curr_khis['month_number']
                del tx_curr_khis['month']
                khis_others = khis_perf_df[khis_perf_df['indicator'] != "Number Current on ART Total"]

                khis_others = khis_others.groupby(['indicator', 'quarter_year', 'mfl_code']).sum().reset_index()

                khis_perf_df = pd.concat([khis_others, tx_curr_khis])
            else:
                khis_perf_df = pd.DataFrame(columns=['indicator', 'facility', 'mfl_code', 'KHIS',
                                                     'quarter_year'])
            if "KHIS" in merged_df.columns:
                del merged_df['KHIS']
            merged_df = khis_perf_df.merge(merged_df, on=['mfl_code', 'quarter_year', 'indicator'], how='right').fillna(
                0)

            try:
                merged_df = merged_df[
                    ['mfl_code', 'facility', 'indicator', 'quarter_year', 'Source', 'MOH 731', 'KHIS', 'DATIM']]
            except KeyError:
                messages.info(request, f"No KHIS data for {selected_facility} {quarter_year}!")
                return redirect(request.path_info)
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
                dicts[f"{indy} ({quarter})"] = bar_chart(merged_df_viz, "data sources", "performance",
                                                         has_khis_731_datim=True)
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
        # Create a new PDF object using ReportLab
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'filename="dqa summary {selected_facility} {quarter_year}.pdf"'
        pdf = canvas.Canvas(response, pagesize=letter)

        # Write some content to the PDF
        for data in dqa:
            name = data.facility_name.name
            mfl_code = data.facility_name.mfl_code
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
        # add_footer(pdf, ,request.user)
        pdf.setFont("Helvetica", 4)
        pdf.setFillColor(colors.grey)
        pdf.drawString((letter[0] / 3) + 30, 0.5 * inch,
                       f"Report generated by : {request.user}    Time: {datetime.now()}")
        pdf.restoreState()
        pdf.setFont("Helvetica-Bold", 12)
        coordinates = [
            (70, 590), (325, 590),
            (70, 430), (325, 430),
            (70, 270), (325, 270),
            (70, 110), (325, 110),
            (70, 590), (325, 590),
            (70, 430), (325, 430),
            (70, 270), (325, 270),
            (70, 110), (325, 110),
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
        pdf.showPage()
        pdf.saveState()
        add_footer(pdf, request.user)
        pdf.restoreState()
        pdf.setFont("Helvetica", 12)
        pdf.setFillColor(colors.black)
        pdf.drawString(280, 750, f"AUDIT TEAM ")

        audit_team = AuditTeam.objects.filter(facility_name__id=selected_facility.id,
                                              quarter_year__quarter_year=quarter_year)

        # Create a list to hold the data for the table
        data = [['Name', 'Carder', 'Organization', 'Review Period']]
        # Loop through the audit_team queryset and append the required fields to the data list
        for audit in audit_team:
            data.append([audit.name, audit.carder, audit.organization, audit.quarter_year])

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
        x, y = 80, 740
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
        widths = [71, 71, 71, 81, 80, 51, 71]

        # Create the table object with the column widths
        table = Table(data, colWidths=widths)
        table.setStyle(table_style)

        # Define the initial position for the table
        x, y = 80, 740
        # Add the table to the PDF object
        table.wrapOn(pdf, 0, 0)
        table_height = table._height
        table.drawOn(pdf, x, y - table_height)
        # ++++++++++++++++++++++++++++++++++++++++++++++++++++
        # Write Service Quality Assessment
        # ++++++++++++++++++++++++++++++++++++++++++++++++++++
        write_sqa(pdf, request, selected_facility, quarter_year)
        pdf.save()
        return response


def get_month_number(date_string):
    # define a function to extract the month number from a date string
    date_obj = datetime.strptime(date_string, '%b %Y')
    return date_obj.month


def make_performance_df(fyj_perf, value):
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
                 "tb_stat_d": "New & Relapse TB cases", "ipt": "Number Starting IPT Total", "tb_prev_n": "TB_PREV_N",
                 "tx_ml": "TX_ML", "tx_rtt": "TX_RTT"})

    try:
        indicators_to_use_perf = ['mfl_code', 'quarter_year', "Number initiated on PrEP",
                                  'Maternal HAART Total', 'Number Tested Positive Total',
                                  'Total Positive (PMTCT)', 'Number Starting ART Total',
                                  'New & Relapse TB cases', 'Number Starting IPT Total',
                                  'Number Current on ART Total', "Gend_GBV Sexual Violence",
                                  'Gend_GBV_Physical and Emotional', 'Number Screened for Cervical Cancer',
                                  'Total Infant prophylaxis', 'TB_PREV_N', 'TX_ML', 'TX_RTT'
                                  ]
        fyj_perf_df = fyj_perf_df[indicators_to_use_perf]
        fyj_perf_df = pd.melt(fyj_perf_df, id_vars=['mfl_code', 'quarter_year'],
                              value_vars=list(fyj_perf_df.columns[2:]),
                              var_name='indicator', value_name=value)
    except KeyError:
        fyj_perf_df['Gend_GBV_Physical and Emotional'] = 0
        indicators_to_use_perf = ['mfl_code', 'quarter_year', "Number initiated on PrEP",
                                  'Maternal HAART Total', 'Number Tested Positive Total',
                                  'Total Positive (PMTCT)', 'Number Starting ART Total',
                                  'New & Relapse TB cases', 'Number Starting IPT Total',
                                  'Number Current on ART Total', "Gend_GBV Sexual Violence",
                                  'Gend_GBV_Physical and Emotional', 'Number Screened for Cervical Cancer',
                                  'Total Infant prophylaxis', 'month'
                                  ]
        fyj_perf_df = fyj_perf_df[indicators_to_use_perf]

        fyj_perf_df = pd.melt(fyj_perf_df, id_vars=['mfl_code', 'quarter_year', 'month'],
                              value_vars=list(fyj_perf_df.columns[2:]),
                              var_name='indicator', value_name=value)
    return fyj_perf_df


def create_dqa_df(dqa):
    # loop through both models QI_Projects and Program_qi_projects using two separate lists
    dqa_df = [
        {'indicator': x.indicator,
         'facility': x.facility_name.name,
         'mfl_code': x.facility_name.mfl_code,
         'Source': x.total_source,
         "MOH 731": x.total_731moh,
         "last month source": x.field_3,
         "last month 731": x.field_7,
         "quarter_year": x.quarter_year.quarter_year,
         } for x in dqa
    ]
    # Finally, you can create a dataframe from this list of dictionaries.
    dqa_df = pd.DataFrame(dqa_df)
    indicators_to_use = ['Total Infant prophylaxis', 'Maternal HAART Total ', 'Number tested Positive _Total',
                         'Total Positive (PMTCT)', 'Number of adults and children starting ART', 'Starting_TPT',
                         'New & Relapse TB_Cases', 'Number of adults and children Currently on ART', 'PrEP_New',
                         'GBV_Sexual violence', 'GBV_Emotional and /Physical Violence',
                         'Cervical Cancer Screening (Women on ART)', 'TB_PREV_N', 'TX_ML', 'RTT'
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
    dqa_df['indicator'] = dqa_df['indicator'].replace('RTT', "TX_RTT")
    dqa_df['indicator'] = dqa_df['indicator'].replace('TB_PREV_N', "TB_PREV_N")

    quarterly_indicators = dqa_df[['indicator', 'facility', 'mfl_code',
                                   'quarter_year', 'last month source', 'last month 731']]

    indicators_to_use = ['TX_RTT', 'TX_ML', 'Number Current on ART Total']
    quarterly_indicators = quarterly_indicators[quarterly_indicators['indicator'].isin(indicators_to_use)]
    quarterly_indicators = quarterly_indicators.rename(columns={"last month source": "Source",
                                                                "last month 731": "MOH 731"})
    # Replace TX_RTT and TX_ML with 0 in the MOH 731 column
    quarterly_indicators.loc[quarterly_indicators['indicator'] == 'TX_RTT', 'MOH 731'] = 0
    quarterly_indicators.loc[quarterly_indicators['indicator'] == 'TX_ML', 'MOH 731'] = 0

    dqa_df = dqa_df[~dqa_df['indicator'].isin(indicators_to_use)]
    del dqa_df['last month 731']
    del dqa_df['last month source']
    dqa_df = pd.concat([dqa_df, quarterly_indicators])
    return dqa_df


def compare_data_verification(merged_df, pepfar_col, description_list=None):
    try:
        merged_viz_df = merged_df.copy()
        merged_viz_df[pepfar_col] = merged_viz_df[pepfar_col].astype(int)
        merged_viz_df['Source'] = merged_viz_df['Source'].astype(int)
        merged_viz_df[f'Difference ({pepfar_col}-Source)'] = (merged_viz_df[pepfar_col] - merged_viz_df['Source'])
        merged_viz_df['Absolute difference proportion'] = round(
            (merged_viz_df[pepfar_col] - merged_viz_df['Source']) / merged_viz_df['Source'] * 100, 1).abs()

        merged_viz_df['Percentage'] = merged_viz_df['Absolute difference proportion'].astype(str) + " %"
        cond_list = [merged_viz_df['Absolute difference proportion'] > 10,
                     (merged_viz_df['Absolute difference proportion'] > 5) & (
                             merged_viz_df['Absolute difference proportion'] <= 10),
                     merged_viz_df['Absolute difference proportion'] <= 5]
        choice_list = ["Needs urgent remediation", "Needs improvement", "Meets standard"]
        merged_viz_df['Score'] = np.select(cond_list, choice_list, default="0")
        merged_viz_df.sort_values('Absolute difference proportion', inplace=True)
        merged_viz_df["Score"] = merged_viz_df["Score"].astype("category")
        merged_viz_df['indicator'] = merged_viz_df['indicator'].replace('Number Starting ART Total', 'TX_NEW')
        merged_viz_df['indicator'] = merged_viz_df['indicator'].replace('Number Tested Positive Total', 'HTS_TST_POS')
        merged_viz_df['indicator'] = merged_viz_df['indicator'].replace('Number Starting IPT Total', 'TB_PREV')
        merged_viz_df['indicator'] = merged_viz_df['indicator'].replace('Number Current on ART Total', 'TX_CURR')
        merged_viz_df['indicator'] = merged_viz_df['indicator'].replace('Number initiated on PrEP', 'PrEP_NEW')
        merged_viz_df['indicator'] = merged_viz_df['indicator'].replace('Number Screened for Cervical Cancer',
                                                                        'CXCA_SCRN')
        merged_viz_df = merged_viz_df.rename(
            columns={"Absolute difference proportion": "Absolute difference proportion (Difference/Source*100)"})
    except KeyError:
        merged_viz_df = pd.DataFrame(columns=['indicator', 'quarter_year', 'mfl_code', 'Source', 'MOH 731', 'KHIS',
                                              pepfar_col, f'Difference ({pepfar_col}-Source)',
                                              'Absolute difference proportion (Difference/Source*100)', 'Percentage',
                                              'Score'])

    if description_list:
        merged_df = pd.melt(merged_df, id_vars=['mfl_code', 'indicator', 'quarter_year'],
                            value_vars=list(merged_df.columns[3:]),
                            var_name='data sources', value_name='performance')
    else:
        merged_df = pd.melt(merged_df, id_vars=['indicator', 'quarter_year'],
                            value_vars=list(merged_df.columns[2:]),
                            # value_vars=['Source', 'Monthly Report', pepfar_col],
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
        dicts[f"{indy} ({quarter})"] = bar_chart(merged_df_viz, "data sources", "performance", has_khis_731_datim=True)
    return dicts, merged_viz_df


# def calc_percentage(row):
#     """
#     Calculates the percentage of 'greens', 'yellows', and 'reds' values in the given row
#     and returns a new row with the percentage values added as new columns.
#
#     Args:
#         row: A pandas Series representing a single row in a DataFrame.
#
#     Returns:
#         A new pandas Series representing the same row as the input, but with three additional
#         columns: 'greens %', 'yellows %', and 'reds %'. These columns contain the percentage
#         of 'greens', 'yellows', and 'reds' values in the row, respectively.
#     """
#     total = row['greens'] + row['yellows'] + row['reds'] + row['not applicable']
#
#     # Check for division by zero
#     if total == 0:
#         return row
#
#     # Calculate the percentage values and format them as strings with one decimal place and a percent sign
#     row['greens %'] = f"{round(row['greens'] / total * 100, 1)}%"
#     if row['greens %'] == '0.0%':
#         row['greens %'] = ''
#     row['yellows %'] = f"{round(row['yellows'] / total * 100, 1)}%"
#     if row['yellows %'] == '0.0%':
#         row['yellows %'] = ''
#     row['reds %'] = f"{round(row['reds'] / total * 100, 1)}%"
#     if row['reds %'] == '0.0%':
#         row['reds %'] = ''
#     row['not applicable %'] = f"{round(row['not applicable'] / total * 100, 1)}%"
#     if row['not applicable %'] == '0.0%':
#         row['not applicable %'] = ''
#
#     return row
def calc_percentage(row):
    """
    Calculates the percentage of 'greens', 'yellows', and 'reds' values in the given row
    and returns a new row with the percentage values added as new columns.

    Args:
        row: A pandas Series representing a single row in a DataFrame.

    Returns:
        A new pandas Series representing the same row as the input, but with three additional
        columns: 'greens %', 'yellows %', and 'reds %'. These columns contain the percentage
        of 'greens', 'yellows', and 'reds' values in the row, respectively.
    """
    total = row['blues'] + row['greens'] + row['light_greens'] + row['yellows'] + row['reds'] + row['not applicable']

    # Check for division by zero
    if total == 0:
        return row

    # Calculate the percentage values and format them as strings with one decimal place and a percent sign
    row['blues %'] = f"{round(row['blues'] / total * 100, 1)}%"
    if row['blues %'] == '0.0%':
        row['blues %'] = ''
    row['greens %'] = f"{round(row['greens'] / total * 100, 1)}%"
    if row['greens %'] == '0.0%':
        row['greens %'] = ''
    row['light_greens %'] = f"{round(row['light_greens'] / total * 100, 1)}%"
    if row['light_greens %'] == '0.0%':
        row['light_greens %'] = ''
    row['yellows %'] = f"{round(row['yellows'] / total * 100, 1)}%"
    if row['yellows %'] == '0.0%':
        row['yellows %'] = ''
    row['reds %'] = f"{round(row['reds'] / total * 100, 1)}%"
    if row['reds %'] == '0.0%':
        row['reds %'] = ''
    row['not applicable %'] = f"{round(row['not applicable'] / total * 100, 1)}%"
    if row['not applicable %'] == '0.0%':
        row['not applicable %'] = ''

    return row


def different_dfs(system_assessments_df, calculation_mapping):
    dfs = {}

    for calculation_value, (label, column_name) in calculation_mapping.items():
        if calculation_value == 0:
            # Handle the 'not applicable' case separately
            na_df = system_assessments_df[(system_assessments_df['calculations'] == 0) |
                                          (system_assessments_df['calculations'].isnull())].fillna(0)
            na_df = na_df.rename(columns={"count": column_name})
            if "model_name" in sub_df.columns:
                grouped_df = na_df.groupby(['description', 'model_name']).sum(numeric_only=True)[
                    column_name].reset_index().sort_values(
                    column_name, ascending=False)
            else:
                grouped_df = na_df.groupby(['description'])[
                    column_name].sum(numeric_only=True).reset_index().sort_values(
                    column_name, ascending=False)

            dfs[label] = (na_df, grouped_df)
        else:
            sub_df = system_assessments_df[system_assessments_df['calculations'] == calculation_value]
            sub_df = sub_df.rename(columns={"count": column_name})
            if "model_name" in sub_df.columns:
                grouped_df = sub_df.groupby(['description', 'model_name'])[
                    column_name].sum(numeric_only=True).reset_index().sort_values(
                    column_name, ascending=False)
            else:
                grouped_df = sub_df.groupby(['description'])[
                    column_name].sum(numeric_only=True).reset_index().sort_values(
                    column_name, ascending=False)
            dfs[label] = (sub_df, grouped_df)
    return dfs


# Example usage with a custom calculation_mapping:
custom_mapping = {
    1: ("red", "reds"),
    2: ("yellow", "yellows"),
    3: ("light_green", "light_greens"),
    4: ("green", "greens"),
    5: ("blue", "blues"),
    0: ("not_applicable", "not applicable"),
}


def get_df_from_results(result_dfs):
    if "red" in result_dfs.keys():
        red_df, red_grouped_df = result_dfs['red']
    else:
        red_df = pd.DataFrame(columns=['wards', 'ward_code', 'description', "auditor's note", 'calculations', 'reds'])
        red_grouped_df = pd.DataFrame(columns=['description', 'reds'])

    if "yellow" in result_dfs.keys():
        yellow_df, yellow_grouped_df = result_dfs['yellow']
    else:
        yellow_df = pd.DataFrame(
            columns=['wards', 'ward_code', 'description', "auditor's note", 'calculations', 'yellows'])
        yellow_grouped_df = pd.DataFrame(columns=['description', 'yellows'])

    if "light_green" in result_dfs.keys():
        light_green_df, light_green_grouped_df = result_dfs['light_green']
    else:
        light_green_df = pd.DataFrame(
            columns=['wards', 'ward_code', 'description', "auditor's note", 'calculations', 'light_greens'])
        light_green_grouped_df = pd.DataFrame(columns=['description', 'light_greens'])

    if "green" in result_dfs.keys():
        green_df, green_grouped_df = result_dfs['green']
    else:
        green_df = pd.DataFrame(
            columns=['wards', 'ward_code', 'description', "auditor's note", 'calculations', 'greens'])
        green_grouped_df = pd.DataFrame(columns=['description', 'greens'])

    if "blue" in result_dfs.keys():
        blue_df, blue_grouped_df = result_dfs['blue']
    else:
        blue_df = pd.DataFrame(columns=['wards', 'ward_code', 'description', "auditor's note", 'calculations', 'blues'])
        blue_grouped_df = pd.DataFrame(columns=['description', 'blues'])

    if "not_applicable" in result_dfs.keys():
        na_df, na_df_grouped_df = result_dfs['not_applicable']
    else:
        na_df = pd.DataFrame(
            columns=['wards', 'ward_code', 'description', "auditor's note", 'calculations', 'not applicable'])
        na_df_grouped_df = pd.DataFrame(columns=['description', 'not applicable'])
    return red_df, red_grouped_df, yellow_df, yellow_grouped_df, light_green_df, light_green_grouped_df, green_df, green_grouped_df, blue_df, blue_grouped_df, na_df, na_df_grouped_df


def prepare_data_system_assessment(system_assessments_df, custom_mapping, description_list=None):
    # system_assessments_df.to_csv("system_assessments_df.csv", index=False)
    result_dfs = different_dfs(system_assessments_df, custom_mapping)

    red, reds, yellow, yellows, light_green, light_greens, green, greens, blue, blues, na_df, na_dfs = get_df_from_results(
        result_dfs)
    if description_list:
        scores_df = greens.merge(yellows, on='description', how='outer').merge(reds, on='description',
                                                                               how='outer').merge(
            na_dfs, on='description', how='outer')
    else:
        scores_df = greens.merge(yellows, on=['description', 'model_name'], how='outer').merge(reds, on=['description',
                                                                                                         'model_name'],
                                                                                               how='outer').merge(
            na_dfs, on=['description', 'model_name'], how='outer').merge(
            light_greens, on=['description', 'model_name'], how='outer').merge(
            blues, on=['description', 'model_name'], how='outer')
        scores_df = scores_df[['description', 'model_name', 'blues', 'light_greens', 'greens', 'yellows', 'reds',
                               'not applicable']].fillna(0)
        for i in scores_df.columns[2:]:
            scores_df[i] = scores_df[i].astype(int)

    m_e_structures_list = []
    if description_list:
        scores_df = scores_df.set_index('description')
        scores_df = scores_df.loc[description_list].fillna(0)
        # display(scores_df)
        for i in scores_df.columns[1:]:
            scores_df[i] = scores_df[i].astype(int)
        scores_df = scores_df.reset_index()
        # Slice the dataframe by description
        df_list = [scores_df[scores_df['description'].isin(description_list[:5])],
                   scores_df[scores_df['description'].isin(description_list[5:12])],
                   scores_df[scores_df['description'].isin(description_list[12:17])],
                   scores_df[scores_df['description'].isin(description_list[17:21])],
                   scores_df[scores_df['description'].isin(description_list[21:])]]

        m_e_structures = df_list[0]
        m_e_structures_list = list(m_e_structures['description'].unique())
        value_map = {
            "There is a documented structure/chart that clearly identifies positions that have data management responsibilities at the Facility.": "Documented structure/chart",
            "Positions dedicated to M&E and data management systems in the facility are filled.": "Dedicated position",
            "There is a training plan which includes staff involved in data-collection and reporting at all levels in the reporting process.": "Training plan",
            "There is a designated staff responsible for reviewing the quality of data (i.e., accuracy, completeness and timeliness) before submission to the Sub County.": "Designated DQA staff",
            "All relevant staff have received training on the data management processes and tools.": "Training on data mnx"
        }

        # loop through the value_map and replace the old values with the new values using .loc
        for old_value, new_value in value_map.items():
            m_e_structures.loc[m_e_structures['description'] == old_value, 'description'] = new_value

        m_e_structures = m_e_structures.copy()
        m_e_structures['blues'] = 0
        m_e_structures['light_greens'] = 0

        m_e_data_mnx = df_list[1]
        m_e_data_mnx_list = list(m_e_data_mnx['description'].unique())

        # create a dictionary to map old values to new values
        value_map = {
            "The facility has data quality SOPs for monthly reporting processes and quality checks": "Data quality SOPs",
            "The facility conducts internal data quality checks and validation before submission of reports": "Internal data quality checks",
            "The facility has conducted a data quality audit in the last 6 months": "Conducted DQA 6/12 ago",
            "There is a documented data improvement action plan? Verify by seeing": "Data improvement action plan",
            "Feedback is systematically provided to the facility on the quality of their reporting (i.e., accuracy, completeness and timeliness).": "Systematic feedback",
            "The facility regularly reviews data to inform decision making (Ask for evidence e.g.meeting minutes, MDT feedback data template": "Regular reviews",
            "The facility is aware of their yearly targets and are monitoring monthly performance using wall charts": "Yearly targets awareness"
        }

        # loop through the value_map and replace the old values with the new values using .loc
        for old_value, new_value in value_map.items():
            m_e_data_mnx.loc[m_e_data_mnx['description'] == old_value, 'description'] = new_value

        m_e_data_mnx = m_e_data_mnx.copy()
        m_e_data_mnx['blues'] = 0
        m_e_data_mnx['light_greens'] = 0

        m_e_indicator_definition = df_list[2]
        m_e_indicator_definition_list = list(m_e_indicator_definition['description'].unique())

        # create a dictionary to map old values to new values
        value_map = {
            'The facility has been provided with indicator definitions reference guides for both MOH and MER 2.6 '
            'indicators.': 'Indicator reference guides',
            'The facility staff are very clear on what they are supposed to report on.': 'Clarity on reporting content',
            'The facility staff are very clear on how (e.g., in what specific format) reports are to be submitted.': 'Clarity on reporting format',
            'The facility staff are very clear on to whom the reports should be submitted.': 'Clarity on reporting '
                                                                                             'recipients',
            'The facility staff are very clear on when the reports are due.': 'Clarity on reporting deadlines'
        }

        # loop through the value_map and replace the old values with the new values using .loc
        for old_value, new_value in value_map.items():
            m_e_indicator_definition.loc[
                m_e_indicator_definition['description'] == old_value, 'description'] = new_value
        m_e_indicator_definition = m_e_indicator_definition.copy()
        m_e_indicator_definition['blues'] = 0
        m_e_indicator_definition['light_greens'] = 0

        m_e_data_collect_report = df_list[3]
        m_e_data_collect_report_list = list(m_e_data_collect_report['description'].unique())

        # create a dictionary to map old values to new values
        value_map = {
            'The facility has the latest versions of source documents (registers) and aggregation tool (MOH 731)': 'Latest source documents and MOH 731',
            'Clear instructions have been provided to the facility on how to complete the data collection and reporting forms/tools.': 'Clear instructions',
            'The facility has the revised HTS register in all service delivery points and a clear inventory is available detailing the number of HTS registers in use by service delivery point': 'Revised HTS register',
            'HIV client files are well organised and stored in a secure location': 'Organized HIV files'}

        # loop through the value_map and replace the old values with the new values using .loc
        for old_value, new_value in value_map.items():
            m_e_data_collect_report.loc[m_e_data_collect_report['description'] == old_value, 'description'] = new_value
        m_e_data_collect_report = m_e_data_collect_report.copy()
        m_e_data_collect_report['blues'] = 0
        m_e_data_collect_report['light_greens'] = 0

        m_e_emr_systems = df_list[4]
        m_e_emr_systems_list = list(m_e_emr_systems['description'].unique())

        # create a dictionary to map old values to new values
        value_map = {
            'Do you use your EMR to generate reports?': 'EMR report generation',
            'There is a clearly documented and actively implemented database administration procedure in place. This '
            'includes backup/recovery procedures, security admininstration, and user administration.': 'Database '
                                                                                                       'administration '
                                                                                                       'procedure',
            'The facility carries out daily back up of EMR data (Ask to see the back up for the day of the DQA)': 'Daily '
                                                                                                                  'EMR data backup',
            'The facility has conducted an RDQA of the EMR system in the last 3 months with documented action points,'
            'What is your main challenge regarding data management and reporting?': 'Recent RDQA with action points '
        }

        # loop through the value_map and replace the old values with the new values using .loc
        for old_value, new_value in value_map.items():
            m_e_emr_systems.loc[m_e_emr_systems['description'] == old_value, 'description'] = new_value
        m_e_emr_systems = m_e_emr_systems.copy()
        m_e_emr_systems['blues'] = 0
        m_e_emr_systems['light_greens'] = 0
    else:
        # documentation
        m_e_structures = scores_df[scores_df['model_name'] == "documentation"]
        value_map = {
            'The M&E plan has a logic model/ results framework and/or Theory of Change linking project/ program goal, outcomes and outputs':
                'M&E plan with logic model/ToC',
            'There are guidelines and schedules for routine supervisory site visits':
                'Guidelines for site visits',
            'There is a detailed data flow diagram from Service Delivery Sites (facilities) to Intermediate Aggregation Levels (e.g. project district or regional offices); and from Intermediate Aggregation Levels (if any) to the national office (could be part of the M&E plan)':
                'Detailed data flow diagram',
            'Sub grantee have a copy of standard guidelines describing reporting requirements (what to report on, due dates, data sources, report recipients, etc.)':
                'Standard reporting guidelines for sub grantees',
            'There is a written guideline to all reporting entities (e.g., regions, districts, facilities) on reporting requirements and deadlines':
                'Written guidelines for reporting entities',
            'There is an up to date M&E plan/PMP':
                'Up-to-date M&E plan/PMP',
            'There is an up-to-date M&E work plan that details the implementation timeline for M&E activities and indicates persons responsible for each activity':
                'Up-to-date M&E work plan with responsibilities',
            'The M&E plan or other project design document has an organogram describing the organization of the M&E unit in relation to the overall project team':
                'Organogram in M&E plan/project design document',
            'All indicators being tracked have documented operational definitions (including data disaggregation by age, sex, etc) in the indicator reference sheets':
                'Indicators with operational definitions and data disaggregation',
            'The M&E plan includes indicators for measuring input, outputs, outcomes and where relevant, impact indicators, and the indicators are linked to the project objectives':
                'M&E plan with linked indicators to objectives',
            "There is an up to date Performance Indicator Tracking Table that is complete (include a list of indicators, baseline, annual and cummulative targets, and data sources)":
                'Up-to-date Performance Indicator Tracking Table with complete data',
            'There is a written description or guidance of how project activities (such as service delivery, training and follow-up, etc) are documented in source documents (e.g registers, supervision reports, etc)':
                'Written description of documenting project activities in source documents'
        }

        # loop through the value_map and replace the old values with the new values using .loc
        for old_value, new_value in value_map.items():
            m_e_structures.loc[m_e_structures['description'] == old_value, 'description'] = new_value
        # data analysis system
        m_e_data_mnx = scores_df[scores_df['model_name'] == "data-quality"]
        value_map = {
            'The DQA plan is implemented and on track as planned': 'Implemented DQA plan on track',
            'There are clear links between fields on data entry/collection forms and summary or compilation forms to reduce transcription error (for service statistics, training data and other project data that involves compiliation)': 'Clear links between data entry/collection forms and summary forms',
            'There are designated staff responsible for reviewing the quality of data (i.e., accuracy, completeness,  timeliness and confidentiality ) received from sub-reporting levels (e.g., regions, districts, facilities)': 'Designated staff for data quality review',
            'There are documented procedures for addressing specific data quality challenges (e.g. double-counting, “lost to follow-up”)': 'Procedures for addressing data quality challenges',
            'There are up-to-date DQA reports that are up to standard': 'Up-to-date and standard DQA reports',
            'There is evidence that corrections have been made to historical data following data quality assessments': 'Corrections made to historical data after DQA',
            'There is evidence that supervisory site visits have been made in the last 12 months where data quality has been reviewed': 'Supervisory site visits with data quality review in the last 12 months',
            'There is up-to-date DQA plan which clearly outlines the DQA strategy (including the frequency for which data from different data sources or indicators will be assessed and for what data quality dimensions-validity, reliability, integrity, precision, timeliness, completeness, confidentiality and ethics)': 'Up-to-date DQA plan with strategy details',
            'To the extent possible, relevant data are collected with electronic devices (check if routine data and/or research/study data are collected with electronic devices, note the difference in the rationale)': 'Relevant data collected with electronic devices',
            'The number of transcription stages (manual transfer of data from one form to another) are minimized to limit transcription error (check if data are entered directly into the database or they are aggregated in another software or aggregated manually first)': 'Minimized transcription stages to limit error',
            'A senior staff member (e.g., Program Director) is responsible for reviewing the aggregated numbers prior to the submission reports from the country office': 'Senior staff review of aggregated numbers',
            'All expected sub grantees reports have been received': 'All expected sub grantees reports received',
            'M&E work plan includes regular internal DQA activities': 'M&E work plan includes internal DQA activities',
            'All reporting levels (facilities, districts, regions)  are reporting on all required indicators': 'All reporting levels report on required indicators',
            'At least once a year both program and M&E staff review a sample of  completed data collection tools  for completion,  accuracy or service quality issues': 'Annual review of data collection tools',
            'Data reported corresponds with donor-specified report periods': 'Data corresponds with donor report periods',
            'Definitions and interpretations of indicators are followed consistently when transferring data from data collection forms to summary formats and reports': 'Consistent use of indicator definitions',
            'Donor reports are submitted on time': 'Donor reports submitted on time',
            'Feedback is provided to all reporting levels  on the quality of their reporting  (i.e., accuracy, completeness and timeliness)': 'Feedback provided on reporting quality',
            'Performance indicator definitions are consistent with existing standard guidelines in the FYJ Indicator database (select a sample)': 'Performance indicator definitions consistent with FYJ database',
            'Standard forms/tools are used consistently by all reporting levels': 'Consistent use of standard forms/tools',
            'Steps are taken to limit calculation/aggregation errors, including automation  of spreadsheets where possible (for data aggregation)': 'Steps taken to limit calculation/aggregation errors',
            'Sub grantees reports are filled in completely (review a sample of the tools)': 'Sub grantees reports filled in completely',
            'Systems are in place for detecting missing data': 'Systems in place for detecting missing data',
            'Systems are in place to adjust for double-counting': 'Systems in place to adjust for double-counting',
            'Written instructions/guidance on correctly filling in data collection and reporting tools, including addressing data quality challenges is evident at different reporting levels (district/regional office, sub- grantee or facility level)': 'Written instructions/guidance on filling data collection/reporting tools'
        }
        # loop through the value_map and replace the old values with the new values using .loc
        for old_value, new_value in value_map.items():
            m_e_data_mnx.loc[m_e_data_mnx['description'] == old_value, 'description'] = new_value
        # data collection, reporting and management
        m_e_indicator_definition = scores_df[scores_df['model_name'] == "data-collection"]
        value_map = {
            'Safeguards (such as passwords and ascribing different data management roles to staff) are in place to prevent unauthorized changes to data': 'Safeguards for preventing unauthorized data changes',
            'There are standard source documents (e.g.register, training report template, supervision visits etc.) to record all types of project data (service statistics, training and follow-up, supervision visits, advocacy visits, etc).': 'Standard source documents for recording project data',
            'There is a data management guideline that describes all data-verification, aggregation, analysis and manipulation steps performed at each reporting level': 'Data management guideline for each reporting level',
            'The project has one or more electronic database which is up to date (last month data is available)': 'Up-to-date electronic databases',
            'There are clear written instructions for completing the data-collection and reporting forms': 'Clear instructions for completing forms',
            'There is a written description of  the project database -what is stored, who maintains/administers it, procedure for back-up etc.': 'Written description of project database',
            'There is a description of the filing system for paper-based data collection and/or reporting (e.g. if supervision visits are filed in physical cabinets and not uploaded in an electronic data capture system or database)': 'Description of paper-based data filing system',
            'The number of data collection tools is sufficient for program needs and not excessive (all data collected are reported)': 'Sufficient data collection tools',
            'There is management support for following up any persistent data gaps with partners': 'Management support for addressing data gaps',
            'There is no (or minimal) duplication in data collection requirements for staff/partners, i.e. they are not required to report the same activityion more than one tool': 'Minimized duplication in data collection requirements',
            'All sub-grantees use a standard reporting template': 'Standard reporting template for sub-grantees',
            'Data collection and reporting forms include all required program/project indicators': 'Inclusion of all required indicators in forms',
            'Historical data are properly stored, up to date and readily available (check 12-24 month data, depending on the project year)': 'Properly stored and up-to-date historical data',
            'Project data (service statistics, training, follow-up, advocacy, sensitization, etc) are disaggregated by sex, age and other criteria (income, location, etc)': 'Data disaggregation by various criteria',
            'Reporting forms/tools are  standardized across all district/regions of  project': 'Standardized reporting forms/tools across districts/regions',
            'Standard reporting forms/tools are available to staff responsible for data collection at the facilities, project district/region office, and national office': 'Availability of standard forms/tools to data collection staff'
        }

        # loop through the value_map and replace the old values with the new values using .loc
        for old_value, new_value in value_map.items():
            m_e_indicator_definition.loc[
                m_e_indicator_definition['description'] == old_value, 'description'] = new_value

        # data quality assessment
        m_e_data_collect_report = scores_df[scores_df['model_name'] == "data-quality-assessment"]
        value_map = {
            'Are procedures or safeguards in place to minimize data transcription errors?': 'Procedures to minimize data transcription errors',
            'Has the data ever been independently reviewed by a person outside the data collection effort': 'Independent review of data',
            'Is there a list of the required reporting units for the data?': 'List of required reporting units',
            'Did all the required reporting units (facilities, districts) report data for the reporting period?': 'All required reporting units submitted data',
            'Does the information collected measure what it is supposed to measure or the intended result?': 'Measurement alignment with intended result',
            'Are data available frequently enough to inform program management decisions?': 'Frequent data availability for program decisions',
            'If data are personally identifiable and sensitive, access to database is passworded and limited': 'Restricted access for sensitive data',
            'Is there independence in key data collection, management, and assessment procedures?': 'Independence in data procedures',
            'Is the date of data collection clearly identified in reports?': 'Clear identification of data collection date',
            'Is the data collection method/tool fine-tuned or exact enough to register the expected change? (E.g. an aggregated national system may not be a precise enough to measure a change of a few districts).': 'Precision of data collection tool',
            'If the indicator involve data manipulation such as calculation of rates or proportion,  is the same formulae are applied consistently (and correctly) within the reporting period and in all location?': 'Consistency in calculation formulae',
            'If the data is based on a sample, is the margin of error acceptable? (i.e. is it lesser than the expected change being measured? E.g. If a change of only 2 percent is expected and the margin of error is +/- 5 percent, then the tool is not precise enough to detect the change.)': 'Acceptable margin of error for sample data',
            'If the data is based on a sample, has the margin of error been reported along with the data?': 'Reporting of margin of error for sample data',
            'If data is from a sample, have the organizational procedures for ethical review of the data collection protocols been adhered to?': 'Ethical review adherence for sample data',
            'If data is from a sample, files such as pictures, success stories, and GIS data have been stored in a way that no individual or group of people can be identified': 'Protection of individual/group identity in sample data files',
            'If data is from a sample, does the reporting/presentation exaggerates the interpretation of the data?': 'Avoidance of data exaggeration in sample data',
            'If data is from a sample, are processes for obtaining informed consent in place?': 'Informed consent processes for sample data',
            'Are data collection and analysis methods documented in writing and being used to ensure the same procedures are followed each time?': 'Documentation and consistency of data collection and analysis methods',
            'If data are personally identifiable and sensitive, data are reported/presented in such a way that discrete variables cannot be used (alone or in combination) to identify an individual': 'Protection of personal identity in sensitive data reporting',
            'If data are personally identifiable and sensitive, the data is stored in a way that cannot be traced to an individual (personal identifiable information are replaced with  identification codes in the database)': 'Protection of personal identity in sensitive data storage',
            'Are the data available for the most current reporting period ?': 'Availability of data for the most current reporting period',
            'Are the limitations of the data collection tool well documented and reported': 'Documentation and reporting of data collection tool limitations',
            'Are mechanisms in place to prevent unauthorized changes to the data?': 'Mechanisms to prevent unauthorized data changes',
            'Are sound research methods being used to collect the data?': 'Use of sound research methods in data collection',
            'Are the data aggregated, analyzed and reported as soon as possible after collection?': 'Timely aggregation, analysis, and reporting of data',
            'For data from a secondary source, is there a confidence in the credibility of the data?': 'Confidence in credibility of secondary data',
            'Are the data used in computing the indicator measured from the same data source, with the same data collection tool within the reporting period, in different location (facilities, districts, regions)?': 'Consistency of data sources and collection tools for computing indicators',
            'Was data appropriately disaggregated (sex, age, geographical location) as planned?': 'Appropriate data disaggregation as planned',
            'Are there safeguards in place to prevent misrepresentation of data (such as marking up data, changing responses or falsification of data)?': 'Safeguards against misrepresentation of data',
            'Did the data collection tool focus on the information needed to answer the question or measure performance? (i.e. the tools and collection procedures are well designed and  limit the potential for systematic or random errors)': 'Focus of data collection tool on needed information',
            'Do data collected fall within a plausible range? (E.g. an indicator value of 400% compared to the target should raise a red flag)': 'Plausibility of collected data'
        }

        # loop through the value_map and replace the old values with the new values using .loc
        for old_value, new_value in value_map.items():
            m_e_data_collect_report.loc[m_e_data_collect_report['description'] == old_value, 'description'] = new_value

        # None
        m_e_emr_systems = pd.DataFrame(columns=['description', 'model_name', 'blues', 'light_greens', 'greens',
                                                'yellows', 'reds', 'not applicable'])
    all_dfs = pd.concat(
        [m_e_structures, m_e_data_mnx, m_e_indicator_definition, m_e_data_collect_report, m_e_emr_systems]).fillna(0)

    # display(all_dfs)
    for i in all_dfs.columns[2:]:
        all_dfs[i] = all_dfs[i].astype(int)
    # display(all_dfs)
    if description_list:
        all_dfs = pd.melt(all_dfs, id_vars=['description'], value_vars=['greens', 'yellows', 'reds', 'not applicable'],
                          var_name="Scores", value_name="# of scores")
    else:
        all_dfs = pd.melt(all_dfs, id_vars=['description'],
                          value_vars=['blues', 'greens', 'light_greens', 'yellows', 'reds', 'not applicable'],
                          var_name="Scores", value_name="# of scores")

    if description_list:
        all_dfs['Scores'] = all_dfs['Scores'].replace("greens", "Meets standards")
        all_dfs['Scores'] = all_dfs['Scores'].replace("yellows", "Needs improvement")
        all_dfs['Scores'] = all_dfs['Scores'].replace("reds", "Needs urgent remediation")

    else:
        all_dfs['Scores'] = all_dfs['Scores'].replace("greens", "Meets standards (Greens and Blues)")
        all_dfs['Scores'] = all_dfs['Scores'].replace("blues", "Meets standards (Greens and Blues)")
        all_dfs['Scores'] = all_dfs['Scores'].replace("light_greens", "Needs improvement (Light greens and Yellows)")
        all_dfs['Scores'] = all_dfs['Scores'].replace("yellows", "Needs improvement (Light greens and Yellows)")
        all_dfs['Scores'] = all_dfs['Scores'].replace("reds", "Needs urgent remediation (Reds)")
    all_dfs = all_dfs.groupby('Scores')['# of scores'].sum(numeric_only=True).reset_index().sort_values('# of scores',
                                                                                                        ascending=False)
    # calculate the total number of scores
    total_scores = all_dfs['# of scores'].sum()

    # add a column for the percentage of scores
    all_dfs['% of scores'] = round((all_dfs['# of scores'] / total_scores) * 100, 1)
    all_dfs['% of scores'] = all_dfs['% of scores'].astype(str) + '%'
    all_dfs['scores (%)'] = all_dfs['# of scores'].astype(str) + " (" + all_dfs['% of scores'] + ")"
    del all_dfs['% of scores']

    m_e_structures = m_e_structures.apply(calc_percentage, axis=1)

    m_e_data_mnx = m_e_data_mnx.apply(calc_percentage, axis=1)
    m_e_indicator_definition = m_e_indicator_definition.apply(calc_percentage, axis=1)
    m_e_data_collect_report = m_e_data_collect_report.apply(calc_percentage, axis=1)
    m_e_emr_systems = m_e_emr_systems.apply(calc_percentage, axis=1)

    def assign_component(df):
        if len(df) != 0:
            if len(m_e_structures_list) > 0:
                df.loc[df['description'].isin(m_e_structures_list), 'Component of the M&E System'] = \
                    'I - M&E Structure, Functions and Capabilities'
                df.loc[df['description'].isin(m_e_data_mnx_list), 'Component of the M&E System'] = \
                    'II- Data Management Processes'
                df.loc[df['description'].isin(m_e_indicator_definition_list), 'Component of the M&E System'] = \
                    'III- Indicator Definitions and Reporting Guidelines'
                df.loc[df['description'].isin(m_e_data_collect_report_list), 'Component of the M&E System'] = \
                    'IV- Data-collection and Reporting Forms / Tools'
                df.loc[df['description'].isin(m_e_emr_systems_list), 'Component of the M&E System'] = 'V- EMR Systems'
            else:
                df.loc[df['model_name'] == "documentation", 'Component of the M&E System'] = \
                    'I - Documentation'
                df.loc[df['model_name'] == "data-quality", 'Component of the M&E System'] = \
                    'II- Data Quality Systems'
                df.loc[df['model_name'] == "data-collection", 'Component of the M&E System'] = \
                    'III- Data Collection, Reporting and Management'
                df.loc[df['model_name'] == "data-quality-assessment", 'Component of the M&E System'] = \
                    'IV- Data Quality Assessment by Data Source'
            #                 df.loc[df['model_name'].isin(m_e_emr_systems_list), 'Component of the M&E System'] = 'V- EMR Systems'
            df.sort_values("Component of the M&E System", inplace=True)
            if "yellows" in df.columns:
                del df['yellows']
            if "reds" in df.columns:
                del df['reds']
            if "blues" in df.columns:
                del df['blues']
            df = df.reset_index(drop=True)
        else:
            df = pd.DataFrame(columns=['facilities', 'mfl_code', 'description', "auditor's note", 'calculations',
                                       'Component of the M&E System'])
        return df

    yellow = assign_component(yellow)
    red = assign_component(red)
    na_df = assign_component(na_df)
    green = assign_component(green)
    if description_list:
        blue = pd.DataFrame(columns=['wards', 'ward_code', 'description', "auditor's note", 'calculations',
                                     'model_name', 'blues'])
        light_green = pd.DataFrame(columns=['wards', 'ward_code', 'description', "auditor's note", 'calculations',
                                            'model_name', 'light_greens'])
    else:

        blue = assign_component(blue)
        light_green = assign_component(light_green)

    return m_e_structures, m_e_data_mnx, m_e_indicator_definition, m_e_data_collect_report, m_e_emr_systems, red, yellow, na_df, green, light_green, blue, all_dfs


def create_system_assessment_bar_charts(dataframe, chart_title, quarter_year, description_list=None):
    # if description_list:
    #     # create a stacked bar chart with custom colors
    #     colors = {'greens': 'green', 'yellows': 'yellow', 'reds': 'red',
    #               'not applicable': 'grey'}
    #     column_name=['greens', 'yellows', 'reds', 'not applicable']
    #     texts = [dataframe['greens %'], dataframe['yellows %'],
    #              dataframe['reds %'], dataframe['not applicable %']]
    # else:
    #     # create a stacked bar chart with custom colors
    #     colors = {'blues': 'blue', 'greens': 'green', 'light_greens': 'lightgreen', 'yellows': 'yellow', 'reds': 'red',
    #               'not applicable': 'grey'}
    #     column_name = ['blues', 'greens', 'light_greens', 'yellows', 'reds', 'not applicable']
    #     texts = [dataframe['blues %'], dataframe['greens %'], dataframe['light_greens %'], dataframe['yellows %'],
    #              dataframe['reds %'], dataframe['not applicable %']]
    if description_list:
        # create a stacked bar chart with custom colors
        colors = {'greens': 'green', 'yellows': 'yellow', 'reds': 'red',
                  'not applicable': 'grey'}
        column_name = ['greens', 'yellows', 'reds', 'not applicable']
        texts = [dataframe.get('greens %', 0), dataframe.get('yellows %', 0),
                 dataframe.get('reds %', 0), dataframe.get('not applicable %', 0)]
    else:
        # create a stacked bar chart with custom colors
        colors = {'blues': 'blue', 'greens': 'green', 'light_greens': 'lightgreen', 'yellows': 'yellow', 'reds': 'red',
                  'not applicable': 'grey'}
        column_name = ['blues', 'greens', 'light_greens', 'yellows', 'reds', 'not applicable']
        texts = [dataframe.get('blues %', 0), dataframe.get('greens %', 0), dataframe.get('light_greens %', 0),
                 dataframe.get('yellows %', 0), dataframe.get('reds %', 0), dataframe.get('not applicable %', 0)]

    fig = px.bar(dataframe, x='description', y=column_name, barmode='stack', color_discrete_map=colors, height=450)

    texts = texts
    for i, t in enumerate(texts):
        if i < len(fig.data):  # Check if i is within the range of fig.data
            fig.data[i].text = t
    # add labels and title
    fig.update_layout(xaxis_title='Description', yaxis_title='Frequency', title=f"{chart_title} ({quarter_year})")
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
                size=8
            ),
            title_font=dict(
                size=10
            )
        ),
        yaxis=dict(
            title_font=dict(
                size=8
            )
        ),
        legend=dict(
            font=dict(
                size=10
            )
        ),
        title=dict(
            font=dict(
                size=14
            )
        )
    )
    fig.update_traces(textfont_size=10)
    fig.update_layout(legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    ))

    # show the chart
    return plot(fig, include_plotlyjs=False, output_type="div")


@login_required(login_url='login')
def dqa_summary(request):
    if not request.user.first_name:
        return redirect("profile")
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
    # facility_form = FacilitySelectionForm(request.POST or None, initial=facility_form_initial)

    # form = QuarterSelectionForm(request.POST or None)
    # year_form = YearSelectionForm(request.POST or None)
    # facility_form = FacilitySelectionForm(request.POST or None)
    plot_div = None

    selected_quarter = "Qtr1"
    year_suffix = "21"
    selected_facility = None
    average_dictionary = None
    site_avg = None
    audit_team = None
    selected_quarter = "Qtr1"
    selected_year = "2021"
    if form.is_valid():
        selected_quarter = form.cleaned_data['quarter']

    if year_form.is_valid():
        selected_year = year_form.cleaned_data['year']
    facility_form = FacilitySelectionForm(request.POST or None,
                                          selected_year=selected_year,
                                          selected_quarter=selected_quarter,
                                          model_to_check=DataVerification)
    ##########################################
    # Show quarterly trends
    ##########################################
    quarterly_trend_fig = show_quarterly_trends(request, DataVerification, "Data Verification")

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
    system_assessments = None

    if selected_facility:
        dqa = DataVerification.objects.filter(facility_name__mfl_code=selected_facility.mfl_code,
                                              quarter_year__quarter_year=quarter_year)
        fyj_perf = FyjPerformance.objects.filter(mfl_code=selected_facility.mfl_code,
                                                 quarter_year=quarter_year).values()
        khis_perf = KhisPerformance.objects.filter(mfl_code=selected_facility.mfl_code,
                                                   quarter_year=quarter_year).values()

        if dqa:
            dqa_df = create_dqa_df(dqa)
            if dqa_df.empty:
                messages.info(request, f"A few DQA indicators for {selected_facility} have been capture but not "
                                       f"enough for data visualization")
        else:
            dqa_df = pd.DataFrame(columns=['indicator', 'facility', 'mfl_code', 'Source', 'MOH 731', 'KHIS',
                                           'quarter_year', 'last month'])
            messages.info(request, f"No DQA data for {selected_facility} {quarter_year}")
        if fyj_perf:
            fyj_perf_df = make_performance_df(fyj_perf, 'DATIM')
            if dqa_df.empty:
                messages.info(request, f"A few DATIM indicators for {selected_facility} have been capture but not "
                                       f"enough for data visualization")


        else:
            fyj_perf_df = pd.DataFrame(columns=['mfl_code', 'quarter_year', 'indicator', 'DATIM'])
            messages.info(request, f"No DATIM data for {selected_facility} {quarter_year}!")
        merged_df = dqa_df.merge(fyj_perf_df, on=['mfl_code', 'quarter_year', 'indicator'], how='right')
        if khis_perf:
            khis_perf_df = make_performance_df(khis_perf, 'KHIS')

            tx_curr_khis = khis_perf_df[khis_perf_df['indicator'] == "Number Current on ART Total"]

            # apply the function to the 'date' column and store the result in a new column
            tx_curr_khis['month_number'] = tx_curr_khis['month'].apply(get_month_number)
            tx_curr_khis = tx_curr_khis.sort_values('month_number', ascending=False).head(1)
            del tx_curr_khis['month_number']
            del tx_curr_khis['month']
            khis_others = khis_perf_df[khis_perf_df['indicator'] != "Number Current on ART Total"]

            khis_others = khis_others.groupby(['indicator', 'quarter_year', 'mfl_code']).sum().reset_index()

            khis_perf_df = pd.concat([khis_others, tx_curr_khis])
        else:
            khis_perf_df = pd.DataFrame(columns=['indicator', 'facility', 'mfl_code', 'KHIS',
                                                 'quarter_year'])

        if "KHIS" in merged_df.columns:
            del merged_df['KHIS']
        merged_df = khis_perf_df.merge(merged_df, on=['mfl_code', 'quarter_year', 'indicator'], how='right').fillna(0)
        try:
            merged_df = merged_df[
                ['mfl_code', 'facility', 'indicator', 'quarter_year', 'Source', 'MOH 731', 'KHIS', 'DATIM']]
        except KeyError:
            messages.info(request, f"No KHIS data for {selected_facility} {quarter_year}!")
            return redirect(request.path_info)
        dicts, merged_viz_df = compare_data_verification(merged_df, 'DATIM', description_list)

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
        # if audit_team:
        #     disable_update_buttons(request, audit_team)
        if not audit_team:
            messages.info(request,
                          f"No audit team assigned for {selected_facility}  {quarter_year}. Please ensure that data"
                          f" verification and system assessment data has been entered before assigning an audit team. "
                          f"Once all data is verified, the 'Add audit team' button will be available on this page.")

    sqa_context = show_sqa_summary(request)

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
        "audit_team": audit_team, "quarterly_trend_fig": quarterly_trend_fig,
        "system_assessments": system_assessments,
    }
    # Add only the 'data' from sqa_context
    if 'data' in sqa_context:
        context['data'] = sqa_context['data']
    return render(request, 'dqa/dqa_summary.html', context)


def display_data_verification(request, data_verification, selected_facility, selected_quarter, year_suffix, quarters):
    quarter_year = selected_quarter
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
               'Currently on ART 15+ years', 'Number of adults and children Currently on ART', 'TB_PREV_N', 'TX_ML',
               'RTT']

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
        disable_update_buttons(request, data_verification)
        remaining_indicators = [choice for choice in indicator_choices if
                                choice not in [obj.indicator for obj in sorted_data_verification]]
        if data_verification.count() < 33:
            messages.error(request, f"Only {data_verification.count()} DQA indicators for {selected_facility} "
                                    f"({quarter_year}) have been recorded so far. To ensure proper data visualization,"
                                    f" it is important to capture all indicators.")
            if remaining_indicators:
                messages.error(request,
                               f"{len(remaining_indicators)} remaining indicators: {', '.join(remaining_indicators)}")
            else:
                messages.info(request, "All indicators have been recorded.")

    if not data_verification:
        if selected_facility:
            messages.error(request,
                           f"No data verification found for {selected_facility} {selected_quarter}-FY{year_suffix}.")

    try:
        fyj_performance = FyjPerformance.objects.filter(mfl_code=selected_facility.mfl_code,
                                                        quarter_year=quarter_year
                                                        )
        if not fyj_performance:
            messages.info(request, f"No DATIM data for {selected_facility} {quarter_year}!")
    except:
        fyj_performance = None
    try:
        # ensure queryset is ordered chronologically by month
        khis_performance = KhisPerformance.objects.filter(mfl_code=selected_facility.mfl_code,
                                                          quarter_year=quarter_year
                                                          ).annotate(
            month_as_date=Cast(
                ExpressionWrapper(
                    Concat(Value('1'), Value(' '), 'month'),
                    output_field=CharField()
                ),
                output_field=DateField()
            )
        ).order_by('month_as_date')
        if khis_performance.exists():
            total = khis_performance.aggregate(
                prep_new_total=Sum('prep_new'),
                ipt_total=Sum('ipt'),
                tst_t_total=Sum('tst_t'),
                gbv_sexual_total=Sum('gbv_sexual'),
                cx_ca_total=Sum('cx_ca'),
                tst_pos_p_total=Sum('tst_pos_p'),
                tst_pos_a_total=Sum('tst_pos_a'),
                kp_anc_total=Sum('kp_anc'),
                new_pos_anc_total=Sum('new_pos_anc'),
                on_haart_anc_total=Sum('on_haart_anc'),
                new_on_haart_anc_total=Sum('new_on_haart_anc'),
                tx_new_p_total=Sum('tx_new_p'),
                tx_new_a_total=Sum('tx_new_a'),
                tb_stat_d_total=Sum('tb_stat_d'),
                tx_curr_p_total=Sum('tx_curr_p'),
                tx_curr_a_total=Sum('tx_curr_a'),
            )
        else:
            total = {
                'prep_new_total': 0,
                'ipt_total': 0,
                'tst_t_total': 0,
                'gbv_sexual_total': 0,
                'cx_ca_total': 0,
                'tst_pos_p_total': 0,
                'tst_pos_a_total': 0,
                'kp_anc_total': 0,
                'new_pos_anc_total': 0,
                'on_haart_anc_total': 0,
                'new_on_haart_anc_total': 0,
                'tx_new_p_total': 0,
                'tx_new_a_total': 0,
                'tb_stat_d_total': 0,
                'tx_curr_p_total': 0,
                'tx_curr_a_total': 0,
            }
            messages.info(request, f"No KHIS data for {selected_facility} {quarter_year}!")
    except:
        khis_performance = None
        total = {
            'prep_new_total': 0,
            'ipt_total': 0,
            'tst_t_total': 0,
            'gbv_sexual_total': 0,
            'cx_ca_total': 0,
            'tst_pos_p_total': 0,
            'tst_pos_a_total': 0,
            'kp_anc_total': 0,
            'new_pos_anc_total': 0,
            'on_haart_anc_total': 0,
            'new_on_haart_anc_total': 0,
            'tx_new_p_total': 0,
            'tx_new_a_total': 0,
            'tb_stat_d_total': 0,
            'tx_curr_p_total': 0,
            'tx_curr_a_total': 0,
        }

    display_dicts = {
        "quarters": quarters,
        "selected_year": year_suffix,
        'data_verification': sorted_data_verification,
        "program_accessed": program_accessed,
        "fyj_performance": fyj_performance,
        "khis_performance": khis_performance,
        "total": total,
    }
    return display_dicts


@login_required(login_url='login')
def dqa_work_plan_create(request, pk, quarter_year):
    if not request.user.first_name:
        return redirect("profile")
    year_suffix = quarter_year[-2:]
    facility = DataVerification.objects.filter(facility_name_id=pk,
                                               quarter_year__quarter_year=quarter_year
                                               ).order_by('-date_modified').first()
    system_assessment_qs = SystemAssessment.objects.filter(facility_name_id=pk,
                                                           quarter_year__quarter_year=quarter_year)
    system_assessment_partly = system_assessment_qs.filter(calculations=2)
    system_assessment_no = system_assessment_qs.filter(calculations=1)
    today = timezone.now().date()

    selected_facility = Facilities.objects.get(id=pk)
    data_verification = DataVerification.objects.filter(quarter_year__quarter_year=quarter_year,
                                                        facility_name_id=pk,
                                                        )
    quarters = {
        quarter_year.split("-")[0]: [
            f'Oct-{year_suffix}', f'Nov-{year_suffix}', f'Dec-{year_suffix}', 'Total'
        ] if 'Qtr1' in quarter_year else [
            f'Jan-{year_suffix}', f'Feb-{year_suffix}', f'Mar-{year_suffix}', 'Total'
        ] if 'Qtr2' in quarter_year else [
            f'Apr-{year_suffix}', f'May-{year_suffix}', f'Jun-{year_suffix}', 'Total'
        ] if 'Qtr3' in quarter_year else [
            f'Jul-{year_suffix}', f'Aug-{year_suffix}', f'Sep-{year_suffix}', 'Total'
        ]
    }
    # Display data verification
    display_dicts = display_data_verification(request, data_verification, selected_facility, quarter_year, year_suffix,
                                              quarters)

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
            messages.success(request, 'DQA Work Plan created successfully!')
            return redirect('dqa_work_plan_create', pk=pk, quarter_year=quarter_year)
    else:
        form = DQAWorkPlanForm()

    context = {'form': form, 'title': 'Add DQA Work Plan', 'facility': facility.facility_name.name,
               'mfl_code': facility.facility_name.mfl_code, 'date_modified': facility.date_modified,
               'system_assessment_partly': system_assessment_partly, 'system_assessment_no': system_assessment_no,
               "quarter_year": quarter_year,
               } | display_dicts

    return render(request, 'dqa/add_qi_manager.html', context)


@login_required(login_url='login')
def show_dqa_work_plan(request):
    if not request.user.first_name:
        return redirect("profile")
    form = QuarterSelectionForm(request.POST or None)
    year_form = YearSelectionForm(request.POST or None)
    facility_form = FacilitySelectionForm(request.POST or None)
    selected_facility = None
    work_plan = None
    work_plan_qs = None
    quarter_year = None
    selected_quarter = "Qtr1"
    selected_year = "2021"
    if form.is_valid():
        selected_quarter = form.cleaned_data['quarter']

    if year_form.is_valid():
        selected_year = year_form.cleaned_data['year']
    facility_form = FacilitySelectionForm(request.POST or None,
                                          selected_year=selected_year,
                                          selected_quarter=selected_quarter,
                                          model_to_check=DQAWorkPlan)

    quarterly_trend_fig = show_quarterly_trends(request, DQAWorkPlan, "DQA Worplans")

    if form.is_valid() and year_form.is_valid() and facility_form.is_valid():
        selected_quarter = form.cleaned_data['quarter']
        selected_year = year_form.cleaned_data['year']
        selected_facility = facility_form.cleaned_data['name']
        year_suffix = selected_year[-2:]
        quarter_year = f"{selected_quarter}-{year_suffix}"

    if selected_facility:
        work_plan_qs = DQAWorkPlan.objects.filter(facility_name_id=selected_facility.id).order_by("quarter_year")
        work_plan = work_plan_qs.filter(quarter_year__quarter_year=quarter_year)

        # Exclude work_plan from work_plan_qs
        work_plan_qs = work_plan_qs.exclude(quarter_year__quarter_year=quarter_year)
        #####################################
        # DECREMENT REMAINING TIME DAILY    #
        #####################################
        calculate_progress(work_plan)
        calculate_progress(work_plan_qs)

        if not work_plan:
            messages.error(request, f"No work plan for {selected_facility} ({quarter_year}) found.")
    context = {
        "work_plan": work_plan, "work_plan_qs": work_plan_qs, "form": form, "quarter_year": quarter_year,
        "year_form": year_form, "facility_form": facility_form, "quarterly_trend_fig": quarterly_trend_fig
    }
    return render(request, 'dqa/dqa_work_plan_list.html', context)


@login_required(login_url='login')
def add_system_verification(request):
    if not request.user.first_name:
        return redirect("profile")
    if not request.user.first_name:
        return redirect("profile")
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
    formset = SystemAssessmentFormSet(request.POST or None, queryset=SystemAssessment.objects.none(),
                                      initial=initial_data)
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
                messages.error(request, "Please fill all rows in the 'Answer dropdown option columns' before saving.")
                for form in formset.forms:
                    if not form.cleaned_data.get('dropdown_option'):
                        form.add_error('dropdown_option', "Please choose an option before saving.")
                    if form.cleaned_data.get('dropdown_option', '') in ('No', 'Partly') and not form.cleaned_data.get(
                            'auditor_note', ''):
                        messages.warning(request,
                                         "Please provide a note in the 'Auditor Note' field before saving. This is "
                                         "required because you selected 'Partly' or 'No' in the 'Dropdown Option' "
                                         "field.")
                        form.add_error('auditor_note',
                                       "Please provide a note before saving.")

                context = {
                    "formset": formset,
                    "quarter_form": quarter_form,
                    "year_form": year_form,
                    "facility_form": facility_form,
                    "date_form": date_form,
                    "descriptions": descriptions,
                    "page_from": request.session.get('page_from', '/'),
                }
                return render(request, 'dqa/add_system_assessment.html', context)
            try:
                errors = False
                for form in formset.forms:
                    if form.cleaned_data.get('dropdown_option', '') in ('No', 'Partly') and not form.cleaned_data.get(
                            'auditor_note', ''):
                        errors = True
                        messages.warning(request,
                                         "Please provide a note in the 'Auditor Note' field before saving. This is "
                                         "required because you selected 'Partly' or 'No' in the 'Dropdown Option' "
                                         "field.")
                        form.add_error('auditor_note',
                                       "Please provide a note before saving.")
                if errors:
                    context = {
                        "formset": formset,
                        "quarter_form": quarter_form,
                        "year_form": year_form,
                        "facility_form": facility_form,
                        "date_form": date_form,
                        "descriptions": descriptions,
                        "page_from": request.session.get('page_from', '/'),

                    }
                    return render(request, 'dqa/add_system_assessment.html', context)
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
                    messages.success(request, f"System assessment data for {selected_facility} {period} was "
                                              f"successfully saved to the database!")
            except DatabaseError:
                messages.error(request,
                               f"Data for {selected_facility} {period} already exists!")

    context = {
        "formset": formset,
        "quarter_form": quarter_form,
        "year_form": year_form,
        "facility_form": facility_form,
        "date_form": date_form,
    }
    return render(request, 'dqa/add_system_assessment.html', context)


@login_required(login_url='login')
def choose_facilities_sqa(request):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    quarter_form = QuarterSelectionForm(request.POST or None)
    year_form = YearSelectionForm(request.POST or None)
    facility_form = FacilitySelectionForm(request.POST or None)
    # date_form = DateSelectionForm(request.POST or None)
    if request.method == "POST":
        if quarter_form.is_valid() and year_form.is_valid() and facility_form.is_valid():
            selected_quarter = quarter_form.cleaned_data['quarter']
            selected_facility = facility_form.cleaned_data['name']
            selected_year = year_form.cleaned_data['year']
            # selected_date = date_form.cleaned_data['date']
            # Generate the URL for the redirect
            url = reverse('sqa',
                          kwargs={"report_name": "None", 'quarter': selected_quarter, 'year': selected_year,
                                  'pk': selected_facility.id,
                                  # 'date': selected_date
                                  })

            return redirect(url)
    context = {
        "quarter_form": quarter_form,
        "year_form": year_form,
        "facility_form": facility_form,
        # "date_form": date_form,
        "title": "Service Quality Assessment (SQA)"
    }
    return render(request, 'dqa/add_facilities_data_inventory.html', context)


def generate_descriptions(report_name):
    if report_name == "gbv":
        descriptions = [
            'Are GBV services integrated in all other service delivery points',
            'Are the staff offering GBV services trained on LIVES',
            'Are GBV services offered in a private and confidential space',
            'Does the facility have the GBV pathways job aid',
            'Do the CHPs attached to the facility sensitized on available GBV response services',
            'Does the facility have well utilized GBV registers that collect information about a patient’s experience '
            'of GBV and the post-GBV care s/he received',
        ]
    elif report_name == "vmmc":
        descriptions = [
            'Are surgical guidelines and SOPs readily available to the clinicians? i) Conventional Surgical ii) EIMC'
            ' iii) DEVICES',
            'Is TTCV administered as per the SOP?',
            'Does the facility have the current local anesthesia dosing chart on site? (for EIMC and adult)',
            'Is surgery performed as per guidelines and protocol? i) Conventional Surgical ii) EIMC'
            ' iii) DEVICES',
            'Does the MC surgical room observe privacy and confidentiality to clients?',
            'Are service delivery data completely and accurately collected and timely reported?',
            'Are analyzed data used for the planning and improvement of service delivery?',
            'Is VMMC data used to inform best practices at sub county, county or national level?',
            'Randomly select 12 most recent entries in the VMMC client card within the past 6 months What proportion '
            'of the clients were properly i) consented?',
            'ii) What proportion of clients were circumcised',
            'iii) Using Dorsal slit method?',
            'iv) What proportion of the clients were followed up as per guideline?',
            'v) What proportion of clients who missed scheduled follow up were actively '
            'followed?',
            'vi) For sites implementing EIMC, how many clients had HEI screening?',
        ]
    elif report_name == "hts":
        descriptions = [
            'Has HTS services been integrated to other services?',
            # 'If Yes for no 1: Where is hts  integrated? OPD, FP Clinic , ANC , CCC, Special Clinic, Other (Specify)',
            'Have all HTS service providers undergone the approved NASCOP HTS training program?',
            'Have all service HTS providers undergone refresher training/CME in the last one years? ',
            'Have all HTS Pos clients been received confirmatory test befor initiation to ART',
            'Is the HTS algorithm Adhered to?',
            'Is safety and infection prevention adhered to in the HTS room?',
            'If yes (to safety and infection prevention adherence above). What is present?  running water, soap, waste segregation (Yellow, Black, Red bins & '
            'liners and a sharp box), room has adequate lighting. & PEP Protocol ',
            'Is the HTS officer conversant with testing frequency for adolescent and young people? ',
            'Does the HTS provider in ANC adhere to testing frequency for ANC/PNC clients? ',
            'Does the HTS provider in MCH adhere to testing frequency for L&D clients?',
            'Does the facility offer index testing services?',
            'Is the facility HTS providers linking clients to combination prevent?',

        ]
    elif report_name == "prep":
        descriptions = [
            'Has PrEP services been integrated to other services ?',
            # 'If Yes for no 1: Where is PrEP integrated? OPD, FP Clinic , ANC , CCC, Special Clinic, Other (Specify)',
            'Have all the service providers offering PrEP received a refresher training in the last one year?',
            'Does the facility have PrEP Clinical encounter cards/EMR?',
            'Are they (PrEP Clinical encounter cards/EMR) appropriately documented',
            'Does the facility routinely  carry out Rapid Assessment Screening using the RAST tool',
            'Are client assessed for eligibility prior to PrEP initiation?',
            # 'Are clients on followup for PrEP offered  HIV Testing ?',
            'Are clients on followup for PrEP assessed for adverse drugs effects?',
            'Are clients on followup for PrEP assessesd for adherence and offered adherence counselling?',
            'Does the facility collect samples for drug resistance testing for clients who test HIV positive while on PrEP?',
            'Does the facility follow up new initiations to come for 1 month refill',
            'Does the facility provide testing at 1 month refill for PrEP',

        ]
    elif report_name == "tb":
        descriptions = [
            'Are clients screened for TB at every clinic visit?',
            'Does the facility start clients on TPT/TB Rx?',
            'Is documentation done for clients who have completed TPT?',
            'Are the clients tested for baseline CD4 test?',

        ]
    elif report_name == "care_treatment":
        descriptions = [
            'Are the clients tested for baseline CD4 test?',
            'Does the facility screen for NCDs in each visit? (BMI, RBS, BP, CaCx)',
            'Does the facility have USHAURI?',
            " Is it active?",
            'Does the facility have a system for assessment and management of clients with HVL? ',
            'Do the clients undergo 3 consecutive EAC before the 2nd VL is done?',
            'Does the facility assign a case manager for clients failing treatment?',
        ]
    elif report_name == "cqi":
        descriptions = [
            'Is there a quality committee that plans and oversees quality activities for the facility?',
            'How is client feedback incorporated?',
        ]
    elif report_name == "pharmacy":
        descriptions = [
            'Does the facility have manual/electronic stock control cards/Bin cards for ARVs and OI medicines?',
            'If Yes, are the bin cards upto date?',
        ]
    else:
        descriptions = []
    return descriptions


def generate_verification(report_name):
    if report_name == "gbv":
        numerators = [
            ".",
            ".",
            ".",
            'Check to confirm',
            'Check training log',
            'Check completion of MoH 363, 364, 365 including EMR',

        ]
    elif report_name == "vmmc":
        numerators = [
            'Physical Verification of SOPs and guidelines',
            'Check the TTCV administration SOP',
            'Check dosing chart on the wall',
            'Directly observe a procedure',
            'Physical Verification',
            'Verify on Minor Theatre Register & MOH 731',
            'Availability of ‘talking wall’ charts',
            'Check with in-charge on best practices documentation e.g. abstracts, newsletters and publications',
            'Check definitions of numerators and denominators in the SOP',
            'Check definitions of numerators and denominators in the SOP',
            'Check definitions of numerators and denominators in the SOP',
            'Check definitions of numerators and denominators in the SOP',
            'Check definitions of numerators and denominators in the SOP',
            'Check definitions of numerators and denominators in the SOP',
        ]
    elif report_name == "hts":
        numerators = [
            # 'Tick as appropriate',
            # 'Tick all that apply',
            ".",
            # "",
            'Confirm availability of certificates',
            'Check HTS log file/folder if the HTS names appear.Partly if some, No if none',
            'Sample 10 positive clients and crosscheck with retesting register. If 100% score if <100% score No',
            "Verify on the HTS register (MOH 362) Score Yes if  -	HIV Negative clients should only have result "
            "indicated under column for determine test,-	HIV positive client should have results indicated under "
            "columns for Determine and First response if the above is not followed (IS BELOW TEXT NECESSARY?) Ask and "
            "also check if test one is documented as determine and test two is documented as first response (confirm "
            "from the HTS register). Check for negative results (only determine) and positive results (determine and "
            "first response). If not followed score 'No' If followed but not always score 'partial' If algorithm "
            "strictly followed score 'YES'",
            'Check if the following are in place:',
            '.',
            'The answer is Yes if adhering to the HTS operational manual.   Ask and Check in MOH 362 AYP for next appointment. No if the TCA is longer',
            'Sample 10 clients in ANC Register, If yes – Check HTS provider to explain and Check PNC register, no if not adhering. IF 100% SCORE Yes , if >100% score Partly',
            'Sample 10 clients in Maternity Register, If yes – Check MAT register, no if not adhering. IF 100% SCORE Yes , if >100% score Partly',
            'Check for 5 clients who tested HIV positive during the review period, verify if they were transferred into the aPNS register and if partner elicitation and follow up was done. If there is documentation of elicitation & follow-up - Score Yes If there is documentation of follow up on the aPNS register.',
            'Sample 10 clients If yes verify in MOH 362 for linkage to prevention, Partial if some and No if none',
        ]

    elif report_name == "prep":
        numerators = [
            # 'Tick as appropriate',
            ".",
            # 'Tick all that apply',
            'Calculate the proportion of service providers who have received a refresher training out of the total number offering PrEP. If 100% tick Yes , if <100% tick no ',
            'Verify availability of clinical encounter card, , if available and well documented score Yes, If available and not well documented score partial If not available score No',
            ".",
            'Sample 5 encounter card for clients  for clients initiated on PrEP during the review period  verify documentation of risk assessment . Indicate the number clients with assessment done (numerator) total cards sampled (denominator)',
            'Sample 10 encounter card for clients initiated on PrEP during the review period  verify documentation of eligibility status  at basesline. Indicate the number  with eligibility assessment done (numerator) total cards sampled (denominator) If all the parameters for eligibility  are indicated score Yes if any is missing score No Parameters for eligibility:  HIV Test Negative, Screening for Kidney/Liver disease / No Contraindication to TDF/FTC/3TC / Client willing to initiate PrEP ) ',
            # 'Sample 10 client encounter cards, for clients who made a clinical  follow up visit during the review period.verify if they were tested for HIV Indicate the number  with documented HIV results (numerator) total cards sampled (denominator) If all the clients were tested indicate Yes , If some indicate Partial If none indicate No ',
            'Sample 5 client encounter cards, for clients who made a   follow up visit during the review period.verify if they were assessed for adverse drugs events.Indicate the number  with documented screening for adverse effects (numerator) total cards sampled (denominator) If all the clients were assesed for adverse drug effects indicate Yes , If some indicate Partial If none indicate No  ',
            'Sample 5 client encounter cards, for clients who made a   follow up visit during the review period.verify if they were assessed for adherence and offered adherence counselling. Indicate the number  with documented  adherence assessment (numerator) total cards sampled (denominator) If all the clients were assessed for adherence indicate Yes , If some indicate Partial If none indicate No  ',
            'Verify from  the PrEP register if there has been  any client who tested positive while on PrEP. Verify if clients were offered DRT on the the specific client  encounter card or sample tracking  log. If sample collected or results available indicate Yes if no documentation score No If not client has ever tested positive while on PrEP indicate NA',
            'Sample  5 client encounter cards of clients initiated for PrEP 1 month ago and assess whether they came for 1 month refill (What is the retention)',
            'Sample  5 client encounter cards of clients initiated for PrEP 1 month ago  and who came for 1 month refill and check if they were tested for HIV (What Is the testing rate)',

        ]
    elif report_name == "tb":
        numerators = [
            'Sample  5 green cards/EMR clients who attended clinic and check if TB screening was done at the last clinical visit. 2 peads and 3 adults and provide the proportion(num/den)',
            'Sample  5 new on art  clients who attended clinic 2, peads 3 adults and provide the proportion(num/den)',
            'Sample  5 client encounter cards/TB4 register/ICF card of active clients and started HAART >6 months ago 2, peads 3 adults and provide the proportion(num/den)',
        ]
    elif report_name == "care_treatment":
        numerators = [
            'Sample 10  files for verification- Tease out 10 patients who have been newly enrolled most recently ',
            'Sample 10 >15 client files and check for completeness of all the NCD parameters indicated in MOH 257',
            'Check if in the last 3 clinics  sms reminders were sent out',
            ".",
            'These are clients who have a 2nd VL of >1000 copies/ml after 3 consecutive EACs',
            'check for MDT, SOPs, availability of trained adherence counsellors)',
            'Check for EAC records and the dates',
        ]

    elif report_name == "cqi":
        numerators = [
            'Check for most recent available QI Meeting minutes, Member TOR',
            'Observe for available feedback mechanisms. Eg. Suggestion box available and in use, Client exit interviews done',
        ]
    elif report_name == "pharmacy":
        numerators = [
            'Check for any 5 electronic or physical bincards',
            "Choose the electronic or Physical TLD bin card and check if most recent delivery from KEMSA/MEDS or S11 from Central site is updated on the bin card).",

        ]
    else:
        numerators = []
    return numerators


def generate_numerator(report_name):
    if report_name == "gbv":
        numerators = [
            '# SDPs with GBV services intergrated',
            '# of staffs offering GBV services are trained on LIVES',
            '# of private and confidential spaces available for GBV services',
            '# of SDPs with the GBV pathways job aid',
            '# of CHPs sensitized on GBV response services',
            '# of well utilized GBV registers'

        ]
    elif report_name == "vmmc":
        numerators = [
            '# of surgical guidelines and SOPs available to clinicians',
            '# of TTCV administrations adhering to SOP',
            '1 (if chart is present) or 0 (if chart is absent)',
            '# of surgeries performed as per guidelines',
            '# of surgical rooms maintaining privacy/confidentiality',
            '# of service delivery data entries accurate and timely',
            "1 (if 'talking wall' charts are present) or 0 (if 'talking wall' charts are absent)",
            '# of best practice documents informed by VMMC data',
            '# of clients properly consented',
            '# of clients circumcised',
            '# of clients circumcised using Dorsal slit method',
            '# of clients followed up as per guideline',
            '# of clients who missed follow-up and were actively followed',
            '# of clients with HEI screening',
        ]
    elif report_name == "hts":
        numerators = [
            '# HTS services intergrated',
            # '',
            '# of HTS providers trained on NASCOP HTS training',
            '# of HTS providers who have undergone refresher training/CME in the last one year',
            '# of HTS positive clients who received confirmatory tests before initiation to ART',
            '1 (HTS algorithm is followed) or 0 (if not)',
            '# of HTS rooms where safety and infection prevention measures are adhered to',
            '',
            '# of HTS officers who are conversant with testing frequency for adolescents and young people',
            '# of ANC/PNC clients tested as per guideline frequency',
            '# of L&D clients tested as per guideline frequency',
            '# of clients who tested HIV positive and received index testing services',
            '# of clients linked to combination prevention by facility HTS providers',

        ]
    elif report_name == "prep":
        numerators = [
            '# PrEP services intergrated',
            # '',
            '# of service providers offering PrEP received a refresher training in the last one year',
            '.',
            "",
            '# clients with assessment done',

            '# with eligibility assessment done',
            # '# with documented HIV results',
            '# with documented screening for adverse effects',
            '# with documented  adherence assessment',
            '# of DRT collected for clients who test HIV positive while on PrEP',
            '# of PrEP clients who attended 1 month appointment',
            '# of PrEP clients with HIV test at 1 month visit',

        ]
    elif report_name == "tb":
        numerators = [
            'Number of clients screened for TB',
            'Number of clients started on TPT/TB Rx',
            'Number of clients with documentation for completed TPT',

        ]
    elif report_name == "care_treatment":
        numerators = [
            'Number of clients tested for baseline CD4 test',
            'Number of clients with completed NCD parameters',
            '1 (if ushauri is present) or 0 (if  absent)',
            "",
            '# documented in HVL register',
            '# with 3 consecutive EACs',
            '# of HVL clients with case managers',
        ]
    elif report_name == "cqi":
        numerators = [
            '1 (if most recent QI meeting minutes present) or 0 (if  absent)',
            '1 (if client feedback is routinely collected) or 0 (if  absent)',

        ]
    elif report_name == "pharmacy":
        numerators = [
            '1 (if bin cards are present) or 0 (if  absent)',
            '# with updated bin cards',
        ]
    else:
        numerators = []
    return numerators


def generate_denominator(report_name):
    if report_name == "gbv":
        numerators = [
            '# SDPs offering GBV services in the facility',
            '# of staffs offering GBV services',
            '# of GBV service delivery points',
            '# of service delivery points assessed',
            '# of CHPs attached to the facility',
            '# of GBV registers required'
        ]
    elif report_name == "vmmc":
        numerators = [
            '# of required surgical guidelines and SOPs',
            '# of TTCV administrations',
            '1',
            '# of surgeries observed',
            '# of surgical rooms assessed',
            '# of service delivery data entries checked',
            '1',
            '# of best practice documents reviewed',
            '12',
            '12',
            '# of clients circumcised',
            '12',
            '# of clients who missed scheduled follow-up',
            '# of clients eligible for HEI screening',
        ]
    elif report_name == "hts":
        numerators = [
            '# of SDPs',
            # '',
            '# of HTS providers',
            'Total # of HTS providers in the facility',
            'Total # of HTS positive clients',
            '1',
            'Total # of HTS rooms in the facility',
            '',
            'Total # of HTS officers in the facility',
            'Total sampled clients',
            'Total sampled clients',
            'Total # of clients who tested HIV positive during the review period',
            'Total # of clients tested',

        ]

    elif report_name == "prep":
        numerators = [
            '# of SDPs',
            # '',
            '# of service providers offering PrEP',
            '.',
            ".",
            'Total card sampled',
            'Total card sampled',
            # 'Total card sampled',
            'Total card sampled',
            'Total card sampled',
            '# of clients who test HIV positive while on PrEP',
            'Total client sampled',
            'Total client sampled',

        ]
    elif report_name == "tb":
        numerators = [
            'Total clients sampled',
            'Total clients sampled',
            'Total clients sampled',
        ]
    elif report_name == "care_treatment":
        numerators = [
            'Total clients sampled',
            'Total clients sampled',
            '1',
            "",
            '# of the client with HVL (Active on ART Patients Linelist)',
            '# of the client with 2nd VL with HVL',
            '# of the client with HVL (Active on ART Patients Linelist)',

        ]

    elif report_name == "cqi":
        numerators = [
            '1',
            '1',

        ]
    elif report_name == "pharmacy":
        numerators = [
            '1',
            '# of bin cards sampled',
        ]
    else:
        numerators = []
    return numerators


def create_sqa_formset(report_name, request, initial_data):
    # Define a dictionary mapping report names to model and form classes
    report_mapping = {
        "gbv": (Gbv, GbvForm),
        "vmmc": (Vmmc, VmmcForm),
        "hts": (Hts, HtsForm),
        "prep": (Prep, PrepForm),
        "tb": (Tb, TbForm),
        "care_treatment": (CareTreatment, CareTreatmentForm),
        "pharmacy": (Pharmacy, PharmacyForm),
        "cqi": (Cqi, CqiForm),
    }

    if report_name in report_mapping:
        model_class, form_class = report_mapping[report_name]
    else:
        model_class, form_class = report_mapping["gbv"]

    inventory_form_set = modelformset_factory(
        model_class,
        form=form_class,
        extra=len(initial_data)
    )
    formset = inventory_form_set(
        request.POST or None,
        queryset=model_class.objects.none(),
        initial=initial_data
    )

    return formset, inventory_form_set, model_class, form_class


@login_required(login_url='login')
def sqa(request, report_name=None, quarter=None, year=None, pk=None):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    quarter_form = QuarterSelectionForm(request.POST or None)
    year_form = YearSelectionForm(request.POST or None)
    facility_form = FacilitySelectionForm(request.POST or None)
    # date_form = DateSelectionForm(request.POST or None)
    descriptions = generate_descriptions(report_name)
    numerators = generate_numerator(report_name)
    denominators = generate_denominator(report_name)
    verifications = generate_verification(report_name)
    request.session['descriptions'] = descriptions
    request.session['numerators'] = numerators
    request.session['denominators'] = numerators
    request.session['verifications'] = verifications

    # Combine descriptions and numerators into a single list of dictionaries
    initial_data = [{'description': desc, 'numerator_description': num, 'denominator_description': den
                        , 'verification': ver} for
                    desc, num, den, ver in zip(descriptions, numerators, denominators, verifications)]

    formset, inventory_form_set, model_class, form_class = create_sqa_formset(report_name, request, initial_data)
    period_check, created = Period.objects.get_or_create(quarter=quarter, year=year)
    quarter_year_id = period_check.id

    facility, created = Facilities.objects.get_or_create(id=pk)
    facility_name = facility

    models_to_check = {
        "gbv": Gbv,
        "vmmc": Vmmc,
        "hts": Hts,
        "prep": Prep,
        "tb": Tb,
        "care_treatment": CareTreatment,
        "pharmacy": Pharmacy,
        "cqi": Cqi,
    }
    model_names = list(models_to_check.keys())

    def get_data_entered():
        # Create an empty list to store the filtered objects
        filtered_data = []

        # Iterate over the model names
        for model_name_ in model_names:
            # Get the model class from the models_to_check dictionary
            model_class_ = models_to_check[model_name_]
            # Filter the objects based on the conditions
            objects = model_class_.objects.filter(
                Q(facility_name_id=pk) &
                Q(quarter_year__id=quarter_year_id)
            )
            if objects:
                # Append the filtered objects to the list
                filtered_data.append(model_name_)
        return filtered_data

    filtered_data = get_data_entered()
    model_names = ['gbv', 'vmmc', 'hts', 'prep', 'tb', 'care_treatment', 'cqi', 'pharmacy']
    missing = [item for item in model_names if item not in filtered_data]
    if len(missing) == 0:
        messages.success(request, f"All data for {facility_name} {period_check} is successfully saved! "
                                  f"Please select a different facility.")
        return redirect("choose_facilities_inventory")

    if report_name == "None":
        # Redirect to the URL with the first missing item as the report_name
        url = reverse('sqa',
                      kwargs={"report_name": missing[0], 'quarter': quarter, 'year': year, 'pk': pk,
                              # 'date': date
                              })
        return redirect(url)

    if request.method == "POST":
        formset = inventory_form_set(request.POST, initial=initial_data)
        if formset.is_valid():
            # selected_date = date
            instances = formset.save(commit=False)
            context = {
                "formset": formset, "quarter_form": quarter_form, "year_form": year_form,
                "facility_form": facility_form,
                # "date_form": date_form,
                "descriptions": descriptions,
                "page_from": request.session.get('page_from', '/'),
                "report_name": missing[0],
                "quarter": quarter,
                "year": year,
                "facility_id": pk,
                # "date": date,
                "filtered_data": filtered_data
            }
            #######################################
            # CHECK IF USER SELECTION IS LOGICAL  #
            #######################################
            fields_to_validate = [
                ('adult_arv_tdf_3tc_dtg', 'adult_arv_tdf_3tc_dtg'),
                ('pead_arv_dtg_10mg', 'pead_arv_dtg_10mg'),
                ('paed_arv_abc_3tc_120_60mg', 'paed_arv_abc_3tc_120_60mg'),
                ('tb_3hp', 'tb_3hp'),
                ('family_planning_rod', 'family_planning_rod'),
                ('al_24', 'al_24'),
            ]

            # for field_to_validate, error_field in fields_to_validate:
            #     if form_class == StockCardsForm:
            #         question_1_value = formset.forms[0].cleaned_data.get(field_to_validate)
            #         question_2_value = formset.forms[1].cleaned_data.get(field_to_validate)
            #         if question_1_value == 'No' and question_2_value == 'Yes':
            #             formset.forms[1].add_error(error_field,
            #                                        f"Invalid selection. Can't select 'Yes' if above question is 'No'.")
            #     elif form_class == ExpiredForm:
            #         question_1_value = formset.forms[1].cleaned_data.get(field_to_validate)
            #         question_2_value = formset.forms[2].cleaned_data.get(field_to_validate)
            #         if question_1_value == 'No' and question_2_value == 'Yes':
            #             formset.forms[2].add_error(error_field,
            #                                        f"Invalid selection. Can't select 'Yes' if above question is 'No'.")
            ############################################
            # CHECK IF THERE ARE ERRORS IN THE FORMSET #
            ############################################
            if any(form.errors for form in formset.forms):
                # There are form errors in the formset
                return render(request, 'dqa/add_sqa.html', context)

            #################################################
            # CHECK IF ALL FORMS IN THE FORMSET ARE FILLED  #
            #################################################
            if not all([form.has_changed() for form in formset.forms]):
                for form in formset.forms:
                    if not form.has_changed():
                        for field in form.fields:
                            if field != "comments":
                                form.add_error(field, "This field is required.")
                return render(request, 'dqa/add_sqa.html', context)
            try:
                errors = False

                ##############################################
                # CHECK IF THERE IS A COMMENT FOR ANY 'NO'!  #
                ##############################################
                fields_to_check = [
                    ('adult_arv_tdf_3tc_dtg', "TLD 90s"),
                    ('pead_arv_dtg_10mg', "DTG 10mg"),
                    ('paed_arv_abc_3tc_120_60mg', "ABC/3TC 120/60"),
                    ('tb_3hp', "3HP"),
                    ('family_planning_rod', "IMPLANT 1 ROD"),
                    ('al_24', "AL 24"),
                ]

                for form in formset.forms:
                    error_fields = []
                    for field, field_name in fields_to_check:
                        if report_name != "expiry_tracking":
                            if report_name == "cqi":
                                if form.cleaned_data.get(field) == 'Yes' and not form.cleaned_data.get('comments'):
                                    errors = True
                                    error_fields.append(field_name)
                            else:
                                if form.cleaned_data.get(field) == 'No' and not form.cleaned_data.get('comments'):
                                    errors = True
                                    error_fields.append(field_name)

                    if error_fields:
                        if report_name == "cqi":
                            error_message = f"Please provide a comment for 'Yes' selection in the following fields: " \
                                            f"{', '.join(error_fields)} "
                            form.add_error('comments', error_message)

                        else:
                            error_message = f"Please provide a comment for 'No' selection in the following fields: " \
                                            f"{', '.join(error_fields)} "
                            form.add_error('comments', error_message)

                if errors:
                    return render(request, 'dqa/add_sqa.html', context)

                #################################################
                # CHECK IF ALREADY DATA EXIST IN THE DATABASE!  #
                # 'MANUAL CHECK FOR UNIQUE TOGETHER'            #
                #################################################
                existing_data = model_class.objects.values_list('description', 'facility_name', 'quarter_year')
                for form in formset.forms:
                    description_check = form.cleaned_data.get('description')
                    # facility_check, created = Facilities.objects.get_or_create(id=selected_facility)
                    # facility_name_check = facility_check.id
                    # period_check, created = Period.objects.get_or_create(quarter=selected_quarter, year=selected_year)
                    # quarter_year_check = period_check.id

                    if (description_check, facility_name, quarter_year_id) in existing_data:
                        messages.error(request, f"Data for {facility_name} {period_check} already exists!")
                        return render(request, 'dqa/add_sqa.html', context)

                ###########################################################
                # SAVE DATA IF IT DOES NOT EXIST AND THERE IS NO ERRORS!  #
                ###########################################################
                with transaction.atomic():
                    for form, instance in zip(formset.forms, instances):
                        facility_id = Facilities.objects.get(id=pk)
                        # Get all related sub_counties using filter
                        sub_counties_ids = Sub_counties.facilities.through.objects.filter(
                            facilities_id=facility_id.id).values_list('sub_counties_id', flat=True)

                        # Get the first sub_county_id (if exists) to use for filtering counties
                        if sub_counties_ids:
                            first_sub_county_id = sub_counties_ids[0]

                            # Get the county related to the first sub_county_id
                            county_id = Sub_counties.counties.through.objects.filter(
                                sub_counties_id=first_sub_county_id).values_list('counties_id', flat=True).first()

                            # Assign the county to the post
                            if county_id:
                                instance.county = Counties.objects.get(id=county_id)
                            # Assign the first sub_county to the post
                            instance.sub_county = Sub_counties.objects.get(id=first_sub_county_id)

                        # Set instance fields from form data
                        instance.dropdown_option = form.cleaned_data['dropdown_option']
                        if instance.dropdown_option == 'Yes':
                            instance.calculations = 3
                        elif instance.dropdown_option == 'Partly':
                            instance.calculations = 2
                        elif instance.dropdown_option == 'No':
                            instance.calculations = 1
                        elif instance.dropdown_option == 'N/A':
                            instance.calculations = None
                        instance.numerator = form.cleaned_data['numerator']
                        instance.denominator = form.cleaned_data['denominator']
                        # Check if both numerator and denominator are >0
                        if instance.numerator is not None and instance.denominator is not None:
                            # Avoid division by zero error
                            if instance.denominator != 0:
                                instance.indicator_performance = round(
                                    (instance.numerator / instance.denominator) * 100, 1)
                            else:
                                instance.indicator_performance = 0
                        else:
                            instance.indicator_performance = None
                        # instance.dqa_date = selected_date
                        instance.created_by = request.user
                        instance.description = form.cleaned_data['description']
                        instance.verification = form.cleaned_data['verification']
                        instance.numerator_description = form.cleaned_data['numerator_description']
                        instance.denominator_description = form.cleaned_data['denominator_description']
                        # facility, created = Facilities.objects.get_or_create(id=selected_facility)
                        instance.facility_name = facility
                        # Get or create the Period instance
                        # period, created = Period.objects.get_or_create(quarter=selected_quarter, year=selected_year)
                        instance.quarter_year = period_check
                        # Get or create the Table instance
                        table_name, created = TableNames.objects.get_or_create(model_name=report_name)
                        instance.model_name = table_name
                        instance.save()

                    filtered_data = get_data_entered()
                    missing = [item for item in model_names if item not in filtered_data]
                    if len(missing) != 0:
                        messages.success(request, f"Data for {facility_name} {period_check} is successfully saved!")
                        # Redirect to the URL with the first missing item as the report_name
                        url = reverse('sqa',
                                      kwargs={"report_name": missing[0], 'quarter': quarter, 'year': year, 'pk': pk,
                                              # 'date': date
                                              })
                        return redirect(url)
                    else:
                        messages.success(request, f"All data for {facility_name} {period_check} is successfully saved! "
                                                  f"Please select a different facility.")
                        return redirect("choose_facilities_sqa")

            except DatabaseError:
                messages.error(request,
                               f"Data for {facility_name} {period_check} already exists!")
    context = {
        "formset": formset, "facility_name": facility_name,
        "report_name": report_name,
        "quarter": quarter,
        "year": year,
        "facility_id": pk,
        # "date": date,
        "filtered_data": filtered_data
    }
    return render(request, 'dqa/add_sqa.html', context)


def show_quarterly_trends(request, model, title):
    """
    Generate a line chart showing the quarterly trend of unique values in a given field of a given model.

    Args:
    model: The Django model to query.
    field: The field of the model to count unique values for.
    title: The title of the chart.

    Returns:
    A Plotly line chart.
    """
    # Get the number of unique facilities done per quarter_year
    # unique_facilities_per_quarter = model.objects.select_related('quarter_year').values(
    #     'quarter_year__quarter', 'quarter_year__year').annotate(
    #     unique_facilities=Count('facility_name', distinct=True)).order_by('quarter_year__year',
    #                                                                       'quarter_year__quarter')

    unique_facilities_per_quarter = model.objects.values('quarter_year__quarter',
                                                         'quarter_year__year').annotate(
        unique_facilities=Count('facility_name', distinct=True)).order_by('quarter_year__year', 'quarter_year__quarter')

    try:
        # Convert the queryset to a pandas DataFrame
        df = pd.DataFrame(unique_facilities_per_quarter)
        # Create a new column for the quarter and year
        df['quarter_year'] = df['quarter_year__quarter'].astype(str) + '-' + df['quarter_year__year'].astype(str)
        df = df.rename(columns={"unique_facilities": "Number of facilities"})

        quarterly_trend_fig = line_chart_median_mean(df, "quarter_year", "Number of facilities",
                                                     f"Number of Facilities with {title} Completed Per Quarter",
                                                     time=104, xaxis_title=" FY Quarter - Year"
                                                     )
    except KeyError:
        quarterly_trend_fig = None
    return quarterly_trend_fig


@login_required(login_url='login')
def system_assessment_table(request):
    if not request.user.first_name:
        return redirect("profile")
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
    # facility_form = FacilitySelectionForm(request.POST or None, initial=facility_form_initial)

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
    selected_quarter = "Qtr1"
    selected_year = "2021"
    if quarter_form.is_valid():
        selected_quarter = quarter_form.cleaned_data['quarter']

    if year_form.is_valid():
        selected_year = year_form.cleaned_data['year']

    facility_form = FacilitySelectionForm(request.POST or None,
                                          selected_year=selected_year,
                                          selected_quarter=selected_quarter,
                                          model_to_check=SystemAssessment,
                                          initial=facility_form_initial)

    ##########################################
    # Show quarterly trends
    ##########################################

    quarterly_trend_fig = show_quarterly_trends(request, SystemAssessment, "System Assessments")

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
            disable_update_buttons(request, system_assessments)

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

        # disable_update_buttons(request, system_assessments)

    context = {
        "quarter_form": quarter_form,
        "year_form": year_form,
        "facility_form": facility_form,
        "date_form": date_form,
        'system_assessments': system_assessments,
        "average_dictionary": average_dictionary,
        "expected_counts_dictionary": expected_counts_dictionary, "quarterly_trend_fig": quarterly_trend_fig,
    }
    return render(request, 'dqa/show_system_assessment.html', context)


def create_description_dict():
    gbv = [
        'Are GBV services integrated in all other service delivery points',
        'Are the staff offering GBV services trained on LIVES',
        'Are GBV services offered in a private and confidential space',
        'Does the facility have the GBV pathways job aid',
        'Do the CHPs attached to the facility sensitized on available GBV response services',
        'Does the facility have well utilized GBV registers that collect information about a patient’s experience of GBV and the post-GBV care s/he received',
    ]
    vmmc = [
        'Are surgical guidelines and SOPs readily available to the clinicians? i) Conventional Surgical ii) EIMC iii) DEVICES',
        'Is TTCV administered as per the SOP?',
        'Does the facility have the current local anesthesia dosing chart on site? (for EIMC and adult)',
        'Is surgery performed as per guidelines and protocol? i) Conventional Surgical ii) EIMC iii) DEVICES',
        'Does the MC surgical room observe privacy and confidentiality to clients?',
        'Are service delivery data completely and accurately collected and timely reported?',
        'Are analyzed data used for the planning and improvement of service delivery?',
        'Is VMMC data used to inform best practices at sub county, county or national level?',
        'Randomly select 12 most recent entries in the VMMC client card within the past 6 months What proportion of the clients were properly i) consented? ii) What proportion of clients were circumcised iii) Using Dorsal slit method? iv) What proportion of the clients were followed up as per guideline? v) What proportion of clients who missed scheduled follow up were actively followed? vi) For sites implementing EIMC, how many clients had HEI screening?',
    ]
    hts = [
        'Has HTS services been integrated to other services?',
        'Have all HTS service providers undergone the approved NASCOP HTS training program?',
        'Have all service HTS providers undergone refresher training/CME in the last one years? ',
        'Have all HTS Pos clients been received confirmatory test befor initiation to ART',
        'Is the HTS algorithm Adhered to?',
        'Is safety and infection prevention adhered to in the HTS room?',
        'If yes (to safety and infection prevention adherence above). What is present?  running water, soap, waste segregation (Yellow, Black, Red bins & liners and a sharp box), room has adequate lighting. & PEP Protocol ',
        'Is the HTS officer conversant with testing frequency for adolescent and young people? ',
        'Does the HTS provider in ANC adhere to testing frequency for ANC/PNC clients? ',
        'Does the HTS provider in MCH adhere to testing frequency for L&D clients?',
        'Does the facility offer index testing services?',
        'Is the facility HTS providers linking clients to combination prevent?',
    ]
    prep = [
        'Has PrEP services been integrated to other services ?',
        'Have all the service providers offering PrEP received a refresher training in the last one year?',
        'Does the facility have PrEP Clinical encounter cards/EMR?',
        'Are they (PrEP Clinical encounter cards/EMR) appropriately documented',
        'Does the facility routinely  carry out Rapid Assessment Screening using the RAST tool',
        'Are client assessed for eligibility prior to PrEP initiation?',
        'Are clients on followup for PrEP assessed for adverse drugs effects?',
        'Are clients on followup for PrEP assessesd for adherence and offered adherence counselling?',
        'Does the facility collect samples for drug resistance testing for clients who test HIV positive while on PrEP?',
        'Does the facility follow up new initiations to come for 1 month refill',
        'Does the facility provide testing at 1 month refill for PrEP',
    ]
    tb = [
        'Are clients screened for TB at every clinic visit?',
        'Does the facility start clients on TPT/TB Rx?',
        'Is documentation done for clients who have completed TPT?',
        'Are the clients tested for baseline CD4 test?',
    ]
    care_rx = [
        'Are the clients tested for baseline CD4 test?',
        'Does the facility screen for NCDs in each visit? (BMI, RBS, BP, CaCx)',
        'Does the facility have USHAURI?',
        " Is it active?",
        'Does the facility have a system for assessment and management of clients with HVL? ',
        'Do the clients undergo 3 consecutive EAC before the 2nd VL is done?',
        'Does the facility assign a case manager for clients failing treatment?',
    ]
    cqi = [
        'Is there a quality committee that plans and oversees quality activities for the facility?',
        'How is client feedback incorporated?',
    ]
    pharmacy = [
        'Does the facility have manual/electronic stock control cards/Bin cards for ARVs and OI medicines?',
        'If Yes, are the bin cards upto date?',
    ]

    description_dict = {
        'gbv': gbv,
        'vmmc': vmmc,
        'hts': hts,
        'prep': prep,
        'tb': tb,
        'caretreatment': care_rx,
        'cqi': cqi,
        'pharmacy': pharmacy,
    }

    return description_dict


def calculate_averages_(request, model_data):
    total_score = 0
    num_assessments = 0
    for assessment in model_data:
        if assessment.calculations is not None:
            total_score += assessment.calculations
            num_assessments += 1
    average = total_score / num_assessments if num_assessments > 0 else 0
    return {
        'average': round(average, 1),
        'total_score': int(total_score),
        'num_assessments': num_assessments
    }


def split_at_caps(s):
    return re.findall('[A-Z][^A-Z]*', s)


def show_sqa_summary(request):
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

    date_form = DateSelectionForm(request.POST or None)
    data = {}
    description_dict = create_description_dict()

    selected_quarter = "Qtr1"
    selected_year = "2021"
    if quarter_form.is_valid():
        selected_quarter = quarter_form.cleaned_data['quarter']

    if year_form.is_valid():
        selected_year = year_form.cleaned_data['year']

    facility_form = FacilitySelectionForm(request.POST or None,
                                          selected_year=selected_year,
                                          selected_quarter=selected_quarter,
                                          model_to_check=[Gbv, Vmmc, Hts, Prep, Tb, CareTreatment, Pharmacy, Cqi],
                                          initial=facility_form_initial)
    missing_models = []
    if quarter_form.is_valid() and year_form.is_valid() and facility_form.is_valid():
        selected_quarter = quarter_form.cleaned_data['quarter']
        selected_facility = facility_form.cleaned_data['name']
        selected_year = year_form.cleaned_data['year']

        year_suffix = selected_year[-2:]
        quarter_year = f"{selected_quarter}-{year_suffix}"

        # Loop through all models and retrieve data
        for model in [Gbv, Vmmc, Hts, Prep, Tb, CareTreatment, Pharmacy, Cqi]:
            model_data = model.objects.filter(
                quarter_year__quarter_year=quarter_year,
                facility_name=selected_facility
            ).order_by(
                Case(
                    *[When(description=d, then=pos) for pos, d in enumerate(description_dict[model.__name__.lower()])],
                    output_field=IntegerField()
                )
            )
            if model_data:
                # average_dictionary, expected_counts_dictionary = calculate_averages(model_data, description_dict[
                #     model.__name__.lower()])
                average_data = calculate_averages_(request, model_data)
                data[model.__name__.lower()] = {
                    'system_assessments': model_data,
                    'average_data': average_data

                }
            else:
                split_name = split_at_caps(model.__name__)
                upper_name = [part.upper() for part in split_name]
                result = " ".join(upper_name)
                missing_models.append(result)

        if missing_models:
            missing_models_str = ", ".join(missing_models)
            messages.error(request,
                           f"Data was not found for {selected_facility} ({quarter_year}) in the following section(s): {missing_models_str}")

    if quarter_form_initial:
        for model in [Gbv, Vmmc, Hts, Prep, Tb, CareTreatment, Pharmacy, Cqi]:
            model_data = model.objects.filter(
                quarter_year__quarter_year=quarter_form_initial['quarter'],
                facility_name=Facilities.objects.get(name=facility_form_initial["name"])
            ).order_by(
                Case(
                    *[When(description=d, then=pos) for pos, d in enumerate(description_dict[model.__name__.lower()])],
                    output_field=IntegerField()
                )
            )
            if model_data:
                # average_dictionary, expected_counts_dictionary = calculate_averages(model_data, description_dict[
                #     model.__name__.lower()])
                average_data = calculate_averages_(request, model_data)
                data[model.__name__.lower()] = {
                    'system_assessments': model_data,
                    'average_data': average_data

                }

    context = {
        "quarter_form": quarter_form,
        "year_form": year_form,
        "facility_form": facility_form,
        "date_form": date_form,
        'data': data,
    }
    return context


@login_required(login_url='login')
def sqa_table(request):
    if not request.user.first_name:
        return redirect("profile")

    context = show_sqa_summary(request)
    return render(request, 'dqa/show_sqa.html', context)


@login_required(login_url='login')
def instructions(request):
    if not request.user.first_name:
        return redirect("profile")
    return render(request, 'dqa/instructions.html')


@login_required(login_url='login')
def update_system_assessment(request, pk):
    if not request.user.first_name:
        return redirect("profile")
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
        "title": "Update Systems Assessment"
    }
    return render(request, 'dqa/update_system_assessment.html', context)


def update_sqa(request, model_name, pk):
    if not request.user.first_name:
        return redirect("profile")

    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    model_names = {
        "vmmc": "Vmmc",
        "cqi": "Cqi",
        "gbv": "Gbv",
        "hts": "Hts",
        "prep": "Prep",
        "tb": "Tb",
        "caretreatment": "CareTreatment",
    }

    modelName = model_names.get(model_name, "Pharmacy")

    # Get the model class based on the model name
    model = apps.get_model(app_label='dqa', model_name=modelName)
    item = model.objects.get(id=pk)

    # Get the form class based on the model name
    form_class = type(f'{modelName}Form', (BaseForm,), {'Meta': type(f'Meta', (BaseForm.Meta,), {'model': model})})
    item = model.objects.get(id=pk)
    if request.method == "POST":
        form = form_class(request.POST, instance=item)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.dropdown_option = form.cleaned_data['dropdown_option']
            instance.auditor_note = form.cleaned_data['auditor_note']
            instance.verification = form.cleaned_data['verification']
            instance.numerator = form.cleaned_data['numerator']
            instance.denominator = form.cleaned_data['denominator']
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

            item = model.objects.get(id=pk)
            facility_id = Facilities.objects.get(name=item.facility_name)
            instance.created_by = request.user
            instance.facility_name_id = item.facility_name_id
            instance.quarter_year_id = item.quarter_year_id
            # https://stackoverflow.com/questions/14820579/how-to-query-directly-the-table-created-by-django-for-a-manytomany-relation
            all_subcounties = Sub_counties.facilities.through.objects.all()
            all_counties = Sub_counties.counties.through.objects.all()
            # loop
            sub_county_list = []
            for sub_county in all_subcounties:
                if facility_id.id == sub_county.facilities_id:
                    # assign an instance to sub_county
                    instance.sub_county = Sub_counties(id=sub_county.sub_counties_id)
                    sub_county_list.append(sub_county.sub_counties_id)
            for county in all_counties:
                if sub_county_list[0] == county.sub_counties_id:
                    instance.county = Counties.objects.get(id=county.counties_id)

            instance.save()

            # messages.success(request, "Record successfully updated!")
            # Set the initial values for the forms
            quarter_form_initial = {'quarter': instance.quarter_year.quarter_year}
            year_form_initial = {'year': instance.quarter_year.year}
            facility_form_initial = {"name": instance.facility_name.name}

            messages.success(request, "Record successfully updated!")
            # Redirect to the system assessment table view with the initial values for the forms
            url = reverse('sqa_table')
            url = f'{url}?quarter_form={quarter_form_initial}&year_form={year_form_initial}&facility_form={facility_form_initial}'
            return redirect(url)
            # return redirect(reverse('sqa_table'))

    else:
        form = form_class(instance=item)

    context = {
        "form": form,
        "title": "Update SQA", "facility_data": item, "modelName": modelName.upper()
    }
    return render(request, 'dqa/update_sqa.html', context)


@login_required(login_url='login')
def update_dqa_workplan(request, pk):
    if not request.user.first_name:
        return redirect("profile")
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


@login_required(login_url='login')
def add_audit_team(request, pk, quarter_year):
    if not request.user.first_name:
        return redirect("profile")
    if not request.user.first_name:
        return redirect("profile")
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
    disable_update_buttons(request, audit_team)
    context = {
        "form": form,
        "title": "audit team",
        "audit_team": audit_team,
        "quarter_year": quarter_year,
    }
    return render(request, 'dqa/add_period.html', context)


@login_required(login_url='login')
def update_audit_team(request, pk):
    if not request.user.first_name:
        return redirect("profile")
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
    if not request.user.first_name:
        return redirect("profile")
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
        if audit_team:
            disable_update_buttons(request, audit_team)
        else:
            messages.error(request, f"No audit team data was found in the database for {selected_facility} "
                                    f"{selected_quarter}-FY{year_suffix}.")
    elif facility_form_initial:
        selected_quarter = quarter_form_initial['quarter']
        selected_facility = facility_form_initial['name']
        audit_team = AuditTeam.objects.filter(facility_name=Facilities.objects.get(name=selected_facility),
                                              quarter_year__quarter_year=selected_quarter)
        if audit_team:
            disable_update_buttons(request, audit_team)

    context = {
        "audit_team": audit_team,
        'form': form,
        "year_form": year_form,
        "facility_form": facility_form,
        'title': 'show team',
        "quarter_year": quarter_year,
    }
    return render(request, 'dqa/add_period.html', context)


def update_button_settings(request):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    update_settings = UpdateButtonSettings.objects.first()
    if request.method == 'POST':
        form = UpdateButtonSettingsForm(request.POST, instance=update_settings)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = UpdateButtonSettingsForm(instance=update_settings)
    return render(request, 'dqa/upload.html', {'form': form, "title": "update time"})


def bar_chart_dqa(df, x_axis, y_axis, pepfar_col=None, title=None, color=None):
    if df.empty:
        return None
    if "Number of scores" == y_axis:
        fig = px.bar(df, x=x_axis, y=y_axis, title=title, height=300, text=y_axis,
                     hover_data=["Number of scores", "%"])
    elif "# of scores" == y_axis:
        fig = px.bar(df, x=x_axis, y=y_axis, title=title, height=300, text="scores (%)",
                     hover_data=["# of scores", "scores (%)"])
    elif "timeframe (wks)" == x_axis:
        fig = px.bar(df, x=x_axis, y=y_axis, title=title, height=300, text="# (%)",
                     hover_data=["Number of action points", "# (%)"])
    elif 'trend' in title.lower():
        fig = px.line(df, x=x_axis, y=y_axis, text=y_axis, title=title, height=500)
        fig.update_traces(textposition='top center')
    elif 'indicator' == x_axis:
        colors = {'Meets standard': 'green', 'Needs improvement': 'yellow', 'Needs urgent remediation': 'red'}
        fig = px.bar(df, x=x_axis, y=y_axis, title=title, height=400, color='Score', text="Percentage",
                     color_discrete_map=colors,
                     hover_data=[f'Difference ({pepfar_col}-Source)',
                                 "Absolute difference proportion (Difference/Source*100)",
                                 "Percentage",
                                 "Source", pepfar_col])
        fig.update_layout(legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ))
    elif "count" not in y_axis:
        fig = px.bar(df, x=x_axis, y=y_axis, title=title, height=300, text=y_axis, color=color)

    else:
        fig = px.bar(df, x=x_axis, y=y_axis, title=title, height=300)
    if y_axis == "Number of scores" and color is not None:
        fig.update_traces(marker_color=color)
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
                size=9
            ),
            title_font=dict(
                size=10
            )
        ),
        yaxis=dict(
            title_font=dict(
                size=8
            )
        ),
        legend=dict(
            font=dict(
                size=10
            )
        ),
        title=dict(
            font=dict(
                size=14
            )
        )
    )
    fig.update_traces(hoverlabel=dict(font=dict(size=8)))
    return plot(fig, include_plotlyjs=False, output_type="div")


def prepare_dqa_workplan_viz(dqa_workplan_df, col_name):
    dqa_workplan_df['Number of action points'] = 1
    facilities_df = dqa_workplan_df.groupby(col_name)[
        'Number of action points'].sum(numeric_only=True).reset_index()
    facilities_df.sort_values('Number of action points', inplace=True)

    area_reviewed_df = dqa_workplan_df.groupby('Program Areas Reviewed')[
        'Number of action points'].sum(numeric_only=True).reset_index()
    area_reviewed_df.sort_values('Number of action points', inplace=True)

    area_reviewed_facility_df = \
        dqa_workplan_df.groupby([col_name, 'Program Areas Reviewed'])[
            'Number of action points'].sum(numeric_only=True).reset_index()
    # replace spaces and slashes with underscores in the column
    area_reviewed_facility_df['Program Areas Reviewed'] = area_reviewed_facility_df[
        'Program Areas Reviewed'].str.replace(', ', '_').str.replace(' ', '_').str.replace('/', '_').str.replace('&',
                                                                                                                 '_')
    area_reviewed_facility_df.sort_values('Number of action points', inplace=True)

    action_point_status_df = dqa_workplan_df.groupby('completion')[
        'Number of action points'].sum(numeric_only=True).reset_index()
    action_point_status_df.sort_values('completion', inplace=True)
    action_point_status_df['% completetion'] = action_point_status_df['completion'].astype(str) + "%"

    dqa_date_df = dqa_workplan_df.groupby(['dqa_date', col_name])[
        'Number of action points'].sum(numeric_only=True).reset_index()
    # dqa_date_df=dqa_date_df.rename(columns={'Number of action points':"Number of DQAs done"})
    dqa_date_df['Number of DQAs done'] = 1
    dqa_date_df.sort_values('dqa_date', inplace=True)

    # Convert the dqa_date column to a datetime format
    dqa_date_df["dqa_date"] = pd.to_datetime(dqa_date_df["dqa_date"])

    # Group the dates by week and count the number of DQAs done each week
    weekly_counts = dqa_date_df.set_index("dqa_date")["Number of DQAs done"].resample("W").sum().reset_index()
    weekly_counts['dqa_date'] = weekly_counts['dqa_date'].astype(str) + "."
    weekly_counts = weekly_counts.rename(columns={"dqa_date": "dqa_dates (weekly)"})

    dqa_workplan_df['Timeframe'] = dqa_workplan_df['Timeframe'] / 7
    timeframe_df = dqa_workplan_df.groupby('Timeframe')['Number of action points'].sum(numeric_only=True).reset_index()
    timeframe_df.sort_values('Timeframe', inplace=True)

    cond_list = [timeframe_df['Timeframe'] < 2, (timeframe_df['Timeframe'] >= 2) & (timeframe_df['Timeframe'] <= 4),
                 (timeframe_df['Timeframe'] > 4) & (timeframe_df['Timeframe'] <= 8),
                 (timeframe_df['Timeframe'] > 8) & (timeframe_df['Timeframe'] <= 12),
                 timeframe_df['Timeframe'] > 12]
    choice_list = ["<2 wks", "2-4 wks", "4-8 wks", "8-12 wks", ">12 wks"]
    timeframe_df['timeframe (wks)'] = np.select(cond_list, choice_list, default="0")

    timeframe_df = timeframe_df.groupby('timeframe (wks)')[
        'Number of action points'].sum(numeric_only=True).reset_index()
    timeframe_df['timeframe (wks)'] = pd.Categorical(timeframe_df['timeframe (wks)'],
                                                     categories=['<2 wks', '2-4 wks', '4-8 wks', '8-12 wks', '>12 wks'],
                                                     ordered=True)
    timeframe_df.sort_values('timeframe (wks)', inplace=True)
    timeframe_df['%'] = round(
        timeframe_df['Number of action points'] / sum(timeframe_df['Number of action points']) * 100, 1)
    timeframe_df['# (%)'] = timeframe_df['Number of action points'].astype(str) + " (" + timeframe_df['%'].astype(
        str) + "%)"

    return facilities_df, area_reviewed_df, action_point_status_df, weekly_counts, timeframe_df, area_reviewed_facility_df


def get_mean_color(fyj_mean, thresholds, list_colors):
    for i in range(len(thresholds)):
        if fyj_mean >= thresholds[i]:
            return fyj_mean, list_colors[i]
    return fyj_mean, list_colors[-1]


def create_system_assessment_chart(df, fyj_mean, mean_color, quarter_year):
    # Creating the plot using plotly express
    fig = px.bar(df, x='Component of the M&E System', y='Mean', height=450,
                 title=f'FYJ {quarter_year} DQA system assessment', text='Mean',
                 labels={'Component of the M&E System': 'Component of the M&E System', 'Mean': 'Mean'}
                 , color='color', color_discrete_sequence=df['color'].unique(),
                 # template='simple_white'
                 )
    line_length = df.shape[0] - 0.3
    # Adding the mean line to the plot
    fig.add_shape(type='line', x0=-0.5, y0=fyj_mean, x1=line_length, y1=fyj_mean,
                  line=dict(color='red', width=2, dash='dot'))
    # if fyj_mean >= 2.5:
    #     mean_color = "green"
    # elif fyj_mean < 2.5 and fyj_mean >= 1.5:
    #     mean_color = "#ebba34"
    # else:
    #     mean_color = "red"

    # Adding the mean label to the plot
    fig.add_annotation(x=line_length, y=fyj_mean, text=f'Mean: {fyj_mean}', showarrow=True,
                       font=dict(size=14, color=mean_color), arrowhead=1)

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
                size=8
            ),
            title_font=dict(
                size=10
            )
        ),
        yaxis=dict(
            title_font=dict(
                size=8
            )
        ),
        legend=dict(
            font=dict(
                size=10
            )
        ),
        title=dict(
            font=dict(
                size=14
            )
        )
    )
    fig.update_layout(showlegend=False)
    return plot(fig, include_plotlyjs=False, output_type="div")


def clean_audit_team_df(audit_team_df):
    audit_team_df['Number of audit team'] = 1
    audit_team_df['Carder'] = audit_team_df['Carder'].str.replace("Monitoring and Evaluation", "M&E")
    audit_team_df['Carder'] = audit_team_df['Carder'].str.replace("SIA", "SI Associate")

    mel_df = audit_team_df[audit_team_df['Carder'].str.contains("ag. mel spe", case=False)]
    mel_df['Carder'] = "AG. MEL SPECIALIST"
    non_mel_df = audit_team_df[~audit_team_df['Carder'].str.contains("ag. mel spe", case=False)]
    audit_team_df = pd.concat([mel_df, non_mel_df])

    si_df = audit_team_df[audit_team_df['Carder'] == "SI"]
    si_df['Carder'] = "SI Associate"
    non_si_df = audit_team_df[audit_team_df['Carder'] != "SI"]
    audit_team_df = pd.concat([si_df, non_si_df])

    # audit_team_df['Carder'] = audit_team_df['Carder'].str.replace("SI", "SI Associate")
    audit_team_df['Carder'] = audit_team_df['Carder'].str.upper()
    audit_team_df['Carder'] = audit_team_df['Carder'].str.replace("S.I ASSOCIATE", "SI ASSOCIATE", regex=True)
    audit_team_df['Carder'] = audit_team_df['Carder'].str.replace("RCO", "CLINICAL OFFICER")
    audit_team_df['Carder'] = audit_team_df['Carder'].str.replace("CLINICIAN", "CLINICAL OFFICER")

    clinician_df = audit_team_df[audit_team_df['Carder'] == "CLINICIAN"]
    si_df['Carder'] = "CLINICAL OFFICER"
    non_clinician_df = audit_team_df[audit_team_df['Carder'] != "CLINICIAN"]
    audit_team_df = pd.concat([clinician_df, non_clinician_df])

    clinician_df = audit_team_df[audit_team_df['Carder'] == "M&E ASS"]
    si_df['Carder'] = "M&E ASSISTANT"
    non_clinician_df = audit_team_df[audit_team_df['Carder'] != "M&E ASS"]
    audit_team_df = pd.concat([clinician_df, non_clinician_df])

    # audit_team_df['Carder'] = audit_team_df['Carder'].str.replace("M&E ASS", "M&E ASSISTANT")
    audit_team_df['Carder'] = audit_team_df['Carder'].str.replace("HIS/M&E ASS", "M&E ASSISTANT")
    audit_team_df['Carder'] = audit_team_df['Carder'].str.replace("M & E ASSISTANT", "M&E ASSISTANT")
    audit_team_df['Carder'] = audit_team_df['Carder'].str.replace("HUB 3", "")
    audit_team_df['Carder'] = audit_team_df['Carder'].str.replace("HUB 1", "")
    audit_team_df['Carder'] = audit_team_df['Carder'].str.replace("HUB 2", "")
    audit_team_df['Carder'] = audit_team_df['Carder'].str.replace("SUB COUNTY HRIO", "SCHRIO")

    # Replace matching substrings with 'FYJ'
    fyj_df = audit_team_df[
        audit_team_df['Organization'].str.contains("fyj|sil|savannah|fahari|jamii|usaid|uon|university of nairobi",
                                                   case=False)]
    fyj_df = fyj_df.copy()
    fyj_df['Organization'] = "FYJ"

    # Replace matching substrings with 'MOH'
    non_fyj_df = audit_team_df[
        ~audit_team_df['Organization'].str.contains("fyj|sil|savannah|fahari|jamii|usaid|uon|university of nairobi",
                                                    case=False)]
    non_fyj_df = non_fyj_df.copy()
    non_fyj_df['Organization'] = "MOH"
    audit_team_df = pd.concat([non_fyj_df, fyj_df])

    # avoid counting names twice
    audit_team_df = audit_team_df.groupby(['Name', 'Carder', 'Organization']).sum(
        numeric_only=True).reset_index().sort_values("Number of audit team", ascending=False)

    # final grouping
    audit_team_df = audit_team_df.groupby(['Carder', 'Organization']).sum(
        numeric_only=True).reset_index().sort_values("Number of audit team", ascending=False)
    return audit_team_df


def prepare_deep_dive_dfs(df, col):
    # df=dfs.copy()
    df['Number of scores'] = 1
    df = df.groupby(col).sum(numeric_only=True)['Number of scores'].reset_index()
    df['%'] = round(df['Number of scores'] / sum(df['Number of scores']) * 100, 1)
    if col == "description":
        df = df.sort_values("%", ascending=False)
    return df


def pluralize_word(word, count):
    # This is a simple example, you can customize it for more complex pluralization rules
    if count == 1:
        return word
    else:
        return word + 's'


def generate_missing_indicators_message(data_verification_data, model_name, interested_unit, quarter_year):
    # Create a dictionary to track wards and the number of missing indicators
    wards_missing_indicators = defaultdict(int)

    # Iterate through unique wards
    unique_wards = set(item[interested_unit] for item in data_verification_data)
    for ward in unique_wards:
        # Get the indicators for this ward
        ward_indicators = set(
            item['indicator'] for item in data_verification_data if item[interested_unit] == ward)

        # Count the number of missing indicators for the ward
        missing_indicators_count = sum(
            1
            for indicator_choice in model_name.INDICATOR_CHOICES[1:]
            if indicator_choice[0] not in ward_indicators
        )

        # If the ward is missing any indicators, add it to the dictionary
        if missing_indicators_count > 0:
            wards_missing_indicators[ward] = missing_indicators_count

    # Generate a message for the wards missing indicators
    if wards_missing_indicators:
        # Sort wards by the number of missing indicators in descending order
        sorted_wards = sorted(wards_missing_indicators.items(), key=lambda x: x[1], reverse=True)

        missing_wards_message = "\n".join(
            f" {ward} is missing {count} {pluralize_word('indicator', count)},"
            for ward, count in sorted_wards
        )
        return f"Data Verification section {quarter_year}:" + missing_wards_message
    else:
        return None  # No missing indicators


@login_required(login_url='login')
def dqa_dashboard(request, dqa_type=None):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    quarter_form = QuarterSelectionForm(request.POST or None)
    year_form = YearSelectionForm(request.POST or None)
    hub_form = HubSelectionForm(request.POST or None)
    subcounty_form = SubcountySelectionForm(request.POST or None)
    county_form = CountySelectionForm(request.POST or None)
    program_form = ProgramSelectionForm(request.POST or None)
    viz = None
    sub_county_viz = None
    county_viz = None
    hub_viz = None
    quarter_year = None
    system_assessment_viz = None
    dicts = None
    data = None
    system_assessment = None
    khis_performance = None
    fyj_performance = None
    charts = None
    audit_team = None
    audit_team_df_copy = None
    county_hub_sub_county_df = None
    data_verification = None
    audit_viz = None
    red = None
    yellow = None
    na_df = None
    non_performance_df = None
    na_viz_quest = None
    na_viz_comp = None
    red_viz_quest = None
    red_viz_comp = None
    yellow_viz_quest = None
    yellow_viz_comp = None
    all_dfs_viz = None
    dqa_workplan = None
    selected_level = None
    work_plan_facilities_viz = None
    work_plan_actionpoint_status_viz = None
    work_plan_areas_reviewed_viz = None
    work_plan_trend_viz = None
    work_plan_timeframe_viz = None
    data_verification_viz = None
    facility_charts = None
    reset_queries()
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
    if dqa_type == "program":
        if quarter_form.is_valid() and year_form.is_valid() and program_form.is_valid():
            selected_quarter = quarter_form.cleaned_data['quarter']
            selected_year = year_form.cleaned_data['year']
            selected_program = program_form.cleaned_data['program']
            selected_level = selected_program
            year_suffix = selected_year[-2:]
            quarter_year = f"{selected_quarter}-{year_suffix}"

            data_verification = DataVerification.objects.filter(quarter_year__quarter_year=quarter_year).select_related(
                'quarter_year', 'facility_name')
            system_assessment = SystemAssessment.objects.filter(quarter_year__quarter_year=quarter_year).select_related(
                'quarter_year', 'facility_name')
            fyj_performance = FyjPerformance.objects.filter(quarter_year=quarter_year).values()
            khis_performance = KhisPerformance.objects.filter(quarter_year=quarter_year).values()
            audit_team = AuditTeam.objects.filter(quarter_year__quarter_year=quarter_year).select_related(
                'quarter_year', 'facility_name')
            dqa_workplan = DQAWorkPlan.objects.filter(quarter_year__quarter_year=quarter_year).select_related(
                'quarter_year', 'facility_name').order_by(
                'facility_name')
            #####################################
            # DECREMENT REMAINING TIME DAILY    #
            #####################################
            if dqa_workplan:
                calculate_progress(dqa_workplan)

            # fetch data from the Sub_counties model
            data = Sub_counties.objects.values('facilities__name', 'facilities__mfl_code', 'hub__hub',
                                               'counties__county_name', 'sub_counties')

    elif dqa_type == "subcounty":
        if quarter_form.is_valid() and year_form.is_valid() and subcounty_form.is_valid():
            selected_quarter = quarter_form.cleaned_data['quarter']
            selected_year = year_form.cleaned_data['year']
            selected_subcounty = subcounty_form.cleaned_data['subcounty']
            selected_level = selected_subcounty
            year_suffix = selected_year[-2:]
            quarter_year = f"{selected_quarter}-{year_suffix}"
            sub_county = Sub_counties.objects.get(sub_counties=selected_subcounty)
            facilities = sub_county.facilities.all()
            data_verification = DataVerification.objects.filter(quarter_year__quarter_year=quarter_year,
                                                                facility_name__in=facilities).select_related(
                'facility_name', 'quarter_year')

            system_assessment = SystemAssessment.objects.filter(quarter_year__quarter_year=quarter_year,
                                                                facility_name__in=facilities).select_related(
                'facility_name', 'quarter_year')
            fyj_performance = FyjPerformance.objects.filter(quarter_year=quarter_year).values()
            khis_performance = KhisPerformance.objects.filter(quarter_year=quarter_year).values()
            audit_team = AuditTeam.objects.filter(quarter_year__quarter_year=quarter_year,
                                                  facility_name__in=facilities).select_related('facility_name',
                                                                                               'quarter_year')
            dqa_workplan = DQAWorkPlan.objects.filter(quarter_year__quarter_year=quarter_year,
                                                      facility_name__in=facilities).select_related('facility_name',
                                                                                                   'quarter_year').order_by(
                'facility_name')
            #####################################
            # DECREMENT REMAINING TIME DAILY    #
            #####################################
            if dqa_workplan:
                calculate_progress(dqa_workplan)

            # fetch data from the Sub_counties model
            data = Sub_counties.objects.values('facilities__name', 'facilities__mfl_code', 'hub__hub',
                                               'counties__county_name', 'sub_counties')

    elif dqa_type == "county":
        if quarter_form.is_valid() and year_form.is_valid() and county_form.is_valid():
            selected_quarter = quarter_form.cleaned_data['quarter']
            selected_year = year_form.cleaned_data['year']
            selected_county = county_form.cleaned_data['county']
            selected_level = selected_county
            year_suffix = selected_year[-2:]
            quarter_year = f"{selected_quarter}-{year_suffix}"
            # county = Counties.objects.get(county_name=selected_county)

            data_verification = DataVerification.objects.filter(
                quarter_year__quarter_year=quarter_year,
                facility_name__sub_counties__counties__county_name=selected_county).select_related('facility_name',
                                                                                                   'quarter_year')

            system_assessment = SystemAssessment.objects.filter(
                quarter_year__quarter_year=quarter_year,
                facility_name__sub_counties__counties__county_name=selected_county).select_related('facility_name',
                                                                                                   'quarter_year')
            fyj_performance = FyjPerformance.objects.filter(quarter_year=quarter_year).values()
            khis_performance = KhisPerformance.objects.filter(quarter_year=quarter_year).values()
            audit_team = AuditTeam.objects.filter(
                quarter_year__quarter_year=quarter_year,
                facility_name__sub_counties__counties__county_name=selected_county).select_related('facility_name',
                                                                                                   'quarter_year')
            dqa_workplan = DQAWorkPlan.objects.filter(
                quarter_year__quarter_year=quarter_year,
                facility_name__sub_counties__counties__county_name=selected_county).select_related('facility_name',
                                                                                                   'quarter_year').order_by(
                'facility_name')
            #####################################
            # DECREMENT REMAINING TIME DAILY    #
            #####################################
            if dqa_workplan:
                calculate_progress(dqa_workplan)

            # fetch data from the Sub_counties model
            data = Sub_counties.objects.values('facilities__name', 'facilities__mfl_code', 'hub__hub',
                                               'counties__county_name', 'sub_counties')

    elif dqa_type == "hub":
        if quarter_form.is_valid() and year_form.is_valid() and hub_form.is_valid():
            selected_quarter = quarter_form.cleaned_data['quarter']
            selected_year = year_form.cleaned_data['year']
            selected_hub = hub_form.cleaned_data['hub']
            selected_level = selected_hub
            year_suffix = selected_year[-2:]
            quarter_year = f"{selected_quarter}-{year_suffix}"

            data_verification = DataVerification.objects.filter(
                quarter_year__quarter_year=quarter_year,
                facility_name__sub_counties__hub__hub=selected_hub).select_related('facility_name', 'quarter_year')

            system_assessment = SystemAssessment.objects.filter(
                quarter_year__quarter_year=quarter_year,
                facility_name__sub_counties__hub__hub=selected_hub).select_related('facility_name', 'quarter_year')
            fyj_performance = FyjPerformance.objects.filter(quarter_year=quarter_year).values()
            khis_performance = KhisPerformance.objects.filter(quarter_year=quarter_year).values()
            audit_team = AuditTeam.objects.filter(
                quarter_year__quarter_year=quarter_year,
                facility_name__sub_counties__hub__hub=selected_hub).select_related('facility_name', 'quarter_year')
            dqa_workplan = DQAWorkPlan.objects.filter(
                quarter_year__quarter_year=quarter_year,
                facility_name__sub_counties__hub__hub=selected_hub).select_related(
                'facility_name', 'quarter_year').order_by('facility_name')
            #####################################
            # DECREMENT REMAINING TIME DAILY    #
            #####################################
            if dqa_workplan:
                calculate_progress(dqa_workplan)

            # fetch data from the Sub_counties model
            data = Sub_counties.objects.values('facilities__name', 'facilities__mfl_code', 'hub__hub',
                                               'counties__county_name', 'sub_counties')

    if dqa_type is not None and quarter_form.is_valid():
        if data_verification:
            data_verification_data = data_verification.values('facility_name__name', 'indicator')
            message = generate_missing_indicators_message(data_verification_data, DataVerification,
                                                          'facility_name__name', quarter_year)
            if message:
                messages.success(request, message)
            facilities = [
                {'facilities': x.facility_name.name,
                 'mfl_code': x.facility_name.mfl_code,
                 } for x in data_verification
            ]
            # convert data from database to a dataframe
            facilities_df = pd.DataFrame(facilities).drop_duplicates()
            facilities_df.sort_values('facilities', inplace=True)
            facilities_df['count'] = 1
            viz = bar_chart_dqa(facilities_df, "facilities", "count",
                                title=f"{len(facilities_df)} Facilities DQA Summary for {quarter_year}")
        else:
            facilities_df = pd.DataFrame(columns=['facilities', 'mfl_code', 'count'])

        if data:
            # create a list of dictionaries containing the data
            county_hub_sub_county = []
            for d in data:
                county_hub_sub_county.append({
                    'facilities': d['facilities__name'],
                    'mfl_code': d['facilities__mfl_code'],
                    'hubs': d['hub__hub'],
                    'counties': d['counties__county_name'],
                    'sub_counties': d['sub_counties']
                })

            # convert the list of dictionaries to a pandas dataframe
            county_hub_sub_county_df = pd.DataFrame(county_hub_sub_county)
            county_hub_sub_county_df.sort_values('facilities', inplace=True)

            merged_df = county_hub_sub_county_df.merge(facilities_df, on=['facilities', 'mfl_code'], how="right")
            if merged_df.shape[0] > 0:
                merged_df['sub_counties'] = merged_df['sub_counties'].str.replace(" Sub County", "")
                sub_county_df = merged_df.groupby('sub_counties')[
                    'count'].sum(numeric_only=True).reset_index().sort_values('count')
                sub_county_df = sub_county_df.rename(columns={"count": "Number of facilities"})
                sub_county_viz = bar_chart_dqa(sub_county_df, "sub_counties", "Number of facilities",
                                               title=f"{len(sub_county_df)} Sub-counties DQA Summary for {quarter_year}")
                county_df = merged_df.groupby('counties').sum(numeric_only=True)['count'].reset_index().sort_values(
                    'count')
                county_df = county_df.rename(columns={"count": "Number of facilities"})
                county_viz = bar_chart_dqa(county_df, "counties", "Number of facilities",
                                           title=f"Counties DQA Summary for {quarter_year}")
                hub_df = merged_df.groupby('hubs').sum(numeric_only=True)['count'].reset_index().sort_values(
                    'count')
                hub_df = hub_df.rename(columns={"count": "Number of facilities"})
                hub_viz = bar_chart_dqa(hub_df, "hubs", "Number of facilities",
                                        title=f"{len(hub_df)} Hubs DQA Summary for {quarter_year}")
        if system_assessment:
            system_assessments_qs = [
                {'facilities': x.facility_name.name,
                 'mfl_code': x.facility_name.mfl_code,
                 'description': x.description,
                 "auditor's note": x.auditor_note,
                 'calculations': x.calculations
                 } for x in system_assessment
            ]
            # convert data from database to a dataframe
            system_assessments_df = pd.DataFrame(system_assessments_qs)
            # system_assessments_df = system_assessments_df[system_assessments_df['calculations'].notna()]
            system_assessments_df.sort_values('facilities', inplace=True)
            system_assessments_df['count'] = 1
            fyj_mean = round(system_assessments_df['calculations'].mean(), 2)

            average_dictionary, expected_counts_dictionary = calculate_averages(system_assessment,
                                                                                description_list)
            df = pd.DataFrame(average_dictionary.items(), columns=['Component of the M&E System', 'Mean'])
            df['Component of the M&E System'] = df['Component of the M&E System'].str.replace(
                "average_calculations_5_12", "Data Management Processes")
            df['Component of the M&E System'] = df['Component of the M&E System'].str.replace(
                "average_calculations_5",
                "M&E Structure, Functions and Capabilities")

            df['Component of the M&E System'] = df['Component of the M&E System'].str.replace(
                "average_calculations_12_17", "Indicator Definitions and Reporting Guidelines")
            df['Component of the M&E System'] = df['Component of the M&E System'].str.replace(
                "average_calculations_17_21", "Data-collection and Reporting Forms / Tools")
            df['Component of the M&E System'] = df['Component of the M&E System'].str.replace(
                "average_calculations_21_25", "EMR Systems")

            cond_list = [df['Mean'] >= 2.5, (df['Mean'] >= 1.5) & (df['Mean'] < 2.5), df['Mean'] < 1.5]
            choice_list = ["green", "yellow", "red"]
            df['color'] = np.select(cond_list, choice_list, default="n/a")
            thresholds = [2.5, 1.5]
            color_list = ["green", "#ebba34", "red"]
            fyj_mean, mean_color = get_mean_color(fyj_mean, thresholds, color_list)
            system_assessment_viz = create_system_assessment_chart(df, fyj_mean, mean_color, quarter_year)
            # Show system assessment performance
            custom_mapping = {
                1: ("red", "reds"),
                2: ("yellow", "yellows"),
                3: ("green", "greens"),
                0: ("not_applicable", "not applicable"),
            }
            m_e_structures, m_e_data_mnx, m_e_indicator_definition, m_e_data_collect_report, m_e_emr_systems, red, \
                yellow, na_df, green, light_green, blue, all_dfs = prepare_data_system_assessment(system_assessments_df,
                                                                                                  custom_mapping,
                                                                                                  description_list)
            names = ["I - M&E Structure, Functions and Capabilities", "II - Data Management Processes",
                     "III - Indicator Definitions and Reporting Guidelines",
                     "IV - Data-collection and Reporting Forms / Tools",
                     "V - EMR Systems"]
            lists = [m_e_structures, m_e_data_mnx, m_e_indicator_definition, m_e_data_collect_report,
                     m_e_emr_systems]

            non_performance_df = {
                "yellow": yellow,
                "red": red,
                "na_df": na_df,
            }
            all_dfs_viz = bar_chart_dqa(all_dfs, "Scores", '# of scores',
                                        title=f"Distribution of system assessment scores N = {all_dfs['# of scores'].sum()}"
                                              f" ({quarter_year})"
                                        )

            yellow_dfs = prepare_deep_dive_dfs(yellow, 'Component of the M&E System')
            yellow_viz_comp = bar_chart_dqa(yellow_dfs, "Component of the M&E System", 'Number of scores',
                                            title="Distribution of yellow scores per component of the M&E System",
                                            color='yellow')
            yellow_dfs = prepare_deep_dive_dfs(yellow, 'description')
            yellow_viz_quest = bar_chart_dqa(yellow_dfs, "description", 'Number of scores',
                                             title="Distribution of yellow scores per description",
                                             color='yellow')

            red_dfs = prepare_deep_dive_dfs(red, 'Component of the M&E System')
            red_viz_comp = bar_chart_dqa(red_dfs, "Component of the M&E System", 'Number of scores',
                                         title="Distribution of red scores per component of the M&E System",
                                         color='red')
            red_dfs = prepare_deep_dive_dfs(red, 'description')
            red_viz_quest = bar_chart_dqa(red_dfs, "description", 'Number of scores',
                                          title="Distribution of red scores per description", color='red')

            na_dfs = prepare_deep_dive_dfs(na_df, 'Component of the M&E System')
            na_viz_comp = bar_chart_dqa(na_dfs, "Component of the M&E System", 'Number of scores',
                                        title="Distribution of not applicable per component of the M&E System",
                                        color='grey')
            na_dfs = prepare_deep_dive_dfs(na_df, 'description')
            na_viz_quest = bar_chart_dqa(na_dfs, "description", 'Number of scores',
                                         title="Distribution of not applicable scores per description", color='grey')

            charts_dict = dict(zip(names, lists))
            charts = []
            for title, df in charts_dict.items():
                charts.append(create_system_assessment_bar_charts(df, title, quarter_year, description_list))
            if 'Number of scores' in yellow.columns:
                del yellow['Number of scores']
            if 'Number of scores' in red.columns:
                del red['Number of scores']
            if 'Number of scores' in na_df.columns:
                del na_df['Number of scores']
        else:
            messages.info(request, f"No system assessment data for {quarter_year}!")
        if data_verification:
            dqa_df = create_dqa_df(data_verification)
            if dqa_df.empty:
                messages.info(request, f"A few DQA indicators have been capture but not "
                                       f"enough for data visualization")
        else:
            dqa_df = pd.DataFrame(columns=['indicator', 'facility', 'mfl_code', 'Source', 'MOH 731', 'KHIS',
                                           'quarter_year', 'last month'])
            messages.info(request, f"No DQA data for {quarter_year}")
        if fyj_performance:
            fyj_perf_df = make_performance_df(fyj_performance, 'DATIM')
        else:
            fyj_perf_df = pd.DataFrame(columns=['mfl_code', 'quarter_year', 'indicator', 'DATIM'])
            messages.info(request, f"No DATIM data for {quarter_year}!")
        merged_df = dqa_df.merge(fyj_perf_df, on=['mfl_code', 'quarter_year', 'indicator'], how='right')
        merged_df = merged_df[merged_df['facility'].notnull()]
        if khis_performance:
            khis_perf_df = make_performance_df(khis_performance, 'KHIS')

            tx_curr_khis = khis_perf_df[khis_perf_df['indicator'] == "Number Current on ART Total"]

            # apply the function to the 'date' column and store the result in a new column
            # tx_curr_khis['month_number'] = tx_curr_khis['month'].apply(get_month_number)

            tx_curr_khis['month'] = pd.to_datetime(tx_curr_khis['month'], format='%b %Y')
            tx_curr_khis['month_number'] = tx_curr_khis['month'].dt.month

            tx_curr_khis = tx_curr_khis[tx_curr_khis['month_number'] == max(tx_curr_khis['month_number'])]
            del tx_curr_khis['month_number']
            del tx_curr_khis['month']
            khis_others = khis_perf_df[khis_perf_df['indicator'] != "Number Current on ART Total"]

            khis_others = khis_others.groupby(['indicator', 'quarter_year', 'mfl_code']).sum(
                numeric_only=True).reset_index()

            khis_perf_df = pd.concat([khis_others, tx_curr_khis])
        else:
            khis_perf_df = pd.DataFrame(columns=['indicator', 'facility', 'mfl_code', 'KHIS',
                                                 'quarter_year'])

        if "KHIS" in merged_df.columns:
            del merged_df['KHIS']
        if not khis_perf_df.empty and not merged_df.empty:
            merged_df = khis_perf_df.merge(merged_df, on=['mfl_code', 'quarter_year', 'indicator'], how='right').fillna(
                0)
            try:
                merged_df = merged_df[
                    ['mfl_code', 'facility', 'indicator', 'quarter_year', 'Source', 'MOH 731', 'KHIS', 'DATIM']]
            except KeyError:
                messages.info(request, f"No KHIS data for {quarter_year}!")
            for i in merged_df.columns[4:]:
                merged_df[i] = merged_df[i].astype(int)
            merged_df = merged_df.groupby(['indicator', 'quarter_year']).sum(numeric_only=True).reset_index()
            dicts, merged_viz_df = compare_data_verification(merged_df, 'DATIM', description_list)
            indicator_list = ['TB_PREV', 'Gend_GBV_Physical and Emotional', 'CXCA_SCRN',
                              'TB_PREV_N', 'Total Infant prophylaxis', 'Gend_GBV Sexual Violence']
            merged_viz_df = merged_viz_df[~merged_viz_df['indicator'].isin(indicator_list)]
            data_verification_viz = bar_chart_dqa(merged_viz_df, "indicator",
                                                  "Absolute difference proportion (Difference/Source*100)",
                                                  pepfar_col="DATIM", color='Score',
                                                  title="Data verification final scores")
        if viz is None:
            messages.error(request, f"No DQA data found for {quarter_year}")
        if audit_team:
            audit_team_qs = [
                {'Facilities': x.facility_name.name,
                 'mfl_code': x.facility_name.mfl_code,
                 'Name': x.name,
                 'Carder': x.carder,
                 'Organization': x.organization,
                 } for x in audit_team
            ]
            # convert data from database to a dataframe
            audit_team_df = pd.DataFrame(audit_team_qs)
            # groupby 'name' ,'carder','organization' and aggregate the facility names as a string
            audit_team_df = audit_team_df.groupby(['Name', 'Carder', 'Organization']).agg(
                {'Facilities': lambda x: ', '.join(set(x))})

            audit_team_df = audit_team_df.reset_index()
            audit_team_df_copy = audit_team_df.copy()
            audit_team_df = clean_audit_team_df(audit_team_df)
            audit_viz = bar_chart_dqa(audit_team_df, "Carder", 'Number of audit team', color="Organization",
                                      title=f"DQA Audit Team Participation by Organization and Carder "
                                            f"N = {audit_team_df['Number of audit team'].sum()}")

        if dqa_workplan:
            dqa_workplan_qs = [
                {'Facilities': x.facility_name.name,
                 'mfl_code': x.facility_name.mfl_code,
                 'dqa_date': x.dqa_date,
                 'Program Areas Reviewed': x.program_areas_reviewed,
                 'completion': x.percent_completed,
                 'Timeframe': x.timeframe,
                 } for x in dqa_workplan
            ]
            # convert data from database to a dataframe
            dqa_workplan_df = pd.DataFrame(dqa_workplan_qs)
            facilities_df, area_reviewed_df, action_point_status_df, weekly_counts, timeframe_df, \
                area_reviewed_facility_df = prepare_dqa_workplan_viz(dqa_workplan_df, 'Facilities')
            work_plan_facilities_viz = bar_chart_dqa(facilities_df, "Facilities", "Number of action points",
                                                     title=f"Distribution of DQA action points per facility N = "
                                                           f"{facilities_df['Number of action points'].sum()}"
                                                           f" ({quarter_year})",
                                                     color=None)
            work_plan_areas_reviewed_viz = bar_chart_dqa(area_reviewed_df, "Program Areas Reviewed",
                                                         "Number of action points",
                                                         title=f"Distribution of DQA action points by program area "
                                                               f"reviewed N = "
                                                               f"{area_reviewed_df['Number of action points'].sum()}"
                                                               f" ({quarter_year})",
                                                         color=None)
            program_areas = ["CHART_ABSTRACTION", "M_E_SYSTEMS", "Data_Management_Systems", "HTS_PREVENTION_PMTCT"]
            facility_charts = {}
            for program_area in program_areas:
                area_reviewed_facility_df_area = area_reviewed_facility_df[
                    area_reviewed_facility_df['Program Areas Reviewed'] == program_area]
                title = f"Distribution of {program_area.replace('_', ' ')} DQA action points by facility ({quarter_year})"
                chart = bar_chart_dqa(area_reviewed_facility_df_area, "Facilities", "Number of action points",
                                      title=title, color=None)
                facility_charts[program_area] = chart

            work_plan_actionpoint_status_viz = bar_chart_dqa(action_point_status_df, "% completetion",
                                                             "Number of action points",
                                                             title=f"Distribution of DQA Action Points by Completion "
                                                                   f"Percentage N = "
                                                                   f"{action_point_status_df['Number of action points'].sum()}"
                                                                   f" ({quarter_year})",
                                                             color=None)
            work_plan_trend_viz = bar_chart_dqa(weekly_counts, 'dqa_dates (weekly)', 'Number of DQAs done',
                                                title='Trend of DQA activities')
            work_plan_timeframe_viz = bar_chart_dqa(timeframe_df, "timeframe (wks)", "Number of action points",
                                                    title=f"Distribution of DQA Action Points' timeframe by weeks N = "
                                                          f"{timeframe_df['Number of action points'].sum()}"
                                                          f" ({quarter_year})",
                                                    color=None)

    # Print the number of queries executed
    # print(f"Number of queries: {len(connection.queries)}")

    context = {
        "quarter_form": quarter_form,
        "year_form": year_form,
        "viz": viz,
        "sub_county_viz": sub_county_viz,
        "county_viz": county_viz,
        "hub_viz": hub_viz,
        "quarter_year": quarter_year,
        "system_assessment_viz": system_assessment_viz,
        "dicts": dicts,
        "charts": charts,
        "audit_team": audit_team,
        "audit_team_df": audit_team_df_copy,
        "hub_form": hub_form,
        "subcounty_form": subcounty_form,
        "county_form": county_form,
        "program_form": program_form,
        "dqa_type": dqa_type,
        "audit_viz": audit_viz,
        "na_df": na_df,
        "red": red,
        "yellow": yellow,
        "non_performance_df": non_performance_df,
        "yellow_viz_comp": yellow_viz_comp,
        "yellow_viz_quest": yellow_viz_quest,
        "red_viz_comp": red_viz_comp,
        "red_viz_quest": red_viz_quest,
        "na_viz_comp": na_viz_comp,
        "na_viz_quest": na_viz_quest,
        "all_dfs_viz": all_dfs_viz,
        "dqa_workplan": dqa_workplan,
        "selected_level": selected_level,
        "work_plan_facilities_viz": work_plan_facilities_viz,
        "work_plan_areas_reviewed_viz": work_plan_areas_reviewed_viz,
        "work_plan_actionpoint_status_viz": work_plan_actionpoint_status_viz,
        "work_plan_trend_viz": work_plan_trend_viz,
        "work_plan_timeframe_viz": work_plan_timeframe_viz,
        "data_verification_viz": data_verification_viz,
        "facility_charts": facility_charts

    }
    return render(request, 'dqa/dqa_dashboard.html', context)
