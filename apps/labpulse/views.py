import csv
import io
import json
import math
import os
import re
import textwrap
from datetime import date, datetime, timedelta, timezone
from functools import reduce
from urllib.parse import unquote

import numpy as np
import pandas as pd
import pdfplumber
import plotly.express as px
import plotly.graph_objs as go
import pytz
import tzlocal
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.staticfiles.finders import find
from django.core import serializers
from django.core.cache import cache
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.core.serializers.json import DjangoJSONEncoder
from django.db import IntegrityError, transaction
from django.db.models import ExpressionWrapper, F, IntegerField, Q, Sum
from django.db.models.functions import Extract
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.decorators.cache import cache_page
from plotly.offline import plot
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
# from silk.profiling.profiler import silk_profile

from apps.cqi.forms import FacilitiesForm
from apps.cqi.models import Counties, Facilities, Sub_counties
from apps.cqi.views import bar_chart
from apps.data_analysis.views import get_key_from_session_names
from apps.labpulse.decorators import group_required
from apps.labpulse.filters import BiochemistryResultFilter, Cd4trakerFilter, DrtResultFilter
from apps.labpulse.forms import BiochemistryForm, Cd4TestingLabForm, Cd4TestingLabsForm, Cd4trakerForm, \
    Cd4trakerManualDispatchForm, \
    DrtForm, DrtPdfFileForm, DrtResultsForm, LabPulseUpdateButtonSettingsForm, ReagentStockForm, facilities_lab_Form
from apps.labpulse.models import BiochemistryResult, Cd4TestingLabs, Cd4traker, DrtPdfFile, DrtProfile, DrtResults, \
    EnableDisableCommodities, \
    LabPulseUpdateButtonSettings, ReagentStock
from config.settings.base import BASE_DIR


def results(df):
    """
    Determine the result status based on the given data.

    This function calculates the result status for a given dataset containing 'High Limit' and 'Result' values.
    It classifies the result into categories such as 'High', 'Normal', 'Low', based on the provided limits.

    Args:
        df (pandas.DataFrame): A DataFrame containing the columns 'High Limit' and 'Result'.

    Returns:
        str: A string representing the result status, which can be 'High', 'Normal', 'Low'.

    Examples:
        Example usage:
        df = pd.DataFrame({'High Limit': [100, 80, 120], 'Result': [90, 105, 70]})
        status = results(df)
        print(status)  # Output could be 'Normal', 'High', or 'Low' based on the data.
    """
    if df['High Limit'] < df['Result']:
        return "High"
    elif df['High Limit'] > df['Result'] > df['Low Limit']:
        return "Normal"
    elif df['Low Limit'] > df['Result']:
        return "Low"
    else:
        return "Normal"


def biochemistry_data_prep(df):
    """
    Prepare and clean biochemistry data.

    This function prepares and cleans a DataFrame containing biochemistry data.
    It performs various operations, such as extracting the MFL code from the 'Patient id', filtering out specific codes,
    converting date columns to datetime objects, and applying a results function to interpret results.
    It also adds a 'number_of_samples' column with a default value of 1.

    Args:
        df (pandas.DataFrame): A DataFrame containing biochemistry data with specific columns.

    Returns:
        pandas.DataFrame: A cleaned and processed DataFrame ready for further analysis.

    Examples:
        Example usage:
        df = pd.read_csv('biochemistry_data.csv')
        cleaned_data = biochem_data_prep(df, results)
        print(cleaned_data.head())
    """
    df['mfl_code'] = df['Patient Id'].str[:5]
    df = df[df['mfl_code'] != "EQA"]
    df['Collection'] = pd.to_datetime(df['Collection'])
    df['Result time'] = pd.to_datetime(df['Result time'])
    df['mfl_code'] = df['mfl_code'].astype(int)
    df['Patient Id'] = df['Patient Id'].astype(int)
    df['results_interpretation'] = df.apply(results, axis=1)
    df['number_of_samples'] = 1
    return df


def disable_update_buttons(request, audit_team, relevant_date_field):
    ##############################################################
    # DISABLE UPDATE BUTTONS AFTER A SPECIFIED TIME AND DAYS AGO #
    ##############################################################
    local_tz = pytz.timezone("Africa/Nairobi")
    settings = LabPulseUpdateButtonSettings.objects.first()
    try:
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
                              "You have not yet set the time to disable the LabPulse update button. Please click on the"
                              " 'Change DQA Update Time' button on the left navigation bar to set the time or contact "
                              "an administrator to set it for you.")
    except AttributeError:
        messages.info(request,
                      "You have not yet set the time to disable the LabPulse update button. Please click on the 'Change "
                      "labPulse Update Time' button on the left navigation bar to set the time or contact an "
                      "administrator to set it for you.")
    return redirect(request.path_info)


def lab_pulse_update_button_settings(request):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    update_settings = LabPulseUpdateButtonSettings.objects.first()
    if request.method == 'POST':
        form = LabPulseUpdateButtonSettingsForm(request.POST, instance=update_settings)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = LabPulseUpdateButtonSettingsForm(instance=update_settings)
    return render(request, 'lab_pulse/upload.html', {'form': form, "title": "update time"})


# Create your views here.
@login_required(login_url='login')
@group_required(['laboratory_staffs_labpulse'])
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
                              'report_type': "Current", 'pk_lab': testing_lab_name.id})

            return redirect(url)
    context = {
        "cd4_testing_lab_form": cd4_testing_lab_form,
        "title": "CD4 TRACKER"
    }
    return render(request, 'lab_pulse/add_cd4_data.html', context)


@login_required(login_url='login')
@group_required(['laboratory_staffs_labpulse'])
@permission_required('labpulse.view_add_retrospective_cd4_count', raise_exception=True)
def choose_testing_lab_manual(request):
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
                              'report_type': "Retrospective", 'pk_lab': testing_lab_name.id})

            return redirect(url)
    context = {
        "cd4_testing_lab_form": cd4_testing_lab_form,
        "title": "CD4 TRACKER"
    }
    return render(request, 'lab_pulse/add_cd4_data.html', context)


def validate_cd4_count_form(form, report_type):
    received_status = form.cleaned_data['received_status']
    reason_for_rejection = form.cleaned_data['reason_for_rejection']
    date_of_collection = form.cleaned_data['date_of_collection']
    date_sample_received = form.cleaned_data['date_sample_received']
    date_of_testing = form.cleaned_data['date_of_testing']
    cd4_count_results = form.cleaned_data['cd4_count_results']
    serum_crag_results = form.cleaned_data['serum_crag_results']
    reason_for_no_serum_crag = form.cleaned_data['reason_for_no_serum_crag']
    cd4_percentage = form.cleaned_data['cd4_percentage']
    age = form.cleaned_data['age']
    today = timezone.now().date()

    if report_type != "Current":
        date_dispatched = form.cleaned_data['date_dispatched']
        if date_of_collection and date_of_collection > date_dispatched:
            error_message = "Collection date is greater than Dispatch date!"
            form.add_error('date_of_collection', error_message)
            form.add_error('date_dispatched', error_message)
            return False
        if date_dispatched > today:
            form.add_error('date_dispatched', "Date of sample dispatched cannot be in the future.")
            return False

        if date_sample_received and date_sample_received > date_dispatched:
            error_message = "Received date is greater than Dispatch date!"
            form.add_error('date_sample_received', error_message)
            form.add_error('date_dispatched', error_message)
            return False

        if date_of_testing and date_of_testing > date_dispatched:
            error_message = "Testing date is greater than Dispatch date!"
            form.add_error('date_of_testing', error_message)
            form.add_error('date_dispatched', error_message)
            return False

    if date_of_collection > date_sample_received:
        error_message = "Collection date is greater than Receipt date!"
        form.add_error('date_of_collection', error_message)
        form.add_error('date_sample_received', error_message)
        return False

    if received_status == 'Rejected':
        if not reason_for_rejection:
            error_message = "Please specify the reason for rejection."
            form.add_error('reason_for_rejection', error_message)
            return False
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
            return False

    if received_status == "Accepted":
        if reason_for_rejection:
            error_message = f"Check if this information is correct"
            form.add_error('received_status', error_message)
            form.add_error('reason_for_rejection', error_message)
            return False

        if not date_of_testing:
            error_message = f"Provide Testing date"
            form.add_error('received_status', error_message)
            form.add_error('date_of_testing', error_message)
            return False

        if date_of_testing < date_of_collection:
            error_message = f"Testing date is less than Collection date!"
            form.add_error('date_of_testing', error_message)
            form.add_error('date_of_collection', error_message)
            return False
        if date_of_testing < date_sample_received:
            error_message = f"Testing date is less than Receipt date!"
            form.add_error('date_of_testing', error_message)
            form.add_error('date_sample_received', error_message)
            return False

        # Check date fields
        if date_of_testing > today:
            form.add_error('date_of_testing', "Date of testing cannot be in the future.")
        if date_of_collection > today:
            form.add_error('date_of_collection', "Date of collection cannot be in the future.")
        if date_sample_received > today:
            form.add_error('date_sample_received', "Date of sample received cannot be in the future.")

        if form.errors:
            # If there are any errors, return the form with the error messages
            return False

        if not cd4_count_results:
            error_message = f"Provide CD4 count results"
            form.add_error('received_status', error_message)
            form.add_error('cd4_count_results', error_message)
            return False

        if age > 5 and cd4_percentage:
            error_message = f"CD4 % values ought to be for <=5yrs."
            form.add_error('age', error_message)
            form.add_error('cd4_percentage', error_message)
            return False
        if cd4_count_results <= 200 and not serum_crag_results and not reason_for_no_serum_crag:
            error_message = f"Select a reason why serum CRAG was not done"
            form.add_error('reason_for_no_serum_crag', error_message)
            form.add_error('cd4_count_results', error_message)
            form.add_error('serum_crag_results', error_message)
            return False

        if cd4_count_results > 200 and not serum_crag_results and reason_for_no_serum_crag:
            error_message = f"Check if the information is correct"
            form.add_error('reason_for_no_serum_crag', error_message)
            form.add_error('cd4_count_results', error_message)
            form.add_error('serum_crag_results', error_message)
            return False

        if serum_crag_results and reason_for_no_serum_crag:
            error_message = f"Check if the information is correct"
            form.add_error('reason_for_no_serum_crag', error_message)
            form.add_error('serum_crag_results', error_message)
            return False
    return True


def validate_add_drt_form(form):
    date_of_collection = form.cleaned_data['date_collected']
    date_sample_received = form.cleaned_data['date_received']
    date_of_testing = form.cleaned_data['date_tested']
    date_reported = form.cleaned_data['date_reported']
    date_reviewed = form.cleaned_data['date_reviewed']
    today = timezone.now().date()

    if date_of_collection and date_of_collection > date_reviewed:
        error_message = "Collection date is greater than Review date!"
        form.add_error('date_collected', error_message)
        form.add_error('date_reviewed', error_message)
        return False

    if date_reviewed > today:
        form.add_error('date_reviewed', "Date of DRT review cannot be in the future.")
        return False
    if date_of_collection > today:
        form.add_error('date_collected', "Date of sample collection cannot be in the future.")
        return False

    if date_sample_received > today:
        form.add_error('date_received', "Receive date cannot be in the future.")
        return False
    if date_reported > today:
        form.add_error('date_reported', "Date of DRT reporting cannot be in the future.")
        return False

    if date_sample_received and date_sample_received > date_reviewed:
        error_message = "Received date is greater than Review date!"
        form.add_error('date_received', error_message)
        form.add_error('date_reviewed', error_message)
        return False

    if date_of_testing and date_of_testing > date_reviewed:
        error_message = "Testing date is greater than Review date!"
        form.add_error('date_reviewed', error_message)
        form.add_error('date_tested', error_message)
        return False

    if date_of_collection and date_sample_received and date_of_collection > date_sample_received:
        error_message = "Collection date is greater than Received date!"
        form.add_error('date_received', error_message)
        form.add_error('date_collected', error_message)
        return False
    if date_of_collection and date_reported and date_of_collection > date_reported:
        error_message = "Collection date is greater than Reporting date!"
        form.add_error('date_reported', error_message)
        form.add_error('date_collected', error_message)
        return False
    if date_of_collection and date_of_testing and date_of_collection > date_of_testing:
        error_message = "Collection date is greater than Testing date!"
        form.add_error('date_tested', error_message)
        form.add_error('date_collected', error_message)
        return False

    if date_of_collection > date_sample_received:
        error_message = "Collection date is greater than Receipt date!"
        form.add_error('date_collected', error_message)
        form.add_error('date_received', error_message)
        return False

    if date_sample_received > date_reported:
        error_message = "Receive date is greater than Reporting date!"
        form.add_error('date_reported', error_message)
        form.add_error('date_received', error_message)
        return False
    return True


def get_total_remaining_stocks(df, reagent_type):
    cd4_df = df[df['reagent_type'] == reagent_type]
    cd4_total_remaining = cd4_df.loc[cd4_df['reagent_type'] == reagent_type, 'total_remaining'].values[0]
    return cd4_total_remaining


def show_remaining_commodities(selected_lab):
    time_threshold = timezone.now() - timedelta(days=365)
    commodities = ReagentStock.objects.filter(facility_name__mfl_code=selected_lab.mfl_code,
                                              date_commodity_received__gte=time_threshold
                                              ).order_by("-date_commodity_received")
    # Aggregate remaining quantities by reagent type
    remaining_commodities = commodities.values(
        'reagent_type', 'date_commodity_received'
    ).annotate(total_remaining=Sum('remaining_quantity'))

    # Convert the remaining_commodities queryset to a list of dictionaries
    remaining_commodities_list = list(remaining_commodities)
    df = pd.DataFrame(remaining_commodities_list)
    if df.empty:
        reagent_types = ['Serum CrAg', 'TB LAM', 'CD4']
        total_remaining = [0, 0, 0]

        data = {
            'reagent_type': reagent_types,
            'date_commodity_received': pd.NaT,
            'total_remaining': total_remaining
        }

        df = pd.DataFrame(data)
        naive_timestamp = pd.Timestamp(datetime(1970, 1, 1))  # A neutral date in the past
        df['date_commodity_received'] = pd.to_datetime(naive_timestamp, utc=True)

    # Convert the dates to your local timezone
    local_timezone = tzlocal.get_localzone()

    # Convert the dates to the local timezone
    df['date_commodity_received'] = df['date_commodity_received'].dt.tz_convert(local_timezone)

    # Find the minimum and maximum dates
    min_date = df['date_commodity_received'].min().date()
    max_date = df['date_commodity_received'].max().date()

    # Group by reagent type and sum the total remaining quantities
    df = df.groupby('reagent_type').sum(numeric_only=True)['total_remaining'].reset_index()

    # Remaining stocks
    try:
        cd4_total_remaining = get_total_remaining_stocks(df, 'CD4')
    except IndexError:
        cd4_total_remaining = 0
    try:
        tb_lam_total_remaining = get_total_remaining_stocks(df, 'TB LAM')
    except IndexError:
        tb_lam_total_remaining = 0
    try:
        crag_total_remaining = get_total_remaining_stocks(df, 'Serum CrAg')
    except IndexError:
        crag_total_remaining = 0

    if min_date == pd.Timestamp('1970-01-01'):
        title = f'Remaining commodities per reagent type'
    else:
        title = f'Remaining commodities per reagent type (Received between {min_date} - {max_date})'

    # Create a bar chart using Plotly Express
    fig = px.bar(df, x='reagent_type', y='total_remaining', text='total_remaining',
                 labels={'reagent_type': 'Reagent Type', 'total_remaining': 'Reagents Remaining'},
                 title=title, height=350,
                 )
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
                size=12
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
    commodity_status = plot(fig, include_plotlyjs=False, output_type="div")
    return commodity_status, commodities, cd4_total_remaining, crag_total_remaining, tb_lam_total_remaining


def generate_commodity_error_message(commodity_name):
    return f"{commodity_name} reagents are currently unavailable in the database. " \
           f"Saving {commodity_name} results will not be possible. Please contact your laboratory supervisor for assistance " \
           f"or proceed to add commodities to replenish the stock."


def validate_date_fields(form, date_fields):
    """
    Validate date fields in a form.

    Args:
        form (Form): The form containing the date fields.
        date_fields (list): List of date field names to validate.

    Returns:
        bool: True if all date fields are valid, False otherwise.
    """
    # Loop through each date field for validation
    for field_name in date_fields:
        # Get the date value from the cleaned data
        date_value = form.cleaned_data.get(field_name)
        if date_value:
            # Define the allowable date range
            min_date = date(1900, 1, 1)  # Minimum allowable date
            max_date = date(3100, 12, 31)  # Maximum allowable date
            # Check if the date is within the allowable range
            if not (min_date <= date_value <= max_date):
                # Add an error to the form for invalid date
                form.add_error(field_name, 'Please enter a valid date using datepicker.')

    # Check if any errors were added to the form
    if any(field_name in form.errors for field_name in date_fields):
        return False  # Validation failed
    else:
        return True  # Validation succeeded


def deduct_commodities(request, form, report_type, post, selected_lab, context, template_name):
    if report_type == "Current":
        # Check if CD4 test was performed
        cd4_count_results = form.cleaned_data['cd4_count_results']
        if cd4_count_results is not None:
            post.cd4_reagent_used = True

        # Check if TB LAM test was performed
        tb_lam_results = form.cleaned_data['tb_lam_results']
        if tb_lam_results is not None:
            post.tb_lam_reagent_used = True

        # Check if serum CRAG test was performed
        serum_crag_results = form.cleaned_data['serum_crag_results']
        if serum_crag_results is not None:
            post.serum_crag_reagent_used = True

        # Update reagent usage
        if post.cd4_reagent_used:
            if ReagentStock.objects.filter(reagent_type='CD4',
                                           facility_name__mfl_code=selected_lab.mfl_code,
                                           remaining_quantity__gt=0).exists():
                cd4_reagent_stock = ReagentStock.objects.filter(reagent_type='CD4',
                                                                facility_name__mfl_code=selected_lab.mfl_code,
                                                                remaining_quantity__gt=0).order_by(
                    'date_commodity_received').first()
                cd4_reagent_stock.quantity_used += 1
                cd4_reagent_stock.save()
            else:
                error_message = "CD4 reagents are out of stock!"
                messages.error(request, error_message)
                form.add_error('cd4_count_results', error_message)
                return render(request, template_name, context)
        if post.serum_crag_reagent_used:
            if ReagentStock.objects.filter(reagent_type='Serum CrAg',
                                           facility_name__mfl_code=selected_lab.mfl_code,
                                           remaining_quantity__gt=0).exists():
                serum_crag_reagent_stock = ReagentStock.objects.filter(reagent_type='Serum CrAg',
                                                                       facility_name__mfl_code=selected_lab.mfl_code,
                                                                       remaining_quantity__gt=0).order_by(
                    'date_commodity_received').first()
                serum_crag_reagent_stock.quantity_used += 1
                serum_crag_reagent_stock.save()
            else:
                error_message = "Serum CrAg reagents are out of stock!"
                messages.error(request, error_message)
                form.add_error('serum_crag_results', error_message)
                return render(request, template_name, context)
        if post.tb_lam_reagent_used:
            if ReagentStock.objects.filter(reagent_type='TB LAM',
                                           facility_name__mfl_code=selected_lab.mfl_code,
                                           remaining_quantity__gt=0).exists():
                tb_lam_reagent_stock = ReagentStock.objects.filter(reagent_type='TB LAM',
                                                                   facility_name__mfl_code=selected_lab.mfl_code,
                                                                   remaining_quantity__gt=0).order_by(
                    'date_commodity_received').first()
                tb_lam_reagent_stock.quantity_used += 1
                tb_lam_reagent_stock.save()
            else:
                error_message = "LF-TB LAM reagents are out of stock!"
                messages.error(request, error_message)
                form.add_error('tb_lam_results', error_message)
                return render(request, template_name, context)


def handle_commodity_errors(request, form, crag_total_remaining, tb_lam_total_remaining, template_name, context):
    serum_crag_results = form.cleaned_data.get('serum_crag_results')
    tb_lam_results = form.cleaned_data.get('tb_lam_results')

    if serum_crag_results is not None and crag_total_remaining == 0:
        error_message = "ScrAg reagents are out of stock."
        form.add_error('serum_crag_results', error_message)
        return render(request, template_name, context)

    if tb_lam_results is not None and tb_lam_total_remaining == 0:
        error_message = "LF TB LAM reagents are out of stock."
        form.add_error('tb_lam_results', error_message)
        return render(request, template_name, context)

    return None


@login_required(login_url='login')
@group_required(['laboratory_staffs_labpulse'])
def add_cd4_count(request, report_type, pk_lab):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    selected_lab, created = Cd4TestingLabs.objects.get_or_create(id=pk_lab)
    template_name = 'lab_pulse/add_cd4_data.html'

    use_commodities = False
    enable_commodities = EnableDisableCommodities.objects.first()
    if enable_commodities and enable_commodities.use_commodities:
        use_commodities = True

    if report_type == "Current":
        form = Cd4trakerForm(request.POST or None)
        commodity_status, commodities, cd4_total_remaining, crag_total_remaining, tb_lam_total_remaining = \
            show_remaining_commodities(selected_lab)
        context = {
            "form": form, "report_type": report_type, "commodities": commodities, "use_commodities": use_commodities,
            "title": f"Add CD4 Results for {selected_lab.testing_lab_name.title()} (Testing Laboratory)",
            "commodity_status": commodity_status,
            "cd4_total_remaining": cd4_total_remaining, "tb_lam_total_remaining": tb_lam_total_remaining,
            "crag_total_remaining": crag_total_remaining,
        }
        if use_commodities:
            if crag_total_remaining == 0:
                messages.error(request, generate_commodity_error_message("Serum CrAg"))
            if tb_lam_total_remaining == 0:
                messages.error(request, generate_commodity_error_message("LF TB LAM"))
            if cd4_total_remaining == 0:
                messages.error(request, generate_commodity_error_message("CD4"))
                return render(request, template_name, context)
    else:
        crag_total_remaining = None
        tb_lam_total_remaining = None
        # Check if the user has the required permission
        if not request.user.has_perm('labpulse.view_add_retrospective_cd4_count'):
            # Redirect or handle the case where the user doesn't have the permission
            return HttpResponseForbidden("You don't have permission to access this form.")
        form = Cd4trakerManualDispatchForm(request.POST or None)
        context = {
            "form": form, "report_type": report_type, "use_commodities": use_commodities,
            "title": f"Add CD4 Results for {selected_lab.testing_lab_name.title()} (Testing Laboratory)",
        }

    if request.method == "POST":
        if form.is_valid():
            post = form.save(commit=False)
            #################
            # Validate date
            #################
            date_fields_to_validate = ['date_of_collection', 'date_of_testing', 'date_sample_received']
            if not validate_date_fields(form, date_fields_to_validate):
                # Render the template with the form and errors
                return render(request, template_name, context)
            if not validate_cd4_count_form(form, report_type):
                # If validation fails, return the form with error messages
                return render(request, template_name, context)
            if report_type == "Current" and use_commodities:
                # Call the function to handle serum_crag_results and tb_lam_results errors
                error_response = handle_commodity_errors(request, form, crag_total_remaining, tb_lam_total_remaining,
                                                         template_name, context)
                if error_response:
                    return error_response  # Render with errors if any
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
            post.report_type = report_type
            ####################################
            # Deduct Commodities used
            ####################################
            if use_commodities:
                deduct_commodities(request, form, report_type, post, selected_lab, context, template_name)

            post.save()
            messages.error(request, "Record saved successfully!")
            # Generate the URL for the redirect
            url = reverse('add_cd4_count', kwargs={'report_type': report_type, 'pk_lab': pk_lab})
            return redirect(url)
        else:
            messages.error(request, f"Record already exists.")
            render(request, template_name, context)
    return render(request, template_name, context)


def update_commodities(request, form, post, report_type, pk, template_name, context):
    if report_type == "Current":
        ###################################################
        # Choose facility to update commodity records for #
        ###################################################
        item = Cd4traker.objects.get(id=pk)
        # DEDUCT FROM TESTING LABS
        facility_mfl_code_to_update = None
        if item.facility_name.mfl_code == item.testing_laboratory.mfl_code:
            # if request.user.groups.filter('laboratory_staffs_labpulse').exists():
            facility_mfl_code_to_update = item.testing_laboratory.mfl_code
        elif item.facility_name.mfl_code != item.testing_laboratory.mfl_code:
            if item.serum_crag_results != post.serum_crag_results:
                facility_mfl_code_to_update = item.testing_laboratory.mfl_code
            if item.tb_lam_results != post.tb_lam_results:
                if request.user.groups.filter(name='laboratory_staffs_labpulse').exists():
                    facility_mfl_code_to_update = item.testing_laboratory.mfl_code
                # DEDUCT FROM REFERRING LABS
                elif request.user.groups.filter(name='referring_laboratory_staffs_labpulse').exists():
                    facility_mfl_code_to_update = item.facility_name.mfl_code

        # Check for changes in reagent fields and update reagent usage flags

        # if not item.cd4_reagent_used:
        if post.cd4_count_results != item.cd4_count_results and item.cd4_reagent_used == False:
            post.cd4_reagent_used = True
        else:
            post.cd4_reagent_used = item.cd4_reagent_used

        # if not item.tb_lam_reagent_used:
        if post.tb_lam_results != item.tb_lam_results and item.tb_lam_reagent_used == False:
            post.tb_lam_reagent_used = True
        else:
            post.tb_lam_reagent_used = item.tb_lam_reagent_used

        # if not item.serum_crag_reagent_used:
        if post.serum_crag_results != item.serum_crag_results and item.serum_crag_reagent_used == False:
            post.serum_crag_reagent_used = True
        else:
            post.serum_crag_reagent_used = item.serum_crag_reagent_used

        # Update reagent usage flags
        # Check if any reagent type has been used and not tracked before

        if item.cd4_reagent_used != post.cd4_reagent_used:
            if ReagentStock.objects.filter(reagent_type='CD4',
                                           facility_name__mfl_code=facility_mfl_code_to_update).exists():
                cd4_reagent_stock = ReagentStock.objects.filter(reagent_type='CD4',
                                                                facility_name__mfl_code=facility_mfl_code_to_update,
                                                                remaining_quantity__gt=0
                                                                ).order_by('date_commodity_received').first()
                cd4_reagent_stock.quantity_used += 1
                cd4_reagent_stock.save()
            else:
                messages.error(request,
                               "CD4 reagents are currently unavailable. The operation cannot be completed. "
                               "Please contact your laboratory supervisor for assistance or proceed to add "
                               "commodities to replenish the stock.")
                error_message = "CD4 reagents are out of stock!"
                # messages.error(request, error_message)
                form.add_error('cd4_count_results', error_message)
                return render(request, template_name, context)
        if item.serum_crag_reagent_used != post.serum_crag_reagent_used:
            if ReagentStock.objects.filter(reagent_type='Serum CrAg',
                                           facility_name__mfl_code=facility_mfl_code_to_update,
                                           remaining_quantity__gt=0
                                           ).exists():
                serum_crag_reagent_stock = ReagentStock.objects.filter(reagent_type='Serum CrAg',
                                                                       facility_name__mfl_code=facility_mfl_code_to_update,
                                                                       remaining_quantity__gt=0
                                                                       ).order_by(
                    'date_commodity_received').first()
                serum_crag_reagent_stock.quantity_used += 1
                serum_crag_reagent_stock.save()
            else:
                messages.error(request,
                               "Serum CrAg reagents are currently unavailable. The operation cannot be "
                               "completed. Please contact your laboratory supervisor for assistance or proceed"
                               " to add commodities to replenish the stock.")
                error_message = "Serum CrAg reagents are out of stock!"
                # messages.error(request, error_message)
                form.add_error('serum_crag_results', error_message)
                return render(request, template_name, context)
        if item.tb_lam_reagent_used != post.tb_lam_reagent_used:
            if ReagentStock.objects.filter(reagent_type='TB LAM',
                                           facility_name__mfl_code=facility_mfl_code_to_update).exists():
                tb_lam_reagent_stock = ReagentStock.objects.filter(reagent_type='TB LAM',
                                                                   facility_name__mfl_code=facility_mfl_code_to_update,
                                                                   remaining_quantity__gt=0
                                                                   ).order_by('date_commodity_received').first()
                tb_lam_reagent_stock.quantity_used += 1
                tb_lam_reagent_stock.save()
            else:
                messages.error(request,
                               "LF TB LAM reagents are currently unavailable. The operation cannot be completed. "
                               "Please contact your laboratory supervisor for assistance or proceed to add "
                               "commodities to replenish the stock.")
                error_message = "LF TB LAM reagents are out of stock!"
                # messages.error(request, error_message)
                form.add_error('tb_lam_results', error_message)
                return render(request, template_name, context)


@login_required(login_url='login')
@group_required(['laboratory_staffs_labpulse', 'referring_laboratory_staffs_labpulse'])
def update_cd4_results(request, report_type, pk):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    item = Cd4traker.objects.get(id=pk)
    if report_type == "Current":
        commodity_status, commodities, cd4_total_remaining, crag_total_remaining, tb_lam_total_remaining = \
            show_remaining_commodities(item.facility_name)
    else:
        commodity_status = None
        # commodities = None
        cd4_total_remaining = 0
        crag_total_remaining = 0
        tb_lam_total_remaining = 0

    # Fetch the first instance of EnableDisableCommodities
    enable_commodities = EnableDisableCommodities.objects.first()
    # Check if commodities should be enabled or disabled
    if enable_commodities and enable_commodities.use_commodities:
        use_commodities = True
    else:
        use_commodities = False
    template_name = 'lab_pulse/update results.html'
    if request.method == "POST":
        if report_type == "Current":
            form = Cd4trakerForm(request.POST, instance=item, user=request.user)
        else:
            # Check if the user has the required permission
            if not request.user.has_perm('labpulse.view_add_retrospective_cd4_count'):
                # Redirect or handle the case where the user doesn't have the permission
                return HttpResponseForbidden("You don't have permission to access this form.")
            form = Cd4trakerManualDispatchForm(request.POST, instance=item)
        if form.is_valid():
            context = {
                "form": form, "report_type": report_type, "use_commodities": use_commodities,
                "title": "Update Results", "commodity_status": commodity_status,
                "cd4_total_remaining": cd4_total_remaining, "tb_lam_total_remaining": tb_lam_total_remaining,
                "crag_total_remaining": crag_total_remaining,
            }
            # template_name = 'lab_pulse/add_cd4_data.html'
            post = form.save(commit=False)
            #################
            # Validate date
            #################
            date_fields_to_validate = ['date_of_collection', 'date_of_testing', 'date_sample_received']
            if not validate_date_fields(form, date_fields_to_validate):
                # Render the template with the form and errors
                return render(request, template_name, context)
            facility_name = form.cleaned_data['facility_name']
            if not validate_cd4_count_form(form, report_type):
                # If validation fails, return the form with error messages
                return render(request, template_name, context)
            if report_type == "Current" and use_commodities:
                # Call the function to handle serum_crag_results and tb_lam_results errors
                error_response = handle_commodity_errors(request, form, crag_total_remaining, tb_lam_total_remaining,
                                                         template_name, context)
                if error_response:
                    return error_response  # Render with errors if any

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
            #############################
            # Update Commodities used
            #############################
            if use_commodities:
                # update_commodities(request, form, report_type,post, pk, template_name, context)
                if report_type == "Current":
                    ###################################################
                    # Choose facility to update commodity records for #
                    ###################################################
                    item = Cd4traker.objects.get(id=pk)
                    # DEDUCT FROM TESTING LABS
                    facility_mfl_code_to_update = None
                    if item.facility_name.mfl_code == item.testing_laboratory.mfl_code:
                        # if request.user.groups.filter('laboratory_staffs_labpulse').exists():
                        facility_mfl_code_to_update = item.testing_laboratory.mfl_code
                    elif item.facility_name.mfl_code != item.testing_laboratory.mfl_code:
                        if item.serum_crag_results != post.serum_crag_results:
                            facility_mfl_code_to_update = item.testing_laboratory.mfl_code
                        if item.tb_lam_results != post.tb_lam_results:
                            if request.user.groups.filter(name='laboratory_staffs_labpulse').exists():
                                facility_mfl_code_to_update = item.testing_laboratory.mfl_code
                            # DEDUCT FROM REFERRING LABS
                            elif request.user.groups.filter(name='referring_laboratory_staffs_labpulse').exists():
                                facility_mfl_code_to_update = item.facility_name.mfl_code

                    # Check for changes in reagent fields and update reagent usage flags

                    # if not item.cd4_reagent_used:
                    if post.cd4_count_results != item.cd4_count_results and item.cd4_reagent_used == False:
                        post.cd4_reagent_used = True
                    else:
                        post.cd4_reagent_used = item.cd4_reagent_used

                    # if not item.tb_lam_reagent_used:
                    if post.tb_lam_results != item.tb_lam_results and item.tb_lam_reagent_used == False:
                        post.tb_lam_reagent_used = True
                    else:
                        post.tb_lam_reagent_used = item.tb_lam_reagent_used

                    # if not item.serum_crag_reagent_used:
                    if post.serum_crag_results != item.serum_crag_results and item.serum_crag_reagent_used == False:
                        post.serum_crag_reagent_used = True
                    else:
                        post.serum_crag_reagent_used = item.serum_crag_reagent_used

                    # Update reagent usage flags
                    # Check if any reagent type has been used and not tracked before

                    if item.cd4_reagent_used != post.cd4_reagent_used:
                        if ReagentStock.objects.filter(reagent_type='CD4',
                                                       facility_name__mfl_code=facility_mfl_code_to_update).exists():
                            cd4_reagent_stock = ReagentStock.objects.filter(reagent_type='CD4',
                                                                            facility_name__mfl_code=facility_mfl_code_to_update,
                                                                            remaining_quantity__gt=0
                                                                            ).order_by(
                                'date_commodity_received').first()
                            cd4_reagent_stock.quantity_used += 1
                            cd4_reagent_stock.save()
                        else:
                            messages.error(request,
                                           "CD4 reagents are currently unavailable. The operation cannot be completed. "
                                           "Please contact your laboratory supervisor for assistance or proceed to add "
                                           "commodities to replenish the stock.")
                            error_message = "CD4 reagents are out of stock!"
                            # messages.error(request, error_message)
                            form.add_error('cd4_count_results', error_message)
                            return render(request, template_name, context)
                    if item.serum_crag_reagent_used != post.serum_crag_reagent_used:
                        if ReagentStock.objects.filter(reagent_type='Serum CrAg',
                                                       facility_name__mfl_code=facility_mfl_code_to_update,
                                                       remaining_quantity__gt=0
                                                       ).exists():
                            serum_crag_reagent_stock = ReagentStock.objects.filter(reagent_type='Serum CrAg',
                                                                                   facility_name__mfl_code=facility_mfl_code_to_update,
                                                                                   remaining_quantity__gt=0
                                                                                   ).order_by(
                                'date_commodity_received').first()
                            serum_crag_reagent_stock.quantity_used += 1
                            serum_crag_reagent_stock.save()
                        else:
                            messages.error(request,
                                           "Serum CrAg reagents are currently unavailable. The operation cannot be "
                                           "completed. Please contact your laboratory supervisor for assistance or proceed"
                                           " to add commodities to replenish the stock.")
                            error_message = "Serum CrAg reagents are out of stock!"
                            # messages.error(request, error_message)
                            form.add_error('serum_crag_results', error_message)
                            return render(request, template_name, context)
                    if item.tb_lam_reagent_used != post.tb_lam_reagent_used:
                        if ReagentStock.objects.filter(reagent_type='TB LAM',
                                                       facility_name__mfl_code=facility_mfl_code_to_update).exists():
                            tb_lam_reagent_stock = ReagentStock.objects.filter(reagent_type='TB LAM',
                                                                               facility_name__mfl_code=facility_mfl_code_to_update,
                                                                               remaining_quantity__gt=0
                                                                               ).order_by(
                                'date_commodity_received').first()
                            tb_lam_reagent_stock.quantity_used += 1
                            tb_lam_reagent_stock.save()
                        else:
                            messages.error(request,
                                           "LF TB LAM reagents are currently unavailable. The operation cannot be completed. "
                                           "Please contact your laboratory supervisor for assistance or proceed to add "
                                           "commodities to replenish the stock.")
                            error_message = "LF TB LAM reagents are out of stock!"
                            # messages.error(request, error_message)
                            form.add_error('tb_lam_results', error_message)
                            return render(request, template_name, context)
            post.save()
            messages.error(request, "Record updated successfully!")
            return HttpResponseRedirect(request.session['page_from'])
    else:
        if report_type == "Current":
            form = Cd4trakerForm(instance=item, user=request.user)
        else:
            # Check if the user has the required permission
            if not request.user.has_perm('labpulse.view_add_retrospective_cd4_count'):
                # Redirect or handle the case where the user doesn't have the permission
                return HttpResponseForbidden("You don't have permission to access this form.")
            form = Cd4trakerManualDispatchForm(instance=item)
    # cd4_total_remaining=0
    context = {
        "form": form, "report_type": report_type, "use_commodities": use_commodities,
        "title": "Update Results", "commodity_status": commodity_status, "cd4_total_remaining": cd4_total_remaining,
        "tb_lam_total_remaining": tb_lam_total_remaining,
        "crag_total_remaining": crag_total_remaining,
    }
    return render(request, 'lab_pulse/update results.html', context)


def pagination_(request, item_list, record_count=None):
    page = request.GET.get('page', 1)
    if record_count is None:
        record_count = request.GET.get('record_count', '5')
    else:
        record_count = record_count

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


def calculate_positivity_rate(df, column_name, title):
    # Filter the DataFrame for rows with valid results
    filtered_df = df[df[column_name].notna()]

    # Calculate the number of tests done
    num_tests_done = len(filtered_df)

    # Calculate the number_of_samples positive
    num_samples_positive = (filtered_df[column_name] == 'Positive').sum()
    num_samples_negative = (filtered_df[column_name] == 'Negative').sum()

    # Calculate the positivity rate
    try:
        positivity_rate = round(num_samples_positive / num_tests_done * 100, 1)
    except ZeroDivisionError:
        positivity_rate = 0

    # Create the new DataFrame
    positivity_df = pd.DataFrame({
        f'Number of {title} Tests Done': [num_tests_done],
        'number_of_samples Positive': [num_samples_positive],
        'number_of_samples Negative': [num_samples_negative],
        f'{title} Positivity (%)': [positivity_rate]
    })
    positivity_df = positivity_df.T.reset_index().fillna(0)
    positivity_df.columns = ['variables', 'values']
    positivity_df = positivity_df[positivity_df['values'] != 0]
    fig = bar_chart(positivity_df, "variables", "values", f"{title} Testing Results", color='variables')

    return fig, positivity_df


def line_chart_median_mean(df, x_axis, y_axis, title, color=None, xaxis_title=None, yaxis_title=None, time=52,
                           background_shadow=False,use_one_year_data=True):
    df = df.copy()
    if use_one_year_data:
        df = df.tail(time)
    mean_sample_tested = sum(df[y_axis]) / len(df[y_axis])
    median_sample_tested = df[y_axis].median()

    fig = px.line(df, x=x_axis, y=y_axis, text=y_axis, color=color,
                  height=450,
                  title=title)
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)
    if yaxis_title is None:
        yaxis_title = y_axis
    else:
        yaxis_title = yaxis_title
    fig.update_layout(
        xaxis_title=f"{xaxis_title}",
        yaxis_title=f"{yaxis_title}",
        legend_title=f"{xaxis_title}",
    )
    if not background_shadow:
        fig.update_layout({
            'plot_bgcolor': 'rgba(0, 0, 0, 0)',
            'paper_bgcolor': 'rgba(0, 0, 0, 0)',
        })
    fig.update_traces(textposition='top center')
    if 'TAT type' not in df.columns:
        fig.add_shape(type='line', x0=df[x_axis].iloc[0], y0=mean_sample_tested,
                      x1=df[x_axis].iloc[-1],
                      y1=mean_sample_tested,
                      line=dict(color='red', width=2, dash='dot'))

        fig.add_annotation(x=df[x_axis].iloc[-1], y=mean_sample_tested,
                           text=f"Mean {mean_sample_tested:.0f}",
                           showarrow=True, arrowhead=1,
                           font=dict(size=8, color='red'))

        fig.add_shape(type='line', x0=df[x_axis].iloc[0], y0=median_sample_tested,
                      x1=df[x_axis].iloc[-1],
                      y1=median_sample_tested,
                      line=dict(color='black', width=2, dash='dot'))

        fig.add_annotation(x=df[x_axis].iloc[0], y=median_sample_tested,
                           text=f"Median {median_sample_tested:.0f}",
                           showarrow=True, arrowhead=1,
                           font=dict(size=8, color='black'))
    else:
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
    return plot(fig, include_plotlyjs=False, output_type="div")


def create_summary_chart(data, column_name, title):
    unique_values = data[column_name].unique()
    unique_values = unique_values[~pd.isnull(unique_values)]

    summary_df = pd.DataFrame({
        column_name: unique_values,
        'Count': [(data[column_name] == value).sum() for value in unique_values]
    }).sort_values('Count')

    total = summary_df['Count'].sum()
    fig = bar_chart(summary_df, column_name, 'Count', f"{title} N={total}")

    return fig, summary_df


def calculate_weekly_tat(df):
    """
    Calculate weekly mean Turnaround Time (TAT) for different types and reshape the data.

    Parameters:
        df (DataFrame): Input DataFrame containing relevant columns.

    Returns:
        DataFrame: Reshaped DataFrame with weekly mean TAT values.
    """
    # Convert date columns to datetime
    date_cols = ['Date Dispatch', 'Collection Date', 'Received date']
    df[date_cols] = df[date_cols].transform(pd.to_datetime)

    # Calculate TAT values in days
    df['sample TAT (c-d)'] = (df['Date Dispatch'] - df['Collection Date']).dt.days
    df['sample TAT (c-r)'] = (df['Received date'] - df['Collection Date']).dt.days

    # Group by week_start and calculate mean TAT
    df['week_start'] = df['Collection Date'].dt.to_period('W').dt.start_time
    weekly_tat_df = df.groupby('week_start').mean(numeric_only=True)[
        ['sample TAT (c-d)', 'sample TAT (c-r)']].reset_index()
    weekly_tat_df['Mean weekly TAT(C-D)'] = weekly_tat_df['sample TAT (c-d)'].round()
    weekly_tat_df['Mean weekly TAT(C-R)'] = weekly_tat_df['sample TAT (c-r)'].round()

    # Calculate means
    mean_c_d = round(weekly_tat_df.loc[:, 'Mean weekly TAT(C-D)'].mean())
    mean_c_r = round(weekly_tat_df.loc[:, 'Mean weekly TAT(C-R)'].mean())

    # Drop unnecessary columns
    weekly_tat_df.drop(columns=['sample TAT (c-d)', 'sample TAT (c-r)'], inplace=True)
    weekly_tat_df = weekly_tat_df.sort_values("week_start").fillna(0)
    weekly_tat_df = weekly_tat_df.tail(104)
    weekly_tat_df['Weekly Trend'] = weekly_tat_df["week_start"].astype(str) + "."

    # Reshape the DataFrame using melt
    weekly_tat = pd.melt(
        weekly_tat_df,
        id_vars=['Weekly Trend'],
        value_vars=['Mean weekly TAT(C-R)', 'Mean weekly TAT(C-D)'],
        var_name="TAT type",
        value_name="Weekly mean TAT"
    )
    weekly_tat.reset_index(drop=True, inplace=True)

    # Convert the "Weekly Trend" column to datetime objects
    weekly_tat.loc[:, 'Weekly Trend'] = pd.to_datetime(weekly_tat['Weekly Trend'], format='%Y-%m-%d.')

    # Sort the DataFrame by the "Weekly Trend" column
    weekly_tat.sort_values(by='Weekly Trend', inplace=True)

    # Convert the "Weekly Trend" column back to string for plotting (if needed)
    weekly_tat['Weekly Trend'] = weekly_tat['Weekly Trend'].dt.strftime('%Y-%m-%d.')

    return weekly_tat, mean_c_r, mean_c_d


def visualize_facility_results_positivity(df, test_type, title):
    if df.shape[0] > 50:
        df_copy = df.head(50)
        title = f"Top Fifty Facilities with Positive {title} Results. Total facilities {df.shape[0]}"
    else:
        df_copy = df.copy()
        title = f"Number of Positive {title} Results by Facility. Total facilities {df.shape[0]}"

    fig = bar_chart(df_copy, "Facilities",
                    f"Number of Positive {test_type}",
                    title)
    return fig


def filter_result_type(list_of_projects_fac, column_name):
    rename_column_name = column_name.split(" ")[0] + " " + column_name.split(" ")[1].upper()
    # Filter the DataFrame for rows where Serum Crag is positive
    positive_crag_df = list_of_projects_fac[list_of_projects_fac[column_name] == 'Positive']

    # Group by Facility and count the number of positive serum CRAG results
    facility_positive_count = positive_crag_df.groupby('Facility')[column_name].count().reset_index().fillna(0)

    # rename column
    column_name = f'Number of Positive {rename_column_name}'

    # Rename the column for clarity
    facility_positive_count.columns = ['Facilities', column_name]
    facility_positive_count = facility_positive_count.sort_values(column_name, ascending=False)
    facility_positive_count = facility_positive_count[facility_positive_count[column_name] != 0]
    return facility_positive_count


# @silk_profile(name='generate_results_df')
# def generate_results_df(list_of_projects):
#     # convert data from database to a dataframe
#     list_of_projects = pd.DataFrame(list_of_projects)
#     # Define a dictionary to rename columns
#     cols_rename = {
#         "county__county_name": "County", "sub_county__sub_counties": "Sub-county",
#         "testing_laboratory__testing_lab_name": "Testing Laboratory", "facility_name__name": "Facility",
#         "facility_name__mfl_code": "MFL CODE", "patient_unique_no": "CCC NO.", "age": "Age", "sex": "Sex",
#         "date_of_collection": "Collection Date", "date_of_testing": "Testing date",
#         "date_sample_received": "Received date",
#         "date_dispatched": "Date Dispatch",
#         "justification": "Justification", "cd4_count_results": "CD4 Count",
#         "date_serum_crag_results_entered": "Serum CRAG date",
#         "serum_crag_results": "Serum Crag", "date_tb_lam_results_entered": "TB LAM date",
#         "tb_lam_results": "TB LAM", "received_status": "Received status",
#         "reason_for_rejection": "Rejection reason",
#         "tat_days": "TAT", "age_unit": "age_unit",
#     }
#     list_of_projects = list_of_projects.rename(columns=cols_rename)
#     list_of_projects_fac = list_of_projects.copy()
#
#     # Convert Timestamp objects to strings
#     list_of_projects_fac = list_of_projects_fac.sort_values('Collection Date').reset_index(drop=True)
#     # convert to datetime with UTC
#     date_columns = ['Testing date', 'Collection Date', 'Received date', 'Date Dispatch']
#     list_of_projects_fac[date_columns] = list_of_projects_fac[date_columns].astype("datetime64[ns, UTC]")
#     # Convert the dates to user local timezone
#     local_timezone = tzlocal.get_localzone()
#     # Convert the dates to the local timezone
#     list_of_projects_fac['Collection Date'] = list_of_projects_fac['Collection Date'].dt.tz_convert(
#         local_timezone)
#     list_of_projects_fac['Received date'] = list_of_projects_fac['Received date'].dt.tz_convert(
#         local_timezone)
#     list_of_projects_fac['Date Dispatch'] = list_of_projects_fac['Date Dispatch'].dt.tz_convert(
#         local_timezone)
#     list_of_projects_fac['Testing date'] = list_of_projects_fac['Testing date'].dt.tz_convert(
#         local_timezone)
#     list_of_projects_fac['Testing date'] = pd.to_datetime(list_of_projects_fac['Testing date']).dt.date
#     list_of_projects_fac['Received date'] = pd.to_datetime(list_of_projects_fac['Received date']).dt.date
#     list_of_projects_fac['Collection Date'] = pd.to_datetime(list_of_projects_fac['Collection Date']).dt.date
#     list_of_projects_fac['Date Dispatch'] = pd.to_datetime(list_of_projects_fac['Date Dispatch']).dt.date
#     list_of_projects_fac['TB LAM date'] = pd.to_datetime(list_of_projects_fac['TB LAM date']).dt.date
#     list_of_projects_fac['Serum CRAG date'] = pd.to_datetime(list_of_projects_fac['Serum CRAG date']).dt.date
#     list_of_projects_fac['Collection Date'] = list_of_projects_fac['Collection Date'].astype(str)
#     list_of_projects_fac['Testing date'] = list_of_projects_fac['Testing date'].replace(np.datetime64('NaT'),
#                                                                                         '')
#     list_of_projects_fac['Testing date'] = list_of_projects_fac['Testing date'].astype(str)
#     list_of_projects_fac['Received date'] = list_of_projects_fac['Received date'].replace(np.datetime64('NaT'),
#                                                                                           '')
#     list_of_projects_fac['Received date'] = list_of_projects_fac['Received date'].astype(str)
#     list_of_projects_fac['Date Dispatch'] = list_of_projects_fac['Date Dispatch'].astype(str)
#     list_of_projects_fac['TB LAM date'] = list_of_projects_fac['TB LAM date'].replace(np.datetime64('NaT'), '')
#     list_of_projects_fac['TB LAM date'] = list_of_projects_fac['TB LAM date'].astype(str)
#     list_of_projects_fac['Serum CRAG date'] = list_of_projects_fac['Serum CRAG date'].replace(
#         np.datetime64('NaT'),
#         '')
#     list_of_projects_fac['Serum CRAG date'] = list_of_projects_fac['Serum CRAG date'].astype(str)
#     list_of_projects_fac.index = range(1, len(list_of_projects_fac) + 1)
#     max_date = list_of_projects_fac['Collection Date'].max()
#     min_date = list_of_projects_fac['Collection Date'].min()
#     missing_df = list_of_projects_fac.loc[
#         (list_of_projects_fac['CD4 Count'] < 200) & (list_of_projects_fac['Serum Crag'].isna())]
#     missing_tb_lam_df = list_of_projects_fac.loc[
#         (list_of_projects_fac['CD4 Count'] < 200) & (list_of_projects_fac['TB LAM'].isna())]
#     crag_pos_df = list_of_projects_fac.loc[(list_of_projects_fac['Serum Crag'] == "Positive")]
#     tb_lam_pos_df = list_of_projects_fac.loc[(list_of_projects_fac['TB LAM'] == "Positive")]
#     rejected_df = list_of_projects_fac.loc[(list_of_projects_fac['Received status'] == "Rejected")]
#
#     # Create the summary dataframe
#     summary_df = pd.DataFrame({
#         'Total CD4': [list_of_projects_fac.shape[0]],
#         'Rejected': [(list_of_projects_fac['Received status'] == 'Rejected').sum()],
#         'CD4 >200': [(list_of_projects_fac['CD4 Count'] > 200).sum()],
#         'CD4 <= 200': [(list_of_projects_fac['CD4 Count'] <= 200).sum()],
#         'TB-LAM': [list_of_projects_fac['TB LAM'].notna().sum()],
#         '-ve TB-LAM': [(list_of_projects_fac['TB LAM'] == 'Negative').sum()],
#         '+ve TB-LAM': [(list_of_projects_fac['TB LAM'] == 'Positive').sum()],
#         'Missing TB LAM': [
#             (list_of_projects_fac.loc[list_of_projects_fac['CD4 Count'] < 200, 'TB LAM'].isna()).sum()],
#         'CRAG': [list_of_projects_fac['Serum Crag'].notna().sum()],
#         '-ve CRAG': [(list_of_projects_fac['Serum Crag'] == 'Negative').sum()],
#         '+ve CRAG': [(list_of_projects_fac['Serum Crag'] == 'Positive').sum()],
#         'Missing CRAG': [
#             (list_of_projects_fac.loc[list_of_projects_fac['CD4 Count'] < 200, 'Serum Crag'].isna()).sum()],
#     })
#
#     # Display the summary dataframe
#     summary_df = summary_df.T.reset_index()
#     summary_df.columns = ['variables', 'values']
#     summary_df = summary_df[summary_df['values'] != 0]
#     ###################################
#     # CD4 SUMMARY CHART
#     ###################################
#     cd4_summary_fig = bar_chart(summary_df, "variables", "values",
#                                 f"Summary of CD4 Records and Serum CrAg Results Between {min_date} and {max_date} ")
#
#     # Group the data by testing laboratory and calculate the counts
#     summary_df = list_of_projects_fac.groupby('Testing Laboratory').agg({
#         'CD4 Count': 'count',
#         'Serum Crag': lambda x: x.count() if x.notnull().any() else 0
#     }).reset_index()
#
#     # Rename the columns
#     summary_df.rename(columns={'CD4 Count': 'Total CD4 Count', 'Serum Crag': 'Total CRAG Reports'},
#                       inplace=True)
#
#     # Sort the dataframe by testing laboratory name
#     summary_df.sort_values('Testing Laboratory', inplace=True)
#
#     # Reset the index
#     summary_df.reset_index(drop=True, inplace=True)
#
#     summary_df = pd.melt(summary_df, id_vars="Testing Laboratory",
#                          value_vars=['Total CD4 Count', 'Total CRAG Reports'],
#                          var_name="Test done", value_name='values')
#     show_cd4_testing_workload = False
#     show_crag_testing_workload = False
#     cd4_df = summary_df[summary_df['Test done'] == "Total CD4 Count"].sort_values("values").fillna(0)
#     cd4_df = cd4_df[cd4_df['values'] != 0]
#     if not cd4_df.empty:
#         show_cd4_testing_workload = True
#     crag_df = summary_df[summary_df['Test done'] == "Total CRAG Reports"].sort_values("values").fillna(0)
#     crag_df = crag_df[crag_df['values'] != 0]
#     if not crag_df.empty:
#         show_crag_testing_workload = True
#     ###################################
#     # CRAG TESTING SUMMARY CHART
#     ###################################
#     crag_testing_lab_fig = bar_chart(crag_df, "Testing Laboratory", "values",
#                                      f"Number of sCrAg Reports Processed per Testing Laboratory ({crag_df.shape[0]}).")
#     ###################################
#     # CD4 TESTING SUMMARY CHART
#     ###################################
#     cd4_testing_lab_fig = bar_chart(cd4_df, "Testing Laboratory", "values",
#                                     f"Number of CD4 Reports Processed per Testing Laboratory ({cd4_df.shape[0]})")
#
#     age_bins = [0, 1, 4, 9, 14, 19, 24, 29, 34, 39, 44, 49, 54, 59, 64, 150]
#     age_labels = ['<1', '1-4.', '5-9', '10-14.', '15-19', '20-24', '25-29', '30-34', '35-39', '40-44', '45-49',
#                   '50-54', '55-59', '60-64', '65+']
#
#     list_of_projects_fac_above1age_sex = list_of_projects_fac[list_of_projects_fac['age_unit'] == "years"]
#     list_of_projects_fac_below1age_sex = list_of_projects_fac[list_of_projects_fac['age_unit'] != "years"]
#
#     list_of_projects_fac_below1age_sex['Age Group'] = "<1"
#     list_of_projects_fac_above1age_sex['Age Group'] = pd.cut(list_of_projects_fac_above1age_sex['Age'],
#                                                              bins=age_bins, labels=age_labels)
#
#     list_of_projects_fac = pd.concat([list_of_projects_fac_above1age_sex, list_of_projects_fac_below1age_sex])
#
#     age_sex_df = list_of_projects_fac.groupby(['Age Group', 'Sex']).size().unstack().reset_index()
#     return age_sex_df, cd4_summary_fig, crag_testing_lab_fig, cd4_testing_lab_fig, rejected_df, tb_lam_pos_df, \
#         crag_pos_df, missing_tb_lam_df, missing_df, list_of_projects_fac, show_cd4_testing_workload, show_crag_testing_workload


# @silk_profile(name='generate_results_df')
def generate_results_df(list_of_projects):
    # @silk_profile(name='prepare_df_cd4')
    def prepare_df_cd4(list_of_projects):
        column_names = [
            "County", "Sub-county", "Testing Laboratory", "Facility", "MFL CODE", "CCC NO.", "Age", "Sex",
            "Collection Date", "Testing date", "Received date", "Date Dispatch", "Justification", "CD4 Count",
            "Serum CRAG date", "Serum Crag", "TB LAM date", "TB LAM", "Received status", "Rejection reason", "TAT",
            "age_unit",
        ]
        # convert data from database to a dataframe
        list_of_projects = pd.DataFrame(list_of_projects)
        list_of_projects.columns = column_names

        list_of_projects_fac = list_of_projects.copy()

        # Convert Timestamp objects to strings
        # list_of_projects_fac = list_of_projects_fac.sort_values('Collection Date').reset_index(drop=True)
        # convert to datetime with UTC
        date_columns = ['Testing date', 'Collection Date', 'Received date', 'Date Dispatch']
        list_of_projects_fac[date_columns] = list_of_projects_fac[date_columns].astype("datetime64[ns, UTC]")

        return list_of_projects_fac

    list_of_projects_fac = prepare_df_cd4(list_of_projects)

    # @silk_profile(name='check_conditions')
    def check_conditions(dataframe):
        # Check if samples with "Rejected" status exist
        rejected_samples_exist = dataframe["Received status"] == "Rejected"

        # Check if samples with "Positive" TB LAM results exist
        tb_lam_pos_samples_exist = dataframe["TB LAM"] == "Positive"

        # Check if samples with "Positive" Serum Crag results exist
        crag_pos_samples_exist = dataframe["Serum Crag"] == "Positive"

        # Check if samples with missing CRAG results and CD4 <= 200 exist
        missing_crag_samples_exist = (
                (dataframe["CD4 Count"] <= 200) &
                dataframe["Serum Crag"].isnull()
        )

        # Check if samples with missing TB LAM results and CD4 <= 200 exist
        missing_tb_lam_samples_exist = (
                (dataframe["CD4 Count"] <= 200) &
                dataframe["TB LAM"].isnull()
        )

        return {
            "rejected_samples_exist": rejected_samples_exist.any(),
            "tb_lam_pos_samples_exist": tb_lam_pos_samples_exist.any(),
            "crag_pos_samples_exist": crag_pos_samples_exist.any(),
            "missing_crag_samples_exist": missing_crag_samples_exist.any(),
            "missing_tb_lam_samples_exist": missing_tb_lam_samples_exist.any(),
        }

    # Example usage:
    available_dfs = check_conditions(list_of_projects_fac)

    # @silk_profile(name='convert_to_local_date')
    def convert_to_local_date(df, columns):
        local_timezone = tzlocal.get_localzone()
        for col in columns:
            df[col] = pd.to_datetime(df[col]).dt.tz_convert(local_timezone).dt.date
        return df

    # Usage
    date_columns = ['Testing date', 'Collection Date', 'Received date', 'Date Dispatch']
    list_of_projects_fac = convert_to_local_date(list_of_projects_fac, date_columns)

    # @silk_profile(name='process_date_column')
    def process_date_column(df, column_name):
        df[column_name] = pd.to_datetime(df[column_name]).dt.date
        df[column_name] = df[column_name].replace({pd.NaT: ''})
        df[column_name] = df[column_name].astype(str)

    date_columns = ['Testing date', 'Received date', 'Date Dispatch', 'TB LAM date', 'Serum CRAG date']
    for col in date_columns:
        process_date_column(list_of_projects_fac, col)

    list_of_projects_fac['Collection Date'] = pd.to_datetime(list_of_projects_fac['Collection Date']).dt.date
    list_of_projects_fac['Collection Date'] = list_of_projects_fac['Collection Date'].astype(str)

    list_of_projects_fac.index = range(1, len(list_of_projects_fac) + 1)
    max_date = list_of_projects_fac['Collection Date'].max()
    min_date = list_of_projects_fac['Collection Date'].min()

    condition = (list_of_projects_fac['CD4 Count'] < 200)
    missing_df = list_of_projects_fac.loc[condition & list_of_projects_fac['Serum Crag'].isna()]
    missing_tb_lam_df = list_of_projects_fac.loc[condition & list_of_projects_fac['TB LAM'].isna()]

    crag_pos_df = list_of_projects_fac.loc[list_of_projects_fac['Serum Crag'] == "Positive"]
    tb_lam_pos_df = list_of_projects_fac.loc[list_of_projects_fac['TB LAM'] == "Positive"]
    rejected_df = list_of_projects_fac.loc[list_of_projects_fac['Received status'] == "Rejected"]

    # @silk_profile(name='generate_summary_df')
    def generate_summary_df(list_of_projects_fac):
        # Create the summary dataframe
        summary_df = pd.DataFrame({
            'Total CD4': [list_of_projects_fac.shape[0]],
            'Rejected': [(list_of_projects_fac['Received status'] == 'Rejected').sum()],
            'CD4 >200': [(list_of_projects_fac['CD4 Count'] > 200).sum()],
            'CD4 <= 200': [(list_of_projects_fac['CD4 Count'] <= 200).sum()],
            'TB-LAM': [list_of_projects_fac['TB LAM'].notna().sum()],
            '-ve TB-LAM': [(list_of_projects_fac['TB LAM'] == 'Negative').sum()],
            '+ve TB-LAM': [(list_of_projects_fac['TB LAM'] == 'Positive').sum()],
            'Missing TB LAM': [
                (list_of_projects_fac.loc[list_of_projects_fac['CD4 Count'] < 200, 'TB LAM'].isna()).sum()],
            'CRAG': [list_of_projects_fac['Serum Crag'].notna().sum()],
            '-ve CRAG': [(list_of_projects_fac['Serum Crag'] == 'Negative').sum()],
            '+ve CRAG': [(list_of_projects_fac['Serum Crag'] == 'Positive').sum()],
            'Missing CRAG': [
                (list_of_projects_fac.loc[list_of_projects_fac['CD4 Count'] < 200, 'Serum Crag'].isna()).sum()],
        })

        # Display the summary dataframe
        summary_df = summary_df.T.reset_index()
        summary_df.columns = ['variables', 'values']
        summary_df = summary_df[summary_df['values'] != 0]
        return summary_df

    # # Create the summary dataframe
    summary_df = generate_summary_df(list_of_projects_fac)

    ###################################
    # CD4 SUMMARY CHART
    ###################################
    cd4_summary_fig = bar_chart(summary_df, "variables", "values",
                                f"Summary of CD4 Records and Serum CrAg Results Between {min_date} and {max_date} ")

    # @silk_profile(name='generate_workload_summary_df')
    def generate_workload_summary_df(list_of_projects_fac):
        # Generate summary dataframe
        summary_df = (list_of_projects_fac.pivot_table(
            index='Testing Laboratory',
            values=['CD4 Count', 'Serum Crag'],
            aggfunc={'CD4 Count': 'count', 'Serum Crag': lambda x: x.count() if x.notnull().any() else 0}
        ).reset_index()
                      .rename(columns={'CD4 Count': 'Total CD4 Count', 'Serum Crag': 'Total CRAG Reports'})
                      .sort_values('Testing Laboratory')
                      .reset_index(drop=True))

        # Melt the summary dataframe
        summary_df = pd.melt(summary_df, id_vars="Testing Laboratory",
                             value_vars=['Total CD4 Count', 'Total CRAG Reports'],
                             var_name="Test done", value_name='values')

        # Initialize flags
        show_cd4_testing_workload = show_crag_testing_workload = False

        # Filter and process CD4 dataframe
        cd4_df = (summary_df[summary_df['Test done'] == "Total CD4 Count"]
                  .sort_values("values")
                  .fillna(0))
        cd4_df = cd4_df[cd4_df['values'] != 0]
        if not cd4_df.empty:
            show_cd4_testing_workload = True

        # Filter and process CRAG dataframe
        crag_df = (summary_df[summary_df['Test done'] == "Total CRAG Reports"]
                   .sort_values("values")
                   .fillna(0))
        crag_df = crag_df[crag_df['values'] != 0]
        if not crag_df.empty:
            show_crag_testing_workload = True

        return summary_df, show_cd4_testing_workload, show_crag_testing_workload, cd4_df, crag_df

    summary_df, show_cd4_testing_workload, show_crag_testing_workload, cd4_df, crag_df = generate_workload_summary_df(
        list_of_projects_fac)
    ###################################
    # CRAG TESTING SUMMARY CHART
    ###################################
    crag_testing_lab_fig = bar_chart(crag_df, "Testing Laboratory", "values",
                                     f"Number of sCrAg Reports Processed per Testing Laboratory ({crag_df.shape[0]}).")
    ###################################
    # CD4 TESTING SUMMARY CHART
    ###################################
    cd4_testing_lab_fig = bar_chart(cd4_df, "Testing Laboratory", "values",
                                    f"Number of CD4 Reports Processed per Testing Laboratory ({cd4_df.shape[0]})")

    age_bins = [0, 1, 4, 9, 14, 19, 24, 29, 34, 39, 44, 49, 54, 59, 64, 150]
    age_labels = ['<1', '1-4.', '5-9', '10-14.', '15-19', '20-24', '25-29', '30-34', '35-39', '40-44', '45-49',
                  '50-54', '55-59', '60-64', '65+']
    def create_age_sex_df(dataframe, age_bins, age_labels):
        # Separate data based on 'age_unit'
        above_1_age_sex = dataframe[dataframe['age_unit'] == "years"]
        below_1_age_sex = dataframe[dataframe['age_unit'] != "years"]

        # Create 'Age Group' based on age bins
        below_1_age_sex['Age Group'] = "<1"
        above_1_age_sex['Age Group'] = pd.cut(above_1_age_sex['Age'], bins=age_bins, labels=age_labels)

        # Combine the DataFrames
        result_df = pd.concat([above_1_age_sex, below_1_age_sex])

        # Group by 'Age Group' and 'Sex'
        age_sex_df = result_df.groupby(['Age Group', 'Sex']).size().unstack().reset_index()

        return age_sex_df

    age_sex_df = create_age_sex_df(list_of_projects_fac, age_bins, age_labels)
    return age_sex_df, cd4_summary_fig, crag_testing_lab_fig, cd4_testing_lab_fig, rejected_df, tb_lam_pos_df, \
        crag_pos_df, missing_tb_lam_df, missing_df, list_of_projects_fac, show_cd4_testing_workload, \
        show_crag_testing_workload, available_dfs


# @silk_profile(name='save_cd4_report')
def save_cd4_report(writer, queryset):
    """
    Save CD4 report data to a CSV file.

    Args:
        writer (csv.writer): CSV writer object.
        queryset (QuerySet): Django queryset containing CD4 report data.

    Returns:
        None

    Example:
        save_cd4_report(csv.writer(response), queryset)
    """
    # Define the header row for the CSV file
    header = [
        "County", "Sub-County", "Patient Unique No.", "Facility Name", "MFL Code", "Age", "Age Unit", "Sex",
        "Date of Collection", "Date of Receipt", "Date of Testing", "Dispatch Date", "CD4 Count",
        "TB LAM Results", "Serum CRAG Results", "Justification", "Received Status", "Reason for Rejection",
        "Reason for No Serum CRAG", "Testing Laboratory"
    ]
    # Write the header row to the CSV file
    writer.writerow(header)

    # Use select_related to fetch related objects in a single query
    queryset = queryset.select_related('facility_name', 'testing_laboratory', 'sub_county', 'county')

    # Retrieve data as a list of dictionaries
    data_list = list(queryset.values(
        'county__county_name', 'sub_county__sub_counties', 'patient_unique_no', 'facility_name__name',
        'facility_name__mfl_code', 'age', 'age_unit', 'sex', 'date_of_collection', 'date_sample_received',
        'date_of_testing', 'date_dispatched', 'cd4_count_results', 'tb_lam_results', 'serum_crag_results',
        'justification', 'received_status', 'reason_for_rejection', 'reason_for_no_serum_crag',
        'testing_laboratory__testing_lab_name',
    ))

    # Write data rows based on the list of dictionaries
    for record_dict in data_list:
        data_row = [
            record_dict.get("county__county_name", ""),
            record_dict.get("sub_county__sub_counties", ""),
            record_dict.get("patient_unique_no", ""),
            record_dict.get("facility_name__name", ""),
            record_dict.get("facility_name__mfl_code", ""),
            record_dict.get("age", ""),
            record_dict.get("age_unit", ""),
            record_dict.get("sex", ""),
            record_dict.get("date_of_collection", ""),
            record_dict.get("date_sample_received", ""),
            record_dict.get("date_of_testing", ""),
            record_dict.get("date_dispatched", ""),
            record_dict.get("cd4_count_results", ""),
            record_dict.get("tb_lam_results", ""),
            record_dict.get("serum_crag_results", ""),
            record_dict.get("justification", ""),
            record_dict.get("received_status", ""),
            record_dict.get("reason_for_rejection", ""),
            record_dict.get("reason_for_no_serum_crag", ""),
            record_dict.get("testing_laboratory__testing_lab_name", ""),
        ]
        # Write the data row to the CSV file
        writer.writerow(data_row)


# @silk_profile(name='save_drt_report')
def save_drt_report(writer, queryset):
    """
    Save DRT report data to a CSV file.

    Args:
        writer (csv.writer): CSV writer object.
        queryset (QuerySet): Django queryset containing DRT report data.

    Returns:
        None

    Example:
        save_drt_report(csv.writer(response), queryset)

    This function takes a CSV writer object and a Django queryset containing DRT report data.
    It writes the data to the CSV file in the specified format.

    Args:
        - writer (csv.writer): The CSV writer object to write data to the file.
        - queryset (QuerySet): The Django queryset containing DRT report data.

    Example:
        save_cd4_report(csv.writer(response), queryset)
    """
    # Define the header row for the CSV file
    header = ["County", "Sub-County", "Patient Unique No.", "Facility Name", "MFL Code", "Age", "Age Unit", "Sex",
              "Date of Collection", "Date of Receipt", "Date of Testing", "Dispatch Date", "Drug",
              "Drug Abbreviation", "Sequence summary", "Resistance level", "HAART class", "TAT",
              "Performed by"]
    # Write the header row to the CSV file
    writer.writerow(header)

    # Use select_related to fetch related objects in a single query
    queryset = queryset.select_related('facility_name', 'sub_county', 'county')

    # Retrieve data as a list of dictionaries
    data_list = list(queryset.values(
        'county__county_name', 'sub_county__sub_counties', 'patient_id', 'facility_name__name',
        'facility_name__mfl_code', 'age', 'age_unit', 'sex', 'collection_date', 'date_received',
        'date_test_performed', 'date_created', 'drug', 'drug_abbreviation', 'sequence_summary',
        'resistance_level', 'haart_class', 'tat_days', 'test_perfomed_by',
    ))

    # Write data rows based on the list of dictionaries
    for record_dict in data_list:
        data_row = [
            record_dict.get("county__county_name", ""),
            record_dict.get("sub_county__sub_counties", ""),
            record_dict.get("patient_id", ""),
            record_dict.get("facility_name__name", ""),
            record_dict.get("facility_name__mfl_code", ""),
            record_dict.get("age", ""),
            record_dict.get("age_unit", ""),
            record_dict.get("sex", ""),
            record_dict.get("collection_date", ""),
            record_dict.get("date_received", ""),
            record_dict.get("date_test_performed", ""),
            record_dict.get("date_created", ""),
            record_dict.get("drug", ""),
            record_dict.get("drug_abbreviation", ""),
            record_dict.get("sequence_summary", ""),
            record_dict.get("resistance_level", ""),
            record_dict.get("haart_class", ""),
            record_dict.get("tat_days", ""),
            record_dict.get("test_perfomed_by", ""),
        ]
        # Write the data row to the CSV file
        writer.writerow(data_row)


@login_required(login_url='login')
def download_csv(request, filter_type):
    current_page_url = request.session.get('current_page_url', '')
    queryset = Cd4trakerFilter(request.GET).qs

    # Perform filtering based on 'filter_type'
    if filter_type == 'all':
        pass  # No need to filter further for 'all'
    elif filter_type == 'rejected' and "show" in current_page_url:
        queryset = queryset.filter(received_status='Rejected')
    elif filter_type == 'positive_tb_lam' and "show" in current_page_url:
        queryset = queryset.filter(tb_lam_results='Positive')
    elif filter_type == 'positive_crag' and "show" in current_page_url:
        queryset = queryset.filter(serum_crag_results='Positive')
    elif filter_type == 'missing_crag' and "show" in current_page_url:
        queryset = queryset.filter(
            cd4_count_results__isnull=False,
            cd4_count_results__lte=200,
            serum_crag_results__isnull=True
        )
    elif filter_type == 'missing_tb_lam' and "show" in current_page_url:
        queryset = queryset.filter(
            cd4_count_results__isnull=False,
            cd4_count_results__lte=200,
            tb_lam_results__isnull=True
        )
    else:
        # Handle invalid filter_type or other conditions as needed
        queryset = queryset.none()

    # Create a CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filter_type}_records.csv"'

    # Create a CSV writer and write the header row
    writer = csv.writer(response)
    if "show" in current_page_url:
        save_cd4_report(writer, queryset)
    elif "drt" in current_page_url:
        queryset = DrtResultFilter(request.GET).qs
        save_drt_report(writer, queryset)

    return response


# @login_required(login_url='login')
# @group_required(
#     ['project_technical_staffs', 'subcounty_staffs_labpulse', 'laboratory_staffs_labpulse', 'facility_staffs_labpulse'
#         , 'referring_laboratory_staffs_labpulse'])
# def show_results(request):
#     if not request.user.first_name:
#         return redirect("profile")
#     if request.method == "GET":
#         request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
#         # record_count = int(request.GET.get('record_count', 10))  # Get the selected record count (default: 10)
#         record_count = request.GET.get('record_count', '5')
#         if record_count == 'all':
#             record_count = 'all'  # Preserve the 'all' value if selected
#         else:
#             record_count = int(record_count)  # Convert to integer if a specific value is selected
#     else:
#         record_count = 100  # Default record count if no selection is made
#     cd4_summary_fig = None
#     cd4_testing_lab_fig = None
#     crag_testing_lab_fig = None
#     weekly_tat_trend_fig = None
#     facility_tb_lam_positive_fig = None
#     weekly_trend_fig = None
#     age_distribution_fig = None
#     rejection_summary_fig = None
#     justification_summary_fig = None
#     crag_positivity_fig = None
#     tb_lam_positivity_fig = None
#     facility_crag_positive_fig = None
#     list_of_projects_fac = pd.DataFrame()
#     crag_pos_df = pd.DataFrame()
#     tb_lam_pos_df = pd.DataFrame()
#     weekly_df = pd.DataFrame()
#     missing_df = pd.DataFrame()
#     missing_tb_lam_df = pd.DataFrame()
#     rejected_df = pd.DataFrame()
#     rejection_summary_df = pd.DataFrame()
#     justification_summary_df = pd.DataFrame()
#     show_cd4_testing_workload = False
#     show_crag_testing_workload = False
#     crag_positivity_df = pd.DataFrame()
#     tb_lam_positivity_df = pd.DataFrame()
#     facility_positive_count = pd.DataFrame()
#     # Access the page URL
#     current_page_url = request.path
#
#     # Handle N+1 Query /lab-pulse/download/{filter_type}
#     cd4traker_qs = Cd4traker.objects.all().prefetch_related('facility_name', 'sub_county', 'county',
#                                                             'testing_laboratory', 'created_by', 'modified_by'
#                                                             ).order_by('-date_dispatched')
#     my_filters = Cd4trakerFilter(request.GET, queryset=cd4traker_qs)
#     try:
#         if "filtered_queryset" in request.session:
#             del request.session['filtered_queryset']
#         if "current_page_url" in request.session:
#             del request.session['current_page_url']
#
#         # Serialize the filtered queryset to JSON and store it in the session
#         filtered_data_json = serializers.serialize('json', my_filters.qs)
#         request.session['filtered_queryset'] = filtered_data_json
#         request.session['current_page_url'] = current_page_url
#     except KeyError:
#         # Handles the case where the session key doesn't exist
#         pass
#
#     record_count_options = [(str(i), str(i)) for i in [5, 10, 20, 30, 40, 50]] + [("all", "All"), ]
#
#     qi_list = pagination_(request, my_filters.qs, record_count)
#
#     # Check if there records exists in filtered queryset
#     rejected_samples_exist = my_filters.qs.filter(received_status="Rejected").exists()
#     tb_lam_pos_samples_exist = my_filters.qs.filter(tb_lam_results="Positive").exists()
#     crag_pos_samples_exist = my_filters.qs.filter(serum_crag_results="Positive").exists()
#     missing_crag_samples_exist = my_filters.qs.filter(cd4_count_results__isnull=False,
#                                                       cd4_count_results__lte=200,
#                                                       serum_crag_results__isnull=True
#                                                       ).exists()
#     missing_tb_lam_samples_exist = my_filters.qs.filter(cd4_count_results__isnull=False,
#                                                         cd4_count_results__lte=200,
#                                                         tb_lam_results__isnull=True
#                                                         ).exists()
#
#     ######################
#     # Hide update button #
#     ######################
#     if qi_list:
#         disable_update_buttons(request, qi_list, 'date_dispatched')
#     if my_filters.qs:
#         # fields to extract
#         fields = ['county__county_name', 'sub_county__sub_counties', 'testing_laboratory__testing_lab_name',
#                   'facility_name__name', 'facility_name__mfl_code', 'patient_unique_no', 'age', 'sex',
#                   'date_of_collection', 'date_of_testing', 'date_sample_received', 'date_dispatched', 'justification',
#                   'cd4_count_results',
#                   'date_serum_crag_results_entered', 'serum_crag_results', 'date_tb_lam_results_entered',
#                   'tb_lam_results', 'received_status', 'reason_for_rejection', 'tat_days', 'age_unit']
#
#         # Extract the data from the queryset using values()
#         data = my_filters.qs.values(*fields)
#
#         age_sex_df, cd4_summary_fig, crag_testing_lab_fig, cd4_testing_lab_fig, rejected_df, tb_lam_pos_df, \
#             crag_pos_df, missing_tb_lam_df, missing_df, list_of_projects_fac, show_cd4_testing_workload, \
#             show_crag_testing_workload = generate_results_df(data)
#         ###################################
#         # AGE AND SEX CHART
#         ###################################
#         age_sex_df = pd.melt(age_sex_df, id_vars="Age Group",
#                              value_vars=list(age_sex_df.columns[1:]),
#                              var_name="Sex", value_name='# of sample processed')
#
#         age_distribution_fig = bar_chart(age_sex_df, "Age Group", "# of sample processed",
#                                          "CD4 Count Distribution By Age Band and Sex", color="Sex")
#         if "Age Group" in list_of_projects_fac.columns:
#             del list_of_projects_fac['Age Group']
#
#         ###################################
#         # REJECTED SAMPLES
#         ###################################
#         rejection_summary_fig, rejection_summary_df = create_summary_chart(list_of_projects_fac, 'Rejection reason',
#                                                                            'Reasons for Sample Rejection')
#
#         ###################################
#         # Justification
#         ###################################
#         justification_summary_fig, justification_summary_df = create_summary_chart(
#             list_of_projects_fac, 'Justification', 'Justification Summary')
#
#         ###########################
#         # SERUM CRAG POSITIVITY
#         ###########################
#         crag_positivity_fig, crag_positivity_df = calculate_positivity_rate(list_of_projects_fac, 'Serum Crag',
#                                                                             "Serum CrAg")
#         ###############################
#         # FACILITY WITH POSITIVE CRAG #
#         ###############################
#         facility_positive_count = filter_result_type(list_of_projects_fac, "Serum Crag")
#
#         facility_crag_positive_fig = visualize_facility_results_positivity(facility_positive_count, "Serum CRAG",
#                                                                            "Serum CrAg")
#         #################################
#         # FACILITY WITH POSITIVE TB LAM #
#         #################################
#         facility_positive_count = filter_result_type(list_of_projects_fac, "TB LAM")
#         facility_tb_lam_positive_fig = visualize_facility_results_positivity(facility_positive_count, "TB LAM",
#                                                                              "TB LAM")
#         ###########################
#         # TB LAM POSITIVITY
#         ###########################
#         tb_lam_positivity_fig, tb_lam_positivity_df = calculate_positivity_rate(list_of_projects_fac, 'TB LAM',
#                                                                                 "TB LAM")
#         ###################################
#         # Weekly Trend viz
#         ###################################
#         df_weekly = list_of_projects_fac.copy()
#         df_weekly['Collection Date'] = pd.to_datetime(df_weekly['Collection Date'], format='%Y-%m-%d')
#
#         df_weekly['week_start'] = df_weekly['Collection Date'].dt.to_period('W').dt.start_time
#         weekly_df = df_weekly.groupby('week_start').size().reset_index(name='# of samples processed')
#         weekly_df['Weekly Trend'] = weekly_df["week_start"].astype(str) + "."
#         weekly_trend = weekly_df['# of samples processed'].sum()
#         if weekly_df.shape[0] > 1:
#             weekly_trend_fig = line_chart_median_mean(weekly_df, "Weekly Trend", "# of samples processed",
#                                                       f"Weekly Trend CD4 Samples Processing N={weekly_trend}"
#                                                       f"      Maximum # CD4 counts : {max(weekly_df['# of samples processed'])}")
#
#         weekly_df['week_start'] = pd.to_datetime(weekly_df['week_start']).dt.date
#         weekly_df['week_start'] = weekly_df['week_start'].replace(np.datetime64('NaT'), '')
#         weekly_df['week_start'] = weekly_df['week_start'].astype(str)
#
#         ###################################
#         # Weekly TAT Trend viz
#         ###################################
#         melted_tat_df, mean_c_r, mean_c_d = calculate_weekly_tat(list_of_projects_fac.copy())
#         if melted_tat_df.shape[0] > 1:
#             weekly_tat_trend_fig = line_chart_median_mean(melted_tat_df, "Weekly Trend", "Weekly mean TAT",
#                                                           f"Weekly Collection to Dispatch vs Collection to Receipt Mean "
#                                                           f"TAT Trend  (C-D TAT = {mean_c_d}, C-R TAT = {mean_c_r})",
#                                                           color="TAT type",time=104
#                                                           )
#     try:
#         if "list_of_projects_fac" in request.session:
#             del request.session['list_of_projects_fac']
#         request.session['list_of_projects_fac'] = list_of_projects_fac.to_dict()
#     except KeyError:
#         # Handle the case where the session key doesn't exist
#         pass
#
#     dataframes = [
#         (missing_df, 'missing_df'),
#         (missing_tb_lam_df, 'missing_tb_lam_df'),
#         (justification_summary_df, 'justification_summary_df'),
#         (tb_lam_pos_df, 'tb_lam_pos_df'),
#         (weekly_df, 'weekly_df'),
#         (crag_pos_df, 'crag_pos_df'),
#         (rejected_df, 'rejected_df')
#     ]
#
#     for df, session_key in dataframes:
#         if df.shape[0] > 0:
#             request.session[session_key] = df.to_dict()
#         else:
#             if session_key in request.session:
#                 del request.session[session_key]
#
#     # Convert dict_items into a list
#     dictionary = get_key_from_session_names(request)
#     context = {
#         "title": "Results", "record_count_options": record_count_options, "record_count": record_count,
#         "rejected_samples_exist": rejected_samples_exist, "tb_lam_pos_samples_exist": tb_lam_pos_samples_exist,
#         "crag_pos_samples_exist": crag_pos_samples_exist, "missing_crag_samples_exist": missing_crag_samples_exist,
#         "missing_tb_lam_samples_exist": missing_tb_lam_samples_exist, "dictionary": dictionary,
#         "my_filters": my_filters,
#         "qi_list": qi_list, "cd4_summary_fig": cd4_summary_fig, "crag_testing_lab_fig": crag_testing_lab_fig,
#         "weekly_trend_fig": weekly_trend_fig, "cd4_testing_lab_fig": cd4_testing_lab_fig,
#         "age_distribution_fig": age_distribution_fig, "rejection_summary_fig": rejection_summary_fig,
#         "justification_summary_fig": justification_summary_fig, "crag_positivity_fig": crag_positivity_fig,
#         "justification_summary_df": justification_summary_df, "facility_crag_positive_fig": facility_crag_positive_fig,
#         "rejection_summary_df": rejection_summary_df, "show_cd4_testing_workload": show_cd4_testing_workload,
#         "show_crag_testing_workload": show_crag_testing_workload, "crag_positivity_df": crag_positivity_df,
#         "facility_positive_count": facility_positive_count, "tb_lam_positivity_fig": tb_lam_positivity_fig,
#         "tb_lam_positivity_df": tb_lam_positivity_df, "weekly_df": weekly_df,
#         "weekly_tat_trend_fig": weekly_tat_trend_fig, "facility_tb_lam_positive_fig": facility_tb_lam_positive_fig
#     }
#     return render(request, 'lab_pulse/show results.html', context)
# @silk_profile(name='get_cd4_tracker_data')
def get_cd4_tracker_data():
    # Check if the data is already in the cache
    cached_data = cache.get('cd4_tracker_data')
    latest_record_timestamp = cache.get('latest_record_timestamp')

    # If no cached data or new records have been added since the last cache
    if cached_data is None or latest_record_timestamp is None or latest_record_timestamp < Cd4traker.objects.latest(
            'date_dispatched').date_dispatched:
        # If not in the cache or new records added, perform the query
        one_year_ago = timezone.now() - timedelta(days=352)
        cd4_tracker_qs = Cd4traker.objects.filter(
            date_of_collection__gte=one_year_ago
        ).select_related(
            'facility_name', 'sub_county', 'county', 'testing_laboratory', 'created_by',
            'modified_by'
        ).order_by('-date_dispatched')

        # Store the queryset and the timestamp of the latest record in the cache
        cache.set('cd4_tracker_data', cd4_tracker_qs, timeout=3600)  # Cache for 1 hour
        cache.set('latest_record_timestamp', timezone.now(), timeout=3600)  # Cache for 1 hour

        # Return the queryset
        return cd4_tracker_qs

    # Return the cached queryset
    return cached_data

@cache_page(60 * 60)
# @silk_profile(name='show results')
@login_required(login_url='login')
@group_required(
    ['project_technical_staffs', 'subcounty_staffs_labpulse', 'laboratory_staffs_labpulse', 'facility_staffs_labpulse'
        , 'referring_laboratory_staffs_labpulse'])
def show_results(request):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
        # record_count = int(request.GET.get('record_count', 10))  # Get the selected record count (default: 10)
        record_count = request.GET.get('record_count', '5')
        if record_count == 'all':
            record_count = 'all'  # Preserve the 'all' value if selected
        else:
            record_count = int(record_count)  # Convert to integer if a specific value is selected
    else:
        record_count = 100  # Default record count if no selection is made

    cd4_summary_fig = cd4_testing_lab_fig = crag_testing_lab_fig = weekly_tat_trend_fig = \
        facility_tb_lam_positive_fig = weekly_trend_fig = age_distribution_fig = rejection_summary_fig = \
        justification_summary_fig = crag_positivity_fig = tb_lam_positivity_fig = facility_crag_positive_fig = None

    list_of_projects_fac = crag_pos_df = tb_lam_pos_df = weekly_df = missing_df = missing_tb_lam_df = rejected_df = \
        rejection_summary_df = justification_summary_df = crag_positivity_df = tb_lam_positivity_df = \
        facility_positive_count = pd.DataFrame()
    show_cd4_testing_workload = show_crag_testing_workload = False

    available_dfs = {"rejected_samples_exist": False, "tb_lam_pos_samples_exist": False,
                     "crag_pos_samples_exist": False, "missing_crag_samples_exist": False,
                     "missing_tb_lam_samples_exist": False}

    # @silk_profile(name='fetch_cd4_data')
    def fetch_past_one_year_cd4_data(request):
        # Get the user's start_date input from the request GET parameters
        start_date_param = request.GET.get('start_date')
        end_date_param = request.GET.get('end_date')
        use_one_year_data = True
        # Use default logic for one year ago
        one_year_ago = datetime.now() - timedelta(days=365)
        one_year_ago = datetime(
            one_year_ago.year,
            one_year_ago.month,
            one_year_ago.day,
            23, 59, 59, 999999
        )

        if start_date_param:
            # Parse the user's input into a datetime object
            start_date = datetime.strptime(start_date_param, '%m/%d/%Y')

            # If the user's input is beyond one year ago, use it
            if start_date < datetime.now() - timedelta(days=365) and (
                    not end_date_param or start_date < datetime.strptime(end_date_param, '%m/%d/%Y')):
                one_year_ago = start_date
                use_one_year_data=False
        # Handle N+1 Query using prefetch_related /lab-pulse/download/{filter_type}
        cd4traker_qs = Cd4traker.objects.filter(date_of_collection__gte=one_year_ago).select_related(
            'facility_name', 'sub_county', 'county', 'testing_laboratory', 'created_by',
            'modified_by'
        ).order_by('-date_dispatched')

        return cd4traker_qs,use_one_year_data

    cd4traker_qs,use_one_year_data = fetch_past_one_year_cd4_data(request)


    my_filters = Cd4trakerFilter(request.GET, queryset=cd4traker_qs)

    if "current_page_url" in request.session:
        del request.session['current_page_url']
    # Access the page URL
    request.session['current_page_url'] = request.path

    # record_count_options = [(str(i), str(i)) for i in [5, 10, 20]] + [("all", "All"), ]
    record_count_options = [(str(i), str(i)) for i in [5, 10, 20]]


    qi_list = pagination_(request, my_filters.qs, record_count)

    ######################
    # Hide update button #
    ######################
    if qi_list:
        disable_update_buttons(request, qi_list, 'date_dispatched')
    if my_filters.qs.exists():
        # Use select_related to fetch related objects in a single query
        queryset = my_filters.qs.select_related('facility_name', 'testing_laboratory', 'sub_county',
                                                'county').order_by('-date_of_collection')

        # Retrieve data as a list of dictionaries
        data = list(queryset.values(
            'county__county_name', 'sub_county__sub_counties', 'testing_laboratory__testing_lab_name',
            'facility_name__name', 'facility_name__mfl_code', 'patient_unique_no', 'age', 'sex',
            'date_of_collection', 'date_of_testing', 'date_sample_received', 'date_dispatched', 'justification',
            'cd4_count_results', 'date_serum_crag_results_entered', 'serum_crag_results', 'date_tb_lam_results_entered',
            'tb_lam_results', 'received_status', 'reason_for_rejection', 'tat_days', 'age_unit'
        ))

        age_sex_df, cd4_summary_fig, crag_testing_lab_fig, cd4_testing_lab_fig, rejected_df, tb_lam_pos_df, \
            crag_pos_df, missing_tb_lam_df, missing_df, list_of_projects_fac, show_cd4_testing_workload, \
            show_crag_testing_workload, available_dfs = generate_results_df(data)
        ###################################
        # AGE AND SEX CHART
        ###################################
        age_sex_df = pd.melt(age_sex_df, id_vars="Age Group",
                             value_vars=list(age_sex_df.columns[1:]),
                             var_name="Sex", value_name='# of sample processed')

        age_distribution_fig = bar_chart(age_sex_df, "Age Group", "# of sample processed",
                                         "CD4 Count Distribution By Age Band and Sex", color="Sex")
        if "Age Group" in list_of_projects_fac.columns:
            del list_of_projects_fac['Age Group']

        ###################################
        # REJECTED SAMPLES
        ###################################
        rejection_summary_fig, rejection_summary_df = create_summary_chart(list_of_projects_fac, 'Rejection reason',
                                                                           'Reasons for Sample Rejection')

        ###################################
        # Justification
        ###################################
        justification_summary_fig, justification_summary_df = create_summary_chart(
            list_of_projects_fac, 'Justification', 'Justification Summary')

        ###########################
        # SERUM CRAG POSITIVITY
        ###########################
        crag_positivity_fig, crag_positivity_df = calculate_positivity_rate(list_of_projects_fac, 'Serum Crag',
                                                                            "Serum CrAg")
        ###############################
        # FACILITY WITH POSITIVE CRAG #
        ###############################
        facility_positive_count = filter_result_type(list_of_projects_fac, "Serum Crag")

        facility_crag_positive_fig = visualize_facility_results_positivity(facility_positive_count, "Serum CRAG",
                                                                           "Serum CrAg")
        #################################
        # FACILITY WITH POSITIVE TB LAM #
        #################################
        facility_positive_count = filter_result_type(list_of_projects_fac, "TB LAM")
        facility_tb_lam_positive_fig = visualize_facility_results_positivity(facility_positive_count, "TB LAM",
                                                                             "TB LAM")
        ###########################
        # TB LAM POSITIVITY
        ###########################
        tb_lam_positivity_fig, tb_lam_positivity_df = calculate_positivity_rate(list_of_projects_fac, 'TB LAM',
                                                                                "TB LAM")
        ###################################
        # Weekly Trend viz
        ###################################
        df_weekly = list_of_projects_fac.copy()
        df_weekly['Collection Date'] = pd.to_datetime(df_weekly['Collection Date'], format='%Y-%m-%d')

        df_weekly['week_start'] = df_weekly['Collection Date'].dt.to_period('W').dt.start_time
        weekly_df = df_weekly.groupby('week_start').size().reset_index(name='# of samples processed')
        weekly_df['Weekly Trend'] = weekly_df["week_start"].astype(str) + "."
        weekly_trend = weekly_df['# of samples processed'].sum()
        if weekly_df.shape[0] > 1:
            weekly_trend_fig = line_chart_median_mean(weekly_df, "Weekly Trend", "# of samples processed",
                                                      f"Weekly Trend CD4 Samples Processing N={weekly_trend}"
                                                      f"      Maximum # CD4 counts : {max(weekly_df['# of samples processed'])}",
                                                      use_one_year_data=use_one_year_data)

        weekly_df['week_start'] = pd.to_datetime(weekly_df['week_start']).dt.date.replace(np.datetime64('NaT'),
                                                                                          '').astype(str)

        ###################################
        # Weekly TAT Trend viz
        ###################################
        melted_tat_df, mean_c_r, mean_c_d = calculate_weekly_tat(list_of_projects_fac.copy())
        if melted_tat_df.shape[0] > 1:
            weekly_tat_trend_fig = line_chart_median_mean(melted_tat_df, "Weekly Trend", "Weekly mean TAT",
                                                          f"Weekly Collection to Dispatch vs Collection to Receipt Mean "
                                                          f"TAT Trend  (C-D TAT = {mean_c_d}, C-R TAT = {mean_c_r})",
                                                          color="TAT type", time=104,
                                                          use_one_year_data=use_one_year_data
                                                          )
    try:
        if "list_of_projects_fac" in request.session:
            del request.session['list_of_projects_fac']
        request.session['list_of_projects_fac'] = list_of_projects_fac.to_dict()
    except KeyError:
        # Handle the case where the session key doesn't exist
        pass

    dataframes = [
        (missing_df, 'missing_df'),
        (missing_tb_lam_df, 'missing_tb_lam_df'),
        (justification_summary_df, 'justification_summary_df'),
        (tb_lam_pos_df, 'tb_lam_pos_df'),
        (weekly_df, 'weekly_df'),
        (crag_pos_df, 'crag_pos_df'),
        (rejected_df, 'rejected_df')
    ]

    for df, session_key in dataframes:
        if df.shape[0] > 0:
            request.session[session_key] = df.to_dict()
        else:
            if session_key in request.session:
                del request.session[session_key]

    # Convert dict_items into a list
    dictionary = get_key_from_session_names(request)
    context = {
        "title": "Results", "record_count_options": record_count_options, "record_count": record_count,
        "missing_crag_samples_exist": available_dfs["missing_crag_samples_exist"],
        "missing_tb_lam_samples_exist": available_dfs["missing_tb_lam_samples_exist"],
        "rejected_samples_exist": available_dfs["rejected_samples_exist"],
        "tb_lam_pos_samples_exist": available_dfs["tb_lam_pos_samples_exist"],
        "crag_pos_samples_exist": available_dfs["crag_pos_samples_exist"],
        "dictionary": dictionary,"my_filters": my_filters,"qi_list": qi_list,
        "cd4_summary_fig": cd4_summary_fig, "crag_testing_lab_fig": crag_testing_lab_fig,
        "weekly_trend_fig": weekly_trend_fig, "cd4_testing_lab_fig": cd4_testing_lab_fig,
        "age_distribution_fig": age_distribution_fig, "rejection_summary_fig": rejection_summary_fig,
        "justification_summary_fig": justification_summary_fig, "crag_positivity_fig": crag_positivity_fig,
        "justification_summary_df": justification_summary_df, "facility_crag_positive_fig": facility_crag_positive_fig,
        "rejection_summary_df": rejection_summary_df, "show_cd4_testing_workload": show_cd4_testing_workload,
        "show_crag_testing_workload": show_crag_testing_workload, "crag_positivity_df": crag_positivity_df,
        "facility_positive_count": facility_positive_count, "tb_lam_positivity_fig": tb_lam_positivity_fig,
        "tb_lam_positivity_df": tb_lam_positivity_df, "weekly_df": weekly_df,
        "weekly_tat_trend_fig": weekly_tat_trend_fig, "facility_tb_lam_positive_fig": facility_tb_lam_positive_fig
    }
    return render(request, 'lab_pulse/show results.html', context)


def generate_report(request, pdf, name, mfl_code, date_collection, date_testing, date_dispatch, unique_no, age,
                    cd4_count, crag, sex, reason_for_rejection, testing_laboratory, tb_lam_results, tat, y):
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
        # If cd4_count is NaN, display "Rejected" in bold red font
        pdf.setFont("Helvetica-Bold", 7)
        pdf.setFillColor(colors.red)
        pdf.drawString(165, y_position, "Rejected")
        pdf.setFont("Helvetica", 3)
        pdf.drawString(145, y_position - 10, f"(Reason: {reason_for_rejection})")
    elif int(cd4_count) <= 200:
        # If cd4_count is <= 200, display cd4_count in bold font
        pdf.setFont("Helvetica-Bold", 7)
        pdf.drawString(165, y_position, str(int(cd4_count)))
    else:
        # For cd4_count > 200, display cd4_count in regular font
        pdf.setFont("Helvetica", 7)
        pdf.drawString(165, y_position, str(int(cd4_count)))

    pdf.setFont("Helvetica", 7)

    if crag is not None and "pos" in crag.lower() or (crag is None and cd4_count <= 200):
        # If crag is not None and contains "pos" or if crag is None and cd4_count <= 200,
        # display "Missing" or crag value in bold red font
        pdf.setFont("Helvetica-Bold", 7)
        pdf.setFillColor(colors.red)
        pdf.drawString(235, y_position, "Missing" if crag is None else crag)
    else:
        # For other cases, display crag value in regular font
        pdf.setFont("Helvetica", 7)
        pdf.drawString(235, y_position, "" if crag is None else crag)

    if tb_lam_results is not None and "pos" in tb_lam_results.lower() or (tb_lam_results is None and cd4_count <= 200):
        # If tb_lam_results is not None and contains "pos" or if tb_lam_results is None and cd4_count <= 200,
        # display "TB LAM : Missing" or "TB LAM : tb_lam_results" in bold red font
        pdf.setFont("Helvetica-Bold", 7)
        pdf.setFillColor(colors.red)
        pdf.drawString(225, y_position - 15,
                       "TB LAM : Missing" if tb_lam_results is None else f"TB LAM : {tb_lam_results}")
    else:
        # For other cases, display "TB LAM : tb_lam_results" in regular font
        pdf.setFont("Helvetica", 7)
        pdf.setFillColor(colors.black)
        pdf.drawString(225, y_position - 15, "" if tb_lam_results is None else f"TB LAM : {tb_lam_results}")

    pdf.setFont("Helvetica", 7)
    pdf.setFillColor(colors.black)
    pdf.drawString(305, y_position, f"{date_collection}")
    pdf.drawString(375, y_position, f"{date_testing}")
    pdf.drawString(435, y_position, f"{date_dispatch}")
    pdf.setFont("Helvetica-Bold", 3)
    pdf.drawString(432, y_position - 10, f"Collection to Dispatch TAT: {tat} Days")
    pdf.setFont("Helvetica", 7)

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
                       f"Report downloaded by: {request.user}    Time: {datetime.now()}")
    else:
        pdf.setFont("Helvetica", 4)
        pdf.setFillColor(colors.grey)
        pdf.drawString((letter[0] / 3) + 30, y + 0.2 * inch,
                       f"Report downloaded by: {request.user}    Time: {datetime.now()}")

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
            tb_lam_results = data['TB LAM']
            tat = data['TAT']
            y = generate_report(request, pdf, name, mfl_code, date_collection, date_testing, date_dispatch,
                                unique_no, age, cd4_count, crag, sex, reason_for_rejection, testing_laboratory,
                                tb_lam_results, tat, y)

        pdf.save()
        return response


@login_required(login_url='login')
@group_required(['laboratory_staffs_labpulse'])
def add_testing_lab(request):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    testing_labs = Cd4TestingLabs.objects.all()
    if testing_labs:
        disable_update_buttons(request, testing_labs, 'date_created')

    form = Cd4TestingLabForm(request.POST or None)
    if form.is_valid():
        testing_lab_name = form.cleaned_data['testing_lab_name']

        # Check for duplicate testing_lab_name (case-insensitive)
        # existing_lab = Cd4TestingLabs.objects.annotate(lower_name=Lower('testing_lab_name')).filter(
        #     lower_name=testing_lab_name.lower())
        existing_lab = Cd4TestingLabs.objects.filter(testing_lab_name__iexact=testing_lab_name)
        if existing_lab.exists():
            form.add_error('testing_lab_name', 'A CD4 Testing Lab with this name already exists.')
        else:
            form.save()
            messages.error(request, "Record saved successfully!")
            return redirect("choose_testing_lab")
    context = {
        "form": form,
        "title": f"Add CD4 Testing Lab",
        "testing_labs": testing_labs,
    }
    return render(request, 'lab_pulse/add_cd4_data.html', context)


@login_required(login_url='login')
@group_required(['laboratory_staffs_labpulse'])
def update_testing_labs(request, pk):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    item = Cd4TestingLabs.objects.get(id=pk)
    if request.method == "POST":
        form = Cd4TestingLabForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.error(request, "Record updated successfully!")
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = Cd4TestingLabForm(instance=item)
    context = {
        "form": form,
        "title": "Update CD4 testing lab details",
    }
    return render(request, 'lab_pulse/update results.html', context)


@login_required(login_url='login')
def instructions_lab(request, section):
    if not request.user.first_name:
        return redirect("profile")

    # Define a list of valid sections
    valid_sections = ["introduction", "getting_started", "entering_results", "viewing_results", "recommendations"]

    # Check if the provided section is valid
    if section not in valid_sections:
        return redirect("instructions_lab", section="introduction")

    context = {
        "section": section
    }
    return render(request, 'lab_pulse/instructions.html', context)


def validate_commodity_form(form):
    quantity_received = form.cleaned_data['quantity_received']
    negative_adjustment = form.cleaned_data['negative_adjustment']
    positive_adjustment = form.cleaned_data['positive_adjustments']
    date_commodity_received = form.cleaned_data['date_commodity_received']
    quantity_expired = form.cleaned_data['quantity_expired']
    beginning_balance = form.cleaned_data['beginning_balance']

    if date_commodity_received:
        if not quantity_received and not negative_adjustment and not positive_adjustment and not quantity_expired \
                and not beginning_balance:
            error_message = f"Provide a valid value!"
            form.add_error('quantity_received', error_message)
            form.add_error('negative_adjustment', error_message)
            form.add_error('positive_adjustments', error_message)
            form.add_error('quantity_expired', error_message)
            form.add_error('beginning_balance', error_message)
            return False

    return True


@login_required(login_url='login')
@group_required(['laboratory_staffs_labpulse', 'referring_laboratory_staffs_labpulse'])
def add_commodities(request, pk_lab):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    form = ReagentStockForm(request.POST or None)
    selected_lab, created = Facilities.objects.get_or_create(id=pk_lab)
    # commodities = ReagentStock.objects.filter(
    #     facility_name__mfl_code=selected_lab.mfl_code,
    # ).order_by("-date_commodity_received")

    template_name = 'lab_pulse/add_cd4_data.html'
    context = {
        "form": form, "report_type": "commodity",
        "title": f"Add Commodities for {selected_lab.name.title()} Laboratory",
    }
    try:
        commodity_status, commodities, cd4_total_remaining, crag_total_remaining, tb_lam_total_remaining = \
            show_remaining_commodities(selected_lab)
        commodities = pagination_(request, commodities, 100)
    except KeyError:
        # context_copy=context
        # del context_copy['form']
        messages.error(request,
                       f"{selected_lab.name.upper()} reagents are currently unavailable in the database. "
                       f"The operation cannot be completed. Please contact your laboratory supervisor for assistance "
                       f"or proceed to add commodities to replenish the stock.")
        commodity_status = None
        commodities = None
        cd4_total_remaining = None
        crag_total_remaining = None
        tb_lam_total_remaining = None
        # return render(request, template_name,context )
    if request.method == "POST":
        if form.is_valid():
            # reagent_type = form.cleaned_data['reagent_type']
            # try:
            post = form.save(commit=False)
            if not validate_commodity_form(form):
                # If validation fails, return the form with error messages
                return render(request, template_name, context)
            selected_facility = selected_lab.mfl_code

            facility_name = Facilities.objects.filter(mfl_code=selected_facility).first()
            post.facility_name = facility_name
            # now = datetime.now()
            # existing_facility_record = ReagentStock.objects.filter(reagent_type=reagent_type,
            #                                                        facility_name__mfl_code=selected_facility,
            #                                                        remaining_quantity__gt=0,
            #                                                        date_commodity_received__month=now.month)

            #     # TODO FILTER ACTIVE RECORDS(OPERATING BETWEEN 1ST AND END OF THE MONTH)

            post.save()
            messages.error(request, "Record saved successfully!")
            # Generate the URL for the redirect
            url = reverse('add_commodities', kwargs={
                # 'report_type': report_type,
                'pk_lab': pk_lab})
            return redirect(url)

        else:
            messages.error(request, f"Record already exists.")
            render(request, template_name, context)

    context = {
        "form": form, "report_type": "commodity", "commodities": commodities, "commodity_status": commodity_status,
        "title": f"Add Commodities for {selected_lab.name.title()} Laboratory",
        "cd4_total_remaining": cd4_total_remaining, "tb_lam_total_remaining": tb_lam_total_remaining,
        "crag_total_remaining": crag_total_remaining,
    }
    return render(request, 'lab_pulse/add_cd4_data.html', context)


@login_required(login_url='login')
@group_required(['laboratory_staffs_labpulse', 'referring_laboratory_staffs_labpulse'])
def choose_lab(request):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    cd4_testing_lab_form = facilities_lab_Form(request.POST or None)
    if request.method == "POST":
        if cd4_testing_lab_form.is_valid():
            testing_lab_name = cd4_testing_lab_form.cleaned_data['facility_name']
            # Generate the URL for the redirect
            url = reverse('add_commodities',
                          kwargs={
                              'pk_lab': testing_lab_name.id})

            return redirect(url)
    context = {
        "cd4_testing_lab_form": cd4_testing_lab_form,
        "title": "ADD COMMODITIES"
    }
    return render(request, 'lab_pulse/add_cd4_data.html', context)


@login_required(login_url='login')
@group_required(['laboratory_staffs_labpulse'])
def add_facility(request):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    facilities = Facilities.objects.all()

    form = FacilitiesForm(request.POST or None)
    if form.is_valid():
        facility_name = form.cleaned_data['name']
        existing_lab = Facilities.objects.filter(name__iexact=facility_name)
        if existing_lab.exists():
            form.add_error('testing_lab_name', 'A CD4 Testing Lab with this name already exists.')
        else:
            form.save()
            messages.error(request, "Record saved successfully!")
            return redirect("choose_testing_lab")
    context = {
        "form": form,
        "title": f"Add Missing Laboratory",
        "facilities": facilities,
    }
    return render(request, 'lab_pulse/add_cd4_data.html', context)


@login_required(login_url='login')
@group_required(['laboratory_staffs_labpulse', 'referring_laboratory_staffs_labpulse'])
def update_reagent_stocks(request, pk):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    item = ReagentStock.objects.get(id=pk)
    commodity_status, commodities, cd4_total_remaining, crag_total_remaining, tb_lam_total_remaining = \
        show_remaining_commodities(item.facility_name)
    form = ReagentStockForm(instance=item)

    template_name = 'lab_pulse/update results.html'
    context = {
        "form": form,
        "title": "Update Commodities",
        "commodity_status": commodity_status,
        "cd4_total_remaining": cd4_total_remaining, "tb_lam_total_remaining": tb_lam_total_remaining,
        "crag_total_remaining": crag_total_remaining,
    }

    if request.method == "POST":
        form = ReagentStockForm(request.POST, instance=item)
        if form.is_valid():
            post = form.save(commit=False)
            if not validate_commodity_form(form):
                # If validation fails, return the form with error messages
                return render(request, template_name, context)
            selected_facility = item.facility_name.mfl_code

            facility_name = Facilities.objects.filter(mfl_code=selected_facility).first()
            post.facility_name = facility_name
            post.save()
            messages.error(request, "Record updated successfully!")
            # Generate the URL for the redirect
            return HttpResponseRedirect(request.session['page_from'])

    context = {
        "form": form,
        "title": "Update Commodities", "commodity_status": commodity_status, "cd4_total_remaining": cd4_total_remaining,
        "tb_lam_total_remaining": tb_lam_total_remaining,
        "crag_total_remaining": crag_total_remaining,
    }
    return render(request, 'lab_pulse/update results.html', context)


def track_records(df_specific):
    # Convert 'Collection' column to a string
    df_specific['Collection'] = df_specific['Collection'].astype(str)

    # Split the 'Collection' column on 'T' and keep only the first part (the date)
    df_specific['Collection'] = df_specific['Collection'].str.split('T').str[0]

    saved_sample = list(df_specific['Sample Id'].unique())[0]
    return saved_sample


@login_required(login_url='login')
def load_biochemistry_results(request):
    if not request.user.first_name:
        return redirect("profile")
    tests_summary_fig = None
    summary_fig = None
    summary_fig_per_text = None
    weekly_trend_fig = None
    test_trend_fig = None

    #####################################
    # Display existing data
    #####################################
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
        # record_count = int(request.GET.get('record_count', 10))  # Get the selected record count (default: 10)
        record_count = request.GET.get('record_count', '10')
    else:
        record_count = request.GET.get('record_count', '100')

    biochemistry_qs = BiochemistryResult.objects.all()
    record_count_options = [(str(i), str(i)) for i in [5, 10, 20, 30, 40, 50]] + [("all", "All"), ]
    my_filters = BiochemistryResultFilter(request.GET, queryset=biochemistry_qs)
    biochemistry_qs = pagination_(request, my_filters.qs, record_count)

    if my_filters.qs:
        # fields to extract
        fields = ['sample_id', 'patient_id', 'test',
                  'full_name', 'result', 'low_limit', 'high_limit', 'units',
                  'reference_class', 'collection_date', 'result_time', 'mfl_code', 'results_interpretation',
                  'number_of_samples', 'date_created', 'performed_by'
                  ]

        # Extract the data from the queryset using values()
        data = my_filters.qs.values(*fields)
        df = pd.DataFrame(data)
        df = df.rename(columns={"full_name": "test_name"})
        bio_chem_df = df.copy()

        try:
            if "bio_chem_df" in request.session:
                del request.session['bio_chem_df']
            bio_chem_df = bio_chem_df.drop(
                ['test', 'reference_class', 'collection_date', 'mfl_code', 'number_of_samples', 'date_created'], axis=1)
            bio_chem_df['result_time'] = bio_chem_df['result_time'].astype(str)
            request.session['bio_chem_df'] = bio_chem_df.to_dict()
        except KeyError:
            # Handle the case where the session key doesn't exist
            pass

        all_df = df.copy()
        all_df['results_interpretation'] = pd.Categorical(all_df['results_interpretation'],
                                                          ['Low', 'Normal', 'High'])
        all_df.sort_values(['results_interpretation'], inplace=True)
        all_df.sort_values(['number_of_samples'], inplace=True)

        b = all_df.groupby(["results_interpretation", "test_name", "reference_class"]).sum(numeric_only=True)[
            'number_of_samples'].reset_index()

        color_discrete_map = {'Normal': 'green', 'High': 'red', 'Low': 'blue'}
        fig = px.bar(b, x="test_name", y="number_of_samples", text="number_of_samples", height=500,
                     title=f"Distribution of Test Results by Interpretation N={b['number_of_samples'].sum()}",
                     color="results_interpretation",
                     color_discrete_map=color_discrete_map)
        fig.update_layout(legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ))
        tests_summary_fig = plot(fig, include_plotlyjs=False, output_type="div")

        df['results_interpretation'] = pd.Categorical(df['results_interpretation'],
                                                      ['Low', 'Normal', 'High'])
        b = df.groupby("results_interpretation").sum(numeric_only=True)['number_of_samples'].reset_index()

        fig = px.bar(b, x="results_interpretation", y="number_of_samples", text="number_of_samples", height=350,
                     title=f"Overall Results interpretation N={b['number_of_samples'].sum()}")
        # fig.update_layout({
        #     'plot_bgcolor': 'rgba(0, 0, 0, 0)',
        #     'paper_bgcolor': 'rgba(0, 0, 0, 0)',
        # })
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
        summary_fig = plot(fig, include_plotlyjs=False, output_type="div")

        b = df.groupby("test_name").sum(numeric_only=True)['number_of_samples'].reset_index().sort_values(
            "number_of_samples")

        fig = px.bar(b, x="test_name", y="number_of_samples", text="number_of_samples", height=350,
                     title=f"Distribution of Tests Conducted N={b['number_of_samples'].sum()}")
        # fig.update_layout({
        #     'plot_bgcolor': 'rgba(0, 0, 0, 0)',
        #     'paper_bgcolor': 'rgba(0, 0, 0, 0)',
        # })
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
        summary_fig_per_text = plot(fig, include_plotlyjs=False, output_type="div")

        ###################################
        # Weekly Trend viz
        ###################################
        df_weekly = df.copy()
        df_weekly['date_created'] = pd.to_datetime(df_weekly['date_created'], format='%Y-%m-%d')

        df_weekly['week_start'] = df_weekly['date_created'].dt.to_period('W').dt.start_time
        weekly_df = df_weekly.groupby('week_start').size().reset_index(name='number_of_samples')
        weekly_df['Weekly Trend'] = weekly_df["week_start"].astype(str) + "."
        weekly_trend = weekly_df['number_of_samples'].sum()
        if weekly_df.shape[0] > 1:
            weekly_trend_fig = line_chart_median_mean(weekly_df, "Weekly Trend", "number_of_samples",
                                                      f"Weekly Trend of sample uploaded N={weekly_trend}"
                                                      f"      Maximum : {max(weekly_df['number_of_samples'])}")

        weekly_df = df_weekly.groupby(['week_start', 'test_name']).size().reset_index(name='number_of_samples')
        weekly_df['Weekly Trend'] = weekly_df["week_start"].astype(str) + "."
        test_trend_fig = {}
        for i in sorted(weekly_df['test_name'].unique()):
            ind_test_df = weekly_df[weekly_df["test_name"] == i]
            fig = px.line(ind_test_df, x="Weekly Trend", y="number_of_samples", text="number_of_samples", height=500,
                          title=f"Weekly trend for samples uploaded ({i}) N={ind_test_df['number_of_samples'].sum()}",
                          )
            fig.update_layout(legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ))
            fig.update_traces(textposition='top center')
            test_trend_fig[i] = plot(fig, include_plotlyjs=False, output_type="div")

    title = "Results"
    threshold_of_result_to_display = 500
    form = BiochemistryForm()
    context = {"title": title, "biochemistry_qs": biochemistry_qs, "record_count_options": record_count_options,
               "my_filters": my_filters, "record_count": record_count, "tests_summary_fig": tests_summary_fig,
               "threshold_of_result_to_display": threshold_of_result_to_display, "summary_fig": summary_fig,
               "summary_fig_per_text": summary_fig_per_text, "weekly_trend_fig": weekly_trend_fig, "form": form,
               "test_trend_fig": test_trend_fig}

    #####################################
    # Load new data
    #####################################
    if request.method == 'POST':
        form = BiochemistryForm(request.POST, request.FILES)
        if form.is_valid():
            files = request.FILES.getlist('files')
            if files:
                performed_by = form.cleaned_data['performed_by']
                dfs = []
                for file in files:
                    csv_data = io.StringIO(file.read().decode('ISO-8859-1'))
                    dfs.append(pd.read_csv(csv_data, sep=';', quotechar='"', encoding='ISO-8859-1'))
                df = pd.concat(dfs)
                if "Low Limit" in df.columns and "High Limit" in df.columns:
                    df = biochemistry_data_prep(df)
                    saved = []
                    already_exist = []
                    for sample in df['Patient Id'].unique():
                        df_copy = df.copy()
                        df_specific = df_copy[df_copy['Patient Id'] == sample]
                        try:
                            with transaction.atomic():
                                if df_specific.shape[1] == 14:
                                    # Iterate over each row in the DataFrame
                                    for index, row in df_specific.iterrows():
                                        chemistry_results = BiochemistryResult()
                                        chemistry_results.sample_id = row[df_specific.columns[0]]
                                        chemistry_results.patient_id = row[df_specific.columns[1]]
                                        chemistry_results.test = row[df_specific.columns[2]]
                                        chemistry_results.full_name = row[df_specific.columns[3]]
                                        chemistry_results.result = row[df_specific.columns[4]]
                                        chemistry_results.low_limit = row[df_specific.columns[5]]
                                        chemistry_results.high_limit = row[df_specific.columns[6]]
                                        chemistry_results.units = row[df_specific.columns[7]]
                                        chemistry_results.reference_class = row[df_specific.columns[8]]
                                        chemistry_results.collection_date = row[df_specific.columns[9]]
                                        chemistry_results.result_time = row[df_specific.columns[10]]
                                        chemistry_results.mfl_code = row[df_specific.columns[11]]
                                        chemistry_results.results_interpretation = row[df_specific.columns[12]]
                                        chemistry_results.number_of_samples = row[df_specific.columns[13]]
                                        chemistry_results.performed_by = performed_by
                                        chemistry_results.save()
                                    saved.append(track_records(df_specific))
                                else:
                                    # Notify the user that the data is not correct
                                    messages.error(request, f'Invalid files...Kindly upload the correct file')
                                    redirect('load_data')
                        except IntegrityError:
                            already_exist.append(track_records(df_specific))
                            continue
                else:
                    messages.error(request, "Upload the correct file!")
                    return render(request, 'lab_pulse/upload.html', context)
                saved_list = ', '.join(str(saved_sample) for saved_sample in sorted(saved))
                if len(saved_list) > 0:
                    sample_ids_count = len(saved)
                    if sample_ids_count > 1:
                        messages.error(request,
                                       f'{sample_ids_count} sample IDs were successfully saved in the database: {saved_list}')
                    else:
                        messages.error(request, f'One sample ID was successfully saved in the database: {saved_list}')
                already_lists = ', '.join(str(exist) for exist in sorted(already_exist))

                if len(already_exist) > 0:
                    if len(list(already_exist)) == len(df['Sample Id'].unique()):
                        error_msg = f"The entire Biochemistry dataset has already been uploaded. Sample IDs: ({already_lists})"
                    else:
                        error_msg = f"Biochemistry data already exists for the following sample IDs: {already_lists}"
                    messages.error(request, error_msg)
                return redirect('load_biochemistry_results')
    return render(request, 'lab_pulse/upload.html', context)


# Create a function to add an image to the canvas
def add_image(pdf, image_path, x, y, width, height):
    pdf.drawImage(image_path, x, y, width, height)


def insert_dataframe_to_pdf(pdf, df, x, y):
    # Convert the DataFrame to a list of lists
    data = [df.columns.tolist()] + df.values.tolist()

    # Create a table from the data
    table = Table(data)

    # Add style to the table
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),  # Header row background color
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),  # Header text color
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),  # Data row background color
        ('GRID', (0, 0), (-1, -1), 1, colors.black)  # Grid lines
    ]))

    # Add the table to the PDF
    table.wrapOn(pdf, 0, 0)
    table.drawOn(pdf, x, y)  # Adjust the position (x, y) as needed


def create_page(request, pdf, y, image_path, ccc_num, sample_id, df1, start_x=80):
    width = letter[0] - 100
    # Add the image to the canvas above the "BIOCHEMISTRY REPORT" text and take the full width
    add_image(pdf, image_path, x=start_x, y=y, width=width, height=100)

    width = letter[0] - 35

    pdf.setFont("Courier-Bold", 18)
    # Write the facility name in the top left corner of the page
    pdf.drawString(250, y - 25, "BIOCHEMISTRY REPORT")
    pdf.setDash(1, 0)  # Reset the line style
    pdf.line(x1=start_x, y1=y - 10, x2=width, y2=y - 10)
    pdf.line(x1=start_x, y1=y - 30, x2=width, y2=y - 30)
    # Facility info
    pdf.setFont("Helvetica", 12)
    pdf.drawString(start_x, y - 50, f"Unique CCC No: {ccc_num}")
    pdf.drawString(start_x + 200, y - 50, f"Sample Id: {sample_id}")
    performed_by_values = df1['performed_by'].dropna().unique()  # Drop NA/null values and get unique values
    if len(performed_by_values) > 0:
        formatted_value = performed_by_values[0].title()
        pdf.drawString(start_x + 300, y - 50, f"Test Performed by: {formatted_value}")
    df1 = df1.drop("performed_by", axis=1)

    # Insert dataframe
    pdf.setFont("Helvetica", 8)
    insert_dataframe_to_pdf(pdf, df1, start_x - 9, y - 200)
    pdf.setFont("Helvetica", 4)
    pdf.setFillColor(colors.grey)
    formatted_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pdf.drawString((letter[0] / 3) + 30, y - 210,
                   f"Report downloaded by: {request.user}    Time: {formatted_time}")
    pdf.setFont("Helvetica", 12)
    pdf.setFillColor(colors.black)

    pdf.setDash(1, 2)  # Reset the line style
    pdf.line(x1=start_x, y1=y - 220, x2=width, y2=y - 220)


class GenerateBioChemistryPDF(View):
    def get(self, request):
        if request.user.is_authenticated and not request.user.first_name:
            return redirect("profile")

        # Retrieve the serialized DataFrame from the session
        df = request.session.get('bio_chem_df', {})

        # Convert the dictionary back to a DataFrame
        df1 = pd.DataFrame.from_dict(df)

        # Create a new PDF object using ReportLab
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'filename="Biochemistry Report.pdf"'
        pdf = canvas.Canvas(response, pagesize=letter)

        y = 680

        # Get the image path using the find function from staticfiles.finders
        image_path = find('images/biochem_image.png')

        # Generate reports
        for index, i in enumerate(sorted(df1['patient_id'].unique())):
            if index % 2 == 0 and index != 0:
                pdf.showPage()
                y = 680
            df2 = df1[df1['patient_id'] == i]
            sample_id = df2['sample_id'].values[0]
            ccc_num = df2['patient_id'].values[0]
            df2 = df2.drop(["patient_id", "sample_id"], axis=1)  # drop Patient Id and Sample Id
            df2 = df2.rename(columns={"Full name": "Test"})  # Rename column
            create_page(request, pdf, y, image_path, ccc_num, sample_id, df2)
            y = y - 400  # Adjust the y value for the next result on the same page

        pdf.save()
        return response


def convert_np_datetime64_to_datetime(date_np):
    """
    Convert a numpy.datetime64 object to a datetime object.

    Parameters:
        date_np (numpy.datetime64): The input numpy.datetime64 object.

    Returns:
        datetime: The converted datetime object.

    Example:
        Assuming df3['date_collected'].unique()[0] is a numpy.datetime64 object:
        date_collected_np = df3['date_collected'].unique()[0]
        converted_date = convert_np_datetime64_to_datetime(date_collected_np)
    """
    # Convert the numpy.datetime64 to a string with a specific format
    date_str = date_np.astype('datetime64[us]').astype(str)
    # Convert the string to a datetime object
    date_obj = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%f')
    return date_obj


def save_drt_data(request, resistance_patterns_df, model_class, field_mapping, facility_id, all_subcounties,
                  all_counties, drt_file_form):
    for index, row in resistance_patterns_df.iterrows():
        drt_results = model_class()

        # Set common fields
        drt_results.date_received = row['date_received']
        drt_results.date_reported = row['date_reported']
        drt_results.date_test_performed = row['date_test_perfomed']
        drt_results.collection_date = row['date_collected']

        drt_results.patient_id = row['patient_id']
        drt_results.sequence_summary = row['sequence summary']
        drt_results.haart_class = row['haart_class']
        drt_results.test_perfomed_by = row['test_perfomed_by']
        drt_results.age = row['age']
        drt_results.sex = row['sex']
        drt_results.age_unit = row['age_unit']

        # Set model-specific fields using field_mapping
        for field, value in field_mapping.items():
            setattr(drt_results, field, row[value])

        # Check for uniqueness before saving
        if not model_class.objects.filter(
                Q(patient_id=drt_results.patient_id) &
                Q(collection_date=drt_results.collection_date) &
                (
                        Q(drug=row[field_mapping.get('drug', '')]) if 'drug' in field_mapping else
                        Q(mutation_type=row[field_mapping.get('mutation_type', '')])
                )
        ).exists():
            # Save the DrtPdfFile only if no related DrtResults exist
            drt_file_instance = drt_file_form.save()
            drt_results.result = drt_file_instance
        else:
            # Handle the case when the record already exists
            msg = f"A record for Patient ID {drt_results.patient_id} collected on " \
                  f"{drt_results.collection_date.strftime('%Y-%m-%d')} already exists."
            messages.error(request, msg)

        # Assign facility, subcounty, and county
        drt_results.facility_name = facility_id
        drt_results.sub_county = Sub_counties.objects.get(id=all_subcounties[0].sub_counties_id)
        drt_results.county = Counties.objects.get(id=all_counties[0].counties_id)

        drt_results.save()


def group_resistance_patterns(df_resistant_patterns, cols_to_groupby):
    resistance_counts = df_resistant_patterns.groupby(cols_to_groupby).count()['patient_id'].reset_index()
    resistance_counts = resistance_counts.sort_values(by=['resistance_level', 'haart_class'], ascending=False)
    resistance_counts = resistance_counts.rename(columns={"patient_id": "Number of DRT tests"})
    return resistance_counts


def categorize_age(age):
    """
    Categorizes an age into predefined age bands.

    Parameters:
    - age (int): The age to be categorized.

    Returns:
    - str: The age band category.

    Example usage:
    # Apply the function to create a new 'age_band' column
    resistance_num['age_band'] = resistance_num['age'].apply(categorize_age)

    """
    if age < 1:
        return '<1'
    elif age <= 4:
        return '1-4.'
    elif age <= 9:
        return '5-9'
    elif age <= 14:
        return '10-14.'
    elif age <= 19:
        return '15-19'
    elif age <= 24:
        return '20-24'
    elif age <= 29:
        return '25-29'
    elif age <= 34:
        return '30-34'
    elif age <= 39:
        return '35-39'
    elif age <= 44:
        return '40-44'
    elif age <= 49:
        return '45-49'
    elif age <= 54:
        return '50-54'
    elif age <= 59:
        return '55-59'
    elif age <= 64:
        return '60-64'
    else:
        return '65+'


def prepare_age_resistant_patterns(df_resistant_patterns, groupby_list):
    if "resistance_level" in groupby_list:
        df_resistant_patterns = df_resistant_patterns.rename(columns={"patient_id": "Number of Drugs"})
        resistance_num = df_resistant_patterns.groupby(groupby_list).count()['Number of Drugs'].reset_index()
        # Apply the function to create a new 'age_band' column
        resistance_num['age_band'] = resistance_num['age'].apply(categorize_age)

        # Group by 'resistance_level' and 'age_band', then sum the 'Number of Drugs'
        result = resistance_num.groupby(['resistance_level', 'age_band']).agg({'Number of Drugs': 'sum'}).reset_index()
    else:
        df_resistant_patterns = df_resistant_patterns.rename(columns={"patient_id": "Number of DRT results"})
        resistance_num = df_resistant_patterns.drop_duplicates(['Number of DRT results'])
        # Apply the function to create a new 'age_band' column
        resistance_num['age_band'] = resistance_num['age'].apply(categorize_age)

        result = resistance_num.groupby(['age_band', 'sex']).count()['Number of DRT results'].reset_index()
    # # Define the custom sorting order
    # custom_order = ['<1', '1-4.', '5-9', '10-14.', '15-19', '20-24', '25-29', '30-34', '35-39', '40-44', '45-49',
    #                 '50-54', '55-59', '60-64', '65+']
    #
    # # Convert the 'age_band' column to Categorical with custom ordering
    # result['age_band'] = pd.Categorical(result['age_band'], categories=custom_order, ordered=True)
    #
    # # Sort the DataFrame by 'age_band'
    # result = result.sort_values('age_band')
    result, custom_order = sort_custom_agebands(result, 'age_band')
    return result


def sort_custom_agebands(df, col):
    # Define the custom sorting order
    custom_order = ['<1', '1-4.', '5-9', '10-14.', '15-19', '20-24', '25-29', '30-34', '35-39', '40-44', '45-49',
                    '50-54', '55-59', '60-64', '65+']

    # Convert the specified column to Categorical with custom ordering
    df[col] = pd.Categorical(df[col], categories=custom_order, ordered=True)

    # Get the unique values present in the specified column
    available_age_bands = df[col].unique()

    # Sort the DataFrame by the specified column
    df = df.sort_values(col)

    # Return the sorted DataFrame and the available custom order
    return df, available_age_bands


def add_percentage(df4, col, main_col):
    dfs = []
    for specific_drug in df4[main_col].unique():
        specific_drug_df = df4[df4[main_col] == specific_drug].copy()
        totals = specific_drug_df[col].sum()
        specific_drug_df['%'] = round(specific_drug_df[col] / totals * 100, )
        specific_drug_df['%.'] = specific_drug_df['%'].astype(int).astype(str) + "%"
        specific_drug_df[f'{col} (%)'] = specific_drug_df[col].astype(str) + " (" + specific_drug_df[
            '%'].astype(int).astype(str) + "%)"
        dfs.append(specific_drug_df)
    df = pd.concat(dfs)
    return df


def get_month_resistance_order(drug_df, desired_order=None):
    """
    Organize the DataFrame for plotting based on desired orders.

    Parameters:
        drug_df (pd.DataFrame): The DataFrame containing the data.
        desired_order: List of resistance levels

    Returns:
        tuple: A tuple containing the order for months and resistance levels.
    """
    # Define the desired order for resistance_level
    if desired_order is None:
        desired_order = ['Susceptible', 'Potential Low-Level Resistance', 'Low-level resistance',
                         'Intermediate Resistance', 'High-Level Resistance']

    # Get unique resistance levels from the DataFrame
    unique_resistance_levels = drug_df['resistance_level'].unique()

    # Create a list of sorted resistance levels based on the desired order
    resistance_order = sorted(unique_resistance_levels, key=lambda x: desired_order.index(x))

    # Update the DataFrame with categorical types
    drug_df['resistance_level'] = pd.Categorical(drug_df['resistance_level'], categories=resistance_order, ordered=True)

    # Sort the DataFrame by the formatted_collected_date
    drug_df = drug_df.sort_values("formatted_collected_date")

    # Get the unique months from the sorted DataFrame
    month_order = drug_df['formatted_date'].unique()

    return month_order, resistance_order


def generate_bar_chart(data, x_col, y_col, color_col, title, text_col, color_map, xaxis_title=None,
                       category_orders=None):
    fig = px.bar(data, x=x_col, y=y_col, color=color_col, text=text_col,
                 title=title, height=500, category_orders=category_orders, color_discrete_map=color_map)

    fig.update_layout(
        xaxis_title=f"{xaxis_title}",
        yaxis_title=f"{y_col}",
        legend_title=f"{xaxis_title}",
    )

    # Adjust the legend
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
                size=16
            )
        )
    )

    return plot(fig, include_plotlyjs=False, output_type="div")


def filter_last_n_months(df, date_column='formatted_collected_date', n_months=12):
    """
    Filter a DataFrame to include only the last n months of data.

    Parameters:
    - df: DataFrame
    - date_column: str, the name of the column containing date information
    - n_months: int, the number of months to include in the filter

    Returns:
    - DataFrame, the filtered DataFrame
    """
    # Ensure 'formatted_collected_date' is in datetime format
    df[date_column] = pd.to_datetime(df[date_column], format='%Y-%m-%d')

    # Sort the DataFrame by 'formatted_collected_date'
    df = df.sort_values(date_column)

    # Find the cutoff date for the last n months
    cutoff_date = df[date_column].max() - pd.DateOffset(months=n_months)

    # Filter the DataFrame to include only the last n months
    df_last_n_months = df[df[date_column] >= cutoff_date]

    return df_last_n_months


def dynamic_pivot(df, index_col, columns_col, values_col, agg_func='sum', fill_value=0):
    """
    Dynamically pivots a DataFrame based on specified columns.

    Parameters:
    - df: DataFrame to be pivoted.
    - index_col: Column to be used as the index.
    - columns_col: Column to be used as the new columns.
    - values_col: Column to be used as the values.
    - aggfunc: Aggregation function for duplicate entries. Default is 'sum'.
    - fill_value: Fill value for missing entries. Default is 0.

    Returns:
    - Pivoted DataFrame.
    """
    pivoted_df = pd.pivot_table(df, values=values_col, index=index_col, columns=columns_col, aggfunc=agg_func,
                                fill_value=fill_value)
    pivoted_df.reset_index(inplace=True)
    return pivoted_df


def pop_pyramid_chart(data, male_col=None, female_col=None, title=None, age_col='age_band', chart_height=500, ):
    y = data[age_col]

    # Convert to pandas Series if male_col or female_col is not None
    x1 = data[male_col] if male_col is not None else pd.Series()
    x2 = data[female_col] * -1 if female_col is not None else pd.Series()

    # Calculate tick values and text dynamically based on data range
    max_value = max(max(x1, default=0), max(x2, default=0))

    # tickvals = list(range(-max_value, max_value + tick_interval, tick_interval))
    # ticktext = [f'{abs(val)}K' if val != 0 else '0' for val in tickvals]
    if max_value > 10000:
        tick_interval = 20000  # Change tick interval for values in thousands
    elif max_value > 1000:
        tick_interval = 2000  # Change tick interval for values in hundreds
    elif max_value > 100:
        tick_interval = 200  # Change tick interval for values in hundreds
    elif max_value > 10:
        tick_interval = 20  # Change tick interval for values in hundreds
    else:
        tick_interval = 2  # Default tick interval for values in tens

    tickvals = list(range(-max_value, max_value + tick_interval, tick_interval))
    ticktext = [f'{abs(val):,}' if val != 0 else '0' for val in tickvals]

    # Create instance of the figure
    fig = go.Figure()
    if male_col is not None:
        # Add Trace to Figure
        fig.add_trace(go.Bar(y=y, x=x1, name='Male', orientation='h', text=x1,
                             textposition='inside'  # Set text position to 'inside'
                             ))
    if female_col is not None:
        # Add Trace to figure
        fig.add_trace(go.Bar(y=y, x=x2, name='Female', orientation='h', text=x2 * -1,
                             textposition='inside'  # Set text position to 'inside'
                             ))
    if male_col and female_col:
        xaxis_text = f'Gender: [{female_col}/{male_col}]'
    elif male_col:
        xaxis_text = f'Gender: [{male_col}]'
    else:
        xaxis_text = f'Gender: [{female_col}]'

    # Update Figure Layout
    fig.update_layout(title=f'{title}', title_font_size=16, barmode='relative', bargap=0.0, bargroupgap=0,
                      xaxis=dict(tickvals=tickvals, ticktext=ticktext, title=xaxis_text,
                                 title_font_size=14
                                 ),
                      height=chart_height,  # Set the height of the chart
                      legend=dict(
                          title='Gender',  # Update legend title
                          orientation='h',  # Set legend orientation to horizontal
                          x=0,  # Set x to 0 for left-align, adjust as needed
                          y=1.1  # Set y to 1.1 for top position, adjust as needed
                      )
                      )
    fig.update_layout(uniformtext_minsize=14, uniformtext_mode='hide')

    # return figure
    return plot(fig, include_plotlyjs=False, output_type="div")


def prepare_drt_cascade_df(df_cascade):
    # Calculate proportions
    total_tested = len(df_cascade)
    failed_count = len(df_cascade[df_cascade['sequence_summary'] == 'FAILED'])
    passed_count = len(df_cascade[df_cascade['sequence_summary'] == 'PASSED'])

    failed_proportion = round(failed_count / total_tested * 100, )
    passed_proportion = round(passed_count / total_tested * 100, )

    # Create a summary DataFrame with proportions
    summary_df_cascade = pd.DataFrame({
        'variables': ['Total Tested', 'Passed', 'Failed'],
        'counts': [total_tested, passed_count, failed_count],
        '%': ["1", passed_proportion, failed_proportion]
    })

    summary_df_cascade['count (%)'] = summary_df_cascade['counts'].astype(str) + " (" + summary_df_cascade['%'].astype(
        str) + "%)"
    # Find the index of the 'Total Tested' row
    total_tested_index = summary_df_cascade[summary_df_cascade['variables'] == 'Total Tested'].index

    # Update the 'count (%)' value for 'Total Tested'
    summary_df_cascade.loc[total_tested_index, 'count (%)'] = summary_df_cascade.loc[
        total_tested_index, 'count (%)'].str.replace(r" \(\d+%\)", "", regex=True)

    return summary_df_cascade


def add_percentage_and_count_string(haart_class_df):
    # Calculate percentage and round to the nearest integer
    haart_class_df['%'] = round(haart_class_df['count'] / haart_class_df['count'].sum() * 100).astype(int)

    # Create a new column with count and percentage string
    haart_class_df['count (%)'] = haart_class_df['count'].astype(str) + " (" + haart_class_df['%'].astype(str) + "%)"

    return haart_class_df


def get_mutation_counts(df_initial, mutation_type, ccc_num):
    df = df_initial[df_initial['mutation_type'] == mutation_type]

    # Extract unique mutations
    profile_list = list(df['mutations'].unique())

    # Split each string into a list of values
    mutations_list = [mutation.split(',') for mutation in profile_list if mutation != ""]

    # Flatten the list of lists
    flat_mutations_list = [mutation.strip() for sublist in mutations_list for mutation in sublist if
                           mutation.strip() != '']

    # Create a DataFrame with mutations and count columns
    df_mutations = pd.DataFrame({'mutations': flat_mutations_list})

    # Count the occurrences of each mutation
    mutation_counts = df_mutations['mutations'].value_counts().reset_index()

    # Rename the columns
    mutation_counts.columns = ['mutations', 'count']

    # Add HAART class column
    mutation_counts.insert(0, "haart_class", df['haart_class'].unique()[0])
    mutation_counts["haart_class"] = mutation_counts["haart_class"].str.strip()

    mutation_counts.insert(0, "mutation_type", mutation_type)
    mutation_counts["mutation_type"] = mutation_counts["mutation_type"].str.strip()
    mutation_counts.insert(0, "age", int(df['age'].unique()[0]))
    mutation_counts.insert(0, "patient_id", ccc_num)

    return mutation_counts


def generate_mutation_profile_figs(df_resistant_profiles):
    # Clean and filter the input DataFrame
    df_resistant_profiles['mutation_type'] = df_resistant_profiles['mutation_type'].str.strip()
    df_resistant_profiles = df_resistant_profiles[
        (df_resistant_profiles['sequence_summary'].notna()) &
        (~df_resistant_profiles['sequence_summary'].str.contains("fail", case=False, na=False))
        ]

    dfs = []
    # Loop through mutation types and patient IDs to generate mutation counts
    for mutation_type in df_resistant_profiles['mutation_type'].unique():
        for ccc_num in df_resistant_profiles['patient_id'].unique():
            df_specific_pt = df_resistant_profiles[df_resistant_profiles['patient_id'] == ccc_num]
            result_df = get_mutation_counts(df_specific_pt, mutation_type, ccc_num)
            dfs.append(result_df)

    # Concatenate mutation counts DataFrames
    mutations_df = pd.concat(dfs).reset_index(drop=True)
    df_mutations = mutations_df.groupby(['mutation_type', 'mutations']).sum()['count'].reset_index().sort_values(
        "count", ascending=False)

    # Set specific order for mutation types
    df_mutations['mutation_type'] = pd.Categorical(df_mutations['mutation_type'],
                                                   ['NRTI Mutations', 'NNRTI Mutations', 'RT Other Mutations',
                                                    'PI Major Mutations', 'PI Accessory Mutations',
                                                    'PR Other Mutations', 'INSTI Major Mutations',
                                                    'INSTI Accessory Mutations', 'IN Other Mutations'])

    df_mutations.sort_values(['mutation_type'], inplace=True)
    mutation_profile_figs = {}

    # Generate bar charts for each mutation type
    for i in df_mutations['mutation_type'].unique():
        haart_class_df = df_mutations[df_mutations['mutation_type'] == i]
        haart_class_df = haart_class_df.copy().sort_values("count", ascending=False)
        haart_class_df = add_percentage_and_count_string(haart_class_df)

        mutation_profile_figs[i] = bar_chart(haart_class_df, 'mutations', "count",
                                             f"Prevalent Mutation Types by Class: {i} N={haart_class_df['count'].sum()}",
                                             text="count (%)",
                                             background_shadow=True, height=400, title_size=16,
                                             xaxis_title='Mutations',
                                             axis_text_size=14)

    return mutation_profile_figs


def classify_resistance_type(df, resistance_col='resistance_level', new_col='resistance_type'):
    """
    Classify resistance type based on the conditions specified.

    Parameters:
    - df: DataFrame
        The input DataFrame.
    - resistance_col: str
        The name of the column containing resistance levels.
    - new_col: str
        The name of the new column to be created.

    Returns:
    - DataFrame
        The input DataFrame with the new column added.
    """

    # Create a copy of the DataFrame to avoid modifying the original
    df = df.copy()

    # Check conditions using loc to set values
    if all(df[resistance_col] == 'Susceptible'):
        df[new_col] = 'Susceptible'
    elif all(df[resistance_col] == 'Potential Low-Level Resistance'):
        df[new_col] = 'Potential Low-Level Resistance'
    elif all(df[resistance_col] == 'Low-level resistance'):
        df[new_col] = 'Low-level resistance'
    elif all(df[resistance_col] == 'Intermediate Resistance'):
        df[new_col] = 'Intermediate Resistance'
    elif all(df[resistance_col] == 'High-Level Resistance'):
        df[new_col] = 'High-Level Resistance'
    else:
        df[new_col] = 'Mixed Resistance'

    return df


def count_resistance_types(df, patient_id="patient_id", resistance_type="resistance_type"):
    """
    Count the occurrences of each resistance type per patient ID.

    Parameters:
    - df: DataFrame
        The input DataFrame.

    Returns:
    - DataFrame
        DataFrame containing counts of each resistance type per patient ID.
    """
    dfs = []
    df = df[~df['sequence_summary'].str.contains("fail", case=False)]
    for pt_id in df[patient_id].unique():
        pt_level_df = df[df[patient_id] == pt_id]
        result_df = classify_resistance_type(pt_level_df)
        dfs.append(result_df.head(1))

    pt_level_df = pd.concat(dfs)
    pt_level_df = pt_level_df.groupby([resistance_type]).count()[patient_id].reset_index()
    pt_level_df.columns = ['resistance_type', 'count']
    return pt_level_df


def prepare_drt_summary(my_filters, trend_figs, drt_trend_fig, resistance_level_age_fig, resistance_level_fig,
                        drt_distribution_fig, age_summary_fig, drt_tat_fig, prevalence_tat_fig, age_pop_summary_fig,
                        drt_summary_fig, counties_summary_fig, mutation_profile_figs, resistance_type_count_fig):
    # fields to extract
    fields = ['drt_results__patient_id', 'drt_results__collection_date', 'drt_results__county__county_name',
              'drt_results__sub_county__sub_counties',
              'drt_results__facility_name__name', 'drt_results__facility_name__mfl_code', 'drt_results__age',
              'drt_results__age_unit', 'drt_results__sex',
              'drt_results__date_received', 'drt_results__date_reported', 'drt_results__date_test_performed',
              'drt_results__drug_abbreviation',
              'drt_results__resistance_level', 'drt_results__drug',
              'drt_results__sequence_summary', 'drt_results__haart_class', 'drt_results__test_perfomed_by',
              'drt_results__tat_days', 'drt_results__age_unit']

    # Extract the data from the queryset using values()
    data = my_filters.qs.values(*fields)
    df_resistant_patterns = pd.DataFrame(data)
    df_resistant_patterns = df_resistant_patterns.rename(columns={
        'drt_results__patient_id': 'patient_id', 'drt_results__collection_date': 'collection_date',
        'drt_results__county__county_name': 'county_name', 'drt_results__sub_county__sub_counties': 'sub_counties',
        'drt_results__facility_name__name': 'facility_name', 'drt_results__facility_name__mfl_code': 'mfl_code',
        'drt_results__age': 'age', 'drt_results__age_unit': 'age_unit', 'drt_results__sex': 'sex',
        'drt_results__date_received': 'date_received', 'drt_results__tat_days': 'tat_days',
        'drt_results__date_reported': 'date_reported', 'drt_results__date_test_performed': 'date_test_performed',
        'drt_results__drug_abbreviation': 'drug_abbreviation', 'drt_results__drug': 'drug',
        'drt_results__resistance_level': 'resistance_level', 'drt_results__sequence_summary': 'sequence_summary',
        'drt_results__haart_class': 'haart_class', 'drt_results__test_perfomed_by': 'test_perfomed_by', })
    df_resistant_patterns_copy = df_resistant_patterns.copy()
    df_resistant_patterns = df_resistant_patterns[
        (df_resistant_patterns['sequence_summary'].notna()) &
        (~df_resistant_patterns['sequence_summary'].str.contains("fail", case=False, na=False))
        ]

    # fields to extract
    profile_fields = ['drt_profile__patient_id', 'drt_profile__collection_date', 'drt_profile__county__county_name',
                      'drt_profile__sub_county__sub_counties', 'drt_profile__facility_name__name',
                      'drt_profile__facility_name__mfl_code', 'drt_profile__age', 'drt_profile__age_unit',
                      'drt_profile__sex', 'drt_profile__date_received', 'drt_profile__date_reported',
                      'drt_profile__date_test_performed', 'drt_profile__mutation_type', 'drt_profile__mutations',
                      'drt_profile__sequence_summary', 'drt_profile__haart_class', 'drt_profile__test_perfomed_by',
                      'drt_profile__tat_days', 'drt_profile__age_unit']

    # Extract the data from the queryset using values()
    data = my_filters.qs.values(*profile_fields)
    df_resistant_profiles = pd.DataFrame(data)
    df_resistant_profiles = df_resistant_profiles.rename(columns={
        'drt_profile__patient_id': 'patient_id', 'drt_profile__collection_date': 'collection_date',
        'drt_profile__county__county_name': 'county_name', 'drt_profile__sub_county__sub_counties': 'sub_counties',
        'drt_profile__facility_name__name': 'facility_name', 'drt_profile__facility_name__mfl_code': 'mfl_code',
        'drt_profile__age': 'age', 'drt_profile__age_unit': 'age_unit', 'drt_profile__sex': 'sex',
        'drt_profile__date_received': 'date_received',
        'drt_profile__date_reported': 'date_reported', 'drt_profile__date_test_performed': 'date_test_performed',
        'drt_profile__mutations': 'mutations', 'drt_profile__mutation_type': 'mutation_type',
        'drt_profile__resistance_level': 'resistance_level', 'drt_profile__sequence_summary': 'sequence_summary',
        'drt_profile__haart_class': 'haart_class', 'drt_profile__test_perfomed_by': 'test_perfomed_by',
        'drt_profile__tat_days': 'tat_days'})
    df_resistant_profiles = df_resistant_profiles.dropna(subset=['patient_id', 'collection_date'], how='all')
    df_resistant_profiles = df_resistant_profiles[
        (df_resistant_profiles['sequence_summary'].notna()) &
        (~df_resistant_profiles['sequence_summary'].str.contains("fail", case=False, na=False))
        ]

    if df_resistant_profiles.shape[0] > 0:
        mutation_profile_figs = generate_mutation_profile_figs(df_resistant_profiles)

    if df_resistant_patterns.shape[0] > 0:
        # Define the replacement dictionary
        replacement_dict = {'High-Level ': 'High-Level Resistance', 'Susceptible': 'Susceptible',
                            'Potential': 'Potential Low-Level Resistance', 'Intermediate': 'Intermediate Resistance',
                            'Low-Level Resistance': 'Low-level resistance'
                            }

        # Apply the replacements using str.contains and np.select
        df_resistant_patterns['resistance_level'] = np.select(
            [df_resistant_patterns['resistance_level'].str.contains(value, case=False) for value in
             replacement_dict.keys()],
            [replacement_dict[value] for value in replacement_dict.keys()],
            default=df_resistant_patterns['resistance_level']
        )

        df_resistant_patterns['sequence_summary'] = df_resistant_patterns['sequence_summary'].astype(str).str.upper()
        df_resistant_patterns['collection_date'] = pd.to_datetime(
            df_resistant_patterns['collection_date']).dt.tz_convert('Africa/Nairobi')
        df_resistant_patterns['formatted_date'] = df_resistant_patterns['collection_date'].dt.strftime('%b-%Y')
        df_resistant_patterns['formatted_collected_date'] = pd.to_datetime(df_resistant_patterns['formatted_date'],
                                                                           format='%b-%Y')

        df_resistant_patterns = df_resistant_patterns.drop_duplicates(
            ['patient_id', 'drug_abbreviation', 'collection_date'])
        df_resistant_patterns = df_resistant_patterns[~df_resistant_patterns['drug'].str.contains("INHIBITORS")]
        df_resistant_patterns = df_resistant_patterns[df_resistant_patterns['drug'] != "nan"]
        ###############################################
        # DRT CASCADE
        ###############################################
        df_cascade = df_resistant_patterns_copy.drop_duplicates("patient_id", keep="first")
        summary_df_cascade = prepare_drt_cascade_df(df_cascade)
        drt_summary_fig = bar_chart(summary_df_cascade, "variables", "counts", f"DRT Summary", text="count (%)",
                                    background_shadow=True, height=400, title_size=16,
                                    xaxis_title='DRT Summary Cascade',
                                    axis_text_size=14)
        ###############################################
        # COUNTY PICTURE
        ###############################################
        county_summary = df_cascade.groupby("county_name").count()['patient_id'].reset_index()
        county_summary.columns = ["county", "counts"]
        if county_summary.shape[0] > 1:
            xaxis_title = "Counties"
        else:
            xaxis_title = "County"
        counties_summary_fig = bar_chart(county_summary, "county", "counts", f"DRT Summary by County", text="counts",
                                         background_shadow=True, height=400, title_size=16,
                                         xaxis_title=xaxis_title,
                                         axis_text_size=14)

        ##############################################################
        # Patient-wise Distribution of Resistance Types
        ##############################################################
        resistance_type_count = count_resistance_types(df_resistant_patterns_copy)
        resistance_type_count = add_percentage_and_count_string(resistance_type_count)
        total_p = resistance_type_count['count'].sum()
        resistance_type_count_fig = bar_chart(resistance_type_count, "resistance_type", "count",
                                              F"Patient-wise Distribution of Resistance Types N ={total_p}  (Passed)",
                                              text="count (%)", background_shadow=True, height=500, title_size=16,
                                              xaxis_title="resistance_type", yaxis_title="Number of DRT test",
                                              axis_text_size=14)
        ###############################################################
        # Distribution of Drug Resistance Levels Across HAART Regimens
        ##############################################################
        cols_to_groupby = ["resistance_level", "drug", "haart_class"]
        resistance_counts = group_resistance_patterns(df_resistant_patterns, cols_to_groupby)

        # Define a color map for resistance levels
        color_map = {'High-Level Resistance': '#e41a1c', 'Susceptible': '#4daf4a',
                     'Potential Low-Level Resistance': '#ff7f00', 'Intermediate Resistance': '#dede00',
                     'Low-level resistance': '#984ea3',
                     }
        total = len(df_resistant_patterns['patient_id'].unique())
        min_date = df_resistant_patterns['collection_date'].min()
        max_date = df_resistant_patterns['collection_date'].max()

        resistance_order = ['Susceptible', 'Potential Low-Level Resistance', 'Low-level resistance',
                            'Intermediate Resistance', 'High-Level Resistance']
        resistance_counts['resistance_level'] = pd.Categorical(resistance_counts['resistance_level'],
                                                               categories=resistance_order, ordered=True)

        resistance_counts = add_percentage(resistance_counts, "Number of DRT tests", "drug")

        # Create a bar chart
        drt_distribution_fig = generate_bar_chart(data=resistance_counts, x_col="drug", y_col="Number of DRT tests",
                                                  color_col="resistance_level",
                                                  title=f"Distribution of Drug Resistance Levels Across HAART Regimens"
                                                        f"({min_date.strftime('%Y-%m-%d')} to "
                                                        f"{max_date.strftime('%Y-%m-%d')}) - {total} Unique Patients",
                                                  text_col="%.",
                                                  color_map=color_map,
                                                  category_orders={"resistance_level": resistance_order},
                                                  xaxis_title=resistance_counts['haart_class'].unique())

        ##############################################################
        # Distribution of HIV Drugs Across Resistance Levels by Sex
        ##############################################################
        resistance_num = df_resistant_patterns.groupby(["resistance_level", "sex"]).count()['patient_id'].reset_index()
        resistance_num = resistance_num.rename(columns={"patient_id": "Number of Drugs"})
        resistance_num = add_percentage(resistance_num, "Number of Drugs", "sex")

        resistance_num['resistance_level'] = pd.Categorical(resistance_num['resistance_level'],
                                                            categories=resistance_order, ordered=True)
        # Create a bar chart
        resistance_level_fig = generate_bar_chart(data=resistance_num, x_col="sex", y_col="Number of Drugs",
                                                  color_col="resistance_level",
                                                  title="Distribution of HIV Drugs Across Resistance Levels by Sex",
                                                  text_col="Number of Drugs (%)",
                                                  color_map=color_map,
                                                  category_orders={"resistance_level": resistance_order},
                                                  xaxis_title="Sex"
                                                  )

        ##############################################################
        # Distribution of HIV Drugs Across Resistance Levels by Age
        ##############################################################
        age_resistance_num = prepare_age_resistant_patterns(df_resistant_patterns, ["resistance_level", "age"])
        age_resistance_num['resistance_level'] = pd.Categorical(age_resistance_num['resistance_level'],
                                                                categories=resistance_order, ordered=True)
        age_resistance_num = add_percentage(age_resistance_num, "Number of Drugs", "age_band")
        age_resistance_num, available_age_bands = sort_custom_agebands(age_resistance_num, 'age_band')

        resistance_level_age_fig = generate_bar_chart(data=age_resistance_num, x_col="age_band",
                                                      y_col="Number of Drugs",
                                                      color_col="resistance_level",
                                                      title="Distribution of HIV Drugs Across Resistance Levels by Age",
                                                      text_col="%.",
                                                      color_map=color_map,
                                                      category_orders={"resistance_level": resistance_order,
                                                                       "age_band": available_age_bands},
                                                      xaxis_title="Age Bands")
        age_resistance_num = prepare_age_resistant_patterns(df_resistant_patterns_copy, ["age"])
        df_pivoted = dynamic_pivot(age_resistance_num, index_col='age_band', columns_col='sex',
                                   values_col='Number of DRT results')

        # Filter the DataFrame to include rows where any column (except 'patient_id') has a non-zero value
        df_pivoted = df_pivoted[(df_pivoted.iloc[:, 1:] != 0).any(axis=1)]

        if "M" in df_pivoted.columns and "F" in df_pivoted.columns:
            total_males = df_pivoted['M'].sum()
            total_females = df_pivoted['F'].sum()
            total_all = total_females + total_males
            per_male = int(round(total_males / total_all * 100, ))
            per_female = int(round(total_females / total_all * 100, ))
            age_pop_summary_fig = pop_pyramid_chart(df_pivoted, male_col='M', female_col='F',
                                                    title=f"DRT Tests by Age and Sex N = "
                                                          f"{total_all}     M: {total_males} ({per_male} %) "
                                                          f"  F: {total_females} ({per_female} %)")
        elif "M" in df_pivoted.columns:
            total_males = df_pivoted['M'].sum()
            age_pop_summary_fig = pop_pyramid_chart(df_pivoted, male_col='M',
                                                    title=f"DRT Tests by Age and Sex N = {total_males}")
        elif "F" in df_pivoted.columns:
            total_females = df_pivoted['F'].sum()
            age_pop_summary_fig = pop_pyramid_chart(df_pivoted, female_col='F',
                                                    title=f'DRT Tests by Age and Sex N = {total_females}')

        ##############################################################
        # MONTHLY TAT
        ##############################################################
        tat_df = df_resistant_patterns.copy()
        tat_df = tat_df.drop_duplicates(['patient_id', 'formatted_collected_date'])
        tat_df = tat_df.rename(columns={"patient_id": "Number of Drugs"})
        tat = tat_df.groupby(['formatted_date', "formatted_collected_date"]).mean()['tat_days'].reset_index()
        tat['tat_days'] = tat['tat_days'].round().astype(int)
        tat = tat.sort_values("formatted_collected_date")
        drt_tat_fig = line_chart_median_mean(tat, "formatted_date", "tat_days",
                                             f"Monthly Collection to Dispatch TAT", time=24, xaxis_title="Month_Year",
                                             yaxis_title="Mean TAT", background_shadow=True)

        ##############################################################
        # Time-Based Changes in Drug Resistance Prevalence: line chart
        ##############################################################
        prevalence_df = df_resistant_patterns.copy()

        # Assuming date_collected is your time-related column and resistance_level is your drug resistance status column
        prevalence_df['formatted_collected_date'] = pd.to_datetime(prevalence_df['formatted_collected_date'])
        resistance_trends = prevalence_df.groupby(
            ['formatted_date', 'formatted_collected_date', 'resistance_level']).size().reset_index(name='count')
        resistance_trends = resistance_trends.sort_values("formatted_collected_date")

        filtered_df = filter_last_n_months(resistance_trends, date_column='formatted_collected_date', n_months=11)

        dfs = []
        for month in filtered_df['formatted_date']:
            month_res = filtered_df[filtered_df['formatted_date'] == month]
            month_res_total = month_res['count'].sum()
            month_res = month_res.copy()
            month_res['%'] = round(month_res['count'] / month_res_total * 100, )
            month_res['count (%)'] = month_res['count'].astype(str) + " (" + month_res['%'].astype(str) + "%)"
            dfs.append(month_res)
        resistance_trend_df = pd.concat(dfs).sort_values("formatted_collected_date")
        unique_months = resistance_trend_df['formatted_date'].unique()

        # Plotting with Plotly Express
        fig = px.line(resistance_trend_df, x='formatted_date', y='%', color='resistance_level',
                      title='Drug Resistance Prevalence Trend', text="count (%)", height=500,
                      labels={'count': 'Number of Drugs', 'formatted_date': 'Date'},
                      color_discrete_map=color_map, category_orders={'formatted_date': unique_months})

        fig.update_traces(textposition='top center')
        fig.update_layout(
            xaxis_title=f"Month_Year",
            yaxis_title=f"Number of drug resistance plus (%)",
            legend_title=f"Month_Year",
        )
        fig.update_layout(legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ))

        # Show the plot
        prevalence_tat_fig = plot(fig, include_plotlyjs=False, output_type="div")

        ##############################################################
        # Time-Based Changes in Drug Resistance Prevalence: Overall
        ##############################################################
        cols_to_groupby = ["resistance_level", "formatted_date", "formatted_collected_date", "drug", "haart_class"]
        resistance_counts = group_resistance_patterns(df_resistant_patterns, cols_to_groupby)

        resistance_counts = \
            resistance_counts.groupby(["resistance_level", "formatted_date", "formatted_collected_date"]).sum()[
                'Number of DRT tests'].reset_index()
        resistance_counts = resistance_counts.sort_values("formatted_collected_date")
        # Reorder the resistance levels
        resistance_counts['resistance_level'] = pd.Categorical(resistance_counts['resistance_level'],
                                                               categories=resistance_order,
                                                               ordered=True)
        resistance_counts = add_percentage(resistance_counts, "Number of DRT tests", "formatted_date")
        month_order, resistance_order = get_month_resistance_order(resistance_counts, resistance_order)
        # Create a bar chart
        drt_trend_fig = generate_bar_chart(data=resistance_counts, x_col="formatted_date",
                                           y_col="Number of DRT tests",
                                           color_col="resistance_level",
                                           title="Time-Based Changes in Drug Resistance Prevalence",
                                           text_col="Number of DRT tests (%)",
                                           color_map=color_map,
                                           category_orders={"resistance_level": resistance_order,
                                                            "formatted_date": month_order},
                                           xaxis_title="Month_Year"
                                           )

        ##############################################################
        # Time-Based Changes in Drug Resistance Prevalence: By Drug
        ##############################################################
        cols_to_groupby = ["resistance_level", "formatted_date", "formatted_collected_date", "drug", "haart_class"]
        resistance_counts = group_resistance_patterns(df_resistant_patterns, cols_to_groupby)

        resistance_counts = resistance_counts.sort_values('formatted_collected_date')

        # keep the 'formatted_date' column as strings in the 'MMM-YYYY' format
        resistance_counts['formatted_collected_date'] = resistance_counts['formatted_collected_date'].astype(str)
        # custom sort order
        month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        resistance_counts['month_num'] = pd.Categorical(resistance_counts['formatted_collected_date'].str[:3],
                                                        categories=month_order, ordered=True)
        resistance_counts = resistance_counts.sort_values('month_num').drop('month_num', axis=1)

        resistance_counts = resistance_counts.groupby(
            ["resistance_level", "formatted_date", "formatted_collected_date", "drug", "haart_class"]).sum()[
            'Number of DRT tests'].reset_index()

        # Reorder the resistance levels
        resistance_counts['resistance_level'] = pd.Categorical(resistance_counts['resistance_level'],
                                                               categories=resistance_order, ordered=True)
        trend_figs = {}
        for unique_class in sorted(resistance_counts['haart_class'].unique()):
            class_data = resistance_counts[resistance_counts['haart_class'] == unique_class]
            for drug in sorted(class_data['drug'].unique()):
                drug_df = resistance_counts[resistance_counts['drug'] == drug]
                drug_df = add_percentage(drug_df, "Number of DRT tests", "formatted_date")
                drug_df = drug_df.sort_values("formatted_collected_date")
                month_order, resistance_order = get_month_resistance_order(drug_df)
                # Create a bar chart
                trend_figs[drug] = generate_bar_chart(data=drug_df, x_col="formatted_date",
                                                      y_col="Number of DRT tests",
                                                      color_col="resistance_level",
                                                      title=f"Time-Based Changes in Drug Resistance Prevalence "
                                                            f"({unique_class}: {drug.title()})",
                                                      text_col="Number of DRT tests (%)",
                                                      color_map=color_map,
                                                      category_orders={"resistance_level": resistance_order,
                                                                       "formatted_date": month_order},
                                                      xaxis_title="Month_Year"
                                                      )
    return trend_figs, drt_trend_fig, resistance_level_age_fig, resistance_level_fig, drt_distribution_fig, \
        age_summary_fig, drt_tat_fig, prevalence_tat_fig, age_pop_summary_fig, drt_summary_fig, counties_summary_fig, \
        mutation_profile_figs, resistance_type_count_fig


@login_required(login_url='login')
def add_drt_results(request):
    if not request.user.first_name:
        return redirect("profile")
    title = "UPLOAD DRT RESULTS"
    drt_distribution_fig = None
    resistance_level_fig = None
    drt_trend_fig = None
    resistance_level_age_fig = None
    trend_figs = None
    age_summary_fig = None
    age_pop_summary_fig = None
    drt_tat_fig = None
    prevalence_tat_fig = None
    drt_summary_fig = None
    counties_summary_fig = None
    mutation_profile_figs = None
    resistance_type_count_fig = None

    #####################################
    # Display existing data
    #####################################
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
        # record_count = int(request.GET.get('record_count', 10))  # Get the selected record count (default: 10)
        record_count = request.GET.get('record_count', '10')
    else:
        record_count = request.GET.get('record_count', '100')

    results_qs = DrtPdfFile.objects.all().prefetch_related('drt_results', 'drt_profile').order_by('-date_created')
    record_count_options = [(str(i), str(i)) for i in [5, 10, 20, 30, 40, 50]] + [("all", "All"), ]
    my_filters = DrtResultFilter(request.GET, queryset=results_qs)
    if "current_page_url" in request.session:
        del request.session['current_page_url']
    request.session['current_page_url'] = request.path

    # Apply distinct on specific fields to ensure unique combinations
    filtered_qs = my_filters.qs.distinct('drt_results__patient_id', 'drt_results__collection_date',
                                         'drt_results__facility_name', 'date_created')

    results_list = pagination_(request, filtered_qs, record_count)
    qi_list = results_list

    # Control number of DRT results to display
    if len(results_list) > 500:
        results_list = []

    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    template_name = "lab_pulse/add_drt.html"

    if my_filters.qs:
        trend_figs, drt_trend_fig, resistance_level_age_fig, resistance_level_fig, drt_distribution_fig, \
            age_summary_fig, drt_tat_fig, prevalence_tat_fig, age_pop_summary_fig, drt_summary_fig, \
            counties_summary_fig, mutation_profile_figs, resistance_type_count_fig = \
            prepare_drt_summary(my_filters, trend_figs, drt_trend_fig, resistance_level_age_fig, resistance_level_fig,
                                drt_distribution_fig, age_summary_fig, drt_tat_fig, prevalence_tat_fig,
                                age_pop_summary_fig,
                                drt_summary_fig, counties_summary_fig, mutation_profile_figs, resistance_type_count_fig)

    if request.method == "POST":
        drt_file_form = DrtPdfFileForm(request.POST, request.FILES)
        form = DrtResultsForm(request.POST)
        if form.is_valid() and drt_file_form.is_valid():
            context = {"form": form, "drt_file_form": drt_file_form, "title": title, "results": results_list,
                       "my_filters": my_filters, "qi_list": qi_list, "drt_distribution_fig": drt_distribution_fig,
                       "resistance_level_fig": resistance_level_fig, "drt_trend_fig": drt_trend_fig,
                       "trend_figs": trend_figs, "age_summary_fig": age_summary_fig, "drt_tat_fig": drt_tat_fig,
                       "resistance_level_age_fig": resistance_level_age_fig, "prevalence_tat_fig": prevalence_tat_fig,
                       "age_pop_summary_fig": age_pop_summary_fig, "drt_summary_fig": drt_summary_fig,
                       "counties_summary_fig": counties_summary_fig, "mutation_profile_figs": mutation_profile_figs,
                       "record_count": record_count, "resistance_type_count_fig": resistance_type_count_fig, }
            #################
            # Validate date
            #################
            date_fields_to_validate = ['collection_date']
            if not validate_date_fields(form, date_fields_to_validate):
                # Render the template with the form and errors
                return render(request, template_name, context)

            uploaded_file = drt_file_form.cleaned_data['result']
            # Check if the uploaded file is a PDF
            if not uploaded_file.name.lower().endswith('.pdf'):
                drt_file_form.add_error('result', 'Please upload a PDF file.')
                messages.error(request, "Upload a PDF report compiled using this platform")
                return render(request, template_name, context)
            else:

                pdf_text = read_pdf_file(uploaded_file)
                #################
                # Validate PDF
                #################
                if "Sequencing Analysis:" in pdf_text and "MIDR_Lab HIV_DR Report *******" in pdf_text:
                    resistance_profiles_df, resistance_patterns_df = develop_df_from_pdf(pdf_text)
                    # Save extracted data from PDF
                    try:
                        with transaction.atomic():
                            # Facility and Subcounty Query
                            facility_name = form.cleaned_data['facility_name']
                            facility_id = Facilities.objects.get(name=facility_name)
                            all_subcounties = Sub_counties.facilities.through.objects.filter(
                                facilities_id=facility_id.id)
                            all_counties = Sub_counties.counties.through.objects.filter(
                                sub_counties_id__in=[sub_county.sub_counties_id for sub_county in all_subcounties])
                            #######################################################
                            # Iterate over each row in the DataFrame and save data
                            #######################################################
                            # save mutation patterns
                            field_mapping_drt_results = {'drug': 'Drug', 'drug_abbreviation': 'Drug Abbreviation',
                                                         'resistance_level': 'Resistance Level'}
                            save_drt_data(request, resistance_patterns_df, DrtResults, field_mapping_drt_results,
                                          facility_id, all_subcounties, all_counties, drt_file_form)
                            # save mutation profiles
                            field_mapping_drt_profile = {'mutation_type': 'Mutation Type', 'mutations': 'Mutations'}
                            save_drt_data(request, resistance_profiles_df, DrtProfile, field_mapping_drt_profile,
                                          facility_id, all_subcounties, all_counties, drt_file_form)

                        msg = f"Records successfully saved"
                        messages.error(request, msg)

                    except IntegrityError:
                        pass
                    return redirect("add_drt_results")
                else:
                    msg = (
                        "Invalid PDF Format. Please ensure the uploaded file is a valid DRT report "
                        "compiled using this platform."
                    )
                    messages.error(request, msg)
                    return redirect('add_drt_results')
    else:
        form = DrtResultsForm()
        drt_file_form = DrtPdfFileForm()
    context = {"form": form, "drt_file_form": drt_file_form, "title": title, "results": results_list,
               "my_filters": my_filters, "drt_distribution_fig": drt_distribution_fig,
               "resistance_level_fig": resistance_level_fig, "drt_trend_fig": drt_trend_fig, "trend_figs": trend_figs,
               "record_count_options": record_count_options, "qi_list": qi_list, "drt_tat_fig": drt_tat_fig,
               "resistance_level_age_fig": resistance_level_age_fig, "age_summary_fig": age_summary_fig,
               "prevalence_tat_fig": prevalence_tat_fig, "age_pop_summary_fig": age_pop_summary_fig,
               "drt_summary_fig": drt_summary_fig, "counties_summary_fig": counties_summary_fig,
               "mutation_profile_figs": mutation_profile_figs, "resistance_type_count_fig": resistance_type_count_fig, }
    return render(request, "lab_pulse/add_drt.html", context)


@login_required(login_url='login')
def update_drt_results(request, pk):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    item = DrtPdfFile.objects.get(id=pk)
    if request.method == "POST":
        form = DrtPdfFileForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            post = form.save(commit=False)
            facility_name = form.cleaned_data['facility_name']
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
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = DrtPdfFileForm(instance=item)
    context = {
        "form": form,
        "title": "Update DRT Results",
    }
    return render(request, 'lab_pulse/add_drt.html', context)


@login_required(login_url='login')
def delete_drt_result(request, pk):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    item = DrtPdfFile.objects.get(id=pk)
    if request.method == "POST":
        item.delete()

        return HttpResponseRedirect(request.session['page_from'])
    context = {

    }
    return render(request, 'project/delete_test_of_change.html', context)


def read_pdf_file(file):
    """
    Reads a PDF file and extracts text from all its pages.

    Parameters:
    - file (str): The path to the PDF file.

    Returns:
    - str: Combined text from all pages.

    Example:
    file_path = "example.pdf"
    text_content = read_pdf_file(file_path)
    print(text_content)
    'Text from page 1\nText from page 2\n...'
    """
    pdf = pdfplumber.open(file)
    text = []

    # Iterate through each page and extract text
    for page in pdf.pages:
        text.append(page.extract_text())

    # Combine text from all pages into a single string
    return '\n'.join(text)


def join_lines_starting_lowercase(result_list):
    """
    Joins lines in a list where the current line starts with a lowercase letter and the next line continues the thought.

    Parameters:
    - result_list (list): List of strings representing lines of text.

    Returns:
    - list: List of strings where lines starting with a lowercase letter are joined with the previous line.

    Example:
    lines = ['This is a line.', 'continuation of the previous line.', 'Another separate line.']
    result = join_lines_starting_lowercase(lines)
    print(result)
    ['This is a line. continuation of the previous line.', 'Another separate line.']
    """
    joined_list = []
    current_line = ""

    for line in result_list:
        line = line.strip()

        # Check if the line starts with a lowercase letter
        if line and line[0].islower():
            # Join the line with the previous one
            current_line += ' ' + line
        else:
            # Add the current line to the result
            if current_line:
                joined_list.append(current_line.strip())
            current_line = line

    # Add the last line to the result
    if current_line:
        joined_list.append(current_line.strip())

    return joined_list


def join_lines_starting_uppercase(result_list):
    """
    Joins lines in a list where the current line starts with an uppercase letter followed by a digit or ends with an uppercase letter,
    and the next line continues the thought.

    Parameters:
    - result_list (list): List of strings representing lines of text.

    Returns:
    - list: List of strings where lines starting with an uppercase letter are joined with the next line.

    Example:
    lines = ['Section 1A of the document.', 'Continuation of Section 1A.', 'Section 1B.', 'Introduction to Section 1B.']
    result = join_lines_starting_uppercase(lines)
    print(result)
    ['Section 1A of the document. Continuation of Section 1A.', 'Section 1B. Introduction to Section 1B.']
    """
    joined_list = []

    i = 0
    while i < len(result_list):
        current_line = result_list[i].strip()

        if i < len(result_list) - 1:
            next_line = result_list[i + 1].strip()

            # Check if the next line starts with an uppercase letter followed by a digit or ends with an uppercase letter
            if next_line and re.match(r'^[A-Z]\d|[A-Z]+$', next_line):
                # Join the lines
                current_line += ' ' + next_line
                i += 1  # Skip the next line

        joined_list.append(current_line)
        i += 1

    return joined_list


def join_lines_starting_three_lettered_word_uppercase(result_list, have_three_lettered_word=False):
    """
    Joins lines in a list where the current line starts with an uppercase letter followed by a digit or ends with an uppercase letter,
    and the next line continues the thought.

    Parameters:
    - result_list (list): List of strings representing lines of text.

    Returns:
    - list: List of strings where lines starting with an uppercase letter are joined with the next line.

    Example:
    lines = ['Section 1A of the document.', 'Continuation of Section 1A.', 'Section 1B.', 'Introduction to Section 1B.']
    result = join_lines_starting_uppercase(lines)
    print(result)
    ['Section 1A of the document. Continuation of Section 1A.', 'Section 1B. Introduction to Section 1B.']
    """
    joined_list = []

    i = 0
    while i < len(result_list):
        current_line = result_list[i].strip()

        if i < len(result_list) - 1:
            next_line = result_list[i + 1].strip()
            if next_line and re.match(r'[A-Z]{3}(?![A-Z])', next_line) and have_three_lettered_word:
                current_line += ' ' + next_line
                i += 1  # Skip the next line

            # Check if the next line starts with an uppercase letter followed by a digit or ends with an uppercase letter
            elif next_line and re.match(r'^[A-Z]\d+[A-Z]+$', next_line) and not have_three_lettered_word:
                # Join the lines
                current_line += ' ' + next_line
                i += 1  # Skip the next line

        joined_list.append(current_line)
        i += 1

    return joined_list


def preprocess_data(pattern_match_df, variable_2=None):
    # Extract unique values from the DataFrame column
    generated_list = pattern_match_df["col_name"].unique()
    # Process and clean the extracted text
    generated_list = generated_list[0].replace(f" {variable_2}", "")
    generated_list = generated_list.replace(f"{variable_2}", "")
    generated_list = [s.replace('·', ',').replace(',,', ',') for s in generated_list.split("\n")]

    # Join lines based on lowercase and uppercase starting letters
    generated_list = join_lines_starting_lowercase(generated_list)
    if "NRTI" not in generated_list:
        generated_list = join_lines_starting_three_lettered_word_uppercase(generated_list,
                                                                           have_three_lettered_word=True)
    #         generated_list=join_lines_starting_uppercase(generated_list)
    # Remove unwanted strings
    filtered_list = [s for s in generated_list if s != '.']
    filtered_list = [s for s in filtered_list if s != '(CoVDB)']
    filtered_list = [s for s in filtered_list if s != '']
    filtered_list = [item for item in filtered_list if '//' not in item]
    filtered_list = [item for item in filtered_list if 'HIVDB' not in item.upper()]

    # Exclude items with date pattern "MM/DD/YY" or "MM/DD/YYYY"
    filtered_list = [item for item in filtered_list if not re.search(r'\b\d{1,2}/\d{1,2}/\d{2,4}\b', item)]
    return filtered_list


def extract_text(pdf_text, variable_1, variable_2, custom_pattern=None):
    """
    Extracts text between two specified variables in a given PDF text.

    Parameters:
    - pdf_text (str): The text content of the PDF.
    - variable_1 (str): The starting variable or pattern.
    - variable_2 (str): The ending variable or pattern.

    Returns:
    - list: A list of strings containing the extracted text.

    Example:
    pdf_text = "Some text here\nVariable 1\nExtracted Text\nVariable 2\nMore text here"
    result = extract_text(pdf_text, "Variable 1", "Variable 2")
    print(result)
    ['Extracted Text']
    """
    if custom_pattern is None:
        # Using an f-string to incorporate variables into the regular expression
        pattern = re.compile(f'{re.escape(variable_1)}([\s\S]*?){re.escape(variable_2)}', re.MULTILINE)

        # Find the first match in the PDF text
        pattern_match = pattern.search(pdf_text)
    else:
        # Add the NNRTI specific extraction using the provided pattern
        pattern_match = re.findall(custom_pattern, pdf_text, re.DOTALL)

    # Create a dictionary and DataFrame to store the extracted information
    pi_resistance_profile_dict = {}
    if pattern_match and custom_pattern is None:
        pi_resistance_profile_dict["col_name"] = pattern_match.group(0)
        pattern_match_df = pd.DataFrame([pi_resistance_profile_dict])
        filtered_list = preprocess_data(pattern_match_df, variable_2)
    elif pattern_match and custom_pattern is not None:
        pattern_match_df = pd.DataFrame(pattern_match, columns=['col_name'])
        filtered_list = preprocess_data(pattern_match_df, variable_2=None)
    else:
        filtered_list = []

    return filtered_list


def extract_text_between_markers(text):
    """
    Extract text between markers "Other" and "Mutation scoring" and store the results in a dictionary.

    Parameters:
    - text (str): Input text.

    Returns:
    - dict: Dictionary where keys are labels and values are the corresponding extracted text.

    Example:
    input_text = '\nOther\nK20R is a highly polymorphic PI-selected accessory mutation that increases replication fitness in viruses with PI-resistance mutations.\nMutation scoring: PR HIVDB 9.5.1 (2023-11-05)\nNo drug resistance mutations were found for PI.\nDrug resistance interpretation: RT HIVDB 9.5.1 (2023-11-05)\nNRTI Mutations: None\nNNRTI Mutations: None\nRT Other Mutations: E6D·K11Q·V21I·V35T·V60I·T69N·K122E·D123N·,I135T·K173S·Q174K·D177E·I178IM·V179I·T200A·Q207A·\nR211S\nNucleoside Reverse Transcriptase Inhibitors Non-nucleoside Reverse Transcriptase Inhibitors\nabacavir (ABC) Susceptible doravirine (DOR) Susceptible\nzidovudine (AZT) Susceptible efavirenz (EFV) Susceptible\nstavudine (D4T) Susceptible etravirine (ETR) Susceptible\ndidanosine (DDI) Susceptible nevirapine (NVP) Susceptible\nemtricitabine (FTC) Susceptible rilpivirine (RPV) Susceptible\nlamivudine (3TC) Susceptible\ntenofovir (TDF) Susceptible\nRT comments\nOther\nT69N/S/A/I/E are relatively non-polymorphic mutations weakly selected in persons receiving NRTIs. They may minimally contribute reduced AZT susceptibility.\nV179I is a polymorphic mutation that is frequently selected in persons receiving ETR and RPV. However, it has little, if any, direct effect on NNRTI susceptibility.\nMutation scoring: RT HIVDB 9.5.1 (2023-11-05)\nNo drug resistance mutations were found for NRTI.\nNo drug resistance mutations were found for NNRTI.\n© 1998 - 2023. All Rights Reserved. Questions? Contact HIVdb <hivdbteam@lists.stanford.edu>.'
    result = extract_text_between_markers(input_text)
    print(result)
    {'PR': 'K20R is a highly polymorphic PI-selected accessory mutation that increases replication fitness in viruses with PI-resistance mutations.',
     'RT': 'T69N/S/A/I/E are relatively non-polymorphic mutations weakly selected in persons receiving NRTIs. They may minimally contribute reduced AZT susceptibility.\nV179I is a polymorphic mutation that is frequently selected in persons receiving ETR and RPV. However, it has little, if any, direct effect on NNRTI susceptibility.'}
    """
    pattern = r'Other\n(.*?)\nMutation scoring:\s*([A-Z]+)\s+'

    matches = re.findall(pattern, text, re.DOTALL)
    result_dict = {label: join_lines_starting_lowercase(content.strip().split('\n')) for content, label in matches}

    return result_dict


def extract_text_after_keyword(data, keyword1, keyword2):
    """
    Extract text occurring after the specified keywords in each sentence.

    Parameters:
    - data (list): List of strings representing sentences.
    - keyword1 (str): The first keyword to look for in each sentence.
    - keyword2 (str): The second keyword to stop appending sentences.

    Returns:
    - dict: Dictionary with the keywords as keys and lists of text occurring after each keyword in each sentence (including the sentence with the keyword) as the values.
    """
    result = {}
    current_keyword = None

    for sentence in data:
        match1 = re.search(f'{keyword1}', sentence)
        match2 = re.search(f'{keyword2}', sentence)

        if match1:
            current_keyword = re.sub(r'\W+', '', match1.group(0))
            result[current_keyword] = [sentence]
        elif match2:
            current_keyword = re.sub(r'\W+', '', match2.group(0))
            result[current_keyword] = [sentence]
        elif current_keyword is not None:
            if current_keyword in result:
                result[current_keyword].append(sentence)

    return result


def extract_matching_sentences(data, pattern):
    """
    Extract sentences from the input data that match the specified regex pattern.

    Parameters:
    - data (list): List of strings representing sentences.
    - pattern (str): Regex pattern to match.

    Returns:
    - list: List of sentences that match the pattern.
    """
    matching_sentences = [sentence for sentence in data if re.search(pattern, sentence)]
    return matching_sentences


def extract_non_intergrase_text(pdf_text):
    other_pi_mutation_comments = []
    other_rt_comments = []
    pi_resistance_mutation_profile = extract_text(pdf_text,
                                                  "PI Major Mutations",
                                                  "\nProtease Inhibitors")
    pi_resistance_mutation_profile = join_lines_starting_uppercase(pi_resistance_mutation_profile)
    # pi_list = extract_text(pdf_text, "Protease Inhibitors", "\nPR comments")
    # if len(pi_list) == 0:
    #     pi_list = extract_text(pdf_text, "Protease Inhibitors",
    #                            "\nMutation scoring:")
    # pi_list = pi_list[1:]
    pi_atvr = extract_text(pdf_text, "atazanavir/r", "\n")
    pi_drvr = extract_text(pdf_text, "darunavir/r", "\n")
    pi_fpvr = extract_text(pdf_text, "fosamprenavir/r", "\n")
    pi_idvr = extract_text(pdf_text, "indinavir/r", "\n")
    pi_lpvr = extract_text(pdf_text, "lopinavir/r", "\n")
    pi_nfv = extract_text(pdf_text, "nelfinavir", "\n")
    pi_sqvr = extract_text(pdf_text, "saquinavir/r", "\n")
    pi_tpvr = extract_text(pdf_text, "tipranavir/r", "\n")
    pi_list = pi_atvr + pi_drvr + pi_fpvr + pi_idvr + pi_lpvr + pi_nfv + pi_sqvr + pi_tpvr

    pi_mutation_comments = extract_text(pdf_text, "PR comments", "\nOther")
    pi_mutation_comments = [
        item for item in pi_mutation_comments if 'PR comments' not in item
    ]
    #############################################################################################
    # Extract text after "Major" and "Accessory"
    text_after_major = extract_text_after_keyword(pi_mutation_comments,
                                                  'Major', 'Accessory')
    if "Major" in text_after_major:
        pi_mutation_comments_major = text_after_major.get('Major')[1:]
    else:
        pi_mutation_comments_major = []
    if "Accessory" in text_after_major:
        pi_mutation_comments_accessory = text_after_major.get('Accessory')[1:]
    else:
        pi_mutation_comments_accessory = []

    # Extract text between "Other" and "Mutation scoring"
    other_comments_dict = extract_text_between_markers(pdf_text)
    if len(other_comments_dict) != 0:
        for label, content in other_comments_dict.items():
            if label == "PR":
                other_pi_mutation_comments = [value for key, value in other_comments_dict.items() if key == "PR"][0]
            elif label == "RT":
                other_rt_comments = [value for key, value in other_comments_dict.items() if key == "RT"][0]

    rt_resistance_mutation_profile = extract_text(
        pdf_text, "Drug resistance interpretation: RT",
        "\nNucleoside Reverse Transcriptase Inhibitors")
    rt_resistance_mutation_profile = rt_resistance_mutation_profile
    rt_resistance_mutation_profile = join_lines_starting_uppercase(rt_resistance_mutation_profile)

    nrti_tdf = extract_text(pdf_text, "tenofovir", "\n")
    nrti_3tc = extract_text(pdf_text, "lamivudine", "\ntenofovir")
    nrti_ftc = extract_text(pdf_text, "emtricitabine", "rilpivirine")
    nrti_ddi = extract_text(pdf_text, "didanosine", "nevirapine")
    nrti_d4t = extract_text(pdf_text, "stavudine", "etravirine")
    nrti_azt = extract_text(pdf_text, "zidovudine", "efavirenz")
    nrti_abc = extract_text(pdf_text, "abacavir", "doravirine")
    nrti_comments = extract_text(pdf_text, "RT comments\nNRTI", "\nNNRTI")

    #######################################################################
    # Use the function with the provided pattern
    pattern = r'[A-Z]{3}'
    nrti_comments = extract_matching_sentences(nrti_comments[1:], pattern)
    nrti_comments = [x for x in nrti_comments if "NRTI" != x]
    #######################################################################
    nnrti_dor = extract_text(pdf_text, "doravirine", "zidovudine ")
    nnrti_efv = extract_text(pdf_text, "efavirenz", "stavudine")
    nnrti_etr = extract_text(pdf_text, "etravirine", "didanosine")
    nnrti_nvp = extract_text(pdf_text, "nevirapine", "emtricitabine")
    nnrti_rpv = extract_text(pdf_text, "rilpivirine", "lamivudine")
    nnrtis_list = nnrti_dor + nnrti_efv + nnrti_etr + nnrti_nvp + nnrti_rpv
    #######################################################################
    # Using custom pattern for NNRTI extraction
    custom_nnrti_pattern = r'\nNNRTI\n(.*?)\.\nMutation scoring:'

    nnrti_comments = extract_text(pdf_text, "\nNNRTI\n", "\nOther")
    if len(nnrti_comments) == 0:
        nnrti_comments = extract_text(pdf_text, ".\nNNRTI",
                                      ".\nMutation scoring:", custom_pattern=custom_nnrti_pattern)

    nnrti_comments = [x for x in nnrti_comments if (". NNRTI" not in x) and ("NNRTI" not in x)]
    nnrti_comments = join_lines_starting_three_lettered_word_uppercase(nnrti_comments, have_three_lettered_word=True)
    #######################################################################

    generated_list = extract_text(pdf_text, "\n1", "\nSequence summary")
    ccc_num = generated_list[0].split('.')[1].strip()

    # Use regular expression to extract only numbers
    ccc_number_only = re.sub(r'\D', '', ccc_num)

    nrtis_list = nrti_abc + nrti_d4t + nrti_azt + nrti_ddi + nrti_ftc + nrti_3tc + nrti_tdf
    return pi_resistance_mutation_profile, pi_list, pi_mutation_comments, other_pi_mutation_comments, \
        rt_resistance_mutation_profile, nrti_tdf, nrti_3tc, nrti_ftc, nrti_ddi, nrti_d4t, nrti_azt, nrti_abc, \
        nrti_comments, nnrti_dor, nnrti_efv, nnrti_etr, nnrti_nvp, nnrti_rpv, nnrtis_list, nnrti_comments, \
        other_rt_comments, ccc_number_only, nrtis_list, pi_mutation_comments_major, pi_mutation_comments_accessory


def split_text(text, max_width, pdf):
    """
    Split a text into lines, ensuring that each line's width does not exceed the given maximum width.

    Parameters:
    - text (str): The input text to be split.
    - max_width (float): The maximum width allowed for each line.
    - pdf (Canvas): The ReportLab Canvas object for text width measurement.

    Returns:
    List[str]: A list of lines, where each line does not exceed the specified maximum width.
    """
    lines = []  # List to store the resulting lines
    current_line = ""  # Variable to accumulate words into the current line

    for word in text.split(','):
        if not current_line:
            # If current_line is empty, add the first word
            current_line = word
        else:
            # Check the width of the line with the new word
            width_with_word = pdf.stringWidth(current_line + "," + word, "Helvetica", 11)

            if width_with_word <= max_width:
                # If the line is within the width limit, add the word to the current line
                current_line += "," + word + ","
            else:
                # If adding the word exceeds the width limit, start a new line
                lines.append(current_line.strip().replace(",,", ","))
                current_line = word

    if current_line:
        # Add the last line if there's any remaining text
        lines.append(current_line.strip().replace(",,", ","))

    return lines


def draw_text(pdf, x, y, label, value, x_values=70, font_size=11, bold=False, line_spacing=13, underline=False,
              italic=False):
    pdf.setFont("Helvetica", font_size)
    if italic:
        pdf.setFont("Helvetica-Oblique", font_size)
    pdf.drawString(x, y, label)

    if underline:
        pdf.setDash(1, 0)  # Reset the line style
        # Calculate the position for the underline
        underline_y = y - 2
        underline_length = pdf.stringWidth(label, "Helvetica", font_size)
        pdf.line(x, underline_y, x + underline_length, underline_y)

    if bold:
        pdf.setFont("Helvetica-Bold", font_size)

    # Check the length of the value
    max_width = 410  # Adjust this value based on your layout
    value_width = pdf.stringWidth(value, "Helvetica", font_size)
    if value_width > max_width:
        # If the value is too long, split it into multiple lines
        lines = split_text(value, max_width, pdf)
        for line in lines:
            pdf.drawString(x + x_values, y, line)
            y -= line_spacing  # Adjust the spacing between lines
    else:
        pdf.drawString(x + x_values, y, value)
    if bold:
        pdf.setFont("Helvetica", font_size)


def underline(pdf, x, y, font_size, label):
    pdf.setDash(1, 0)  # Reset the line style
    # Calculate the position for the underline
    underline_y = y - 2
    underline_length = pdf.stringWidth(label, "Helvetica", font_size)
    pdf.line(x, underline_y, x + underline_length, underline_y)
    return underline_y


def draw_comment_text(pdf, x, y, label, value, x_values=70, font_size=11, bold=False, line_spacing=13, underline=False):
    pdf.setFont("Helvetica", font_size)
    pdf.drawString(x, y, label)

    if underline:
        pdf.setDash(1, 0)  # Reset the line style
        # Calculate the position for the underline
        underline_y = y - 2
        underline_length = pdf.stringWidth(label, "Helvetica", font_size)
        pdf.line(x, underline_y, x + underline_length, underline_y)

    if bold:
        pdf.setFont("Helvetica-Bold", font_size)

    # Check the length of the value
    max_width = 410  # Adjust this value based on your layout
    value_width = pdf.stringWidth(value, "Helvetica", font_size)
    if value_width > max_width:
        # If the value is too long, split it into multiple lines
        lines = split_comment_text(value, max_width, pdf)
        for line in lines:
            pdf.drawString(x + x_values, y, line)
            y -= line_spacing  # Adjust the spacing between lines
    else:
        pdf.drawString(x + x_values, y, value)
    if bold:
        pdf.setFont("Helvetica", font_size)


def draw_colored_rectangle(pdf, x, y, width, height, fill_color, text, text_color=(0, 0, 0), font="Helvetica-Bold",
                           font_size=9):
    """
    Draw a colored rectangle with text inside on a PDF canvas.

    Parameters:
    - pdf (PDFCanvas): The PDF canvas to draw on.
    - x (float): The x-coordinate of the top-left corner of the rectangle.
    - y (float): The y-coordinate of the top-left corner of the rectangle.
    - width (float): The width of the rectangle.
    - height (float): The height of the rectangle.
    - fill_color (tuple): RGB values representing the fill color of the rectangle.
    - text (str): The text to be displayed inside the rectangle.
    - text_color (tuple, optional): RGB values representing the text color. Default is black.
    - font (str, optional): The font to be used for the text. Default is "Helvetica-Bold".
    - font_size (int, optional): The font size for the text. Default is 9.
    """
    # Set the fill color for the rectangle
    pdf.setFillColorRGB(*fill_color)
    # Draw the colored rectangle
    pdf.rect(x, y, width, height, fill=True, stroke=False)

    # Set the text color and font for the text inside the rectangle
    pdf.setFillColorRGB(*text_color)
    pdf.setFont(font, font_size)
    # Draw the text inside the rectangle with a margin of 5 units from the left and 3 units from the top
    pdf.drawString(x + 5, y + 3, text)


def split_comment_text(text, max_width, pdf):
    """
    Split a text into lines, ensuring that each line's width does not exceed the given maximum width.

    Parameters:
    - text (str): The input text to be split.
    - max_width (float): The maximum width allowed for each line.
    - pdf (Canvas): The ReportLab Canvas object for text width measurement.

    Returns:
    List[str]: A list of lines, where each line does not exceed the specified maximum width.
    """
    lines = textwrap.wrap(text, width=max_width)
    return lines


def draw_footer(pdf, start_x, patient_name, ccc_num, todays_date, page, width, x_value):
    y = 0
    y += 45
    pdf.setFont("Helvetica-Oblique", 6)
    pdf.setFillColor(colors.grey)
    pdf.setDash(1, 0)  # Reset the line style
    pdf.line(x1=start_x, y1=y, x2=width, y2=y)
    y = 0
    y += 30
    draw_text(pdf, start_x, y,
              f"MIDR_Lab HIV_DR Report ******* {patient_name.title()} ******* UID#{ccc_num} ******* {todays_date} ******* Page {page}",
              "", x_value, bold=True, italic=True, font_size=9)
    pdf.setFillColor(colors.black)


def create_new_page(pdf, start_x, y, patient_name, ccc_num, todays_date, page_info, width, x_value):
    if y <= 80:
        page_info['page_count'] += 1
        draw_footer(pdf, start_x, patient_name, ccc_num, todays_date, page_info['page_count'], width, x_value)
        pdf.showPage()
        y = 730
    return y


def write_comments(pdf, y, comment_title, comments, start_x, x_value, patient_name, ccc_num, todays_date, page_info,
                   width):
    y -= 10
    draw_text(pdf, start_x, y, f"{comment_title}", "", x_value, bold=False, underline=True)
    y -= 15
    y = create_new_page(pdf, start_x, y, patient_name, ccc_num, todays_date, page_info, width, x_value)
    # Write comments
    bullet_point = "\u2022"  # Unicode bullet point character
    for i in comments:
        pdf.setFont("Helvetica", 11)
        lines = split_comment_text(i, 95, pdf)  # Adjust the max_width as needed
        for count, line in enumerate(lines):
            formatted_line = f"{bullet_point}      {line}"
            if count == 0:
                draw_comment_text(pdf, start_x + 10, y, f"{formatted_line}", "", x_value, bold=False)
            else:
                draw_comment_text(pdf, start_x + 10, y, f"       {line}", "", x_value, bold=False)
            y -= 15  # linespacing
            y = create_new_page(pdf, start_x, y, patient_name, ccc_num, todays_date, page_info, width, x_value)
    return y


def draw_section_with_list(pdf, y, list_content, section_title, start_x, x_value, width, patient_name, ccc_num,
                           todays_date, page_info):
    y -= 25
    # Call the function to draw a colored rectangle with text inside
    draw_colored_rectangle(pdf, start_x, y, width - 70, 15, (0.980, 0.827, 0.706), section_title)
    y -= 10
    y = create_new_page(pdf, start_x, y, patient_name, ccc_num, todays_date, page_info, width, x_value)
    for i in list_content:
        pdf.setFont("Helvetica", 11)
        draw_text(pdf, start_x, y, f"{i.split(')')[0]})", f"{i.split(')')[1].strip()}", x_value, bold=False)
        y -= 15  # linespacing
        y = create_new_page(pdf, start_x, y, patient_name, ccc_num, todays_date, page_info, width, x_value)
    return y


def write_patient_demographics(pdf, y, x_value, start_x, patient_name, ccc_num, sex, age, age_unit, contact):
    y -= 15
    # Draw patient information
    draw_text(pdf, start_x, y, "Patient Name:", patient_name.title(), x_value, bold=True)
    draw_text(pdf, start_x + 355, y, "Unique ID:", f"{ccc_num}", bold=True)
    y -= 15
    draw_text(pdf, start_x, y, "Sex:", f"{sex}", bold=True)
    draw_text(pdf, start_x + x_value, y, "Age:", f"{age} {age_unit.title()}", bold=True)
    draw_text(pdf, start_x + 355, y, "Contact:", f"{contact}", bold=True)
    return y


def draw_info_block(pdf, start_x, y, x_value, specimen_type, date_collected, request_from, date_received,
                    requesting_clinician, date_reported, spacing=15):
    """
    Draw an information block on the PDF canvas with specified layout.

    Parameters:
    - pdf (PDFCanvas): The PDF canvas to draw on.
    - start_x (int): The starting x-coordinate for drawing.
    - y (int): The starting y-coordinate for drawing.
    - x_value (int): The x-coordinate value for specific text positioning.
    - spacing (int, optional): Vertical spacing between items. Default is 15.

    Returns:
    - int: The final y-coordinate after drawing the information block.
    """
    info_items = [
        ("Specimen Type:", f"{specimen_type.title()}"),  # specimen type
        ("Date Collected:", f"{date_collected}"),  # date collected
        ("Requested From:", f"{request_from.title()}"),  # requested from
        ("Date Received:", f"{date_received}"),  # date received
        ("Requesting Clinician:", f"{requesting_clinician.title()}"),  # requesting clinician
        ("Date Reported:", f"{date_reported}")  # date reported
    ]
    for i, (label, value) in enumerate(info_items):
        if i % 2 == 0:
            y -= spacing
        if "date" in label.lower():
            draw_text(pdf, start_x + 355, y, label, value, 90, bold=True)
        else:
            draw_text(pdf, start_x, y, label, value, x_value, bold=True)
    return y


def write_comments_rt_pi(pdf, y, comment_title, profile, start_x, x_value, width, patient_name, ccc_num, todays_date,
                         page_info):
    y -= 25
    # Call the function to draw a colored rectangle with text inside
    draw_colored_rectangle(pdf, start_x, y, width - 70, 15, (0.980, 0.827, 0.706), comment_title)
    y -= 10
    for i in profile:
        pdf.setFont("Helvetica", 11)
        if "Other" in i.split(':')[0]:
            draw_text(pdf, start_x, y, f"{i.split(':')[0]} :", f"{i.split(':')[1].strip()}", x_value, bold=False)
        else:
            draw_text(pdf, start_x, y, f"{i.split(':')[0]} :", f"{i.split(':')[1].strip()}", x_value, bold=True)
        y -= 15
        y = create_new_page(pdf, start_x, y, patient_name, ccc_num, todays_date, page_info, width, x_value)
    return y


def draw_horizontal_line(pdf, y, start_x, width, dash_pattern=0, width_x=0):
    pdf.setDash(1, dash_pattern)  # Reset the line style
    pdf.line(x1=start_x, y1=y, x2=width - width_x, y2=y)


def extract_intergrase_text(pdf_text):
    generated_list = extract_text(pdf_text, "\n1", "\nSequence summary")
    ccc_num = generated_list[0].split('.')[1].strip()

    intergrase_resistance_mutation_profile = extract_text(
        pdf_text, "\nDrug resistance interpretation: IN", "Integrase Strand Transfer Inhibitors")
    intergrase_resistance_mutation_profile = join_lines_starting_uppercase(intergrase_resistance_mutation_profile)
    # intergrase_resistance_mutations = extract_text(
    #     pdf_text, "Integrase Strand Transfer Inhibitors", "IN comments")
    # intergrase_resistance_mutations = [x for x in intergrase_resistance_mutations if "Strand " not in x]
    insti_bic = extract_text(pdf_text, "bictegravir", "\n")
    insti_cab = extract_text(pdf_text, "cabotegravir", "\n")
    insti_dtg = extract_text(pdf_text, "dolutegravir", "\n")
    insti_evg = extract_text(pdf_text, "nelvitegravir", "\n")
    insti_ral = extract_text(pdf_text, "raltegravir", "\n")
    intergrase_resistance_mutations = insti_bic + insti_cab + insti_dtg + insti_evg + insti_ral

    intergrase_comments = extract_text(pdf_text, "IN comments", "Accessory")
    intergrase_comments = [x for x in intergrase_comments if "IN comments" not in x]

    intergrase_accessory_comments = extract_text(pdf_text, "\nAccessory", "Mutation scoring: IN")
    intergrase_accessory_comments = [x.replace("Accessory", "").strip() for x in intergrase_accessory_comments]
    return intergrase_resistance_mutation_profile, intergrase_resistance_mutations, intergrase_comments, intergrase_accessory_comments, ccc_num


def generate_drt_report(pdf, todays_date, patient_name, ccc_num, rt_resistance_mutation_profile=None, nrtis_list=None,
                        nrti_comments=None, other_rt_comments=None, pi_resistance_mutation_profile=None,
                        nnrtis_list=None, nnrti_comments=None, pi_list=None, other_pi_mutation_comments=None,
                        intergrase_resistance_mutation_profile=None, intergrase_resistance_mutations=None,
                        intergrase_comments=None, intergrase_accessory_comments=None, date_test_perfomed=None,
                        date_test_reviewed=None, sex=None, age=None, age_unit=None, contact=None, specimen_type=None,
                        request_from=None, requesting_clinician=None, performed_by=None, reviewed_by=None,
                        date_collected=None, date_received=None, date_reported=None, pi_mutation_comments_major=None,
                        pi_mutation_comments_accessory=None, sequence_summary=None):
    # Initialize page_info
    page_info = {'page_count': 0}

    y = 660
    start_x = 70
    # Add images to the PDF canvas using absolute paths
    image_path = os.path.join(BASE_DIR, 'assets', 'static', 'images', 'drt_image_updated.png')
    image_path1 = os.path.join(BASE_DIR, 'assets', 'static', 'images', 'end_of_report_drt.png')

    width = letter[0] - 114
    # Add the image to the canvas above the "BIOCHEMISTRY REPORT" text and take the full width
    add_image(pdf, image_path, x=start_x, y=y, width=width, height=100)

    width = letter[0] - 40
    x_value = 140

    ######################################
    # Patient demographics
    ######################################
    y = write_patient_demographics(pdf, y, x_value, start_x, patient_name, ccc_num, sex, age, age_unit, contact)
    y -= 10

    pdf.setFont("Helvetica", 6)

    draw_horizontal_line(pdf, y, start_x, width, dash_pattern=1)

    pdf.setFont("Helvetica", 11)

    ######################################
    # Information Block
    ######################################
    y = draw_info_block(pdf, start_x, y, x_value, specimen_type, date_collected, request_from, date_received,
                        requesting_clinician, date_reported, spacing=15)

    y -= 25
    # Call the function to draw a colored rectangle with text inside
    draw_colored_rectangle(pdf, start_x, y, width - 70, 15, (0.980, 0.827, 0.706), "SEQUENCE SUMMARY")
    y -= 10
    pdf.setFont("Helvetica", 11)
    draw_text(pdf, start_x, y, "Sequencing Analysis:", f"{sequence_summary}", x_value, bold=True)

    y = create_new_page(pdf, start_x, y, patient_name, ccc_num, todays_date, page_info, width, x_value)
    if sequence_summary == "PASSED":
        if rt_resistance_mutation_profile != "":
            ######################################
            # RT RESISTANCE MUTATION PROFILE
            ######################################
            y = write_comments_rt_pi(pdf, y, "RT RESISTANCE MUTATION PROFILE", rt_resistance_mutation_profile,
                                     start_x, x_value, width, patient_name, ccc_num, todays_date, page_info)
            y = create_new_page(pdf, start_x, y, patient_name, ccc_num, todays_date, page_info, width, x_value)

            ######################################
            # NRTI
            ######################################

            y = draw_section_with_list(pdf, y, nrtis_list,
                                       "NUCLEOSIDE REVERSE TRANSCRIPTASE INHIBITORS (NRTIS) DRUG RESISTANCE INTERPRETATION",
                                       start_x, x_value, width, patient_name, ccc_num, todays_date, page_info)
            y = create_new_page(pdf, start_x, y, patient_name, ccc_num, todays_date, page_info, width, x_value)

            y = create_new_page(pdf, start_x, y, patient_name, ccc_num, todays_date, page_info, width, x_value)
            y = write_comments(pdf, y, "NRTI MUTATION COMMENTS:", nrti_comments, start_x, x_value, patient_name,
                               ccc_num, todays_date, page_info, width)
            y = create_new_page(pdf, start_x, y, patient_name, ccc_num, todays_date, page_info, width, x_value)

            ######################################
            # NNRTI
            ######################################
            y = draw_section_with_list(pdf, y, nnrtis_list,
                                       "NON-NUCLEOSIDE REVERSE TRANSCRIPTASE INHIBITORS (NNRTIS) DRUG RESISTANCE INTERPRETATION",
                                       start_x, x_value, width, patient_name, ccc_num, todays_date, page_info)
            y = create_new_page(pdf, start_x, y, patient_name, ccc_num, todays_date, page_info, width, x_value)

            y = write_comments(pdf, y, "NNRTI MUTATION COMMENTS:", nnrti_comments, start_x, x_value, patient_name,
                               ccc_num, todays_date, page_info, width)
            y = create_new_page(pdf, start_x, y, patient_name, ccc_num, todays_date, page_info, width, x_value)

            y = write_comments(pdf, y, "OTHER RT MUTATION COMMENTS:", other_rt_comments, start_x, x_value,
                               patient_name, ccc_num, todays_date, page_info, width)
            y = create_new_page(pdf, start_x, y, patient_name, ccc_num, todays_date, page_info, width, x_value)

            ######################################
            # Protease Inhibitors
            ######################################
            y = write_comments_rt_pi(pdf, y, "PI RESISTANCE MUTATION PROFILE", pi_resistance_mutation_profile,
                                     start_x, x_value, width, patient_name, ccc_num, todays_date, page_info)

            y = create_new_page(pdf, start_x, y, patient_name, ccc_num, todays_date, page_info, width, x_value)
            y = draw_section_with_list(pdf, y, pi_list, "PROTEASE INHIBITORS (PIS) DRUG RESISTANCE INTERPRETATION",
                                       start_x, x_value, width, patient_name, ccc_num, todays_date, page_info)
            y = create_new_page(pdf, start_x, y, patient_name, ccc_num, todays_date, page_info, width, x_value)

            y = write_comments(pdf, y, "PI MUTATION COMMENTS:", "", start_x, x_value,
                               patient_name, ccc_num, todays_date, page_info, width)
            y = create_new_page(pdf, start_x, y, patient_name, ccc_num, todays_date, page_info, width, x_value)

            if len(pi_mutation_comments_major) != 0:
                y = write_comments(pdf, y, "MAJOR:", pi_mutation_comments_major, start_x, x_value,
                                   patient_name, ccc_num, todays_date, page_info, width)
                y = create_new_page(pdf, start_x, y, patient_name, ccc_num, todays_date, page_info, width, x_value)
            if len(pi_mutation_comments_accessory) != 0:
                y = write_comments(pdf, y, "ACCESORY:", pi_mutation_comments_accessory, start_x, x_value,
                                   patient_name, ccc_num, todays_date, page_info, width)
                y = create_new_page(pdf, start_x, y, patient_name, ccc_num, todays_date, page_info, width, x_value)
            y = write_comments(pdf, y, "OTHERS:", other_pi_mutation_comments, start_x, x_value,
                               patient_name, ccc_num, todays_date, page_info, width)
            y = create_new_page(pdf, start_x, y, patient_name, ccc_num, todays_date, page_info, width, x_value)

        if intergrase_resistance_mutation_profile != "":
            ######################################
            # Intergrase Inhibitors
            ######################################
            y = write_comments_rt_pi(pdf, y, "INSTI RESISTANCE MUTATION PROFILE",
                                     intergrase_resistance_mutation_profile, start_x, x_value, width, patient_name,
                                     ccc_num, todays_date, page_info)

            y = create_new_page(pdf, start_x, y, patient_name, ccc_num, todays_date, page_info, width, x_value)

            y = draw_section_with_list(pdf, y, intergrase_resistance_mutations,
                                       "INTERGRASE INHIBITORS (INSTIs) DRUG RESISTANCE INTERPRETATION", start_x,
                                       x_value,
                                       width, patient_name, ccc_num, todays_date, page_info)
            y = create_new_page(pdf, start_x, y, patient_name, ccc_num, todays_date, page_info, width, x_value)

            y = write_comments(pdf, y, "INSTI MUTATION COMMENTS:", intergrase_comments, start_x, x_value,
                               patient_name, ccc_num, todays_date, page_info, width)
            y = create_new_page(pdf, start_x, y, patient_name, ccc_num, todays_date, page_info, width, x_value)

            y = write_comments(pdf, y, "Accesory MUTATION COMMENTS:", intergrase_accessory_comments, start_x,
                               x_value, patient_name, ccc_num, todays_date, page_info, width)
            y = create_new_page(pdf, start_x, y, patient_name, ccc_num, todays_date, page_info, width, x_value)
    else:
        ######################################
        # ADVISORY
        ######################################
        advisory = ["The sample mentioned above failed amplification several times. Monitoring of viral load is "
                    "advised, ", "and a fresh sample after a month may be collected for HIVDR if VL is >1000cp/ml."]
        y -= 25
        draw_text(pdf, start_x, y, f"{advisory[0]}", "", x_value)
        y -= 15
        draw_text(pdf, start_x, y, f"{advisory[1]}", "", x_value)
        y -= 15
        y = create_new_page(pdf, start_x, y, patient_name, ccc_num, todays_date, page_info, width, x_value)

    ######################################
    # End of Report
    ######################################
    y -= 20
    # Add the image to the canvas above the "BIOCHEMISTRY REPORT" text and take the full width
    add_image(pdf, image_path1, x=start_x, y=y, width=width - 50, height=20)
    y = create_new_page(pdf, start_x, y, patient_name, ccc_num, todays_date, page_info, width, x_value)

    ######################################
    # Sign Report
    ######################################
    y -= 20
    x_value = 80
    draw_text(pdf, start_x, y, "Performed By:", f"{performed_by.title()}", x_value, bold=True)

    draw_text(pdf, start_x + 355, y, "Date:", f"{date_test_perfomed}", bold=True)

    y -= 5
    draw_horizontal_line(pdf, y, start_x + 70, width, width_x=150)
    draw_horizontal_line(pdf, y, start_x + 380, width)

    y = create_new_page(pdf, start_x, y, patient_name, ccc_num, todays_date, page_info, width, x_value)
    y -= 20
    draw_text(pdf, start_x, y, "Reviewed By:", f"{reviewed_by.title()}", x_value, bold=True)

    draw_text(pdf, start_x + 355, y, "Date:", f"{date_test_reviewed}", bold=True)
    y -= 5
    draw_horizontal_line(pdf, y, start_x + 70, width, width_x=150)
    draw_horizontal_line(pdf, y, start_x + 380, width)

    y = create_new_page(pdf, start_x, y, patient_name, ccc_num, todays_date, page_info, width, x_value)
    ######################################
    # Add last report footer
    ######################################
    draw_footer(pdf, start_x, patient_name, ccc_num, todays_date, page_info['page_count'] + 1, width, x_value)
    pdf.save()


class GenerateDrtPDF(View):
    def get(self, request):
        if request.user.is_authenticated and not request.user.first_name:
            return redirect("profile")

        # Retrieve the serialized DataFrame from the session
        drt_values_json = request.session.get('drt_values', {})
        drt_values = json.loads(drt_values_json)

        # # Create a new PDF object using ReportLab
        response = HttpResponse(content_type='application/pdf')
        ccc_num = drt_values.get("ccc_num", "")
        # print(drt_values.get("date_collected", ""))
        ccc_num_intergrase = drt_values.get("ccc_num_intergrase", "")
        if ccc_num:
            response[
                'Content-Disposition'] = f'filename="{ccc_num}_DRT Report_{drt_values.get("todays_date", "")}.pdf"'
        else:
            response['Content-Disposition'] = f'filename="DRT Report_{drt_values.get("todays_date", "")}.pdf"'
        pdf = canvas.Canvas(response, pagesize=letter)

        generate_drt_report(
            pdf,
            drt_values.get("todays_date", ""),
            drt_values.get("patient_name", ""),
            ccc_num,
            drt_values.get("rt_resistance_mutation_profile", ""),
            drt_values.get("nrtis_list", ""),
            drt_values.get("nrti_comments", ""),
            drt_values.get("other_rt_comments", ""),
            drt_values.get("pi_resistance_mutation_profile", ""),
            drt_values.get("nnrtis_list", ""),
            drt_values.get("nnrti_comments", ""),
            drt_values.get("pi_list", ""),
            # drt_values.get("pi_mutation_comments", ""),
            drt_values.get("other_pi_mutation_comments", ""),
            drt_values.get("intergrase_resistance_mutation_profile", ""),
            drt_values.get("intergrase_resistance_mutations", ""),
            drt_values.get("intergrase_comments", ""),
            drt_values.get("intergrase_accessory_comments", ""),
            drt_values.get("date_test_perfomed", ""),
            drt_values.get("date_test_reviewed", ""),

            drt_values.get("sex", ""),
            drt_values.get("age", ""),
            drt_values.get("age_unit", ""),
            drt_values.get("contact", ""),
            drt_values.get("specimen_type", ""),
            drt_values.get("request_from", ""),
            drt_values.get("requesting_clinician", ""),
            drt_values.get("performed_by", ""),
            drt_values.get("reviewed_by", ""),
            drt_values.get("date_collected", ""),
            drt_values.get("date_received", ""),
            drt_values.get("date_reported", ""),
            drt_values.get("pi_mutation_comments_major", ""),
            drt_values.get("pi_mutation_comments_accessory", ""),
            drt_values.get("sequence_summary", ""),
        )
        return response


class DateEncoder(DjangoJSONEncoder):
    def default(self, obj):
        if isinstance(obj, date):
            return obj.isoformat()
        return super().default(obj)


@login_required(login_url='login')
def generate_drt_results(request):
    if not request.user.first_name:
        return redirect("profile")
    title = "UPLOAD STANDFORD PDFS"
    todays_date = datetime.now().strftime("%d-%b-%Y")
    ccc_num = None
    sequence_summary = None
    show_download_button = False
    template_name = "lab_pulse/upload.html"

    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    # if request.method == 'POST' and "file" in request.FILES:
    form = DrtForm()
    # file = request.FILES['file']
    if request.method == 'POST':
        form = DrtForm(request.POST, request.FILES)
        context = {"form": form, "title": title, "show_download_button": show_download_button, "ccc_num": ccc_num}
        if form.is_valid():
            # Perform PDF compilation here using your function
            uploaded_files = request.FILES.getlist('files')
            #################
            # Validate date
            #################
            date_fields_to_validate = ['date_collected', 'date_received', 'date_reported', 'date_tested',
                                       'date_reviewed']
            if not validate_date_fields(form, date_fields_to_validate):
                # Render the template with the form and errors
                return render(request, template_name, context)
            #################
            # Validate form
            #################
            if not validate_add_drt_form(form):
                # If validation fails, return the form with error messages
                return render(request, template_name, context)
            # Access the cleaned data from the form
            patient_name = form.cleaned_data['patient_name']
            sex = form.cleaned_data['sex']
            age = form.cleaned_data['age']
            age_unit = form.cleaned_data['age_unit']
            contact = form.cleaned_data['contact']
            specimen_type = form.cleaned_data['specimen_type']
            request_from = form.cleaned_data['request_from']
            requesting_clinician = form.cleaned_data['requesting_clinician']
            performed_by = form.cleaned_data['performed_by']
            reviewed_by = form.cleaned_data['reviewed_by']
            date_collected = form.cleaned_data['date_collected']
            date_received = form.cleaned_data['date_received']
            date_reported = form.cleaned_data['date_reported']
            date_tested = form.cleaned_data['date_tested']
            date_reviewed = form.cleaned_data['date_reviewed']
            sequence_summary = form.cleaned_data['sequence_summary']
            if sequence_summary == "PASSED":
                ccc_num = None
            else:
                ccc_num = form.cleaned_data['patient_unique_no']

            if sequence_summary == "PASSED":
                extracted_pdf_text = []
                for i in uploaded_files:
                    extracted_pdf_text.append(read_pdf_file(i))
                ###############################
                # NON-INTERGRASE PDF
                ###############################
                pdf_text = [i for i in extracted_pdf_text if "Reverse transcriptase (RT)" in i]
                if pdf_text:
                    pi_resistance_mutation_profile, pi_list, pi_mutation_comments, other_pi_mutation_comments, \
                        rt_resistance_mutation_profile, nrti_tdf, nrti_3tc, nrti_ftc, nrti_ddi, nrti_d4t, nrti_azt, nrti_abc, \
                        nrti_comments, nnrti_dor, nnrti_efv, nnrti_etr, nnrti_nvp, nnrti_rpv, nnrtis_list, nnrti_comments, \
                        other_rt_comments, ccc_num, nrtis_list, pi_mutation_comments_major, \
                        pi_mutation_comments_accessory = extract_non_intergrase_text(pdf_text[0])

                else:
                    # Handle the case where pdf_text is empty
                    pi_resistance_mutation_profile = ""
                    pi_list = ""
                    pi_mutation_comments = ""
                    other_pi_mutation_comments = ""
                    rt_resistance_mutation_profile = ""
                    nrti_comments = ""
                    nnrtis_list = ""
                    nnrti_comments = ""
                    other_rt_comments = ""
                    ccc_num = ""
                    nrtis_list = ""
                    pi_mutation_comments_major = ""
                    pi_mutation_comments_accessory = ""
                ###############################
                # INTERGRASE PDF
                ###############################
                # try:
                pdf_text = [i for i in extracted_pdf_text if "Reverse transcriptase (RT)" not in i]
                if pdf_text:
                    intergrase_resistance_mutation_profile, intergrase_resistance_mutations, intergrase_comments, \
                        intergrase_accessory_comments, ccc_num_intergrase = extract_intergrase_text(pdf_text[0])
                else:
                    intergrase_resistance_mutation_profile = ""
                    intergrase_resistance_mutations = ""
                    intergrase_comments = ""
                    intergrase_accessory_comments = ""
                    ccc_num_intergrase = ""

                if ccc_num_intergrase == "":
                    drt_values_dict = {
                        'todays_date': todays_date, 'patient_name': patient_name, "sequence_summary": sequence_summary,
                        'ccc_num': ccc_num, 'rt_resistance_mutation_profile': rt_resistance_mutation_profile,
                        'nrtis_list': nrtis_list, 'nrti_comments': nrti_comments,
                        'other_rt_comments': other_rt_comments,
                        'pi_resistance_mutation_profile': pi_resistance_mutation_profile, 'nnrtis_list': nnrtis_list,
                        'nnrti_comments': nnrti_comments, 'pi_list': pi_list,
                        'pi_mutation_comments': pi_mutation_comments,
                        'other_pi_mutation_comments': other_pi_mutation_comments,

                        'date_test_perfomed': date_tested,
                        'date_test_reviewed': date_reviewed,

                        'sex': sex,
                        'age': age,
                        'age_unit': age_unit,
                        'contact': contact,
                        'specimen_type': specimen_type,
                        'request_from': request_from,
                        'requesting_clinician': requesting_clinician,
                        'performed_by': performed_by,
                        'reviewed_by': reviewed_by,
                        'date_collected': date_collected,
                        'date_received': date_received,
                        'date_reported': date_reported,
                        'pi_mutation_comments_major': pi_mutation_comments_major,
                        'pi_mutation_comments_accessory': pi_mutation_comments_accessory,
                    }
                    if "drt_values" in request.session:
                        del request.session['drt_values']
                        try:
                            request.session['drt_values'] = json.dumps(drt_values_dict, cls=DateEncoder)
                            request.session.save()
                        except Exception as e:
                            messages.error(request, f"Error updating session: {e}")
                    else:
                        request.session['drt_values'] = json.dumps(drt_values_dict, cls=DateEncoder)
                    show_download_button = True
                elif ccc_num == ccc_num_intergrase:
                    drt_values_dict = {
                        'todays_date': todays_date, 'patient_name': patient_name, "sequence_summary": sequence_summary,
                        'ccc_num': ccc_num, 'rt_resistance_mutation_profile': rt_resistance_mutation_profile,
                        'nrtis_list': nrtis_list, 'nrti_comments': nrti_comments,
                        'other_rt_comments': other_rt_comments,
                        'pi_resistance_mutation_profile': pi_resistance_mutation_profile, 'nnrtis_list': nnrtis_list,
                        'nnrti_comments': nnrti_comments, 'pi_list': pi_list,
                        'pi_mutation_comments': pi_mutation_comments,
                        'other_pi_mutation_comments': other_pi_mutation_comments,
                        'intergrase_resistance_mutation_profile': intergrase_resistance_mutation_profile,
                        'intergrase_resistance_mutations': intergrase_resistance_mutations,
                        'intergrase_comments': intergrase_comments,
                        'intergrase_accessory_comments': intergrase_accessory_comments,
                        'ccc_num_intergrase': ccc_num_intergrase, 'date_test_perfomed': date_tested,
                        'date_test_reviewed': date_reviewed,

                        'sex': sex,
                        'age': age,
                        'age_unit': age_unit,
                        'contact': contact,
                        'specimen_type': specimen_type,
                        'request_from': request_from,
                        'requesting_clinician': requesting_clinician,
                        'performed_by': performed_by,
                        'reviewed_by': reviewed_by,
                        'date_collected': date_collected,
                        'date_received': date_received,
                        'date_reported': date_reported,
                        'pi_mutation_comments_major': pi_mutation_comments_major,
                        'pi_mutation_comments_accessory': pi_mutation_comments_accessory,
                    }

                    if "drt_values" in request.session:
                        del request.session['drt_values']
                        try:
                            request.session['drt_values'] = json.dumps(drt_values_dict, cls=DateEncoder)
                            request.session.save()
                        except Exception as e:
                            messages.error(request, f"Error updating session: {e}")
                    else:
                        request.session['drt_values'] = json.dumps(drt_values_dict, cls=DateEncoder)
                    show_download_button = True
                else:
                    messages.error(request,
                                   f"Please upload two PDFs (one with RT/PR and other with INSTIs) for the same patient."
                                   f" The uploaded PDFs belong to different patients. "
                                   f"({ccc_num} and {ccc_num_intergrase}).")
                    render(request, template_name, context)
            else:
                drt_values_dict = {
                    'todays_date': todays_date, 'patient_name': patient_name, "sequence_summary": sequence_summary,
                    'ccc_num': ccc_num, 'date_test_perfomed': date_tested,
                    'date_test_reviewed': date_reviewed,
                    'sex': sex,
                    'age': age,
                    'age_unit': age_unit,
                    'contact': contact,
                    'specimen_type': specimen_type,
                    'request_from': request_from,
                    'requesting_clinician': requesting_clinician,
                    'performed_by': performed_by,
                    'reviewed_by': reviewed_by,
                    'date_collected': date_collected,
                    'date_received': date_received,
                    'date_reported': date_reported,
                }

                if "drt_values" in request.session:
                    del request.session['drt_values']
                    try:
                        request.session['drt_values'] = json.dumps(drt_values_dict, cls=DateEncoder)
                        request.session.save()
                    except Exception as e:
                        messages.error(request, f"Error updating session: {e}")
                else:
                    request.session['drt_values'] = json.dumps(drt_values_dict, cls=DateEncoder)
                show_download_button = True
                pass

    context = {
        "form": form, "sequence_summary": sequence_summary,
        "title": title, "show_download_button": show_download_button, "ccc_num": ccc_num,
    }
    return render(request, template_name, context)


def extract_text_make_df(pi_resistance_profile, col, unique_id, pdf_text):
    pi_resistance_profile_match = pi_resistance_profile.search(pdf_text)
    pi_resistance_profile = {}
    if pi_resistance_profile_match:
        pi_resistance_profile_text = pi_resistance_profile_match.group(1)
        pi_resistance_profile[col] = pi_resistance_profile_text
    pi_resistance_profile_df1 = pd.DataFrame([pi_resistance_profile], )
    pi_resistance_profile_df1['patient_id'] = f"{unique_id}"
    return pi_resistance_profile_df1


def create_specific_data_frame(pattern, col_name, unique_id, sequence_df, pdf_text, haart_class=None):
    if "FAILED" in sequence_df['sequence summary'].values:
        data_frame = pd.DataFrame(columns=[col_name], index=[0])
        data_frame['sequence summary'] = "FAILED"
        data_frame.insert(0, 'patient_id', str(unique_id))

    else:
        data_frame = extract_text_make_df(pattern, col_name, unique_id, pdf_text)
        if data_frame.shape[1] == 2:
            data_frame = create_specific_dfs(data_frame, col_name)
            data_frame['sequence summary'] = "PASSED"
            if haart_class is not None:
                data_frame['haart_class'] = haart_class
            data_frame.insert(0, 'patient_id', str(unique_id))
        else:
            data_frame = pd.DataFrame(columns=['patient_id', 'sequence summary'])
    return data_frame


def process_resistance_df(resistance_df, date_collected, date_received, date_reported, date_performed, performed_by,
                          age, sex):
    resistance_df['date_collected'] = date_collected
    resistance_df['date_received'] = date_received
    resistance_df['date_reported'] = date_reported
    resistance_df['date_test_perfomed'] = date_performed
    resistance_df['test_perfomed_by'] = performed_by
    resistance_df['age'] = age.split()[0]
    resistance_df['age_unit'] = age.split()[1]
    resistance_df['sex'] = sex

    for col in ['date_collected', 'date_received', 'date_reported', 'date_test_perfomed']:
        resistance_df[col] = pd.to_datetime(resistance_df[col])
    return resistance_df


def extract_dates_from_text(pdf_text):
    # Define regular expressions for extracting dates
    performed_by_regex = r'Performed By: (\w+\s\w+)'
    performed_date_regex = r'Date: (\d{4}-\d{2}-\d{2})'
    reviewed_by_regex = r'Reviewed By: (\w+\s\w+)'
    reviewed_date_regex = r'Date: (\d{4}-\d{2}-\d{2})'

    # Search for matches using regular expressions
    performed_by_match = re.search(performed_by_regex, pdf_text)
    performed_date_match = re.search(performed_date_regex, pdf_text)
    reviewed_by_match = re.search(reviewed_by_regex, pdf_text)
    reviewed_date_match = re.search(reviewed_date_regex, pdf_text)

    # Extract information if matches are found
    performed_by = performed_by_match.group(1) if performed_by_match else None
    performed_date = performed_date_match.group(1) if performed_date_match else None
    reviewed_by = reviewed_by_match.group(1) if reviewed_by_match else None
    reviewed_date = reviewed_date_match.group(1) if reviewed_date_match else None

    # Replace "Date" if "performed_by" is present
    if performed_by:
        performed_by = performed_by.replace(" Date", "")
    # Replace "Date" if "reviewed_by" is present
    if reviewed_by:
        reviewed_by = reviewed_by.replace(" Date", "")

    return {
        'performed_by': performed_by,
        'performed_date': performed_date,
        'reviewed_by': reviewed_by,
        'reviewed_date': reviewed_date,
    }


def add_empty_columns(df, columns_to_add, fill_value=np.nan):
    for column in columns_to_add:
        df[column] = fill_value
    return df


def create_failed_df(resistance_patterns_df, resistance_profiles_df, sex):
    # Selecting the first row
    resistance_patterns_df = resistance_patterns_df.head(1)
    resistance_profiles_df = resistance_profiles_df.head(1)

    # Columns to keep
    columns_to_keep = ['patient_id', 'sequence summary', 'date_collected',
                       'date_received', 'date_reported', 'date_test_perfomed',
                       'test_perfomed_by', 'age', 'age_unit', 'sex']

    # Selecting relevant columns
    resistance_patterns_df = resistance_patterns_df[columns_to_keep]
    resistance_profiles_df = resistance_profiles_df[columns_to_keep]

    # Columns to add with empty values
    columns_to_add_patterns = ['Drug', 'Drug Abbreviation', 'Resistance Level', 'haart_class']
    columns_to_add_profiles = ['haart_class', 'Mutation Type', 'Mutations']

    # Adding new columns with NaN values to the DataFrames
    resistance_patterns_df = add_empty_columns(resistance_patterns_df, columns_to_add_patterns)
    resistance_profiles_df = add_empty_columns(resistance_profiles_df, columns_to_add_profiles)

    # Adding 'sex' column
    resistance_patterns_df["sex"] = sex
    resistance_profiles_df["sex"] = sex

    # Reordering columns
    resistance_patterns_df = resistance_patterns_df[columns_to_keep + columns_to_add_patterns]
    resistance_profiles_df = resistance_profiles_df[columns_to_keep + columns_to_add_profiles]

    return resistance_profiles_df, resistance_patterns_df


def develop_df_from_pdf(pdf_text):
    # Define regular expressions for pattern matching
    sequence_summary_pattern = re.compile(r'Sequencing Analysis: (\w+)')
    rt_resistance_pattern = re.compile(
        r'RT RESISTANCE MUTATION PROFILE([\s\S]*?)NUCLEOSIDE REVERSE TRANSCRIPTASE INHIBITORS', re.MULTILINE)
    nrti_resistance_pattern = re.compile(
        r'NUCLEOSIDE REVERSE TRANSCRIPTASE INHIBITORS \(NRTIS\) DRUG RESISTANCE INTERPRETATION([\s\S]*?)NON-NUCLEOSIDE REVERSE TRANSCRIPTASE INHIBITORS',
        re.MULTILINE)
    nnrti_resistance_pattern = re.compile(
        r'NON-NUCLEOSIDE REVERSE TRANSCRIPTASE INHIBITORS \(NNRTIS\) DRUG RESISTANCE INTERPRETATION([\s\S]*?)PROTEASE INHIBITORS',
        re.MULTILINE)
    pi_resistance_pattern = re.compile(
        r'PROTEASE INHIBITORS \(PIS\) DRUG RESISTANCE INTERPRETATION([\s\S]*?)PI MUTATION COMMENTS', re.MULTILINE)
    pi_resistance_profile = re.compile(r'PI RESISTANCE MUTATION PROFILE([\s\S]*?)PROTEASE INHIBITORS', re.MULTILINE)

    insti_resistance_profile = re.compile(r'INSTI RESISTANCE MUTATION PROFILE([\s\S]*?)INTERGRASE INHIBITORS',
                                          re.MULTILINE)
    insti_resistance_pattern = re.compile(r'INTERGRASE INHIBITORS([\s\S]*?)INSTI MUTATION COMMENTS', re.MULTILINE)

    # Define regular expressions for pattern matching
    date_collected_pattern = re.compile(r'Date Collected:([\s\S]*?)Requested', re.MULTILINE)
    date_received_pattern = re.compile(r'Date Received:([\s\S]*?)Requesting Clinician:', re.MULTILINE)
    date_reported_pattern = re.compile(r'Date Reported:([\s\S]*?)SEQUENCE SUMMARY', re.MULTILINE)
    unique_id_pattern = re.compile(r'Unique ID:\s*([\d]+)')
    age_pattern = re.compile(r'Age:([\s\S]*?)Contact:', re.MULTILINE)
    # Define regular expressions for pattern matching
    performed_by_pattern = re.compile(r'Performed By:\s*(.*?)(?=Date:|$)', re.DOTALL)
    reviewed_by_pattern = re.compile(r'Reviewed By:\s*(.*?)(?=Date:|$)', re.DOTALL)
    date_pattern = re.compile(r'Date:\s*([\d/]+)')
    sex_pattern = re.compile(r'Sex:([\s\S]*?)Age:', re.MULTILINE)

    # Extract the information from the text
    date_collected_match = date_collected_pattern.search(pdf_text)
    date_received_match = date_received_pattern.search(pdf_text)
    date_reported_match = date_reported_pattern.search(pdf_text)
    unique_id_match = unique_id_pattern.search(pdf_text)
    # Extract the information from the text
    performed_by_match = performed_by_pattern.search(pdf_text)
    reviewed_by_match = reviewed_by_pattern.search(pdf_text)
    date_match = date_pattern.search(pdf_text)
    age_match = age_pattern.search(pdf_text)
    sex_match = sex_pattern.search(pdf_text)

    # Get the matched values
    date_collected = date_collected_match.group(1) if date_collected_match else "N/A"
    date_received = date_received_match.group(1) if date_received_match else "N/A"
    date_reported = date_reported_match.group(1) if date_reported_match else "N/A"
    unique_id = unique_id_match.group(1) if unique_id_match else "N/A"
    # # Get the matched values
    # performed_by = performed_by_match.group(1).strip().replace(" ", "") if performed_by_match else "N/A"
    #
    # date_performed = date_match.group(1) if date_match else "N/A"
    sex = sex_match.group(1).strip() if unique_id_match else "N/A"
    dates_info = extract_dates_from_text(pdf_text)

    # Access the extracted information
    performed_by = dates_info['performed_by']
    date_performed = dates_info['performed_date']
    reviewed_by = dates_info['reviewed_by']
    reviewed_date = dates_info['reviewed_date']

    age = age_match.group(1).strip() if date_match else "N/A"

    performed_by = re.sub(r"(\w)([A-Z])", r"\1 \2", performed_by)

    sequence_df = extract_text_make_df(sequence_summary_pattern, "sequence summary", unique_id, pdf_text)

    pi_resistance_profile_df = create_specific_data_frame(pi_resistance_profile, "PI Resistance Mutations Profile",
                                                          unique_id, sequence_df, pdf_text)
    if insti_resistance_profile is not None:
        insti_resistance_profile_df = create_specific_data_frame(insti_resistance_profile,
                                                                 "INSTI Resistance Mutations Profile", unique_id,
                                                                 sequence_df, pdf_text)
    else:
        insti_resistance_profile_df = pd.DataFrame(
            columns=['patient_id', 'Mutation Type', 'Mutations', 'sequence summary'])
    rt_resistance_profile_df = create_specific_data_frame(rt_resistance_pattern, "RT Resistance Mutations Profile",
                                                          unique_id, sequence_df, pdf_text)

    nrti_resistance_df = create_specific_data_frame(nrti_resistance_pattern, "NRTI Resistance Mutations", unique_id,
                                                    sequence_df, pdf_text, "NRTIs")
    nnrti_resistance_df = create_specific_data_frame(nnrti_resistance_pattern, "NNRTI Resistance Mutations", unique_id,
                                                     sequence_df, pdf_text, "NNRTIs")
    pi_resistance_df = create_specific_data_frame(pi_resistance_pattern, "PI Resistance Mutations", unique_id,
                                                  sequence_df, pdf_text, "PIs")
    if insti_resistance_pattern is not None:
        insti_resistance_df = create_specific_data_frame(insti_resistance_pattern, "INSTI Resistance Mutations",
                                                         unique_id,
                                                         sequence_df, pdf_text, "INSTIs")
    else:
        insti_resistance_df = pd.DataFrame(columns=['patient_id', 'Mutation Type', 'Mutations', 'sequence summary'])

    resistance_profiles_df = pd.concat(
        [rt_resistance_profile_df, pi_resistance_profile_df, insti_resistance_profile_df])
    resistance_profiles_df = process_resistance_df(resistance_profiles_df, date_collected, date_received, date_reported,
                                                   date_performed, performed_by, age, sex)

    resistance_patterns_df = pd.concat([nrti_resistance_df, nnrti_resistance_df, pi_resistance_df, insti_resistance_df])
    resistance_patterns_df = process_resistance_df(resistance_patterns_df, date_collected, date_received, date_reported,
                                                   date_performed, performed_by, age, sex)
    #

    # Check if 'sequence summary' column is not empty
    if resistance_patterns_df['sequence summary'].unique().size > 0:
        if "failed" not in resistance_patterns_df['sequence summary'].unique()[0].lower():
            resistance_patterns_df = resistance_patterns_df.dropna()
            resistance_profiles_df['haart_class'] = resistance_profiles_df['Mutation Type'].str.split().str[0]
            resistance_profiles_df['haart_class'] = resistance_profiles_df['haart_class'].replace("PR", "PR Other")
            resistance_profiles_df['haart_class'] = resistance_profiles_df['haart_class'].replace("IN", "IN Other")
            resistance_profiles_df['haart_class'] = resistance_profiles_df['haart_class'].replace("RT", "RT Other")
        else:
            resistance_profiles_df, resistance_patterns_df = create_failed_df(resistance_patterns_df,
                                                                              resistance_profiles_df, sex)
    else:
        resistance_profiles_df, resistance_patterns_df = create_failed_df(resistance_patterns_df,
                                                                          resistance_profiles_df, sex)
    return resistance_profiles_df, resistance_patterns_df


def create_specific_dfs(pdf_df, col):
    list_a = list(pdf_df[col].unique())

    # Check if "(" exists in any of the strings
    has_parenthesis = any("(" in s for s in list_a)

    if has_parenthesis:
        # Split the 'PI Resistance Mutations' into separate rows
        pdf_df1 = pdf_df[col].str.split('\n').explode()

        # Extract 'Drug', 'Drug Abbreviation', and 'Resistance Level' from each row
        drug_data = pdf_df1.str.extract(r'^(.+?) \(([^)]+)\) (.+)$')
        drug_data = drug_data[drug_data[drug_data.columns[0]].notnull()]

        # Rename the columns
        drug_data.columns = ['Drug', 'Drug Abbreviation', 'Resistance Level']

        # Reset the index
        drug_data = drug_data.reset_index(drop=True)
        if drug_data.shape[0] == 0:
            drug_data['Drug'] = ""
            drug_data['Drug Abbreviation'] = ""
            drug_data['Resistance Level'] = ""
        drug_data = drug_data[drug_data['Drug'].notnull()]
    else:
        # Split the 'RT Resistance Mutations Profile' into separate rows
        pdf_df1 = pdf_df[col].str.split('\n').explode()

        # Extract 'Mutation Type' and 'Mutations' from each row
        drug_data = pdf_df1.str.extract(r'^(.*?):(.+)$')

        # Rename the columns
        drug_data.columns = ['Mutation Type', 'Mutations']

        # Reset the index
        drug_data = drug_data.reset_index(drop=True)
        if drug_data.shape[0] == 0:
            drug_data['Mutation Type'] = ""
            drug_data['Mutations'] = ""
        drug_data = drug_data[drug_data['Mutation Type'].notnull()]
    return drug_data
