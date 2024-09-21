import ast
import csv
import json
from collections import defaultdict
from datetime import datetime
from io import BytesIO

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
import plotly.offline as opy
import seaborn as sns
from django.apps import apps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import Avg, Case, CharField, DateField, ExpressionWrapper, IntegerField, Q, Sum, Value, When
from django.db.models.functions import Cast, Concat
from django.forms import modelformset_factory
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.views import View
from matplotlib import pyplot as plt
from pandas.errors import ParserError
from plotly.offline import plot
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle

from apps.dqa.form import CountySelectionForm, HubSelectionForm, ProgramSelectionForm, \
    SubcountySelectionForm
from apps.dqa.views import add_footer, bar_chart_dqa, clean_audit_team_df, compare_data_verification, create_polar, \
    create_system_assessment_bar_charts, \
    create_system_assessment_chart, \
    disable_update_buttons, generate_missing_indicators_message, get_mean_color, prepare_data_system_assessment, \
    prepare_deep_dive_dfs, \
    prepare_dqa_workplan_viz
from apps.wash_dqa.forms import AuditTeamForm, DataCollectionForm, DataConcordanceForm, DataConcordanceFormUpdate, \
    DataQualityAssessmentForm, DataQualityForm, \
    DateSelectionForm, \
    DocumentationForm, \
    QuarterSelectionForm, \
    WardSelectionForm, \
    WashDQAWorkPlanForm, YearSelectionForm
from apps.wash_dqa.models import Counties, DataCollectionReportingManagement, DataConcordance, \
    DataQualityAssessment, \
    DataQualitySystems, \
    Documentation, JphesPerformance, Period, \
    SubCounties, Ward, WashAuditTeam, WashDQAWorkPlan


def jphes_data_prep(df):
    df = df.fillna(0)
    # Get the list of column names to convert to integers.
    # Start from the column after 'perioddescription'.
    columns_to_convert = df.columns[df.columns.get_loc('perioddescription') + 1:]

    # Convert the selected columns to integers.
    # use the apply function to apply pd.to_numeric to each column.
    # errors='coerce' converts non-convertible values to NaN.
    # downcast='integer' downcasts the data to save memory.
    df[columns_to_convert] = df[columns_to_convert].apply(pd.to_numeric, errors='coerce', downcast='integer')
    # Convert 'periodname' column to datetime
    df['month'] = pd.to_datetime(df['periodname'], format='%b-%y')
    df['month'] = df['month'].dt.strftime('%b %Y')
    df = df[['organisationunitname', 'organisationunitcode', 'month',
             'training_performance-hlcust wash 120',
             'wash_performance-hl81-1 number of people gain2',
             'wash_performance-hl82-1 number of communities1',
             'wash_performance-hl82-2 number of people gain2',
             'wash_performance-hl82-4 number of basic sanit1']]
    columns_to_rename = {'organisationunitname': 'ward_name', 'organisationunitcode': 'ward_code', 'month': 'Month',
                         'training_performance-hlcust wash 120': 'num_trained',
                         'wash_performance-hl81-1 number of people gain2': 'num_basic_drinking_water',
                         'wash_performance-hl82-1 number of communities1': 'num_certified_open_defecation',
                         'wash_performance-hl82-2 number of people gain2': 'num_basic_sanitation_services',
                         'wash_performance-hl82-4 number of basic sanit1': 'num_basic_sanitation_services_institutions',
                         }
    df = df.rename(columns=columns_to_rename)
    return df


def load_jphes_data(request):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == 'POST' and "file" in request.FILES:
        file = request.FILES['file']
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
            try:
                df = jphes_data_prep(df)
            except KeyError:
                messages.error(request, f"Please use '.csv' file from JPHES website.")
                redirect('load_jphes_data')
            try:
                with transaction.atomic():
                    if len(df.columns) == 8:
                        df[df.columns[0]] = df[df.columns[0]].astype(str)
                        df[df.columns[1]] = df[df.columns[1]].astype(str)
                        df[df.columns[2]] = df[df.columns[2]].astype(str)

                        # Iterate over each row in the DataFrame
                        for index, row in df.iterrows():
                            performance = JphesPerformance()
                            ###########################################################
                            # Available columns in JPHES report.csv (31ST August 2023 )
                            ###########################################################
                            performance.ward_name = row[df.columns[0]]
                            performance.ward_code = row[df.columns[1]]
                            performance.month = row[df.columns[2]]
                            performance.number_trained = row[df.columns[3]]
                            performance.number_access_basic_water = row[df.columns[4]]
                            performance.number_community_open_defecation = row[df.columns[5]]
                            performance.number_access_basic_sanitation = row[df.columns[6]]
                            performance.number_access_basic_sanitation_institutions = row[df.columns[7]]
                            #########################################################
                            # Missing columns in JPHES report.csv (31ST August 2023 )
                            #########################################################
                            performance.number_access_safe_sanitation = 0
                            performance.number_access_safe_water = 0
                            performance.save()
                        messages.error(request, f'Data successfully saved in the database!')
                        return redirect('load_jphes_data')
                    else:
                        # Notify the user that the data is not correct
                        messages.error(request,
                                       f'Kindly confirm if {file} has the required columns. The current file has'
                                       f' {len(df.columns)} columns')
                        redirect('load_jphes_data')
            except IntegrityError:
                month_list = ', '.join(str(month) for month in df['Month'].unique())
                error_msg = f"JPHES Data for {month_list} already exists."
                messages.error(request, error_msg)
        else:
            messages.error(request, f"Please use '.csv' file from JPHES website.")
            redirect('load_jphes_data')
    else:
        message = "Upload '.csv' from <a href='https://jphesportal.uonbi.ac.ke/dhis-web-pivot/?id=zDEZCWQ4yJl'>JPHES website</a>."
        messages.info(request, mark_safe(message))
    return render(request, 'wash_dqa/upload.html')


@login_required(login_url='login')
def load_county_sub_county_ward_data(request):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == 'POST' and "file" in request.FILES:
        file = request.FILES['file']
        # Read the data from the Excel file into a pandas DataFrame
        try:
            df = pd.read_csv(file)
        except ParserError:
            df = pd.read_excel(file)

        if "county_name" in df.columns or "sub_county_name" in df.columns or "ward_name" in df.columns or "ward_code" in df.columns:
            df = df.dropna(subset=['county_name', 'sub_county_name', 'ward_name', 'ward_code'])
            df = df[df["county_name"].str.contains("nairobi", case=False)]
            # Iterate through each row and create/update records
            for index, row in df.iterrows():
                county_name = row['county_name'].strip()
                sub_county_name = row['sub_county_name'].strip()
                ward_name = row['ward_name'].strip()
                ward_code = row['ward_code'].strip()
                with transaction.atomic():
                    try:
                        county = Counties.objects.get(name__iexact=county_name)
                    except Counties.DoesNotExist:
                        county = Counties.objects.create(name=county_name)
                    try:
                        sub_county = SubCounties.objects.get(name__iexact=sub_county_name, county=county)
                    except SubCounties.DoesNotExist:
                        sub_county = SubCounties.objects.create(name=sub_county_name, county=county)
                    try:
                        Ward.objects.create(name=ward_name, sub_county=sub_county, ward_code=ward_code)
                    except IntegrityError:
                        pass
        else:
            messages.error(request,
                           f"Uploaded dataset is missing either 'county_name','sub_county_name', 'ward_name' or  'ward_code' columns")
    return render(request, 'wash_dqa/upload.html')


def prepare_formset(request, descriptions, verification_means_list, staff_involved_list, report_type):
    if report_type == "data-quality-assessment":
        initial_data = [{'description': description} for description in descriptions]
    else:
        initial_data = [
            {'description': description,
             'verification_means': verification_means,
             'staff_involved': staff_involved}
            for (description, verification_means, staff_involved) in
            zip(descriptions, verification_means_list, staff_involved_list)
        ]

    if report_type == "documentation":
        model_name = Documentation
        form_name = DocumentationForm
    elif report_type == "data-quality":
        model_name = DataQualitySystems
        form_name = DataQualityForm
    elif report_type == "data-collection":
        model_name = DataCollectionReportingManagement
        form_name = DataCollectionForm
    else:
        model_name = DataQualityAssessment
        form_name = DataQualityAssessmentForm

    wash_dqa_formset = modelformset_factory(
        model_name,
        form=form_name,
        extra=len(descriptions)

    )
    formset = wash_dqa_formset(request.POST or None, queryset=Documentation.objects.none(),
                               initial=initial_data)
    return initial_data, wash_dqa_formset, formset


def handle_form_entry(request, formset, report_type, quarter_form=None, year_form=None, ward_form=None, date_form=None):
    if not all([form.has_changed() for form in formset.forms]):
        messages.error(request, "Please fill all rows in the 'Rating dropdown option columns' before saving.")
        for form in formset.forms:
            if report_type != "data-quality-assessment":
                if not form.cleaned_data.get('dropdown_option'):
                    form.add_error('dropdown_option', "Please choose an option before saving.")
                if form.cleaned_data.get('dropdown_option',
                                         '') not in ("Fully meets all requirements", "") and not form.cleaned_data.get(
                    'auditor_note', ''):
                    messages.warning(request,
                                     "Please provide a note in the 'Rating rationale' field before saving. This field is "
                                     "required because the item in the detailed checklist does not meet all "
                                     "requirements.")
                    form.add_error('auditor_note',
                                   "Please provide rating rationale before saving.")
            else:
                fields_to_check = ['number_trained', 'number_access_basic_water', 'number_access_safe_water',
                                   'number_community_open_defecation', 'number_access_basic_sanitation',
                                   'number_access_safe_sanitation', 'number_access_basic_sanitation_institutions']

                for field_name in fields_to_check:
                    if not form.cleaned_data.get(field_name):
                        form.add_error(field_name, "This field is required.")

        context = {
            "formset": formset, "report_type": report_type,
            "quarter_form": quarter_form,
            "year_form": year_form,
            "ward_form": ward_form,
            "date_form": date_form,
            "page_from": request.session.get('page_from', '/'),
        }
        # return render(request, 'wash_dqa/add_wash_dqa_.html', context)
        return False, context  # Return False to indicate errors
    else:
        return True, None  # Return True to indicate success


def validate_formset(request, formset=None, report_type=None):
    errors = False
    for form in formset.forms:
        if report_type != "data-quality-assessment":
            if form.cleaned_data.get('dropdown_option',
                                     '') not in (
                    "Fully meets all requirements", "N/A") and not form.cleaned_data.get(
                'auditor_note', ''):
                errors = True
                messages.warning(request,
                                 "Please provide a note in the 'Rating rationale' field before saving. This field is "
                                 "required because the item in the detailed checklist does not meet all "
                                 "requirements.")
                form.add_error('auditor_note',
                               "Please provide rating rationale before saving.")
        else:
            fields_to_check = ['number_trained', 'number_access_basic_water', 'number_access_safe_water',
                               'number_community_open_defecation', 'number_access_basic_sanitation',
                               'number_access_safe_sanitation',
                               'number_access_basic_sanitation_institutions']
            if any(form.cleaned_data.get(field_name) not in ("Yes", "N/A") for field_name in
                   fields_to_check):
                for field_name in fields_to_check:
                    if not form.cleaned_data.get(field_name):
                        form.add_error('auditor_note', "Please provide rating rationale before saving.")

            for field_name in fields_to_check:
                if form.cleaned_data.get(field_name, '') not in ("Yes", "N/A"
                                                                 ) and not form.cleaned_data.get(
                    'auditor_note', ''):
                    errors = True
                    form.add_error('auditor_note',
                                   "Please provide reason(s) for 'No'.")
                    break
    return errors


# Create your views here.
@login_required(login_url='login')
def add_documentation(request, report_type="documentation"):
    if not request.user.first_name:
        return redirect("profile")
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    quarter_form = QuarterSelectionForm(request.POST or None)
    year_form = YearSelectionForm(request.POST or None)
    ward_form = WardSelectionForm(request.POST or None)
    date_form = DateSelectionForm(request.POST or None)
    # Data collection
    data_collection_descriptions = [
        'There are standard source documents (e.g.register, training report template, supervision visits etc.) to record all types of project data (service statistics, training and follow-up, supervision visits, advocacy visits, etc).',
        'Standard reporting forms/tools are available to staff responsible for data collection at the facilities, project district/region office, and national office',
        'Reporting forms/tools are  standardized across all district/regions of  project',
        'Data collection and reporting forms include all required program/project indicators',
        'There are clear written instructions for completing the data-collection and reporting forms',
        # 'There is a  documented or adopted guidelines on how to handle gender sensitive data for each reporting level',
        'There is no (or minimal) duplication in data collection requirements for staff/partners, i.e. they are not required to report the same activityion more than one tool',
        'All sub grantee use a standard reporting template',
        'The number of data collection tools is sufficient for program needs and not excessive (all data collected are reported)',
        'There is a data management guideline that describes all data-verification, aggregation, analysis and manipulation steps performed at each reporting level',
        'The project has one or more electronic database which is up to date (last month data is available)',
        'There is a written description of  the project database -what is stored, who maintains/administers it, procedure for back-up etc.',
        'There is a description of the filing system for paper-based data collection and/or reporting (e.g. if supervision visits are filed in physical cabinets and not uploaded in an electronic data capture system or database)',
        'Historical data are properly stored, up to date and readily available (check 12-24 month data, depending on the project year)',
        'Project data (service statistics, training, follow-up, advocacy, sensitization, etc) are disaggregated by sex, age and other criteria (income, location, etc)',
        # 'If beneficiary-level personal information is collected then IDs are used to protect the confidentiality of clients, and access is restricted to this information',
        'Safeguards (such as passwords and ascribing different data management roles to staff) are in place to prevent unauthorized changes to data',
        'There is management support for following up any persistent data gaps with partners', ]
    data_collection_verification_means_list = [
        'Document review (data flow diagram), observation on site. Take a sample',
        'Document review (e.g monthly service reporting tools), discussion',
        'Document review (e.g monthly service reporting tools), discussion',
        'Document review (Monthly Reporting tools for service statistics, training data collection tools, supervision visit report template, etc)',
        'Document review (Monthly Reporting tools for service statistics, training data collection tools, supervision visit report template, etc)',
        'Document review',
        'Document review (Indicator Reference Sheets, data flow diagrm, Monthly Reporting tools, training data collection tools and other data collection tools)',
        'Report review',
        'Document review (data flow diagram, Monthly Reporting tools, training data tools, CMC/supervision visit template, and other program data collection tools)',
        'Record/document review',
        'Observation/database review',
        'Document review, observation/database review',
        'Document review, observation/database review',
        'Observation/database review',
        'Observation/database review',
        'Observation/database review',
        'Observation/database review',
        'Discussion']
    data_collection_staff_involved_list = ['M&E Staff', 'M&E Staff and program+D19 staff',
                                           'M&E Staff and program staff',
                                           'M&E Staff', 'M&E Staff and program staff', 'M&E Staff and program staff',
                                           'M&E Staff and program staff',
                                           'M&E staff, Sub grantee staff', 'M&E Staff and program staff', 'M&E Staff',
                                           'M&E Staff', 'M&E Staff', 'M&E Staff',
                                           'M&E Staff', 'M&E Staff', 'M&E Staff', 'M&E Staff', 'M&E Staff'
                                           ]

    # Data quality
    data_quality_descriptions = [
        'Performance indicator definitions are consistent with existing standard guidelines in the FYJ Indicator database (select a sample)',
        'Definitions and interpretations of indicators are followed consistently when transferring data from data collection forms to summary formats and reports',
        'There is up-to-date DQA plan which clearly outlines the DQA strategy (including the frequency for which data from different data sources or indicators will be assessed and for what data quality dimensions-validity, reliability, integrity, precision, timeliness, completeness, confidentiality and ethics)',
        'The DQA plan is implemented and on track as planned',
        'There are up-to-date DQA reports that are up to standard',
        'M&E work plan includes regular internal DQA activities',
        'Written instructions/guidance on correctly filling in data collection and reporting tools, including addressing data quality challenges is evident at different reporting levels (district/regional office, sub- grantee or facility level)',
        'Standard forms/tools are used consistently by all reporting levels',
        'All reporting levels (facilities, districts, regions)  are reporting on all required indicators',
        'There are documented procedures for addressing specific data quality challenges (e.g. double-counting, “lost to follow-up”)',
        'Steps are taken to limit calculation/aggregation errors, including automation  of spreadsheets where possible (for data aggregation)',
        'Systems are in place to adjust for double-counting',
        'Systems are in place for detecting missing data',
        'The number of transcription stages (manual transfer of data from one form to another) are minimized to limit transcription error (check if data are entered directly into the database or they are aggregated in another software or aggregated manually first)',
        'There are clear links between fields on data entry/collection forms and summary or compilation forms to reduce transcription error (for service statistics, training data and other project data that involves compiliation)',
        'To the extent possible, relevant data are collected with electronic devices (check if routine data and/or research/study data are collected with electronic devices, note the difference in the rationale)',
        'Feedback is provided to all reporting levels  on the quality of their reporting  (i.e., accuracy, completeness and timeliness)',
        'There is evidence that corrections have been made to historical data following data quality assessments',
        'A senior staff member (e.g., Program Director) is responsible for reviewing the aggregated numbers prior to the submission reports from the country office',
        'There is evidence that supervisory site visits have been made in the last 12 months where data quality has been reviewed',
        'There are designated staff responsible for reviewing the quality of data (i.e., accuracy, completeness,  timeliness and confidentiality ) received from sub-reporting levels (e.g., regions, districts, facilities)',
        'At least once a year both program and M&E staff review a sample of  completed data collection tools  for completion,  accuracy or service quality issues',
        'Sub grantees reports are filled in completely (review a sample of the tools)',
        'All expected sub grantees reports have been received',
        'Donor reports are submitted on time',
        'Data reported corresponds with donor-specified report periods']
    data_quality_verification_means_list = ['Indicator reference sheets/PR Review', 'Observation',
                                            'Record/document review', 'Record/document review',
                                            'Record review/observation', 'Work plan review',
                                            'Observation', 'Observation',
                                            'Record/database review', 'Record/document review',
                                            'Observation', 'Observation, discussion',
                                            'Observation, discussion', 'Observation',
                                            'Document review, observation', 'Discussion',
                                            'Record review', 'Observation',
                                            'Discussion', 'Record review',
                                            'Discussion, record review', 'Discussion, record review',
                                            'Report review', 'Report review',
                                            'Report review, discussion', 'Discussion, record review']
    data_quality_staff_involved_list = ['M&E Staff', 'M&E Staff', 'M&E Staff', 'M&E Staff', 'M&E Staff', 'M&E Staff',
                                        'M&E Staff', 'M&E Staff', 'M&E Staff', 'M&E Staff', 'M&E Staff', 'M&E Staff',
                                        'M&E Staff', 'M&E Staff', 'M&E Staff', 'M&E and management Staff', 'M&E Staff',
                                        'M&E Staff', 'M&E and management Staff', 'M&E Staff', 'M&E Staff',
                                        'M&E and program Staff', 'M&E Staff', 'M&E Staff', 'HQ PM backstop',
                                        'M&E Staff']

    # Documentation
    documentation_descriptions = [
        'There is an up to date M&E plan/PMP',
        'The M&E plan has a logic model/ results framework and/or Theory of Change linking project/ program goal, outcomes and outputs',
        'The M&E plan or other project design document has an organogram describing the organization of the M&E unit in relation to the overall project team',
        'The M&E plan includes indicators for measuring input, outputs, outcomes and where relevant, impact indicators, and the indicators are linked to the project objectives',
        'All indicators being tracked have documented operational definitions (including data disaggregation by age, sex, etc) in the indicator reference sheets',
        'There is an up to date Performance Indicator Tracking Table that is complete (include a list of indicators, baseline, annual and cummulative targets, and data sources)',
        'There is an up-to-date M&E work plan that details the implementation timeline for M&E activities and indicates persons responsible for each activity',
        'There is a detailed data flow diagram from Service Delivery Sites (facilities) to Intermediate Aggregation Levels (e.g. project district or regional offices); and from Intermediate Aggregation Levels (if any) to the national office (could be part of the M&E plan)',
        'There is a written description or guidance of how project activities (such as service delivery, training and follow-up, etc) are documented in source documents (e.g registers, supervision reports, etc)',
        'There is a written guideline to all reporting entities (e.g., regions, districts, facilities) on reporting requirements and deadlines',
        'There are guidelines and schedules for routine supervisory site visits',
        'Sub grantee have a copy of standard guidelines describing reporting requirements (what to report on, due dates, data sources, report recipients, etc.)']
    documentation_verification_means_list = [
        'M&E plan /PMP', 'M&E plan', 'M&E plan', 'M&E plan', 'M&E plan, indicator reference sheets',
        'PITT(Performance Indicator Tracking Table)', 'M&E work plan/project work plan', 'Data flow diagram',
        'Record review, quarterly advisory', 'Record review', 'Record/document review',
        'Record review or observation on site'
    ]
    documentation_staff_involved_list = [
        'M&E Staff', 'M&E Staff', 'M&E Staff', 'M&E Staff', 'M&E Staff', 'M&E Staff', 'M&E Staff', 'M&E Staff',
        'M&E Staff', 'M&E Staff', 'M&E Staff', 'M&E Staff, sub grantee'
    ]

    # Data quality assessment by data source
    data_quality_assessment_descriptions = [
        'Does the information collected measure what it is supposed to measure or the intended result?',
        'Do data collected fall within a plausible range? (E.g. an indicator value of 400% compared to the target should raise a red flag)',
        'Did the data collection tool focus on the information needed to answer the question or measure performance? (i.e. the tools and collection procedures are well designed and  limit the potential for systematic or random errors)',
        'Are sound research methods being used to collect the data?',
        'Are the data used in computing the indicator measured from the same data source, with the same data collection tool within the reporting period, in different location (facilities, districts, regions)?',
        # 'If data come from different sources for different locations(e.g. regions) within a country, are the instruments are similar enough to make the data collected comparable?',
        'If the indicator involve data manipulation such as calculation of rates or proportion,  is the same formulae are applied consistently (and correctly) within the reporting period and in all location?',
        'Are data collection and analysis methods documented in writing and being used to ensure the same procedures are followed each time?',

        'Are procedures or safeguards in place to minimize data transcription errors?',
        'Are mechanisms in place to prevent unauthorized changes to the data?',
        'Is there independence in key data collection, management, and assessment procedures?',
        'For data from a secondary source, is there a confidence in the credibility of the data?',
        'Has the data ever been independently reviewed by a person outside the data collection effort',

        'Was data appropriately disaggregated (sex, age, geographical location) as planned?',
        'If the data is based on a sample, is the margin of error acceptable? (i.e. is it lesser than the expected change being measured? E.g. If a change of only 2 percent is expected and the margin of error is +/- 5 percent, then the tool is not precise enough to detect the change.)',
        'If the data is based on a sample, has the margin of error been reported along with the data?',
        'Is the data collection method/tool fine-tuned or exact enough to register the expected change? (E.g. an aggregated national system may not be a precise enough to measure a change of a few districts).',

        'Are the data available for the most current reporting period ?',
        'Are data available frequently enough to inform program management decisions?',
        'Are the data aggregated, analyzed and reported as soon as possible after collection?',
        'Is the date of data collection clearly identified in reports?',

        'Is there a list of the required reporting units for the data?',
        'Did all the required reporting units (facilities, districts) report data for the reporting period?',

        'If data are personally identifiable and sensitive, the data is stored in a way that cannot be traced to an individual (personal identifiable information are replaced with  identification codes in the database)',
        'If data are personally identifiable and sensitive, data are reported/presented in such a way that discrete variables cannot be used (alone or in combination) to identify an individual',
        'If data are personally identifiable and sensitive, access to database is passworded and limited',

        'If data is from a sample, are processes for obtaining informed consent in place?',
        'If data is from a sample, have the organizational procedures for ethical review of the data collection protocols been adhered to?',
        'If data is from a sample, files such as pictures, success stories, and GIS data have been stored in a way that no individual or group of people can be identified',
        'If data is from a sample, does the reporting/presentation exaggerates the interpretation of the data?',
        'Are the limitations of the data collection tool  well documented and reported',
        'Are there safeguards in place to prevent misrepresentation of data (such as marking up data, changing responses or falsification of data)?'
    ]
    data_quality_assessment_verification_means_list = []
    data_quality_assessment_staff_involved_list = []

    if report_type == "documentation":
        initial_data, wash_dqa_formset, formset = prepare_formset(request, documentation_descriptions,
                                                                  documentation_verification_means_list,
                                                                  documentation_staff_involved_list, report_type)
    elif report_type == "data-quality":
        initial_data, wash_dqa_formset, formset = prepare_formset(request, data_quality_descriptions,
                                                                  data_quality_verification_means_list,
                                                                  data_quality_staff_involved_list, report_type)
    elif report_type == "data-collection":
        initial_data, wash_dqa_formset, formset = prepare_formset(request, data_collection_descriptions,
                                                                  data_collection_verification_means_list,
                                                                  data_collection_staff_involved_list, report_type)
    elif report_type == "data-quality-assessment":
        initial_data, wash_dqa_formset, formset = prepare_formset(request, data_quality_assessment_descriptions,
                                                                  data_quality_assessment_verification_means_list,
                                                                  data_quality_assessment_staff_involved_list,
                                                                  report_type)
    else:
        # Handle the case of an invalid report_type
        error_message = f"Invalid page: {report_type}"
        # You can choose to redirect, render an error page, or provide a response with the error message
        return HttpResponseBadRequest(error_message)

    if request.method == "POST":
        formset = wash_dqa_formset(request.POST, initial=initial_data)
        if formset.is_valid() and quarter_form.is_valid() and year_form.is_valid() and date_form.is_valid() and ward_form.is_valid():
            selected_quarter = quarter_form.cleaned_data['quarter']
            selected_ward = ward_form.cleaned_data['name']
            selected_year = year_form.cleaned_data['year']
            selected_date = date_form.cleaned_data['date']
            instances = formset.save(commit=False)
            # Check if all forms in formset are filled
            success, context = handle_form_entry(request, formset, report_type, quarter_form, year_form, ward_form,
                                                 date_form)
            if not success:
                return render(request, 'wash_dqa/add_wash_dqa_.html', context)
            try:
                errors = validate_formset(request, formset, report_type)
                if errors:
                    context = {
                        "formset": formset, "report_type": report_type,
                        "quarter_form": quarter_form,
                        "year_form": year_form,
                        "ward_form": ward_form,
                        "date_form": date_form,
                        "page_from": request.session.get('page_from', '/'),

                    }
                    return render(request, 'wash_dqa/add_wash_dqa_.html', context)
                with transaction.atomic():
                    for form, instance in zip(formset.forms, instances):
                        # Set instance fields from form data
                        if report_type != "data-quality-assessment":
                            instance.dropdown_option = form.cleaned_data['dropdown_option']
                        instance.auditor_note = form.cleaned_data['auditor_note']
                        instance.dqa_date = selected_date
                        instance.created_by = request.user
                        if report_type != "data-quality-assessment":
                            if instance.dropdown_option == 'Fully meets all requirements':
                                instance.calculations = 5
                            elif instance.dropdown_option == 'Almost meets all requirements':
                                instance.calculations = 4
                            elif instance.dropdown_option == 'Partially meets all requirements':
                                instance.calculations = 3
                            elif instance.dropdown_option == 'Approaches basic requirements':
                                instance.calculations = 2
                            elif instance.dropdown_option == 'Does not meet requirements':
                                instance.calculations = 1
                            elif instance.dropdown_option == 'N/A':
                                instance.calculations = 0
                        # Get or create the Facility instance
                        ward, created = Ward.objects.get_or_create(name=selected_ward)
                        instance.ward_name = ward
                        instance.sub_county_name = ward.sub_county
                        # Get or create the Period instance
                        period, created = Period.objects.get_or_create(quarter=selected_quarter, year=selected_year)
                        instance.quarter_year = period
                        instance.save()
                formset = wash_dqa_formset(None, queryset=Documentation.objects.none(),
                                           initial=initial_data)
                messages.success(request, f"{report_type.title()} data for {selected_ward} {period} was "
                                          f"successfully saved to the database!")
            except DatabaseError:
                messages.error(request,
                               f"{report_type.title()} data for {selected_ward} {period} already exists!")

    context = {
        "formset": formset, "report_type": report_type,
        "quarter_form": quarter_form,
        "year_form": year_form,
        "ward_form": ward_form,
        "date_form": date_form,
    }
    return render(request, 'wash_dqa/add_wash_dqa_.html', context)


def calculate_averages(system_assessments, description_list):
    list_of_projects = [
        {'description': x.description,
         'number_trained': x.number_trained_numeric,
         'number_access_basic_water': x.number_access_basic_water_numeric,
         'number_access_safe_water': x.number_access_safe_water_numeric,
         'number_community_open_defecation': x.number_community_open_defecation_numeric,
         'number_access_basic_sanitation': x.number_access_basic_sanitation_numeric,
         'number_access_safe_sanitation': x.number_access_safe_sanitation_numeric,
         'number_access_basic_sanitation_institutions': x.number_access_basic_sanitation_institutions_numeric,
         'quarter_id': x.quarter_year_id,
         'facility_id': x.ward_name_id,
         } for x in system_assessments
    ]

    # Convert data from database to a dataframe
    df = pd.DataFrame(list_of_projects)

    # Define description ranges
    description_ranges = [
        (0, 4), (4, 8), (8, 13), (13, 17),
        (17, 21), (21, 23), (23, 26), (26, None)
    ]

    # Calculate average and expected counts for each description range
    result = {}
    for i, (start, end) in enumerate(description_ranges):
        chunk = description_list[start:end]

        # Calculate averages for all columns
        avg_values = {}
        for column in ['number_trained', 'number_access_basic_water', 'number_access_safe_water',
                       'number_community_open_defecation', 'number_access_basic_sanitation',
                       'number_access_safe_sanitation', 'number_access_basic_sanitation_institutions']:
            cal_values = df.loc[(df['description'].isin(chunk)) & (df[column] != 0), column]
            avg_calc = cal_values.mean()
            # print(f"avg_calc::::::::::::::::{avg_calc}")
            if not pd.isnull(avg_calc):
                avg_values[column] = round(avg_calc, 2)
            else:
                avg_values[column] = 0
            avg_values[column] = round(avg_calc, 2)
            # print(f"avg_calc1::::::::::::::::{avg_calc}")

        # Store average values in the result dictionary
        key = f'average_values_{start}_{end}'
        result[key] = avg_values

    # Calculate average of averages for each description range
    average_of_averages = {}
    for i, (start, end) in enumerate(description_ranges):
        key = f'average_values_{start}_{end}'
        avg_values = result[key]
        # Check if all values in avg_values are NaN
        all_nans = all(pd.isnull(value) for value in avg_values.values())

        if all_nans:
            # If all values are NaN, set the average to NaN
            average_value = float('nan')
        else:
            # Calculate the average of numeric values in avg_values
            numeric_values = [value for value in avg_values.values() if pd.notnull(value)]
            average_value = round(sum(numeric_values) / len(numeric_values), 2)
        average_of_averages[key] = average_value

    # Include the average of averages in the result dictionary
    result['average_of_averages'] = average_of_averages

    return result


def get_assessment_average(system_assessments, report_type, description_list):
    if report_type == "data-quality-assessment":
        average_dictionary = calculate_averages(system_assessments, description_list)
        # # print(f"AVERAGE:::::::::::DATA QUALITY ASSESSMENT:::::{average_dictionary}:::::::::::")
        # # Flatten the dictionary values into a single list
        # all_values = [value for average_dict in average_dictionary.values() for value in average_dict.values()]
        #
        # # Calculate the average of all values
        # average_dictionary = round(sum(all_values) / len(all_values),2)

        # print(average_values)
        # print(f"AVERAGE:::::::::::DATA QUALITY ASSESSMENT:{average_dictionary}")



    #     disable_update_buttons(request, system_assessments)
    else:
        average_dictionary = system_assessments.exclude(calculations=0).aggregate(Avg('calculations'))[
            'calculations__avg']
        average_dictionary = round(average_dictionary, 2)
        if average_dictionary is None:
            average_dictionary = 0
        # print(f"AVERAGE:::::::::::OTHERS:::::{average_dictionary}:::::::::::")
    return average_dictionary


def get_assessment_list_model_name(report_type):
    if report_type == "data-quality-assessment":
        description_list = [
            'Does the information collected measure what it is supposed to measure or the intended result?',
            'Do data collected fall within a plausible range? (E.g. an indicator value of 400% compared to the target should raise a red flag)',
            'Did the data collection tool focus on the information needed to answer the question or measure performance? (i.e. the tools and collection procedures are well designed and  limit the potential for systematic or random errors)',
            'Are sound research methods being used to collect the data?',
            'Are the data used in computing the indicator measured from the same data source, with the same data collection tool within the reporting period, in different location (facilities, districts, regions)?',
            # 'If data come from different sources for different locations(e.g. regions) within a country, are the instruments are similar enough to make the data collected comparable?',
            'If the indicator involve data manipulation such as calculation of rates or proportion,  is the same formulae are applied consistently (and correctly) within the reporting period and in all location?',
            'Are data collection and analysis methods documented in writing and being used to ensure the same procedures are followed each time?',

            'Are procedures or safeguards in place to minimize data transcription errors?',
            'Are mechanisms in place to prevent unauthorized changes to the data?',
            'Is there independence in key data collection, management, and assessment procedures?',
            'For data from a secondary source, is there a confidence in the credibility of the data?',
            'Has the data ever been independently reviewed by a person outside the data collection effort',

            'Was data appropriately disaggregated (sex, age, geographical location) as planned?',
            'If the data is based on a sample, is the margin of error acceptable? (i.e. is it lesser than the expected change being measured? E.g. If a change of only 2 percent is expected and the margin of error is +/- 5 percent, then the tool is not precise enough to detect the change.)',
            'If the data is based on a sample, has the margin of error been reported along with the data?',
            'Is the data collection method/tool fine-tuned or exact enough to register the expected change? (E.g. an aggregated national system may not be a precise enough to measure a change of a few districts).',

            'Are the data available for the most current reporting period ?',
            'Are data available frequently enough to inform program management decisions?',
            'Are the data aggregated, analyzed and reported as soon as possible after collection?',
            'Is the date of data collection clearly identified in reports?',

            'Is there a list of the required reporting units for the data?',
            'Did all the required reporting units (facilities, districts) report data for the reporting period?',

            'If data are personally identifiable and sensitive, the data is stored in a way that cannot be traced to an individual (personal identifiable information are replaced with  identification codes in the database)',
            'If data are personally identifiable and sensitive, data are reported/presented in such a way that discrete variables cannot be used (alone or in combination) to identify an individual',
            'If data are personally identifiable and sensitive, access to database is passworded and limited',

            'If data is from a sample, are processes for obtaining informed consent in place?',
            'If data is from a sample, have the organizational procedures for ethical review of the data collection protocols been adhered to?',
            'If data is from a sample, files such as pictures, success stories, and GIS data have been stored in a way that no individual or group of people can be identified',
            'If data is from a sample, does the reporting/presentation exaggerates the interpretation of the data?',
            'Are the limitations of the data collection tool  well documented and reported',
            'Are there safeguards in place to prevent misrepresentation of data (such as marking up data, changing responses or falsification of data)?'
        ]
        model_name = DataQualityAssessment
    elif report_type == "data-quality":
        description_list = [
            'Performance indicator definitions are consistent with existing standard guidelines in the FYJ Indicator database (select a sample)',
            'Definitions and interpretations of indicators are followed consistently when transferring data from data collection forms to summary formats and reports',
            'There is up-to-date DQA plan which clearly outlines the DQA strategy (including the frequency for which data from different data sources or indicators will be assessed and for what data quality dimensions-validity, reliability, integrity, precision, timeliness, completeness, confidentiality and ethics)',
            'The DQA plan is implemented and on track as planned',
            'There are up-to-date DQA reports that are up to standard',
            'M&E work plan includes regular internal DQA activities',
            'Written instructions/guidance on correctly filling in data collection and reporting tools, including addressing data quality challenges is evident at different reporting levels (district/regional office, sub- grantee or facility level)',
            'Standard forms/tools are used consistently by all reporting levels',
            'All reporting levels (facilities, districts, regions)  are reporting on all required indicators',
            'There are documented procedures for addressing specific data quality challenges (e.g. double-counting, “lost to follow-up”)',
            'Steps are taken to limit calculation/aggregation errors, including automation  of spreadsheets where possible (for data aggregation)',
            'Systems are in place to adjust for double-counting',
            'Systems are in place for detecting missing data',
            'The number of transcription stages (manual transfer of data from one form to another) are minimized to limit transcription error (check if data are entered directly into the database or they are aggregated in another software or aggregated manually first)',
            'There are clear links between fields on data entry/collection forms and summary or compilation forms to reduce transcription error (for service statistics, training data and other project data that involves compiliation)',
            'To the extent possible, relevant data are collected with electronic devices (check if routine data and/or research/study data are collected with electronic devices, note the difference in the rationale)',
            'Feedback is provided to all reporting levels  on the quality of their reporting  (i.e., accuracy, completeness and timeliness)',
            'There is evidence that corrections have been made to historical data following data quality assessments',
            'A senior staff member (e.g., Program Director) is responsible for reviewing the aggregated numbers prior to the submission reports from the country office',
            'There is evidence that supervisory site visits have been made in the last 12 months where data quality has been reviewed',
            'There are designated staff responsible for reviewing the quality of data (i.e., accuracy, completeness,  timeliness and confidentiality ) received from sub-reporting levels (e.g., regions, districts, facilities)',
            'At least once a year both program and M&E staff review a sample of  completed data collection tools  for completion,  accuracy or service quality issues',
            'Sub grantees reports are filled in completely (review a sample of the tools)',
            'All expected sub grantees reports have been received',
            'Donor reports are submitted on time',
            'Data reported corresponds with donor-specified report periods']
        model_name = DataQualitySystems
    elif report_type == "data-collection":
        description_list = [
            'There are standard source documents (e.g.register, training report template, supervision visits etc.) to record all types of project data (service statistics, training and follow-up, supervision visits, advocacy visits, etc).',
            'Standard reporting forms/tools are available to staff responsible for data collection at the facilities, project district/region office, and national office',
            'Reporting forms/tools are  standardized across all district/regions of  project',
            'Data collection and reporting forms include all required program/project indicators',
            'There are clear written instructions for completing the data-collection and reporting forms',
            # 'There is a  documented or adopted guidelines on how to handle gender sensitive data for each reporting level',
            'There is no (or minimal) duplication in data collection requirements for staff/partners, i.e. they are not required to report the same activityion more than one tool',
            'All sub grantee use a standard reporting template',
            'The number of data collection tools is sufficient for program needs and not excessive (all data collected are reported)',
            'There is a data management guideline that describes all data-verification, aggregation, analysis and manipulation steps performed at each reporting level',
            'The project has one or more electronic database which is up to date (last month data is available)',
            'There is a written description of  the project database -what is stored, who maintains/administers it, procedure for back-up etc.',
            'There is a description of the filing system for paper-based data collection and/or reporting (e.g. if supervision visits are filed in physical cabinets and not uploaded in an electronic data capture system or database)',
            'Historical data are properly stored, up to date and readily available (check 12-24 month data, depending on the project year)',
            'Project data (service statistics, training, follow-up, advocacy, sensitization, etc) are disaggregated by sex, age and other criteria (income, location, etc)',
            # 'If beneficiary-level personal information is collected then IDs are used to protect the confidentiality of clients, and access is restricted to this information',
            'Safeguards (such as passwords and ascribing different data management roles to staff) are in place to prevent unauthorized changes to data',
            'There is management support for following up any persistent data gaps with partners', ]
        model_name = DataCollectionReportingManagement
    else:
        description_list = [
            'There is an up to date M&E plan/PMP',
            'The M&E plan has a logic model/ results framework and/or Theory of Change linking project/ program goal, outcomes and outputs',
            'The M&E plan or other project design document has an organogram describing the organization of the M&E unit in relation to the overall project team',
            'The M&E plan includes indicators for measuring input, outputs, outcomes and where relevant, impact indicators, and the indicators are linked to the project objectives',
            'All indicators being tracked have documented operational definitions (including data disaggregation by age, sex, etc) in the indicator reference sheets',
            'There is an up to date Performance Indicator Tracking Table that is complete (include a list of indicators, baseline, annual and cummulative targets, and data sources)',
            'There is an up-to-date M&E work plan that details the implementation timeline for M&E activities and indicates persons responsible for each activity',
            'There is a detailed data flow diagram from Service Delivery Sites (facilities) to Intermediate Aggregation Levels (e.g. project district or regional offices); and from Intermediate Aggregation Levels (if any) to the national office (could be part of the M&E plan)',
            'There is a written description or guidance of how project activities (such as service delivery, training and follow-up, etc) are documented in source documents (e.g registers, supervision reports, etc)',
            'There is a written guideline to all reporting entities (e.g., regions, districts, facilities) on reporting requirements and deadlines',
            'There are guidelines and schedules for routine supervisory site visits',
            'Sub grantee have a copy of standard guidelines describing reporting requirements (what to report on, due dates, data sources, report recipients, etc.)']
        model_name = Documentation
    return report_type, model_name, description_list


@login_required(login_url='login')
def show_wash_dqa(request, report_type):
    if not request.user.first_name:
        return redirect("profile")
    # Get the query parameters from the URL
    quarter_form_initial = request.GET.get('quarter_form')
    year_form_initial = request.GET.get('year_form')
    ward_form_initial = request.GET.get('ward_form')

    # Parse the string values into dictionary objects
    quarter_form_initial = ast.literal_eval(quarter_form_initial) if quarter_form_initial else {}
    year_form_initial = ast.literal_eval(year_form_initial) if year_form_initial else {}
    ward_form_initial = ast.literal_eval(ward_form_initial) if ward_form_initial else {}

    quarter_form = QuarterSelectionForm(request.POST or None, initial=quarter_form_initial)
    year_form = YearSelectionForm(request.POST or None, initial=year_form_initial)
    ward_form = WardSelectionForm(request.POST or None, initial=ward_form_initial)

    date_form = DateSelectionForm(request.POST or None)
    system_assessments = None
    average_dictionary = None
    selected_ward = None
    expected_counts_dictionary = None
    if report_type not in ["data-quality-assessment", "data-quality", "data-collection", "documentation"]:
        report_type = "documentation"
    report_type, model_name, description_list = get_assessment_list_model_name(report_type)

    form_is_valid = False

    if quarter_form.is_valid() and year_form.is_valid() and ward_form.is_valid():
        form_is_valid = True
        selected_quarter = quarter_form.cleaned_data['quarter']
        selected_ward = ward_form.cleaned_data['name']
        selected_year = year_form.cleaned_data['year']

        year_suffix = selected_year[-2:]
        quarter_year = f"{selected_quarter}-{year_suffix}"
        # retrieves a queryset of SystemAssessment objects that have the specified quarter_year and ward_name.
        system_assessments = model_name.objects.filter(
            quarter_year__quarter_year=quarter_year,
            ward_name=selected_ward
        ).order_by(
            Case(
                *[When(description=d, then=pos) for pos, d in enumerate(description_list)],
                output_field=IntegerField()
            )
        )
        if system_assessments:
            average_dictionary = get_assessment_average(system_assessments, report_type, description_list)

        if not system_assessments:
            messages.error(request, f"Data quality assessment not found for {selected_ward} ({quarter_year})")

    if quarter_form_initial and not form_is_valid:
        selected_ward = ward_form_initial["name"]
        # retrieves a queryset of SystemAssessment objects that have the specified quarter_year and ward_name.
        system_assessments = model_name.objects.filter(
            quarter_year__quarter_year=quarter_form_initial['quarter'],
            ward_name=Ward.objects.get(name=selected_ward)
        ).order_by(
            Case(
                *[When(description=d, then=pos) for pos, d in enumerate(description_list)],
                output_field=IntegerField()
            )
        )
        if system_assessments:
            average_dictionary = get_assessment_average(system_assessments, report_type, description_list)

    context = {
        "quarter_form": quarter_form, "report_type": report_type, "year_form": year_form,
        "selected_ward": selected_ward, "ward_form": ward_form, "date_form": date_form,
        'system_assessments': system_assessments, "average_dictionary": average_dictionary,
        "expected_counts_dictionary": expected_counts_dictionary,
    }
    return render(request, 'wash_dqa/show_data_quality_assessment.html', context)


@login_required(login_url='login')
def update_wash_dqa(request, report_type, pk):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if report_type == "data-quality-assessment":
        item = DataQualityAssessment.objects.get(id=pk)
        model_form = DataQualityAssessmentForm
    elif report_type == "data-collection":
        item = DataCollectionReportingManagement.objects.get(id=pk)
        model_form = DataCollectionForm
    elif report_type == "data-quality":
        item = DataQualitySystems.objects.get(id=pk)
        model_form = DataQualityForm
    else:
        item = Documentation.objects.get(id=pk)
        model_form = DocumentationForm

    if request.method == "POST":
        form = model_form(request.POST, instance=item)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.auditor_note = form.cleaned_data['auditor_note']
            instance.dqa_date = item.dqa_date
            instance.created_by = request.user
            if report_type == "data-quality-assessment":
                # Check if all forms in formset are filled
                fields_to_check = ['auditor_note', 'number_trained', 'number_access_basic_water',
                                   'number_access_safe_water',
                                   'number_community_open_defecation', 'number_access_basic_sanitation',
                                   'number_access_safe_sanitation',
                                   'number_access_basic_sanitation_institutions']

                for field_name in fields_to_check:
                    if not form.cleaned_data.get(field_name):
                        form.add_error(field_name, "This field is required.")

            else:
                if not form.cleaned_data.get('dropdown_option'):
                    form.add_error('dropdown_option', "This field is required.")
                if form.cleaned_data.get('dropdown_option',
                                         '') not in ("Fully meets all requirements", "") and not form.cleaned_data.get(
                    'auditor_note', ''):
                    messages.warning(request,
                                     "Please provide a note in the 'Rating rationale' field before saving. This field is "
                                     "required because the item in the detailed checklist does not meet all "
                                     "requirements.")
                    form.add_error('auditor_note',
                                   "This field is required.")
            if form.errors:
                context = {
                    "form": form,
                    "title": "update",
                    "item": item,
                }
                return render(request, 'wash_dqa/update_system_assessment.html', context)

            if report_type != "data-quality-assessment":
                if instance.dropdown_option == 'Fully meets all requirements':
                    instance.calculations = 5
                elif instance.dropdown_option == 'Almost meets all requirements':
                    instance.calculations = 4
                elif instance.dropdown_option == 'Partially meets all requirements':
                    instance.calculations = 3
                elif instance.dropdown_option == 'Approaches basic requirements':
                    instance.calculations = 2
                elif instance.dropdown_option == 'Does not meet requirements':
                    instance.calculations = 1
                elif instance.dropdown_option == 'N/A':
                    instance.calculations = 0
            # Get or create the Facility instance
            instance.ward_name = item.ward_name
            # Get the Period instance
            instance.quarter_year = item.quarter_year
            instance.save()
            # Set the initial values for the forms
            quarter_form_initial = {'quarter': item.quarter_year.quarter_year}
            year_form_initial = {'year': item.quarter_year.year}
            ward_form_initial = {"name": item.ward_name.name}
            # print(f"WARD NAME:::::::::::::::::::::::::::::::::::::{ward_form_initial}")

            messages.success(request, "Record successfully updated!")
            # # Redirect to the system assessment table view with the initial values for the forms
            url = reverse('show_wash_dqa', kwargs={'report_type': report_type})
            url = f'{url}?quarter_form={quarter_form_initial}&year_form={year_form_initial}&ward_form={ward_form_initial}'
            return redirect(url)
    else:
        form = model_form(instance=item)
    context = {
        "form": form, "report_type": report_type,
        "title": "update", "item": item,
    }
    return render(request, 'wash_dqa/update_system_assessment.html', context)


@login_required(login_url='login')
def add_data_concordance(request):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    # Get the query parameters from the URL
    quarter_form_initial = request.GET.get('quarter_form')
    year_form_initial = request.GET.get('year_form')
    ward_form_initial = request.GET.get('ward_form')

    # Parse the string values into dictionary objects
    quarter_form_initial = ast.literal_eval(quarter_form_initial) if quarter_form_initial else {}
    year_form_initial = ast.literal_eval(year_form_initial) if year_form_initial else {}
    ward_form_initial = ast.literal_eval(ward_form_initial) if ward_form_initial else {}

    quarter_form = QuarterSelectionForm(request.POST or None, initial=quarter_form_initial)
    year_form = YearSelectionForm(request.POST or None, initial=year_form_initial)

    forms = DataConcordanceForm()
    selected_year = "2021"
    year_suffix = selected_year[-2:]
    facility_obj = None
    hide_submit_button = False

    if quarter_form.is_valid() and year_form.is_valid():
        hide_submit_button = True
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
        hide_submit_button = True
        selected_quarter = quarter_form_initial['quarter']
        request.session['selected_quarter'] = selected_quarter

        selected_year = year_form_initial['year']
        request.session['selected_year'] = selected_year

        selected_facility = ward_form_initial['name']
        facility_obj = Ward.objects.filter(name=selected_facility).first()

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

    # Dynamically disable form fields based on the hide_submit_button flag
    quarter_form.fields['quarter'].widget.attrs['disabled'] = hide_submit_button
    year_form.fields['year'].widget.attrs['disabled'] = hide_submit_button
    # Check if the request method is POST and the submit_data button was pressed
    if 'submit_data' in request.POST:
        # Create an instance of the DataConcordanceForm with the submitted data
        form = DataConcordanceForm(request.POST)

        # Check if the form data is valid
        if form.is_valid():
            # Get the selected indicator and facility name from the form data
            selected_indicator = form.cleaned_data['indicator']
            selected_facility = form.cleaned_data['ward_name']

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
                    # Redirect the user to the show_data_verification view
                    # return redirect("show_data_verification")
                    data_verification = DataConcordance.objects.select_related('quarter_year').filter(
                        quarter_year__quarter=request.session['selected_quarter'],
                        quarter_year__year=request.session['selected_year'],
                        ward_name=selected_facility,
                    )

                    indicator_choices = sorted(
                        [choice[0] for choice in DataConcordance.INDICATOR_CHOICES if choice[0] != ''])

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
                    ward_form_initial = {"name": selected_facility.name}

                    messages.success(request, "Record successfully saved!")
                    # Redirect to the system assessment table view with the initial values for the forms
                    url = reverse('add_data_concordance')
                    url = f'{url}?quarter_form={quarter_form_initial}&year_form={year_form_initial}&ward_form={ward_form_initial}'
                    return redirect(url)

            # Handle the IntegrityError exception
            except IntegrityError:
                # Notify the user that the data already exists
                messages.error(request, f'Data for {selected_facility}, {request.session["selected_quarter"]}, '
                                        f'{selected_indicator} '
                                        f'already exists!')
        # If the form data is not valid
        else:
            hide_submit_button = True
            # Add custom error message for failed validation
            messages.error(request, "Invalid Form: Please check the form fields.")
            # Create a new instance of the DataConcordanceForm with the invalid data
            form = DataConcordanceForm(request.POST)
            forms = DataConcordanceForm(initial={'ward_name': facility_obj})

            quarter_form = QuarterSelectionForm(initial={'quarter': request.session['selected_quarter']})

            # Create the form instance and set the initial value
            year_form = YearSelectionForm(initial={'year': request.session['selected_year']})
            # print(f"year_form:{year_form}:::::::::::::::::::::::::")
    # If the request method is not POST or the submit_data button was not pressed
    else:
        # Create an empty instance of the DataConcordanceForm
        form = DataConcordanceForm()
        forms = DataConcordanceForm(initial={'ward_name': facility_obj})
    # Dynamically disable form fields based on the hide_submit_button flag
    quarter_form.fields['quarter'].widget.attrs['disabled'] = hide_submit_button
    year_form.fields['year'].widget.attrs['disabled'] = hide_submit_button

    # convert a form into a list to allow slicing
    form_ = form
    form = list(form)
    # Create the context for the template
    context = {
        "form": form, "form_": form_, "hide_submit_button": hide_submit_button,
        "forms": forms,
        "quarters": quarters,
        "quarter_form": quarter_form,
        "year_form": year_form,
        "year_suffix": year_suffix
    }

    # Render the template with the context
    return render(request, 'wash_dqa/add_data_verification.html', context)


@login_required(login_url='login')
def show_data_concordance(request):
    if not request.user.first_name:
        return redirect("profile")

    # Get the query parameters from the URL
    quarter_form_initial = request.GET.get('quarter_form')
    year_form_initial = request.GET.get('year_form')
    ward_form_initial = request.GET.get('ward_form')

    # Parse the string values into dictionary objects
    quarter_form_initial = ast.literal_eval(quarter_form_initial) if quarter_form_initial else {}
    year_form_initial = ast.literal_eval(year_form_initial) if year_form_initial else {}
    ward_form_initial = ast.literal_eval(ward_form_initial) if ward_form_initial else {}

    form = QuarterSelectionForm(request.POST or None, initial=quarter_form_initial)
    year_form = YearSelectionForm(request.POST or None, initial=year_form_initial)
    ward_form = WardSelectionForm(request.POST or None, initial=ward_form_initial)

    selected_quarter = "Qtr1"
    selected_facility = None
    quarters = {}
    request.session['selected_year_'] = ""

    if form.is_valid() and year_form.is_valid() and ward_form.is_valid():
        selected_quarter = form.cleaned_data['quarter']
        selected_year = year_form.cleaned_data['year']
        request.session['selected_year_'] = selected_year
        selected_facility = ward_form.cleaned_data['name']
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
    # else:
    #     quarters = {}
    elif quarter_form_initial:
        selected_quarter = quarter_form_initial['quarter']
        selected_facility = ward_form_initial['name']

    try:
        selected_year = request.session['selected_year_']
        year_suffix = selected_year[-2:]
        quarter_year = f"{selected_quarter}-{year_suffix}"
        data_verification = DataConcordance.objects.filter(quarter_year__quarter=selected_quarter,
                                                           quarter_year__year=selected_year,
                                                           ward_name=selected_facility,
                                                           )
    except ValidationError:
        selected_year = year_form_initial['year']
        # year_suffix = selected_year[-2:]
        selected_facility = Ward.objects.get(name=selected_facility)
        quarter_year = selected_quarter
        data_verification = DataConcordance.objects.filter(quarter_year__quarter_year=selected_quarter,
                                                           ward_name=selected_facility,
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
    # Get the Indicator choices in the order specified in the list
    indicator_choices = [choice[0] for choice in DataConcordance.INDICATOR_CHOICES if choice[0] != '']
    # available_indicators = [i.indicator for i in data_verification]
    #
    # prevention = ['PrEP_New', 'Starting_TPT', 'GBV_Sexual violence', 'GBV_Emotional and /Physical Violence',
    #               'Cervical Cancer Screening (Women on ART)']
    # hts = ['Total tested ', 'Number tested Positive aged <15 years', 'Number tested Positive aged 15+ years',
    #        'Number tested Positive _Total']
    # pmtct = ['Known Positive at 1st ANC', 'Positive Results_ANC', 'On HAART at 1st ANC', 'Start HAART ANC',
    #          'Infant ARV Prophyl_ANC', 'Positive Results_L&D', 'Start HAART_L&D', 'Infant ARV Prophyl_L&D',
    #          'Positive Results_PNC<=6 weeks', 'Start HAART_PNC<= 6 weeks', 'Infant ARV Prophyl_PNC<= 6 weeks',
    #          'Total Positive (PMTCT)', 'Maternal HAART Total ', 'Total Infant prophylaxis']
    # care_rx = ['Under 15yrs Starting on ART', 'Above 15yrs Starting on ART ',
    #            'Number of adults and children starting ART', 'New & Relapse TB_Cases', 'Currently on ART <15Years',
    #            'Currently on ART 15+ years', 'Number of adults and children Currently on ART', 'TB_PREV_N', 'TX_ML',
    #            'RTT']

    # program_accessed = []
    # for indy in available_indicators:
    #     if indy in prevention:
    #         if "Prevention" not in program_accessed:
    #             program_accessed.append("Prevention")
    #     elif indy in hts:
    #         if "HTS" not in program_accessed:
    #             program_accessed.append("HTS")
    #     elif indy in pmtct:
    #         if "PMTCT" not in program_accessed:
    #             program_accessed.append("PMTCT")
    #     elif indy in care_rx:
    #         if "CARE & RX" not in program_accessed:
    #             program_accessed.append("CARE & RX")
    # Sort the data_verification objects based on the order of the indicator choices
    sorted_data_verification = sorted(data_verification, key=lambda x: indicator_choices.index(x.indicator))
    if data_verification:
        # disable_update_buttons(request, data_verification)
        remaining_indicators = [choice for choice in indicator_choices if
                                choice not in [obj.indicator for obj in sorted_data_verification]]
        # print(f"REANIING INFCATORS:::::::::::::::::::::::::::::{remaining_indicators}:::::::")
        if data_verification.count() < 7:
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
                           f"No data verification found for '{selected_facility} ward' {selected_quarter}-FY{year_suffix}.")

    # try:
    #     fyj_performance = FyjPerformance.objects.filter(ward_code=selected_facility.ward_code,
    #                                                     quarter_year=quarter_year
    #                                                     )
    #     if not fyj_performance:
    #         messages.info(request, f"No DATIM data for {selected_facility} {quarter_year}!")
    # except:
    #     fyj_performance = None
    try:
        # print("VALUES IN TRY BLOCK::::::::::::::::::::::::::::::::")
        # print(f"selected_facility.ward_code:::::::::::{selected_facility.ward_code}")
        # # print(f"selected_facility.ward_code:::::::::::{selected_facility.ward_code}")
        # print(f"quarter_year:::::::::::{quarter_year}")
        # ensure queryset is ordered chronologically by month
        khis_performance = JphesPerformance.objects.filter(ward_code=selected_facility.ward_code,
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
        # print("QUESRY SET:::::::::::::::::::::::::::::::::::")
        # print(khis_performance)
        if khis_performance.exists():
            total = khis_performance.aggregate(
                number_trained_total=Sum('number_trained'),
                number_access_basic_water_total=Sum('number_access_basic_water'),
                number_access_safe_water_total=Sum('number_access_safe_water'),
                number_community_open_defecation_total=Sum('number_community_open_defecation'),
                number_access_basic_sanitation_total=Sum('number_access_basic_sanitation'),
                number_access_safe_sanitation_total=Sum('number_access_safe_sanitation'),
                number_access_basic_sanitation_institutions_total=Sum('number_access_basic_sanitation_institutions'),

            )
        else:
            total = {
                'number_trained_total': 0,
                'number_access_basic_water_total': 0,
                'number_access_safe_water_total': 0,
                'number_community_open_defecation_total': 0,
                'number_access_basic_sanitation_total': 0,
                'number_access_safe_sanitation_total': 0,
                'number_access_basic_sanitation_institutions_total': 0,
            }
            messages.info(request, f"No JPHES data for {selected_facility} {quarter_year}!")
    except:
        khis_performance = None
        total = {
            'number_trained_total': 0,
            'number_access_basic_water_total': 0,
            'number_access_safe_water_total': 0,
            'number_community_open_defecation_total': 0,
            'number_access_basic_sanitation_total': 0,
            'number_access_safe_sanitation_total': 0,
            'number_access_basic_sanitation_institutions_total': 0,
        }
    # print(f"TOTAL:::::::::::::::::{total}:::::::::::::::::::::::::::::::::::::::::")
    context = {
        'form': form,
        "year_form": year_form,
        "ward_form": ward_form,
        "quarters": quarters,
        "selected_year": year_suffix,
        'data_verification': sorted_data_verification,
        # "program_accessed": program_accessed,
        # "fyj_performance": fyj_performance,
        "khis_performance": khis_performance,
        "total": total,
    }
    return render(request, 'wash_dqa/show data verification.html', context)


@login_required(login_url='login')
def update_data_concordance(request, pk):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    quarters = None
    item = DataConcordance.objects.get(id=pk)
    if request.method == "POST":
        form = DataConcordanceFormUpdate(request.POST, instance=item)
        if form.is_valid():
            form.save()
            # Set the initial values for the forms
            quarter_form_initial = {'quarter': item.quarter_year.quarter_year}
            year_form_initial = {'year': item.quarter_year.year}
            facility_form_initial = {"name": item.ward_name.name}

            messages.success(request, "Record successfully updated!")
            # Redirect to the system assessment table view with the initial values for the forms
            url = reverse('show_data_concordance')
            url = f'{url}?quarter_form={quarter_form_initial}&year_form={year_form_initial}&ward_form={facility_form_initial}'
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
        form = DataConcordanceFormUpdate(instance=item)
    context = {
        "form": form,
        "title": "Update DQA data",
        "quarters": quarters,
    }
    return render(request, 'wash_dqa/update_data_verification.html', context)


def bar_chart(df, x_axis, y_axis, title=None):
    fig = px.bar(df, x=x_axis, y=y_axis, text=y_axis, title=title, height=300,
                 color=x_axis,
                 category_orders={
                     x_axis: ['Source', 'Monthly Report', 'JPHES']},
                 color_discrete_map={'Source': '#5B9BD5',
                                     'MOH 731': '#ED7D31',
                                     # 'KHIS': '#A5A5A5',
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
        ,
        font=dict(
            family="Courier New, monospace",
            size=15,
            color="RebeccaPurple"
        )
    )

    fig.update_layout(showlegend=False)
    return plot(fig, include_plotlyjs=False, output_type="div")


def make_wash_performance_df(request, dqa, khis_perf, quarter_year, selected_facility=None):
    if dqa:
        if selected_facility:
            dqa_df = [
                {'indicator': x.indicator,
                 'ward': x.ward_name.name,
                 'ward_code': x.ward_name.ward_code,
                 'Source': x.total_source,
                 "Monthly Report": x.total_monthly_report,
                 "last month source": x.field_3,
                 "last month report": x.field_7,
                 "quarter_year": x.quarter_year.quarter_year,
                 } for x in dqa
            ]
        else:
            dqa_df = [
                {'indicator': x.indicator,
                 'ward': x.ward_name.name,
                 'ward_code': x.ward_name.ward_code,
                 'Source': x.total_source,
                 "Monthly Report": x.total_monthly_report,
                 "last month source": x.field_3,
                 "last month report": x.field_7,
                 "quarter_year": x.quarter_year.quarter_year,
                 } for x in dqa
            ]
        # create a dataframe from this list of dictionaries.
        dqa_df = pd.DataFrame(dqa_df)
        if dqa_df.empty:
            messages.info(request, f"A few DQA indicators for {selected_facility} have been capture but not "
                                   f"enough for data visualization")
    else:
        if selected_facility:
            dqa_df = pd.DataFrame(columns=['indicator', 'ward', 'ward_code', 'Source', 'Monthly Report',
                                           'quarter_year', 'last month'])
            messages.info(request, f"No Data Verification data for {selected_facility} {quarter_year}")
        else:
            dqa_df = pd.DataFrame(columns=['indicator', 'Source', 'Monthly Report',
                                           'quarter_year', 'last month'])
            messages.info(request, f"No Data Verification data for {quarter_year}")

    if khis_perf:
        khis_perf_df = pd.DataFrame(list(khis_perf))
        # if selected_facility:
        indicators_to_use_perf = ['ward_code', 'quarter_year', 'month', 'number_trained',
                                  'number_access_basic_water', 'number_access_safe_water',
                                  'number_community_open_defecation', 'number_access_basic_sanitation',
                                  'number_access_safe_sanitation',
                                  'number_access_basic_sanitation_institutions', ]
        # else:
        #     indicators_to_use_perf = ['ward_code','quarter_year', 'month', 'number_trained',
        #                               'number_access_basic_water', 'number_access_safe_water',
        #                               'number_community_open_defecation', 'number_access_basic_sanitation',
        #                               'number_access_safe_sanitation',
        #                               'number_access_basic_sanitation_institutions', ]
        khis_perf_df = khis_perf_df[indicators_to_use_perf]
        # if selected_facility:
        khis_perf_df = pd.melt(khis_perf_df, id_vars=['ward_code', 'quarter_year', 'month'],
                               value_vars=list(khis_perf_df.columns[2:]),
                               var_name='indicator', value_name="JPHES")
        khis_perf_df = khis_perf_df.groupby(['indicator', 'quarter_year', 'ward_code']).sum(
            numeric_only=True).reset_index()
        # else:
        #     khis_perf_df = pd.melt(khis_perf_df, id_vars=['ward_code', 'quarter_year', 'month'],
        #                            value_vars=list(khis_perf_df.columns[2:]),
        #                            var_name='indicator', value_name="JPHES")
        #     khis_perf_df = khis_perf_df.groupby(['indicator', 'quarter_year','ward_code',]).sum(
        #         numeric_only=True).reset_index()
    else:
        # if selected_facility:
        khis_perf_df = pd.DataFrame(columns=['indicator', 'ward', 'ward_code', 'KHIS',
                                             'quarter_year'])
        # else:
        #     khis_perf_df = pd.DataFrame(columns=['indicator', 'ward','ward_code', 'KHIS',
        #                                          'quarter_year'])

    khis_perf_df['indicator'] = khis_perf_df['indicator'].replace(
        'HL.8.2-1: Number of communities certified as open defecation free (ODF) as a result of USG assistance',
        'Open defecation free')
    khis_perf_df['indicator'] = khis_perf_df['indicator'].replace('number_access_basic_water',
                                                                  'HL.8.1-1: Number of people gaining access to basic drinking water services as a result of USG assistance')
    khis_perf_df['indicator'] = khis_perf_df['indicator'].replace('number_access_safe_water',
                                                                  'HL.8.1-2: Number of people gaining access to a safely managed drinking water service')

    khis_perf_df['indicator'] = khis_perf_df['indicator'].replace('number_access_basic_sanitation',
                                                                  'HL.8.2-2: Number of people gaining access to a basic sanitation service as a result of USG assistance')
    khis_perf_df['indicator'] = khis_perf_df['indicator'].replace(
        'HL.8.2-3: Number of people gaining access to safely managed sanitation services as a result of USG assistance.')
    khis_perf_df['indicator'] = khis_perf_df['indicator'].replace('number_access_safe_sanitation',
                                                                  'HL.8.2-4: Number of basic sanitation facilities provided in institutional settings as a result of USG assistance')
    khis_perf_df['indicator'] = khis_perf_df['indicator'].replace('number_access_basic_sanitation_institutions',
                                                                  'HL.CUST MCH 12.0: Number of individuals trained to implement improved sanitation methods')
    # print("khis_perf_df::::::::::::dqa_df:::::::::::::::::::")
    # khis_perf_df.to_csv("khis_perf_df.csv", index=False)
    # dqa_df.to_csv("dqa_df.csv", index=False)
    if selected_facility:
        merged_df = khis_perf_df.merge(dqa_df, on=['ward_code', 'quarter_year', 'indicator'], how='right').fillna(0)
        # print(merged_df)
        try:
            merged_df = merged_df[
                ['ward_code', 'ward', 'indicator', 'quarter_year', 'Source', 'Monthly Report', 'JPHES']]
        except KeyError:
            messages.info(request, f"No JPHES data for {selected_facility} {quarter_year}!")
            return redirect(request.path_info)

        merged_df = pd.melt(merged_df, id_vars=['ward_code', 'indicator', 'quarter_year'],
                            value_vars=list(merged_df.columns[3:]),
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
    else:
        grouped = pd.DataFrame()
        merged_df = pd.DataFrame()
    return grouped, merged_df, khis_perf_df, dqa_df


def get_model_query_set(request, quarter_year=None, selected_facility=None):
    dfs = []
    missing_reports = []
    available_ward_names = set()
    report_types = ["data-quality-assessment", "data-quality", "data-collection", "documentation"]

    # Create a dictionary to store the wards for each report type
    report_wards_mapping = {report_type: set() for report_type in report_types}
    for report_type in report_types:
        report_type, model_name, description_list = get_assessment_list_model_name(report_type)
        # retrieves a queryset of SystemAssessment objects that have the specified quarter_year and ward_name.
        if selected_facility is None:
            system_assessments = model_name.objects.filter(
                quarter_year__quarter_year=quarter_year
            )
        else:
            system_assessments = model_name.objects.filter(
                quarter_year__quarter_year=quarter_year,
                ward_name=selected_facility
            )
        for assessment in system_assessments:
            available_ward_names.add(assessment.ward_name.name)
            # Add the ward to the dictionary for the current report type
            report_wards_mapping[report_type].add(assessment.ward_name.name)
        if system_assessments and report_type != "data-quality-assessment":
            system_assessments_qs = [
                {'wards': x.ward_name.name,
                 'ward_code': x.ward_name.ward_code,
                 'description': x.description,
                 "auditor's note": x.auditor_note,
                 'calculations': x.calculations
                 } for x in system_assessments
            ]
            system_assessments_df = pd.DataFrame(system_assessments_qs)
            system_assessments_df['model_name'] = f"{report_type}"
            dfs.append(system_assessments_df)
        elif system_assessments and report_type == "data-quality-assessment":
            system_assessments_qs = [
                {'wards': x.ward_name.name,
                 'ward_code': x.ward_name.ward_code,
                 'description': x.description,
                 "auditor's note": x.auditor_note,
                 "number_trained_numeric": x.number_trained_numeric,
                 "number_access_basic_water_numeric": x.number_access_basic_water_numeric,
                 "number_access_safe_water_numeric": x.number_access_safe_water_numeric,
                 "number_community_open_defecation_numeric": x.number_community_open_defecation_numeric,
                 "number_access_basic_sanitation_numeric": x.number_access_basic_sanitation_numeric,
                 "number_access_safe_sanitation_numeric": x.number_access_safe_sanitation_numeric,
                 "number_access_basic_sanitation_institutions_numeric": x.number_access_basic_sanitation_institutions_numeric,
                 # 'calculations': x.calculations
                 } for x in system_assessments
            ]
            system_assessments_df = pd.DataFrame(system_assessments_qs)
            system_assessments_df = pd.melt(system_assessments_df,
                                            id_vars=['wards', 'ward_code', 'description', "auditor's note"],
                                            value_name='calculations',
                                            )
            if "variable" in system_assessments_df.columns:
                del system_assessments_df['variable']
            system_assessments_df['model_name'] = f"{report_type}"
            dfs.append(system_assessments_df)
        else:
            missing_reports.append(report_type)
    # Prepare the message with missing reports and their ward names for each ward
    missing_reports_message = ", ".join([x.replace('-', ' ') for x in missing_reports])

    # Create a list to store messages for each ward
    messages_info = []

    # Create a dictionary to store the count of missing reports per ward
    ward_missing_count = {ward_name: 0 for ward_name in available_ward_names}

    for ward_name in available_ward_names:
        missing_for_ward = [report_type for report_type in report_types if
                            ward_name not in report_wards_mapping[report_type]]

        # Update the count of missing reports for this ward
        ward_missing_count[ward_name] = len(missing_for_ward)

    # Sort the wards by the number of missing reports in descending order
    sorted_wards = sorted(ward_missing_count.keys(), key=lambda k: ward_missing_count[k], reverse=True)

    for ward_name in sorted_wards:
        missing_for_ward = [report_type for report_type in report_types if
                            ward_name not in report_wards_mapping[report_type]]
        if missing_for_ward:
            missing_message = f"{ward_name} ward is missing ({len(missing_for_ward)}) {', '.join([x.replace('-', ' ') for x in missing_for_ward])}:"
            messages_info.append(missing_message)

    messages_info = "\n".join(messages_info)

    if messages_info:
        messages.info(
            request,
            f"Missing {quarter_year} WASH System Assessment data for {missing_reports_message}:\n\n{messages_info}"
        )

    if len(dfs)>0:
        df = pd.concat(dfs)
    else:
        df=pd.DataFrame()
    return df


def get_all_averages(request, quarter_year, selected_facility=None):
    assessment_names_list = []
    assessment_means_list = []

    for report_type in ["data-quality-assessment", "data-quality", "data-collection", "documentation"]:
        report_type, model_name, description_list = get_assessment_list_model_name(report_type)
        # retrieves a queryset of SystemAssessment objects that have the specified quarter_year and ward_name.
        if selected_facility is None:
            system_assessments = model_name.objects.filter(
                quarter_year__quarter_year=quarter_year
            )
        else:
            system_assessments = model_name.objects.filter(
                quarter_year__quarter_year=quarter_year,
                ward_name=selected_facility
            )
        # print("AVERAGE:::::::::::QUERYSET:::{}:::::::::::::::::")
        # print(system_assessments)
        if system_assessments:
            average_dictionary = get_assessment_average(system_assessments, report_type, description_list)
        else:
            if report_type == "data-quality-assessment":
                average_dictionary = {"average_of_averages": 0}
            else:
                average_dictionary = 0
        assessment_names_list.append(report_type.replace("-", " ").title())
        assessment_means_list.append(average_dictionary)

    # if system_assessments:
    #     average_dictionary = get_assessment_average(system_assessments, report_type, description_list)
    # print("AVERAGE::::::::::::::{}:::::::::::::::::")
    # print(assessment_means_list)
    # Get the dictionary out of the list
    average_dict = assessment_means_list.pop(0)

    # Calculate the overall average of averages
    averages = average_dict['average_of_averages']
    try:
        overall_average = round(sum(averages.values()) / len(averages), 2)
    except AttributeError:
        overall_average = 0
        messages.info(request, f"Please update missing data first for a reliable summary.")
    # Insert back the overall average of the averages
    assessment_means_list.insert(0, overall_average)
    average_dictionary = {category: value for category, value in zip(assessment_names_list, assessment_means_list)}
    # print(f"assessment_names_list:::::::::::::::::::::::::::::::::::::{assessment_names_list}")
    # print(f"assessment_means_list:::::::::::::::::::::::::::::::::::::{assessment_means_list}")
    # print(f"average_dictionary:::::::::::::::::::::::::::::::::::::{average_dictionary}")
    #     average_dictionary, expected_counts_dictionary = calculate_averages(system_assessments, description_list)
    #     site_avg = round(average_dictionary, 2)
    site_avg = round(sum(assessment_means_list) / len(assessment_means_list), 2)
    return assessment_means_list, assessment_names_list, site_avg, average_dictionary


def wash_dqa_summary(request):
    if not request.user.first_name:
        return redirect("profile")
    form = QuarterSelectionForm(request.POST or None)
    year_form = YearSelectionForm(request.POST or None)
    facility_form = WardSelectionForm(request.POST or None)
    plot_div = None

    selected_quarter = "Qtr1"
    year_suffix = "21"
    selected_facility = None
    average_dictionary = None
    site_avg = None
    audit_team = None
    show_buttons = False

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
        }

        # Convert the dictionary to a JSON string
        selected_facility_json = json.dumps(selected_facility_dict)

        # Store the JSON string in the session
        request.session['selected_facility'] = selected_facility_json
        request.session['quarter_year'] = quarter_year

    dicts = {}
    dqa = None
    system_assessments = None

    if "submit_data" in request.POST:
        dqa = DataConcordance.objects.filter(ward_name__ward_code=selected_facility.ward_code,
                                             quarter_year__quarter_year=quarter_year)
        khis_perf = JphesPerformance.objects.filter(ward_code=selected_facility.ward_code,
                                                    quarter_year=quarter_year).values()
        # print(f"DQA:::::::::::{dqa}")
        # print(f"JPHES:::::::::::{khis_perf}")

        if dqa and khis_perf:
            grouped, merged_df, khis_perf_df, dqa_df = make_wash_performance_df(request, dqa, khis_perf, quarter_year,
                                                                                selected_facility)
            # print(f"GROUPED::::::::::::{grouped}:::::::::")
            # print(f"MERGED DF::::::::::::{merged_df.columns}:::::::::")
            # print(merged_df)
        else:
            messages.info(request, f"No Data Verification data for {selected_facility} {quarter_year}")
            merged_df = pd.DataFrame(columns=['ward_code', 'indicator', 'quarter_year', 'data sources',
                                              'performance'])
            grouped = pd.Series([])

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

        assessment_means_list, assessment_names_list, site_avg, average_dictionary = get_all_averages(request,
                                                                                                      quarter_year,
                                                                                                      selected_facility)
        data = [
            go.Scatterpolar(
                # r=[average_dictionary],
                # theta=['Documentation',],
                r=assessment_means_list,
                theta=assessment_names_list,
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
                'text': f"System Assessment Averages for {selected_facility.name} Ward ({quarter_year})",
                'y': 0.95,
                'x': 0.5,
                'xanchor': 'center',
                'yanchor': 'top'
            },
        )

        plot_div = opy.plot(fig, auto_open=False, output_type='div')

        # else:
        #     messages.info(request, f"No System assessment data for {selected_facility}")
        audit_team = WashAuditTeam.objects.filter(ward_name__id=selected_facility.id,
                                                  quarter_year__quarter_year=quarter_year)
        # print(f"audit team qs:::::::::::::::::::::::::::::::::::::::::::::::{audit_team}")
        if audit_team:
            disable_update_buttons(request, audit_team)
        if not audit_team:
            messages.info(request,
                          f"No audit team assigned for {selected_facility}  {quarter_year}. Please ensure that data"
                          f" verification and WASH assessment data has been entered before assigning an audit team. "
                          f"Once all data is verified, the 'Add audit team', 'Add workplan' and 'Download PDF' buttons "
                          f"will be available on this page.")

        ###########################################
        # Show or Hide Audit team/Download button
        ###########################################
        documentation = Documentation.objects.filter(ward_name__id=selected_facility.id,
                                                     quarter_year__quarter_year=quarter_year)
        data_quality_syst = DataQualitySystems.objects.filter(ward_name__id=selected_facility.id,
                                                              quarter_year__quarter_year=quarter_year)
        data_collect = DataCollectionReportingManagement.objects.filter(ward_name__id=selected_facility.id,
                                                                        quarter_year__quarter_year=quarter_year)
        data_quality_assessment = DataQualityAssessment.objects.filter(ward_name__id=selected_facility.id,
                                                                       quarter_year__quarter_year=quarter_year)
        data_conc = DataConcordance.objects.filter(ward_name__id=selected_facility.id,
                                                   quarter_year__quarter_year=quarter_year)

        if documentation and data_conc and data_quality_assessment and data_quality_syst and data_collect:
            show_buttons = True
        else:
            section_name = ["Data Quality Assessment", "Data Quality Systems",
                            "Data Collection, Reporting and Management", "Documentation",
                            "Data Verification"]
            section_qs = [data_quality_assessment, data_quality_syst, data_collect, documentation, data_conc, ]
            missing = []
            for name, section in zip(section_name, section_qs):
                if section.count() == 0:
                    missing.append(name)
            messages.info(request, f"{len(missing)} Missing so far: {missing}")

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
        "site_avg": site_avg, "show_buttons": show_buttons,
        "audit_team": audit_team,
        "system_assessments": system_assessments,
    }
    return render(request, 'wash_dqa/dqa_summary.html', context)


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
                post.ward_name = Ward.objects.get(id=pk)
                post.quarter_year = Period.objects.get(quarter_year=quarter_year)
                post.save()
                return HttpResponseRedirect(request.path_info)
            except ValidationError as e:
                error_msg = str(e)
                error_msg = error_msg[1:-1]  # remove the first and last characters (brackets)
                messages.error(request, error_msg)
    else:
        form = AuditTeamForm()
    audit_team = WashAuditTeam.objects.filter(ward_name__id=pk, quarter_year__quarter_year=quarter_year)
    disable_update_buttons(request, audit_team)
    context = {
        "form": form,
        "title": "audit team",
        "audit_team": audit_team,
        "quarter_year": quarter_year,
    }
    return render(request, 'wash_dqa/add_period.html', context)


@login_required(login_url='login')
def update_audit_team(request, pk):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    item = WashAuditTeam.objects.get(id=pk)
    if request.method == "POST":
        form = AuditTeamForm(request.POST, instance=item)
        if form.is_valid():
            audit_team = form.save(commit=False)
            audit_team.ward_name = item.ward_name
            audit_team.quarter_year = item.quarter_year
            audit_team.save()
            # return HttpResponseRedirect(request.session['page_from'])
            # Set the initial values for the forms
            quarter_form_initial = {'quarter': item.quarter_year.quarter_year}
            year_form_initial = {'year': item.quarter_year.year}
            facility_form_initial = {"name": item.ward_name.name}

            messages.success(request, "Record successfully updated!")
            # Redirect to the system assessment table view with the initial values for the forms
            url = reverse('show_wash_audit_team')
            url = f'{url}?quarter_form={quarter_form_initial}&year_form={year_form_initial}&ward_form={facility_form_initial}'
            return redirect(url)
    else:
        form = AuditTeamForm(instance=item)
    context = {
        "form": form,
        'title': 'update audit team',
        'facility': item.ward_name.name,
        'ward_code': item.ward_name.ward_code,
        'date_modified': item.date_modified,
    }
    return render(request, 'wash_dqa/add_period.html', context)


@login_required(login_url='login')
def show_audit_team(request):
    if not request.user.first_name:
        return redirect("profile")
    # Get the query parameters from the URL
    quarter_form_initial = request.GET.get('quarter_form')
    year_form_initial = request.GET.get('year_form')
    facility_form_initial = request.GET.get('ward_form')

    # Parse the string values into dictionary objects
    quarter_form_initial = ast.literal_eval(quarter_form_initial) if quarter_form_initial else {}
    year_form_initial = ast.literal_eval(year_form_initial) if year_form_initial else {}
    facility_form_initial = ast.literal_eval(facility_form_initial) if facility_form_initial else {}

    form = QuarterSelectionForm(request.POST or None, initial=quarter_form_initial)
    year_form = YearSelectionForm(request.POST or None, initial=year_form_initial)
    facility_form = WardSelectionForm(request.POST or None, initial=facility_form_initial)

    audit_team = None
    quarter_year = None

    if form.is_valid() and year_form.is_valid() and facility_form.is_valid():
        selected_quarter = form.cleaned_data['quarter']
        selected_year = year_form.cleaned_data['year']
        selected_facility = facility_form.cleaned_data['name']
        year_suffix = selected_year[-2:]
        quarter_year = f"{selected_quarter}-{year_suffix}"
        audit_team = WashAuditTeam.objects.filter(ward_name__id=selected_facility.id,
                                                  quarter_year__quarter_year=quarter_year)
        if audit_team:
            disable_update_buttons(request, audit_team)
        else:
            messages.error(request, f"No audit team data was found in the database for {selected_facility} "
                                    f"{selected_quarter}-FY{year_suffix}.")
    elif facility_form_initial:
        selected_quarter = quarter_form_initial['quarter']
        selected_facility = facility_form_initial['name']
        audit_team = WashAuditTeam.objects.filter(ward_name=Ward.objects.get(name=selected_facility),
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
    return render(request, 'wash_dqa/add_period.html', context)


@login_required(login_url='login')
def wash_dqa_work_plan_create(request, pk, quarter_year):
    if not request.user.first_name:
        return redirect("profile")
    facility = DataConcordance.objects.filter(ward_name_id=pk,
                                              quarter_year__quarter_year=quarter_year
                                              ).order_by('-date_modified').first()
    ########################################
    # Data Quality Assessment By Data Source
    ########################################
    # filter for numeric fields equal to 2
    filter_numeric_2 = Q(number_trained_numeric=2) & Q(number_access_basic_water_numeric=2) & \
                       Q(number_access_safe_water_numeric=2) & Q(number_community_open_defecation_numeric=2) & \
                       Q(number_access_basic_sanitation_numeric=2) & Q(number_access_safe_sanitation_numeric=2) & \
                       Q(number_access_basic_sanitation_institutions_numeric=2)

    # filter for numeric fields equal to 1
    filter_numeric_1 = Q(number_trained_numeric=1) & Q(number_access_basic_water_numeric=1) & \
                       Q(number_access_safe_water_numeric=1) & Q(number_community_open_defecation_numeric=1) & \
                       Q(number_access_basic_sanitation_numeric=1) & Q(number_access_safe_sanitation_numeric=1) & \
                       Q(number_access_basic_sanitation_institutions_numeric=1)
    data_assessment_qs = DataQualityAssessment.objects.filter(ward_name_id=pk,
                                                              quarter_year__quarter_year=quarter_year)
    data_assessment_partly = data_assessment_qs.filter(filter_numeric_2)
    data_assessment_no = data_assessment_qs.filter(filter_numeric_1)
    ########################################
    # Documentation
    ########################################
    documentation_qs = Documentation.objects.filter(ward_name_id=pk,
                                                    quarter_year__quarter_year=quarter_year)
    documentation_partly = documentation_qs.filter(Q(calculations=2))
    documentation_no = documentation_qs.filter(Q(calculations=1))
    ########################################
    # Data Quality Systems
    ########################################
    data_quality_qs = DataQualitySystems.objects.filter(ward_name_id=pk,
                                                        quarter_year__quarter_year=quarter_year)
    data_quality_partly = data_quality_qs.filter(Q(calculations=2))
    data_quality_no = data_quality_qs.filter(Q(calculations=1))
    ########################################
    # Data Collection, Reporting and Management
    ########################################
    data_collection_qs = DataCollectionReportingManagement.objects.filter(ward_name_id=pk,
                                                                          quarter_year__quarter_year=quarter_year)
    data_collection_partly = data_collection_qs.filter(Q(calculations=2))
    data_collection_no = data_collection_qs.filter(Q(calculations=1))
    ########################################
    # Calculate totals for areas of improvement
    ########################################
    system_assessment_partly_count = data_assessment_partly.count() + documentation_partly.count() + \
                                     data_quality_partly.count() + data_collection_partly.count()

    system_assessment_no_count = data_assessment_no.count() + documentation_no.count() + data_quality_no.count() \
                                 + data_collection_no.count()
    ########################################
    # Show or hide areas of improvement
    ########################################
    system_assessment_partly = False
    system_assessment_no = False
    if system_assessment_partly_count:
        system_assessment_partly = True
    if system_assessment_no_count:
        system_assessment_no = True

    today = timezone.now().date()

    if request.method == 'POST':
        form = WashDQAWorkPlanForm(request.POST, initial={"dqa_date": facility.date_created})
        if form.is_valid():
            dqa_work_plan = form.save(commit=False)
            dqa_work_plan.ward_name = facility.ward_name
            dqa_work_plan.quarter_year = facility.quarter_year
            dqa_work_plan.created_by = request.user
            dqa_work_plan.progress = (dqa_work_plan.due_complete_by - today).days
            dqa_work_plan.timeframe = (dqa_work_plan.due_complete_by - dqa_work_plan.dqa_date).days
            dqa_work_plan.save()
            return redirect('show_wash_dqa_work_plan')
    else:
        form = WashDQAWorkPlanForm(initial={"dqa_date": facility.date_created})

    context = {
        'form': form, 'title': 'Add WASH DQA Work Plan', 'facility': facility.ward_name.name,
        'ward_code': facility.ward_name.ward_code, 'date_modified': facility.date_created,
        'system_assessment_partly': system_assessment_partly, 'system_assessment_no': system_assessment_no,
        "system_assessment_partly_count": system_assessment_partly_count,
        "system_assessment_no_count": system_assessment_no_count, "data_assessment_partly": data_assessment_partly,
        "documentation_partly": documentation_partly, "data_quality_partly": data_quality_partly,
        "data_collection_partly": data_collection_partly, "data_assessment_no": data_assessment_no,
        "documentation_no": documentation_no, "data_quality_no": data_quality_no,
        "data_collection_no": data_collection_no
    }

    return render(request, 'wash_dqa/add_qi_manager.html', context)


@login_required(login_url='login')
def show_wash_dqa_work_plan(request):
    if not request.user.first_name:
        return redirect("profile")
    form = QuarterSelectionForm(request.POST or None)
    year_form = YearSelectionForm(request.POST or None)
    facility_form = WardSelectionForm(request.POST or None)
    selected_facility = None
    work_plan = None
    quarter_year = None
    today = datetime.now(timezone.utc).date()

    if form.is_valid() and year_form.is_valid() and facility_form.is_valid():
        selected_quarter = form.cleaned_data['quarter']
        selected_year = year_form.cleaned_data['year']
        selected_facility = facility_form.cleaned_data['name']
        year_suffix = selected_year[-2:]
        quarter_year = f"{selected_quarter}-{year_suffix}"

    if "submit_data" in request.POST:
        work_plan = WashDQAWorkPlan.objects.filter(ward_name_id=selected_facility.id,
                                                   quarter_year__quarter_year=quarter_year
                                                   )
        #####################################
        # DECREMENT REMAINING TIME DAILY    #
        #####################################
        for plan in work_plan:
            plan.progress = (plan.due_complete_by - today).days

        if not work_plan:
            messages.error(request, f"No work plan for {selected_facility} ({quarter_year}) found.")
    context = {
        "work_plan": work_plan,
        'form': form,
        "year_form": year_form,
        "facility_form": facility_form,
    }
    return render(request, 'wash_dqa/dqa_work_plan_list.html', context)


@login_required(login_url='login')
def update_wash_dqa_workplan(request, pk):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    item = WashDQAWorkPlan.objects.get(id=pk)
    today = timezone.now().date()
    if request.method == "POST":
        form = WashDQAWorkPlanForm(request.POST, instance=item)
        if form.is_valid():
            dqa_work_plan = form.save(commit=False)
            dqa_work_plan.ward_name = item.ward_name
            dqa_work_plan.quarter_year = item.quarter_year
            dqa_work_plan.created_by = request.user
            dqa_work_plan.progress = (dqa_work_plan.due_complete_by - today).days
            dqa_work_plan.timeframe = (dqa_work_plan.due_complete_by - dqa_work_plan.dqa_date).days
            dqa_work_plan.save()
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = WashDQAWorkPlanForm(instance=item)
    context = {
        "form": form,
        'title': 'Update WASH DQA Work Plan',
        'facility': item.ward_name.name,
        'ward_code': item.ward_name.ward_code,
        'date_modified': item.date_modified,
    }
    return render(request, 'wash_dqa/add_qi_manager.html', context)


def bar_chart_report(df, x_axis, y_axis, indy=None, quarter=None):
    image = None
    fig, ax = plt.subplots(figsize=(8, 5))

    sns.barplot(x=x_axis, y=y_axis, data=df, palette={
        'Source': '#5B9BD5',
        'Monthly Report': '#ED7D31',
        # 'KHIS': '#A5A5A5',
        'JPHES': '#FFC000',
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


def make_concordance_chart(grouped, merged_df, bar_chart_report):
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
    return dicts, charts


class GeneratePDF(View):
    def get(self, request):
        if request.user.is_authenticated and not request.user.first_name:
            return redirect("profile")
        # Retrieve the selected facility from the session and convert it back to a dictionary
        selected_facility_json = request.session.get('selected_facility')
        selected_facility_dict = json.loads(selected_facility_json)

        # Create a Facility object from the dictionary
        selected_facility = Ward.objects.get(id=selected_facility_dict['id'])

        quarter_year = request.session['quarter_year']
        dicts = {}
        dqa = None
        average_dictionary = None
        df = None

        name = None
        ward_code = None
        date = None
        site_avg = None
        charts = []
        avg_me = 0
        avg_data_mnx = 0
        avg_indicator = 0
        avg_data_collect = 0

        # if "submit_data" in request.POST:
        dqa = DataConcordance.objects.filter(ward_name__ward_code=selected_facility.ward_code,
                                             quarter_year__quarter_year=quarter_year)
        khis_perf = JphesPerformance.objects.filter(ward_code=selected_facility.ward_code,
                                                    quarter_year=quarter_year).values()
        # if dqa:
        #     grouped, merged_df = make_wash_performance_df(request, dqa, khis_perf, selected_facility, quarter_year)
        if dqa and khis_perf:
            grouped, merged_df, khis_perf_df, dqa_df = make_wash_performance_df(request, dqa, khis_perf, quarter_year,
                                                                                selected_facility)
            # print(f"GROUPED::::::::::::{grouped}:::::::::")
            # print(f"MERGED DF::::::::::::{merged_df.columns}:::::::::")
        else:
            messages.info(request, f"No Data Verification data for {selected_facility} {quarter_year}")
            merged_df = pd.DataFrame(columns=['ward_code', 'indicator', 'quarter_year', 'data sources',
                                              'performance'])
            grouped = pd.Series([])
        # Create an empty dictionary object to store the bar charts for each 'indicator' in 'grouped'
        dicts, charts = make_concordance_chart(grouped, merged_df, bar_chart_report)

        # retrieves a queryset of SystemAssessment objects that have the specified quarter_year and ward_name.
        assessment_means_list, assessment_names_list, site_avg, average_dictionary = get_all_averages(request,
                                                                                                      quarter_year,
                                                                                                      selected_facility)
        # print(f"GENERATE PDF:::::::::::::::::AVERAGE:::::::::::::{average_dictionary}:::::::::::::::")
        # {'Data Quality Assessment': 1.14, 'Data Quality': 4.85, 'Data Collection': 4.33, 'Documentation': 4.42}
        avg_me = average_dictionary['Documentation']
        avg_data_mnx = average_dictionary['Data Quality']
        avg_indicator = average_dictionary['Data Collection']
        avg_data_collect = average_dictionary['Data Quality Assessment']
        data = [
            {
                'category': 'Documentation',
                'value': avg_me
            },
            {
                'category': 'Data Quality',
                'value': avg_data_mnx
            },
            {
                'category': 'Data Collection, Reporting Management',
                'value': avg_indicator
            },
            {
                'category': 'Data Quality Assessment By Data Source',
                'value': avg_data_collect
            },
        ]
        df = pd.DataFrame(data)
        # Create a new PDF object using ReportLab
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'filename="wash dqa summary {selected_facility} {quarter_year}.pdf"'
        pdf = canvas.Canvas(response, pagesize=letter)

        # Write some content to the PDF
        for data in dqa:
            name = data.ward_name.name
            ward_code = data.ward_name.ward_code
            # Convert datetime object to the client's timezone
            client_timezone = timezone.get_current_timezone()
            date = data.date_modified.astimezone(client_timezone).strftime('%B %d, %Y, %I:%M %p')

        period = quarter_year

        # change page size
        pdf.translate(inch, inch)
        pdf.setFont("Courier-Bold", 18)
        # write the facility name in the top left corner of the page
        pdf.drawString(180, 650, "WASH DQA SUMMARY")
        y = 640
        pdf.line(x1=10, y1=y, x2=500, y2=y)
        # facility info
        pdf.setFont("Helvetica", 12)
        pdf.drawString(10, 620, f"Ward: {name}")
        pdf.drawString(10, 600, f"Ward Code: {ward_code}")
        pdf.drawString(10, 580, f"Date Of Audit: {date}")
        pdf.drawString(10, 560, f"Review Period: {period}")
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(310, 625, f"COLOR CODE")
        pdf.drawString(420, 625, f"RANGE")
        # rectangles
        # Constants
        x_start = 300  # X-coordinate of the top-left corner of the bigger rectangle
        y_start = 550  # Y-coordinate of the top-left corner of the bigger rectangle
        width_big = 200  # Width of the bigger rectangle
        height_big = 70  # Height of the bigger rectangle
        num_rows = 5  # Number of rows
        num_columns = 2  # Number of columns

        # Calculate the height of each smaller rectangle
        height_small = height_big / num_rows

        # Define colors for the first column in the desired order
        column1_colors = [colors.red, colors.yellow, colors.lightgreen, colors.green, colors.blue]
        # Color names for the labels
        color_names = ["Red", "Yellow", "Light Green", "Green", "Blue"]
        column2_labels = ["<1.5", ">= 1.5 and <2.5", ">= 2.5 and <3.5", ">= 3.5 and <4.5", ">= 4.5"]

        # Loop to create the smaller rectangles
        for row in range(num_rows):
            for col in range(num_columns):
                # Calculate the coordinates for each smaller rectangle
                x = x_start + (col * (width_big / num_columns))
                y = y_start + (row * height_small)

                # Determine the fill color based on the column and row
                if col == 0:
                    if row < len(column1_colors):
                        pdf.setFillColor(column1_colors[row])
                    else:
                        pdf.setFillColor(colors.white)  # No color for additional rows in the first column
                else:
                    pdf.setFillColor(colors.white)  # No color for the second column

                # Draw the smaller rectangle
                pdf.rect(x, y, width_big / num_columns, height_small, stroke=1, fill=1)
                # Add the color name label inside the first column
                if col == 0:
                    if row < len(color_names):
                        pdf.setFillColor(colors.black)  # Set text color to black
                        pdf.setFont("Helvetica", 10)  # Set font and size for text
                        pdf.drawString(x + 5, y + 5, color_names[row])  # Add the color
                # Add the color name label inside the first column
                if col == 1:
                    if row < len(column2_labels):
                        pdf.setFillColor(colors.black)  # Set text color to black
                        pdf.setFont("Helvetica", 10)  # Set font and size for text
                        pdf.drawString(x + 5, y + 5, column2_labels[row])  # Add the color

        pdf.drawString(180, 520, "SYSTEMS ASSESSMENT RESULTS")

        # rectangles
        # Define the number of rectangles and total width
        num_rectangles = 6
        total_width = 490  # Total width of the canvas

        # Calculate the width of each rectangle
        rectangle_width = total_width / num_rectangles

        # Define the x-coordinate
        x = 10

        # Loop to draw the rectangles
        for i in range(num_rectangles):
            pdf.rect(x, y=440, width=rectangle_width, height=70, stroke=1, fill=0)
            x += rectangle_width  # Move to the next position
        pdf.rect(x=10, y=440, width=490, height=20, stroke=1, fill=0)
        pdf.rect(x=10, y=440, width=490, height=50, stroke=1, fill=0)

        # Add the text labels
        pdf.setFillColor(colors.black)  # Set text color to black
        pdf.setFont("Helvetica", 7)  # Set font and size for text

        # Position the "SUMMARY TABLE" label
        pdf.drawString(12, 493, "SUMMARY TABLE")

        # Position the "I, II, III, IV" labels
        label_x = 90  # Initial x-coordinate for the labels
        labels = ["I", "II", "III", "IV"]

        for label in labels:
            pdf.drawString(label_x + 20, 493, label)
            label_x += rectangle_width  # Adjust the x-coordinate for the next label

        label_x = 90  # Initial x-coordinate for the labels
        labels = [str(avg_me), str(avg_data_mnx), str(avg_indicator), str(avg_data_collect), str(site_avg)]
        for count, label in enumerate(labels):
            if count == 4:
                pdf.setFont("Helvetica-Bold", 10)
                pdf.drawString(label_x + 30, 445, label)
                pdf.setFont("Helvetica", 7)
            else:
                pdf.setFont("Helvetica", 7)
                pdf.drawString(label_x + 20, 445, label)
            label_x += rectangle_width  # Adjust the x-coordinate for the next label

        label_x = 90  # Initial x-coordinate for the labels
        labels = ["Documentation", "Data Quality", "Data Collection,", "Data Quality", "Ward Average"]
        for count, label in enumerate(labels):
            if count == 4:
                pdf.setFont("Helvetica-Bold", 11)
                pdf.drawString(label_x + 5, 480, label)
                pdf.setFont("Helvetica", 7)
            else:
                pdf.setFont("Helvetica", 7)
                pdf.drawString(label_x + 20, 480, label)
            label_x += rectangle_width  # Adjust the x-coordinate for the next label
        label_x = 90  # Initial x-coordinate for the labels
        labels = ["", "Systems", "Reporting and", "Assessment"]
        for label in labels:
            pdf.drawString(label_x + 20, 472, label)
            label_x += rectangle_width  # Adjust the x-coordinate for the next label
        label_x = 90  # Initial x-coordinate for the labels
        labels = ["", "", "Management", ""]
        for label in labels:
            pdf.drawString(label_x + 20, 464, label)
            label_x += rectangle_width  # Adjust the x-coordinate for the next label

        pdf.setFont("Helvetica", 7)
        pdf.drawString(12, 480, "Assessment of Data")
        pdf.setFont("Helvetica", 7)

        pdf.drawString(12, 472, "Management and")
        pdf.drawString(12, 464, "Reporting Systems")
        pdf.drawString(12, 452, "Average ")
        pdf.drawString(12, 443, "(per functional area)")
        pdf.setFont("Helvetica-Bold", 12)

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

        audit_team = WashAuditTeam.objects.filter(ward_name__id=selected_facility.id,
                                                  quarter_year__quarter_year=quarter_year)

        # Create a list to hold the data for the table
        data = [['Name', 'Carder', 'Organization', 'Review Period']]
        # Loop through the audit_team queryset and append the required fields to the data list
        for audit in audit_team:
            data.append([audit.first_name, audit.carder, audit.organization, audit.quarter_year])

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
        work_plan = WashDQAWorkPlan.objects.filter(ward_name__id=selected_facility.id,
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
        pdf.save()
        return response


def rename_df_column(df, old_name, new_name):
    new_df = df.copy()
    new_df = new_df.rename(columns={old_name: new_name})
    return new_df


def delete_df_column(df, col_name):
    new_df = df.copy()
    if f"{col_name}" in new_df.columns:
        del new_df[col_name]
    return new_df




# def generate_missing_indicators_message(data_verification_data,model_name,interested_unit,quarter_year):
#     # Create a dictionary to track wards and the number of missing indicators
#     wards_missing_indicators = defaultdict(int)
#
#     # Iterate through unique wards
#     unique_wards = set(item[interested_unit] for item in data_verification_data)
#     for ward in unique_wards:
#         # Get the indicators for this ward
#         ward_indicators = set(
#             item['indicator'] for item in data_verification_data if item[interested_unit] == ward)
#
#         # Count the number of missing indicators for the ward
#         missing_indicators_count = sum(
#             1
#             for indicator_choice in model_name.INDICATOR_CHOICES[1:]
#             if indicator_choice[0] not in ward_indicators
#         )
#
#         # If the ward is missing any indicators, add it to the dictionary
#         if missing_indicators_count > 0:
#             wards_missing_indicators[ward] = missing_indicators_count
#
#     # Generate a message for the wards missing indicators
#     if wards_missing_indicators:
#         # Sort wards by the number of missing indicators in descending order
#         sorted_wards = sorted(wards_missing_indicators.items(), key=lambda x: x[1], reverse=True)
#
#         missing_wards_message = "\n".join(
#             f" {ward} is missing {count} {pluralize_word('indicator', count)},"
#             for ward, count in sorted_wards
#         )
#         return f"Data Verification section {quarter_year}:" + missing_wards_message
#     else:
#         return None  # No missing indicators
def wash_dqa_dashboard(request, dqa_type=None):
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
    light_green = None
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
    system_assessment_df = pd.DataFrame()
    if dqa_type == "program":
        if quarter_form.is_valid() and year_form.is_valid() and program_form.is_valid():
            selected_quarter = quarter_form.cleaned_data['quarter']
            selected_year = year_form.cleaned_data['year']
            selected_program = program_form.cleaned_data['program']
            selected_level = selected_program
            year_suffix = selected_year[-2:]
            quarter_year = f"{selected_quarter}-{year_suffix}"

            data_verification = DataConcordance.objects.filter(quarter_year__quarter_year=quarter_year)
            system_assessment_df = get_model_query_set(request, quarter_year)
            # system_assessment = Documentation.objects.filter(quarter_year__quarter_year=quarter_year)
            # fyj_performance = FyjPerformance.objects.filter(quarter_year=quarter_year).values()
            khis_performance = JphesPerformance.objects.filter(quarter_year=quarter_year).values()
            audit_team = WashAuditTeam.objects.filter(quarter_year__quarter_year=quarter_year)
            dqa_workplan = WashDQAWorkPlan.objects.filter(quarter_year__quarter_year=quarter_year).order_by('ward_name')
            #####################################
            # DECREMENT REMAINING TIME DAILY    #
            #####################################
            if dqa_workplan:
                today = timezone.now().date()
                for workplan in dqa_workplan:
                    workplan.progress = (workplan.due_complete_by - today).days
            # fetch data from the Sub_counties model
            # data = SubCounties.objects.values('facilities__name', 'facilities__ward_code', 'hub__hub',
            #                                    'counties__county_name', 'sub_counties')
            data = SubCounties.objects.values('ward__name', 'ward__ward_code', 'county__name', 'name')

            # Create a DataFrame from the query results
            df = pd.DataFrame(data)
            # print("DATA:::::::::::::::::::::::::::::::::::::::::::::::::::")
            # print(df)

    # elif dqa_type == "subcounty":
    #     if quarter_form.is_valid() and year_form.is_valid() and subcounty_form.is_valid():
    #         selected_quarter = quarter_form.cleaned_data['quarter']
    #         selected_year = year_form.cleaned_data['year']
    #         selected_subcounty = subcounty_form.cleaned_data['subcounty']
    #         selected_level = selected_subcounty
    #         year_suffix = selected_year[-2:]
    #         quarter_year = f"{selected_quarter}-{year_suffix}"
    #         sub_county = Sub_counties.objects.get(sub_counties=selected_subcounty)
    #         facilities = sub_county.facilities.all()
    #         data_verification = DataConcordance.objects.filter(quarter_year__quarter_year=quarter_year,
    #                                                             facility_name__in=facilities)
    #
    #         system_assessment = SystemAssessment.objects.filter(quarter_year__quarter_year=quarter_year,
    #                                                             facility_name__in=facilities)
    #         fyj_performance = FyjPerformance.objects.filter(quarter_year=quarter_year).values()
    #         khis_performance = JphesPerformance.objects.filter(quarter_year=quarter_year).values()
    #         audit_team = WashAuditTeam.objects.filter(quarter_year__quarter_year=quarter_year,
    #                                               facility_name__in=facilities)
    #         dqa_workplan = WashDQAWorkPlan.objects.filter(quarter_year__quarter_year=quarter_year,
    #                                                   facility_name__in=facilities).order_by('facility_name')
    #         #####################################
    #         # DECREMENT REMAINING TIME DAILY    #
    #         #####################################
    #         if dqa_workplan:
    #             today = timezone.now().date()
    #             for workplan in dqa_workplan:
    #                 workplan.progress = (workplan.due_complete_by - today).days
    #         # fetch data from the Sub_counties model
    #         data = Sub_counties.objects.values('facilities__name', 'facilities__ward_code', 'hub__hub',
    #                                            'counties__county_name', 'sub_counties')
    #
    # elif dqa_type == "county":
    #     if quarter_form.is_valid() and year_form.is_valid() and county_form.is_valid():
    #         selected_quarter = quarter_form.cleaned_data['quarter']
    #         selected_year = year_form.cleaned_data['year']
    #         selected_county = county_form.cleaned_data['county']
    #         selected_level = selected_county
    #         year_suffix = selected_year[-2:]
    #         quarter_year = f"{selected_quarter}-{year_suffix}"
    #         # county = Counties.objects.get(county_name=selected_county)
    #
    #         data_verification = DataConcordance.objects.filter(
    #             quarter_year__quarter_year=quarter_year,
    #             facility_name__sub_counties__counties__county_name=selected_county)
    #
    #         system_assessment = SystemAssessment.objects.filter(
    #             quarter_year__quarter_year=quarter_year,
    #             facility_name__sub_counties__counties__county_name=selected_county)
    #         fyj_performance = FyjPerformance.objects.filter(quarter_year=quarter_year).values()
    #         khis_performance = JphesPerformance.objects.filter(quarter_year=quarter_year).values()
    #         audit_team = WashAuditTeam.objects.filter(
    #             quarter_year__quarter_year=quarter_year,
    #             facility_name__sub_counties__counties__county_name=selected_county)
    #         dqa_workplan = WashDQAWorkPlan.objects.filter(
    #             quarter_year__quarter_year=quarter_year,
    #             facility_name__sub_counties__counties__county_name=selected_county).order_by('facility_name')
    #         #####################################
    #         # DECREMENT REMAINING TIME DAILY    #
    #         #####################################
    #         if dqa_workplan:
    #             today = timezone.now().date()
    #             for workplan in dqa_workplan:
    #                 workplan.progress = (workplan.due_complete_by - today).days
    #         # fetch data from the Sub_counties model
    #         data = Sub_counties.objects.values('facilities__name', 'facilities__ward_code', 'hub__hub',
    #                                            'counties__county_name', 'sub_counties')
    #
    # elif dqa_type == "hub":
    #     if quarter_form.is_valid() and year_form.is_valid() and hub_form.is_valid():
    #         selected_quarter = quarter_form.cleaned_data['quarter']
    #         selected_year = year_form.cleaned_data['year']
    #         selected_hub = hub_form.cleaned_data['hub']
    #         selected_level = selected_hub
    #         year_suffix = selected_year[-2:]
    #         quarter_year = f"{selected_quarter}-{year_suffix}"
    #
    #         data_verification = DataConcordance.objects.filter(
    #             quarter_year__quarter_year=quarter_year,
    #             facility_name__sub_counties__hub__hub=selected_hub)
    #
    #         system_assessment = SystemAssessment.objects.filter(
    #             quarter_year__quarter_year=quarter_year,
    #             facility_name__sub_counties__hub__hub=selected_hub)
    #         fyj_performance = FyjPerformance.objects.filter(quarter_year=quarter_year).values()
    #         khis_performance = JphesPerformance.objects.filter(quarter_year=quarter_year).values()
    #         audit_team = WashAuditTeam.objects.filter(
    #             quarter_year__quarter_year=quarter_year,
    #             facility_name__sub_counties__hub__hub=selected_hub)
    #         dqa_workplan = WashDQAWorkPlan.objects.filter(
    #             quarter_year__quarter_year=quarter_year,
    #             facility_name__sub_counties__hub__hub=selected_hub).order_by('facility_name')
    #         #####################################
    #         # DECREMENT REMAINING TIME DAILY    #
    #         #####################################
    #         if dqa_workplan:
    #             today = timezone.now().date()
    #             for workplan in dqa_workplan:
    #                 workplan.progress = (workplan.due_complete_by - today).days
    #         # fetch data from the Sub_counties model
    #         data = Sub_counties.objects.values('facilities__name', 'facilities__ward_code', 'hub__hub',
    #                                            'counties__county_name', 'sub_counties')

    if dqa_type is not None and quarter_form.is_valid():

        if data_verification and not system_assessment_df.empty:
            data_verification_data = data_verification.values('ward_name__name', 'indicator')
            message = generate_missing_indicators_message(data_verification_data,DataConcordance,'ward_name__name',quarter_year)
            if message:
                messages.success(request, message)
            # # Collect the relevant data into a list or dictionary
            # data_verification_data = data_verification.values('ward_name__name', 'indicator')
            #
            # # Create a dictionary to track wards and the number of missing indicators
            # wards_missing_indicators = defaultdict(int)
            #
            # # Iterate through unique wards
            # unique_wards = set(item['ward_name__name'] for item in data_verification_data)
            # for ward in unique_wards:
            #     # Get the indicators for this ward
            #     ward_indicators = set(
            #         item['indicator'] for item in data_verification_data if item['ward_name__name'] == ward)
            #
            #     # Count the number of missing indicators for the ward
            #     missing_indicators_count = sum(
            #         1
            #         for indicator_choice in DataConcordance.INDICATOR_CHOICES[1:]
            #         if indicator_choice[0] not in ward_indicators
            #     )
            #
            #     # If the ward is missing any indicators, add it to the dictionary
            #     if missing_indicators_count > 0:
            #         wards_missing_indicators[ward] = missing_indicators_count
            #
            # # Generate a message for the wards missing indicators
            # if wards_missing_indicators:
            #     # Sort wards by the number of missing indicators in descending order
            #     sorted_wards = sorted(wards_missing_indicators.items(), key=lambda x: x[1], reverse=True)
            #
            #     missing_wards_message = "\n".join(
            #         f" {ward} is missing {count} {pluralize_word('indicator', count)},"
            #         for ward, count in sorted_wards
            #     )
            #     messages.success(request, "Data Verification section:" + missing_wards_message)

            facilities = [
                {'wards': x.ward_name.name,
                 'ward_code': x.ward_name.ward_code,
                 } for x in data_verification
            ]
            # convert data from database to a dataframe
            facilities_df = pd.DataFrame(facilities).drop_duplicates()

            # print("WARRRRRRRRRRRRRRRRRRRDS DF::::::::::::::::::::::::::::::::::::::::::::::::::::")
            # print(facilities_df)
            facilities_df=pd.concat([system_assessment_df[['wards','ward_code']].drop_duplicates(),facilities_df]).drop_duplicates()
            # print(facilities_df)
            facilities_df.sort_values('wards', inplace=True)
            facilities_df['count'] = 1
            viz = bar_chart_dqa(facilities_df, "wards", "count",
                                title=f"Wards WASH DQA Summary for {quarter_year} N= {len(facilities_df)}")
        else:
            facilities_df = pd.DataFrame(columns=['wards', 'ward_code', 'count'])

        if data:
            # create a list of dictionaries containing the data
            # county_hub_sub_county = []
            # for d in data:
            #     county_hub_sub_county.append({
            #         'ward': d['ward__name'],
            #         'ward_code': d['facilities__ward_code'],
            #         # 'hubs': d['hub__hub'],
            #         'counties': d['counties__county_name'],
            #         'sub_counties': d['sub_counties']
            #     })

            #
            # # convert the list of dictionaries to a pandas dataframe
            # county_hub_sub_county_df = pd.DataFrame(county_hub_sub_county)
            county_hub_sub_county_df = pd.DataFrame(data)
            county_hub_sub_county_df = county_hub_sub_county_df.rename(
                columns={"ward__name": "wards", "ward__ward_code": "ward_code", "county__name": "counties",
                         "name": "sub_counties"})
            county_hub_sub_county_df.sort_values('wards', inplace=True)
            # print(f"county_hub_sub_county_df::::::::::::{county_hub_sub_county_df}::::::::::::::::::::::::")

            merged_df = county_hub_sub_county_df.merge(facilities_df, on=['wards', 'ward_code'], how="right")
            if merged_df.shape[0] > 0:
                sub_county_df = merged_df.groupby('sub_counties')[
                    'count'].sum(numeric_only=True).reset_index().sort_values('count')
                sub_county_df = sub_county_df.rename(columns={"count": "Number of wards"})
                sub_county_df['sub_counties'] = sub_county_df['sub_counties'].str.replace(" Sub County", "")
                sub_county_viz = bar_chart_dqa(sub_county_df, "sub_counties", "Number of wards",
                                               title=f"Sub-counties WASH DQA Summary for {quarter_year} N={len(sub_county_df)} ")
                county_df = merged_df.groupby('counties')['count'].sum(numeric_only=True).reset_index().sort_values(
                    'count')
                county_df = county_df.rename(columns={"count": "Number of wards"})
                county_viz = bar_chart_dqa(county_df, "counties", "Number of wards",
                                           title=f"Counties DQA Summary for {quarter_year}")
                # hub_df = merged_df.groupby('hubs').sum(numeric_only=True)['count'].reset_index().sort_values(
                #     'count')
                # hub_df = hub_df.rename(columns={"count": "Number of wards"})
                # hub_viz = bar_chart_dqa(hub_df, "hubs", "Number of wards",
                #                         f"{len(hub_df)} Hubs DQA Summary for {quarter_year}")
        # if system_assessment:
        #     system_assessments_qs = [
        #         {'wards': x.ward_name.name,
        #          'ward_code': x.ward_name.ward_code,
        #          'description': x.description,
        #          "auditor's note": x.auditor_note,
        #          'calculations': x.calculations
        #          } for x in system_assessment
        #     ]
        #     # convert data from database to a dataframe
        #     system_assessments_df = pd.DataFrame(system_assessments_qs)
        if not system_assessment_df.empty:
            system_assessments_df = system_assessment_df.copy()
            # system_assessments_df = system_assessments_df[system_assessments_df['calculations'].notna()]
            system_assessments_df.sort_values('wards', inplace=True)
            # print(f"system_assessments_df::::::::::::::::::::::::::::::::::::::::::::")
            # print(system_assessments_df['wards'].unique())
            # print(system_assessments_df)
            system_assessments_df['count'] = 1
            assessment_means_list, assessment_names_list, site_avg, average_dictionary = get_all_averages(request,
                                                                                                          quarter_year)
            fyj_mean = round(site_avg, 2)

            # print("AVG DICTS WASH DQA::::::::::::::::::::::::::::::::::::::::::::::::::::::::")
            # print(average_dictionary)
            # print(site_avg)

            df = pd.DataFrame(average_dictionary.items(), columns=['Component of the M&E System', 'Mean'])
            # print(df)

            cond_list = [df['Mean'] >= 4.5, (df['Mean'] >= 3.5) & (df['Mean'] < 4.5),
                         (df['Mean'] >= 2.5) & (df['Mean'] < 3.5),
                         (df['Mean'] >= 1.5) & (df['Mean'] < 2.5), df['Mean'] < 1.5]
            choice_list = ["blue", "green", "lightgreen", "yellow", "red"]
            df['color'] = np.select(cond_list, choice_list, default=0)

            thresholds = [4.5, 3.5, 2.5, 1.5]
            color_list = ["blue", "green", "lightgreen", "#ebba34", "red"]
            fyj_mean, mean_color = get_mean_color(fyj_mean, thresholds, color_list)
            system_assessment_viz = create_system_assessment_chart(df, fyj_mean, mean_color, quarter_year)
            # # Show system assessment performance
            custom_mapping = {1: ("red", "reds"), 2: ("yellow", "yellows"), 3: ("light_green", "light_greens"),
                              4: ("green", "greens"), 5: ("blue", "blues"), 0: ("not_applicable", "not applicable"),
                              }
            for report_type in ["data-quality-assessment", "data-quality", "data-collection", "documentation"]:
                report_type, model_name, description_list = get_assessment_list_model_name(report_type)
            #     print(f"REPORT TYPE:::::::::::::::::::::::{report_type}::::::::::")
            # print(f"STSYETM ASSESSMENT DATA FRAME BEFORE FUNCTION:::::::::::::::::::::::::::::::::::")
            # print(system_assessments_df)
            # print(system_assessments_df['model_name'].unique())
            m_e_structures, m_e_data_mnx, m_e_indicator_definition, m_e_data_collect_report, m_e_emr_systems, red, \
                yellow, na_df, green, light_green, blue, all_dfs = prepare_data_system_assessment(system_assessments_df,
                                                                                                  custom_mapping)
            names = ["I - Documentation", "II- Data Quality Systems",
                     "III- Data Collection, Reporting and Management",
                     "IV- Data Quality Assessment by Data Source",
                     # "V - EMR Systems"
                     ]
            lists = [m_e_structures, m_e_data_mnx, m_e_indicator_definition, m_e_data_collect_report,
                     # m_e_emr_systems
                     ]
            #########################
            # Areas of Improvement
            #########################
            area_yellow = delete_df_column(yellow, "model_name")
            area_red = delete_df_column(red, "model_name")
            area_na_df = delete_df_column(na_df, "model_name")
            area_light_green = delete_df_column(light_green, "model_name")
            non_performance_df = {
                "yellow": area_yellow,
                "red": area_red,
                "na_df": area_na_df,
                "light_green": area_light_green,
            }
            # print("ALL DFS:::Distribution of system assessment scores N::::::")
            # print(all_dfs)
            all_dfs_viz = bar_chart_dqa(all_dfs, "Scores", '# of scores',
                                        title=f"Distribution of system assessment scores N = {all_dfs['# of scores'].sum()}"
                                              f" ({quarter_year})"
                                        )

            needs_improvements_df = pd.concat([yellow, light_green])
            yellow_dfs = prepare_deep_dive_dfs(needs_improvements_df, 'Component of the M&E System')
            yellow_viz_comp = bar_chart_dqa(yellow_dfs, "Component of the M&E System", 'Number of scores',
                                            title="Needs improvement per component of the M&E System",
                                            color='yellow')

            needs_improvements_df = pd.concat([yellow, light_green])
            yellow_dfs = prepare_deep_dive_dfs(needs_improvements_df, 'description')
            yellow_viz_quest = bar_chart_dqa(yellow_dfs, "description", 'Number of scores',
                                             title="Needs improvement per description",
                                             color='yellow')

            red_dfs = prepare_deep_dive_dfs(red, 'Component of the M&E System')
            red_viz_comp = bar_chart_dqa(red_dfs, "Component of the M&E System", 'Number of scores',
                                         title="Needs urgent remediation per component of the M&E System",
                                         color='red')
            red_dfs = prepare_deep_dive_dfs(red, 'description')
            red_viz_quest = bar_chart_dqa(red_dfs, "description", 'Number of scores',
                                          title="Needs urgent remediation per description", color='red')

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
                charts.append(create_system_assessment_bar_charts(df, title, quarter_year))
            if 'Number of scores' in yellow.columns:
                del yellow['Number of scores']
            if 'Number of scores' in red.columns:
                del red['Number of scores']
            if 'Number of scores' in na_df.columns:
                del na_df['Number of scores']
        else:
            messages.info(request, f"No system assessment data for Qtr1-23")
        # if data_verification:
        #     dqa_df = create_dqa_df(data_verification)
        #     if dqa_df.empty:
        #         messages.info(request, f"A few DQA indicators have been capture but not "
        #                                f"enough for data visualization")
        # else:
        #     dqa_df = pd.DataFrame(columns=['indicator', 'facility', 'ward_code', 'Source', 'MOH 731', 'KHIS',
        #                                    'quarter_year', 'last month'])
        #     messages.info(request, f"No DQA data for {quarter_year}")
        # if fyj_performance:
        #     fyj_perf_df = make_performance_df(fyj_performance, 'DATIM')
        # else:
        #     fyj_perf_df = pd.DataFrame(columns=['ward_code', 'quarter_year', 'indicator', 'DATIM'])
        #     messages.info(request, f"No DATIM data for {quarter_year}!")
        # merged_df = dqa_df.merge(fyj_perf_df, on=['ward_code', 'quarter_year', 'indicator'], how='right')
        # merged_df = merged_df[merged_df['facility'].notnull()]
        # if khis_performance:
        #     grouped, merged_df = make_wash_performance_df(request, data_verification, khis_performance,quarter_year)
        #     print("grouped::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::")
        #     print(grouped)
        #     khis_perf_df = make_performance_df(khis_performance, 'KHIS')
        #
        #     tx_curr_khis = khis_perf_df[khis_perf_df['indicator'] == "Number Current on ART Total"]
        #
        #     # apply the function to the 'date' column and store the result in a new column
        #     # tx_curr_khis['month_number'] = tx_curr_khis['month'].apply(get_month_number)
        #
        #     tx_curr_khis['month'] = pd.to_datetime(tx_curr_khis['month'], format='%b %Y')
        #     tx_curr_khis['month_number'] = tx_curr_khis['month'].dt.month
        #
        #     tx_curr_khis = tx_curr_khis[tx_curr_khis['month_number'] == max(tx_curr_khis['month_number'])]
        #     del tx_curr_khis['month_number']
        #     del tx_curr_khis['month']
        #     khis_others = khis_perf_df[khis_perf_df['indicator'] != "Number Current on ART Total"]
        #
        #     khis_others = khis_others.groupby(['indicator', 'quarter_year', 'ward_code']).sum(
        #         numeric_only=True).reset_index()
        #
        #     khis_perf_df = pd.concat([khis_others, tx_curr_khis])
        # else:
        #     khis_perf_df = pd.DataFrame(columns=['indicator', 'facility', 'ward_code', 'KHIS',
        #                                          'quarter_year'])
        #
        # if "KHIS" in merged_df.columns:
        #     del merged_df['KHIS']
        # merged_df = khis_perf_df.merge(merged_df, on=['ward_code', 'quarter_year', 'indicator'], how='right').fillna(
        #     0)
        # try:
        #     merged_df = merged_df[
        #         ['ward_code', 'facility', 'indicator', 'quarter_year', 'Source', 'MOH 731', 'KHIS', 'DATIM']]
        # except KeyError:
        #     messages.info(request, f"No KHIS data for {quarter_year}!")
        # for i in merged_df.columns[4:]:
        #     merged_df[i] = merged_df[i].astype(int)
        # merged_df = merged_df.groupby(['indicator', 'quarter_year']).sum(numeric_only=True).reset_index()

        grouped, merged_df, khis_perf_df, dqa_df = make_wash_performance_df(request, data_verification,
                                                                            khis_performance, quarter_year)
        # print("dqa_df before compare data verification::::::::::::::::::::::::::::::::::")
        # print(dqa_df)
        if not dqa_df.empty and not khis_perf_df.empty :
            dqa_df = dqa_df[
                ['indicator', 'quarter_year', 'ward_code', 'Source', 'Monthly Report']]
            dqa_df['Source'] = dqa_df['Source'].astype(int)
            dqa_df['Monthly Report'] = dqa_df['Monthly Report'].astype(int)
            khis_perf_df['JPHES'] = khis_perf_df['JPHES'].astype(int)
            # print(khis_perf_df)
            # dqa_df = dqa_df.groupby(['quarter_year', 'indicator']).sum().reset_index()
            # print(dqa_df)

            merged_df = khis_perf_df.merge(dqa_df, on=['quarter_year', 'indicator', 'ward_code'], how='right').fillna(0)
            # print(merged_df['ward_code'].unique())
            merged_df = merged_df[
                ['indicator', 'quarter_year', 'Source', 'Monthly Report', 'JPHES']]
            merged_df = merged_df.groupby(['indicator', 'quarter_year']).sum().reset_index()

            # print("dqa_df before compare data verification::::::::::::::::::::::::::::::::::")
            # print(dqa_df)
            # dqa_df = dqa_df[
            #     ['indicator', 'quarter_year', 'Source', 'Monthly Report']]
            # dqa_df['Source']=dqa_df['Source'].astype(int)
            # dqa_df['Monthly Report']=dqa_df['Monthly Report'].astype(int)
            # print(dqa_df)
            # dqa_df=dqa_df.groupby(['quarter_year','indicator']).sum().reset_index()
            # print(dqa_df)
            # merged_df = khis_perf_df.merge(dqa_df, on=['quarter_year', 'indicator'], how='right').fillna(0)
            # merged_df = merged_df[
            #     ['indicator', 'quarter_year', 'Source', 'Monthly Report', 'JPHES']]
            # print("merged before compare data verification::::::::::::::::::::::::::::::::::")
            # print(merged_df)

            dicts, merged_viz_df = compare_data_verification(merged_df, "JPHES")
            # print("merged_viz_df::::::::::::::::::::::::::::::::::::::::::::::")
            # print(merged_viz_df)
            # print(merged_viz_df.columns)
            data_verification_viz = bar_chart_dqa(merged_viz_df, "indicator",
                                                  "Absolute difference proportion (Difference/Source*100)",
                                                  pepfar_col="JPHES",
                                                  color='Score',
                                                  title="Data verification final scores (Discordance rate: Target <=5%)")
        else:
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
                "yellow": yellow, "light_green": light_green,
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
            return render(request, 'wash_dqa/dqa_dashboard.html', context)
        # if viz is None:
        #     messages.error(request, f"No DQA data found for {quarter_year}")
        if audit_team:
            audit_team_qs = [
                {'wards': x.ward_name.name,
                 'ward_code': x.ward_name.ward_code,
                 'First Name': x.first_name,
                 'Last Name': x.first_name,
                 'Carder': x.carder,
                 'Organization': x.organization,
                 } for x in audit_team
            ]
            # convert data from database to a dataframe
            audit_team_df = pd.DataFrame(audit_team_qs)
            audit_team_df['Name'] = audit_team_df["First Name"] + " " + audit_team_df['Last Name']
            # groupby 'name' ,'carder','organization' and aggregate the facility names as a string
            audit_team_df = audit_team_df.groupby(['Name', 'Carder', 'Organization']).agg(
                {'wards': lambda x: ', '.join(set(x))})
            #
            audit_team_df = audit_team_df.reset_index()
            audit_team_df_copy = audit_team_df.copy()
            audit_team_df = clean_audit_team_df(audit_team_df)
            audit_viz = bar_chart_dqa(audit_team_df, "Carder", 'Number of audit team', color="Organization",
                                      title=f"DQA Audit Team Participation by Organization and Carder "
                                            f"N = {audit_team_df['Number of audit team'].sum()}")
        #
        if dqa_workplan:
            dqa_workplan_qs = [
                {'wards': x.ward_name.name,
                 'ward_code': x.ward_name.ward_code,
                 'dqa_date': x.dqa_date,
                 'Program Areas Reviewed': x.program_areas_reviewed,
                 'completion': x.percent_completed,
                 'Timeframe': x.timeframe,
                 } for x in dqa_workplan
            ]
            # convert data from database to a dataframe
            dqa_workplan_df = pd.DataFrame(dqa_workplan_qs)
            facilities_df, area_reviewed_df, action_point_status_df, weekly_counts, timeframe_df, \
                area_reviewed_facility_df = prepare_dqa_workplan_viz(dqa_workplan_df, "wards")
            work_plan_facilities_viz = bar_chart_dqa(facilities_df, "wards", "Number of action points",
                                                     title=f"Distribution of DQA action points per ward N = "
                                                           f"{facilities_df['Number of action points'].sum()}"
                                                           f" ({quarter_year})",
                                                     color=None)
            work_plan_areas_reviewed_viz = bar_chart_dqa(area_reviewed_df, "Program Areas Reviewed",
                                                         "Number of action points",
                                                         title=f"Distribution of DQA action points by focus area "
                                                               f"reviewed N = "
                                                               f"{area_reviewed_df['Number of action points'].sum()}"
                                                               f" ({quarter_year})",
                                                         color=None)
            # print("=======================================================================")
            # print(area_reviewed_facility_df['Program Areas Reviewed'].unique())
            program_areas = ["Documentation", "Data_Quality_Assessment", "Data_Collection_Reporting_and_Management",
                             "Data_Quality_Systems", "Data_Verification"]
            facility_charts = {}
            for program_area in program_areas:
                area_reviewed_facility_df_area = area_reviewed_facility_df[
                    area_reviewed_facility_df['Program Areas Reviewed'] == program_area]
                title = f"Distribution of {program_area.replace('_', ' ')} DQA action points by facility ({quarter_year})"
                chart = bar_chart_dqa(area_reviewed_facility_df_area, "wards", "Number of action points",
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
        "yellow": yellow, "light_green": light_green,
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
    return render(request, 'wash_dqa/dqa_dashboard.html', context)


# def export_wash_dqa_work_plan_csv(request, quarter_year, selected_level):
#     response = HttpResponse(content_type='text/csv')
#     response['Content-Disposition'] = f'attachment; filename="{selected_level} {quarter_year} dqa_workplan.csv"'
#
#     writer = csv.writer(response)
#     writer.writerow(['DQA Date', 'Ward Name', 'Quarter Year', 'Individuals Conducting DQA',
#                      'Program Areas Reviewed', 'Strengths Identified', 'Gaps Identified', 'Recommendation',
#                      '% Completed', 'Individuals Responsible', 'Due/Complete By', 'Comments',
#                      'Created At', 'Updated At', 'Progress', 'Timeframe', 'Created By', 'Modified By'])
#
#     work_plans = WashDQAWorkPlan.objects.all().values_list('dqa_date', 'ward_name__name',
#                                                        'quarter_year__quarter_year', 'individuals_conducting_dqa',
#                                                        'program_areas_reviewed', 'strengths_identified',
#                                                        'gaps_identified', 'recommendation',
#                                                        'percent_completed', 'individuals_responsible',
#                                                        'due_complete_by', 'comments', 'date_created',
#                                                        'date_modified', 'progress', 'timeframe', 'created_by__email',
#                                                        'modified_by__email')
#
#     for work_plan in work_plans:
#         writer.writerow(work_plan)
#
#     return response
# def export_wash_dqa_work_plan_csv(request, quarter_year, selected_level):
#     response = HttpResponse(content_type='text/csv')
#     filename = f"{selected_level} {quarter_year} dqa_workplan.csv"
#     response['Content-Disposition'] = f'attachment; filename="{filename}"'
#
#     writer = csv.writer(response)
#
#     # Get the model dynamically using the app name and model name
#     app_label = "wash_dqa"  # Replace with your app's label
#     model_name = 'WashDQAWorkPlan'  # Replace with your model's name
#     model = apps.get_model(app_label, model_name)
#
#     # Get field names dynamically and exclude specific columns
#     excluded_columns = ['id', 'created_by', 'modified_by', 'date_created', 'date_modified']
#     field_names = [field.name for field in model._meta.get_fields() if field.name not in excluded_columns]
#
#     # Write the header row with field names
#     writer.writerow(field_names)
#
#     # Query the database to get the data
#     work_plans = model.objects.all().values_list(*field_names)
#
#     for work_plan in work_plans:
#         writer.writerow(work_plan)
#
#     return response
def export_wash_dqa_work_plan_csv(request, quarter_year, selected_level,name):
    response = HttpResponse(content_type='text/csv')
    filename = f"{selected_level} {quarter_year} {name} dqa_workplan.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)

    # Get the model dynamically using the app name and model name
    app_label = "wash_dqa"  # Replace with your app's label
    model_name = 'WashDQAWorkPlan'  # Replace with your model's name
    model = apps.get_model(app_label, model_name)

    # Get field names dynamically and exclude specific columns
    excluded_columns = ['id', 'created_by', 'modified_by', 'date_created', 'date_modified','progress']
    field_names = [field.name for field in model._meta.get_fields() if field.name not in excluded_columns]

    # Write the header row with field names
    writer.writerow(field_names)

    # Query the database to get the data
    work_plans = model.objects.all()

    for work_plan in work_plans:
        # Get the names of related fields
        ward_name = work_plan.ward_name.name if work_plan.ward_name else ""
        quarter_year = work_plan.quarter_year.quarter_year if work_plan.quarter_year else ""

        # Create a list of values, including related field names
        row_values = [getattr(work_plan, field) for field in field_names]
        row_values[field_names.index("ward_name")] = ward_name
        row_values[field_names.index("quarter_year")] = quarter_year

        writer.writerow(row_values)

    return response