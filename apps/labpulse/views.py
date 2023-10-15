import csv
import math
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd
import plotly.express as px
import pytz
import tzlocal
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core import serializers
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import ExpressionWrapper, F, IntegerField, Sum
from django.db.models.functions import Extract
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from plotly.offline import plot
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from apps.cqi.forms import FacilitiesForm
from apps.cqi.models import Counties, Facilities, Sub_counties
from apps.cqi.views import bar_chart
from apps.data_analysis.views import get_key_from_session_names
# from apps.dqa.views import disable_update_buttons
from apps.labpulse.decorators import group_required
from apps.labpulse.filters import Cd4trakerFilter
from apps.labpulse.forms import Cd4TestingLabForm, Cd4TestingLabsForm, Cd4trakerForm, Cd4trakerManualDispatchForm, \
    LabPulseUpdateButtonSettingsForm, ReagentStockForm, facilities_lab_Form
from apps.labpulse.models import Cd4TestingLabs, Cd4traker, EnableDisableCommodities, LabPulseUpdateButtonSettings, \
    ReagentStock


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

    # Calculate the number of samples positive
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
        'Number of Samples Positive': [num_samples_positive],
        'Number of Samples Negative': [num_samples_negative],
        f'{title} Positivity (%)': [positivity_rate]
    })
    positivity_df = positivity_df.T.reset_index().fillna(0)
    positivity_df.columns = ['variables', 'values']
    positivity_df = positivity_df[positivity_df['values'] != 0]
    fig = bar_chart(positivity_df, "variables", "values", f"{title} Testing Results", color='variables')

    return fig, positivity_df


def line_chart_median_mean(df, x_axis, y_axis, title, color=None):
    df = df.copy()
    df = df.tail(52)
    mean_sample_tested = sum(df[y_axis]) / len(df[y_axis])
    median_sample_tested = df[y_axis].median()

    fig = px.line(df, x=x_axis, y=y_axis, text=y_axis, color=color,
                  height=450,
                  title=title)
    y = int(mean_sample_tested)
    x = int(median_sample_tested)
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)
    fig.update_layout({
        'plot_bgcolor': 'rgba(0, 0, 0, 0)',
        'paper_bgcolor': 'rgba(0, 0, 0, 0)',
    })
    fig.update_traces(textposition='top center')
    if 'TAT type' not in df.columns:
        fig.add_shape(type='line', x0=df[x_axis].min(), y0=y,
                      x1=df[x_axis].max(),
                      y1=y,
                      line=dict(color='red', width=2, dash='dot'))

        fig.add_annotation(x=df[x_axis].max(), y=y,
                           text=f"Mean weekly CD4 count collection {y}",
                           showarrow=True, arrowhead=1,
                           font=dict(size=8, color='red'))
        fig.add_shape(type='line', x0=df[x_axis].min(), y0=x,
                      x1=df[x_axis].max(),
                      y1=x,
                      line=dict(color='black', width=2, dash='dot'))

        fig.add_annotation(x=df[x_axis].min(), y=x,
                           text=f"Median weekly CD4 count collection {x}",
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
    df['Date Dispatch'] = pd.to_datetime(df['Date Dispatch'])
    df['Collection Date'] = pd.to_datetime(df['Collection Date'])
    df['Received date'] = pd.to_datetime(df['Received date'])

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


def generate_results_df(list_of_projects):
    # convert data from database to a dataframe
    list_of_projects = pd.DataFrame(list_of_projects)
    # Define a dictionary to rename columns
    cols_rename = {
        "county__county_name": "County", "sub_county__sub_counties": "Sub-county",
        "testing_laboratory__testing_lab_name": "Testing Laboratory", "facility_name__name": "Facility",
        "facility_name__mfl_code": "MFL CODE", "patient_unique_no": "CCC NO.", "age": "Age", "sex": "Sex",
        "date_of_collection": "Collection Date", "date_of_testing": "Testing date",
        "date_sample_received": "Received date",
        "date_dispatched": "Date Dispatch",
        "justification": "Justification", "cd4_count_results": "CD4 Count",
        "date_serum_crag_results_entered": "Serum CRAG date",
        "serum_crag_results": "Serum Crag", "date_tb_lam_results_entered": "TB LAM date",
        "tb_lam_results": "TB LAM", "received_status": "Received status",
        "reason_for_rejection": "Rejection reason",
        "tat_days": "TAT", "age_unit": "age_unit",
    }
    list_of_projects = list_of_projects.rename(columns=cols_rename)
    list_of_projects_fac = list_of_projects.copy()

    # Convert Timestamp objects to strings
    list_of_projects_fac = list_of_projects_fac.sort_values('Collection Date').reset_index(drop=True)
    # convert to datetime with UTC
    date_columns=['Testing date','Collection Date','Received date','Date Dispatch']
    list_of_projects_fac[date_columns] = list_of_projects_fac[date_columns].astype("datetime64[ns, UTC]")
    # Convert the dates to user local timezone
    local_timezone = tzlocal.get_localzone()
    # Convert the dates to the local timezone
    list_of_projects_fac['Collection Date'] = list_of_projects_fac['Collection Date'].dt.tz_convert(
        local_timezone)
    list_of_projects_fac['Received date'] = list_of_projects_fac['Received date'].dt.tz_convert(
        local_timezone)
    list_of_projects_fac['Date Dispatch'] = list_of_projects_fac['Date Dispatch'].dt.tz_convert(
        local_timezone)
    list_of_projects_fac['Testing date'] = list_of_projects_fac['Testing date'].dt.tz_convert(
        local_timezone)
    list_of_projects_fac['Testing date'] = pd.to_datetime(list_of_projects_fac['Testing date']).dt.date
    list_of_projects_fac['Received date'] = pd.to_datetime(list_of_projects_fac['Received date']).dt.date
    list_of_projects_fac['Collection Date'] = pd.to_datetime(list_of_projects_fac['Collection Date']).dt.date
    list_of_projects_fac['Date Dispatch'] = pd.to_datetime(list_of_projects_fac['Date Dispatch']).dt.date
    list_of_projects_fac['TB LAM date'] = pd.to_datetime(list_of_projects_fac['TB LAM date']).dt.date
    list_of_projects_fac['Serum CRAG date'] = pd.to_datetime(list_of_projects_fac['Serum CRAG date']).dt.date
    list_of_projects_fac['Collection Date'] = list_of_projects_fac['Collection Date'].astype(str)
    list_of_projects_fac['Testing date'] = list_of_projects_fac['Testing date'].replace(np.datetime64('NaT'),
                                                                                        '')
    list_of_projects_fac['Testing date'] = list_of_projects_fac['Testing date'].astype(str)
    list_of_projects_fac['Received date'] = list_of_projects_fac['Received date'].replace(np.datetime64('NaT'),
                                                                                          '')
    list_of_projects_fac['Received date'] = list_of_projects_fac['Received date'].astype(str)
    list_of_projects_fac['Date Dispatch'] = list_of_projects_fac['Date Dispatch'].astype(str)
    list_of_projects_fac['TB LAM date'] = list_of_projects_fac['TB LAM date'].replace(np.datetime64('NaT'), '')
    list_of_projects_fac['TB LAM date'] = list_of_projects_fac['TB LAM date'].astype(str)
    list_of_projects_fac['Serum CRAG date'] = list_of_projects_fac['Serum CRAG date'].replace(
        np.datetime64('NaT'),
        '')
    list_of_projects_fac['Serum CRAG date'] = list_of_projects_fac['Serum CRAG date'].astype(str)
    list_of_projects_fac.index = range(1, len(list_of_projects_fac) + 1)
    max_date = list_of_projects_fac['Collection Date'].max()
    min_date = list_of_projects_fac['Collection Date'].min()
    missing_df = list_of_projects_fac.loc[
        (list_of_projects_fac['CD4 Count'] < 200) & (list_of_projects_fac['Serum Crag'].isna())]
    missing_tb_lam_df = list_of_projects_fac.loc[
        (list_of_projects_fac['CD4 Count'] < 200) & (list_of_projects_fac['TB LAM'].isna())]
    crag_pos_df = list_of_projects_fac.loc[(list_of_projects_fac['Serum Crag'] == "Positive")]
    tb_lam_pos_df = list_of_projects_fac.loc[(list_of_projects_fac['TB LAM'] == "Positive")]
    rejected_df = list_of_projects_fac.loc[(list_of_projects_fac['Received status'] == "Rejected")]

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
    ###################################
    # CD4 SUMMARY CHART
    ###################################
    cd4_summary_fig = bar_chart(summary_df, "variables", "values",
                                f"Summary of CD4 Records and Serum CrAg Results Between {min_date} and {max_date} ")

    # Group the data by testing laboratory and calculate the counts
    summary_df = list_of_projects_fac.groupby('Testing Laboratory').agg({
        'CD4 Count': 'count',
        'Serum Crag': lambda x: x.count() if x.notnull().any() else 0
    }).reset_index()

    # Rename the columns
    summary_df.rename(columns={'CD4 Count': 'Total CD4 Count', 'Serum Crag': 'Total CRAG Reports'},
                      inplace=True)

    # Sort the dataframe by testing laboratory name
    summary_df.sort_values('Testing Laboratory', inplace=True)

    # Reset the index
    summary_df.reset_index(drop=True, inplace=True)

    summary_df = pd.melt(summary_df, id_vars="Testing Laboratory",
                         value_vars=['Total CD4 Count', 'Total CRAG Reports'],
                         var_name="Test done", value_name='values')
    show_cd4_testing_workload = False
    show_crag_testing_workload = False
    cd4_df = summary_df[summary_df['Test done'] == "Total CD4 Count"].sort_values("values").fillna(0)
    cd4_df = cd4_df[cd4_df['values'] != 0]
    if not cd4_df.empty:
        show_cd4_testing_workload = True
    crag_df = summary_df[summary_df['Test done'] == "Total CRAG Reports"].sort_values("values").fillna(0)
    crag_df = crag_df[crag_df['values'] != 0]
    if not crag_df.empty:
        show_crag_testing_workload = True
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

    list_of_projects_fac_above1age_sex = list_of_projects_fac[list_of_projects_fac['age_unit'] == "years"]
    list_of_projects_fac_below1age_sex = list_of_projects_fac[list_of_projects_fac['age_unit'] != "years"]

    list_of_projects_fac_below1age_sex['Age Group'] = "<1"
    list_of_projects_fac_above1age_sex['Age Group'] = pd.cut(list_of_projects_fac_above1age_sex['Age'],
                                                             bins=age_bins, labels=age_labels)

    list_of_projects_fac = pd.concat([list_of_projects_fac_above1age_sex, list_of_projects_fac_below1age_sex])

    age_sex_df = list_of_projects_fac.groupby(['Age Group', 'Sex']).size().unstack().reset_index()
    return age_sex_df, cd4_summary_fig, crag_testing_lab_fig, cd4_testing_lab_fig, rejected_df, tb_lam_pos_df, \
        crag_pos_df, missing_tb_lam_df, missing_df, list_of_projects_fac, show_cd4_testing_workload, show_crag_testing_workload

def download_csv(request, filter_type):
    # Get the serialized filtered data from the session
    filtered_data_json = request.session.get('filtered_queryset')

    # Deserialize the JSON data and reconstruct the queryset
    filtered_data = serializers.deserialize('json', filtered_data_json)
    queryset = [item.object for item in filtered_data]

    # Perform filtering based on 'filter_type'
    if filter_type == 'all':
        pass  # No need to filter further for 'all'
    elif filter_type == 'rejected':
        queryset = [item for item in queryset if item.received_status == 'Rejected']
    elif filter_type == 'positive_tb_lam':
        queryset = [item for item in queryset if item.tb_lam_results == 'Positive']
    elif filter_type == 'positive_crag':
        queryset = [item for item in queryset if item.serum_crag_results == 'Positive']
    elif filter_type == 'missing_crag':
        queryset = [item for item in queryset if
                    item.cd4_count_results is not None and item.cd4_count_results <= 200 and item.serum_crag_results is None]
    elif filter_type == 'missing_tb_lam':
        queryset = [item for item in queryset if
                    item.cd4_count_results is not None and item.cd4_count_results <= 200 and item.tb_lam_results is None]
    else:
        # Handle invalid filter_type or other conditions as needed
        queryset = []

    # Create a CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filter_type}_records.csv"'

    # Create a CSV writer and write the header row
    writer = csv.writer(response)
    header = ["Patient Unique No.", "Facility Name", "Age", "Age Unit", "Sex",
              "Date of Collection", "Date of Receipt", "Date of Testing", "Dispatch Date", "CD4 Count",
              "TB LAM Results", "Serum CRAG Results", "Justification", "Received Status", "Reason for Rejection",
              "Reason for No Serum CRAG", "Testing Laboratory"]
    writer.writerow(header)

    # Write data rows based on the filtered queryset
    for record in queryset:
        data_row = [
            record.patient_unique_no,
            record.facility_name.name if record.facility_name else '',
            record.age,
            record.get_age_unit_display(),
            record.get_sex_display(),
            record.date_of_collection if record.date_of_collection else '',
            record.date_sample_received if record.date_sample_received else '',
            record.date_of_testing if record.date_of_testing else '',
            record.date_dispatched if record.date_dispatched else '',
            record.cd4_count_results if record.cd4_count_results else '',
            record.tb_lam_results if record.tb_lam_results else '',
            record.serum_crag_results if record.serum_crag_results else '',
            record.justification if record.justification else '',
            record.get_received_status_display(),
            record.reason_for_rejection if record.reason_for_rejection else '',
            record.reason_for_no_serum_crag if record.reason_for_no_serum_crag else '',
            record.testing_laboratory.testing_lab_name if record.testing_laboratory else '',

        ]
        writer.writerow(data_row)

    return response


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
    cd4_summary_fig = None
    cd4_testing_lab_fig = None
    crag_testing_lab_fig = None
    weekly_tat_trend_fig = None
    facility_tb_lam_positive_fig = None
    weekly_trend_fig = None
    age_distribution_fig = None
    rejection_summary_fig = None
    justification_summary_fig = None
    crag_positivity_fig = None
    tb_lam_positivity_fig = None
    facility_crag_positive_fig = None
    list_of_projects_fac = pd.DataFrame()
    crag_pos_df = pd.DataFrame()
    tb_lam_pos_df = pd.DataFrame()
    weekly_df = pd.DataFrame()
    missing_df = pd.DataFrame()
    missing_tb_lam_df = pd.DataFrame()
    rejected_df = pd.DataFrame()
    rejection_summary_df = pd.DataFrame()
    justification_summary_df = pd.DataFrame()
    show_cd4_testing_workload = False
    show_crag_testing_workload = False
    crag_positivity_df = pd.DataFrame()
    tb_lam_positivity_df = pd.DataFrame()
    facility_positive_count = pd.DataFrame()

    cd4traker_qs = Cd4traker.objects.all().order_by('-date_dispatched')
    # Calculate TAT in days and annotate it in the queryset
    queryset = cd4traker_qs.annotate(
        tat_days=ExpressionWrapper(
            Extract(F('date_dispatched') - F('date_of_collection'), 'day'),
            output_field=IntegerField()
        )
    )
    my_filters = Cd4trakerFilter(request.GET, queryset=queryset)
    try:
        if "filtered_queryset" in request.session:
            del request.session['filtered_queryset']

        # Serialize the filtered queryset to JSON and store it in the session
        filtered_data_json = serializers.serialize('json', my_filters.qs)
        request.session['filtered_queryset'] = filtered_data_json
    except KeyError:
        # Handles the case where the session key doesn't exist
        pass

    record_count_options = [(str(i), str(i)) for i in [5, 10, 20, 30, 40, 50]] + [("all", "All"), ]

    qi_list = pagination_(request, my_filters.qs, record_count)

    # Check if there records exists in filtered queryset
    rejected_samples_exist = my_filters.qs.filter(received_status="Rejected").exists()
    tb_lam_pos_samples_exist = my_filters.qs.filter(tb_lam_results="Positive").exists()
    crag_pos_samples_exist = my_filters.qs.filter(serum_crag_results="Positive").exists()
    missing_crag_samples_exist = my_filters.qs.filter(cd4_count_results__isnull=False,
                                                      cd4_count_results__lte=200,
                                                      serum_crag_results__isnull=True
                                                      ).exists()
    missing_tb_lam_samples_exist = my_filters.qs.filter(cd4_count_results__isnull=False,
                                                        cd4_count_results__lte=200,
                                                        tb_lam_results__isnull=True
                                                        ).exists()

    ######################
    # Hide update button #
    ######################
    if qi_list:
        disable_update_buttons(request, qi_list, 'date_dispatched')
    if my_filters.qs:
        # fields to extract
        fields = ['county__county_name', 'sub_county__sub_counties', 'testing_laboratory__testing_lab_name',
                  'facility_name__name', 'facility_name__mfl_code', 'patient_unique_no', 'age', 'sex',
                  'date_of_collection', 'date_of_testing', 'date_sample_received', 'date_dispatched', 'justification',
                  'cd4_count_results',
                  'date_serum_crag_results_entered', 'serum_crag_results', 'date_tb_lam_results_entered',
                  'tb_lam_results', 'received_status', 'reason_for_rejection', 'tat_days', 'age_unit']

        # Extract the data from the queryset using values()
        data = my_filters.qs.values(*fields)

        age_sex_df, cd4_summary_fig, crag_testing_lab_fig, cd4_testing_lab_fig, rejected_df, tb_lam_pos_df, \
            crag_pos_df, missing_tb_lam_df, missing_df, list_of_projects_fac, show_cd4_testing_workload,\
            show_crag_testing_workload = generate_results_df(data)
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
                                                      f"      Maximum # CD4 counts : {max(weekly_df['# of samples processed'])}")

        weekly_df['week_start'] = pd.to_datetime(weekly_df['week_start']).dt.date
        weekly_df['week_start'] = weekly_df['week_start'].replace(np.datetime64('NaT'), '')
        weekly_df['week_start'] = weekly_df['week_start'].astype(str)

        ###################################
        # Weekly TAT Trend viz
        ###################################
        melted_tat_df, mean_c_r, mean_c_d = calculate_weekly_tat(list_of_projects_fac.copy())
        if melted_tat_df.shape[0] > 1:
            melted_tat_df = melted_tat_df.head(52)
            weekly_tat_trend_fig = line_chart_median_mean(melted_tat_df, "Weekly Trend", "Weekly mean TAT",
                                                          f"Weekly Collection to Dispatch vs Collection to Receipt Mean "
                                                          f"TAT Trend  (C-D TAT = {mean_c_d}, C-R TAT = {mean_c_r})",
                                                          color="TAT type"
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
        "title": "Results", "record_count_options": record_count_options,"record_count": record_count,
        "rejected_samples_exist": rejected_samples_exist,"tb_lam_pos_samples_exist": tb_lam_pos_samples_exist,
        "crag_pos_samples_exist": crag_pos_samples_exist,"missing_crag_samples_exist": missing_crag_samples_exist,
        "missing_tb_lam_samples_exist": missing_tb_lam_samples_exist,"dictionary": dictionary,"my_filters": my_filters,
        "qi_list": qi_list,"cd4_summary_fig": cd4_summary_fig,"crag_testing_lab_fig": crag_testing_lab_fig,
        "weekly_trend_fig": weekly_trend_fig,"cd4_testing_lab_fig": cd4_testing_lab_fig,
        "age_distribution_fig": age_distribution_fig,"rejection_summary_fig": rejection_summary_fig,
        "justification_summary_fig": justification_summary_fig,"crag_positivity_fig": crag_positivity_fig,
        "justification_summary_df": justification_summary_df,"facility_crag_positive_fig": facility_crag_positive_fig,
        "rejection_summary_df": rejection_summary_df,"show_cd4_testing_workload": show_cd4_testing_workload ,
        "show_crag_testing_workload": show_crag_testing_workload,"crag_positivity_df": crag_positivity_df,
        "facility_positive_count": facility_positive_count,"tb_lam_positivity_fig": tb_lam_positivity_fig,
        "tb_lam_positivity_df": tb_lam_positivity_df, "weekly_df": weekly_df,
        "weekly_tat_trend_fig": weekly_tat_trend_fig,"facility_tb_lam_positive_fig": facility_tb_lam_positive_fig
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
            reagent_type = form.cleaned_data['reagent_type']
            # try:
            post = form.save(commit=False)
            if not validate_commodity_form(form):
                # If validation fails, return the form with error messages
                return render(request, template_name, context)
            selected_facility = selected_lab.mfl_code

            facility_name = Facilities.objects.filter(mfl_code=selected_facility).first()
            post.facility_name = facility_name
            now = datetime.now()
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
