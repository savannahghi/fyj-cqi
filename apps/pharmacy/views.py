# import ast
# import uuid
# from datetime import datetime
# from urllib.parse import urlencode
import ast
import uuid
from datetime import datetime

import numpy as np
import pandas as pd
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction, IntegrityError
from django.db.models import Q
from django.forms import modelformset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404

# Create your views here.
from django.urls import reverse
from django.utils import timezone

from apps.cqi.models import Facilities
from apps.dqa.form import QuarterSelectionForm, YearSelectionForm, FacilitySelectionForm
from apps.dqa.models import Period
from apps.dqa.views import disable_update_buttons
from apps.pharmacy.forms import PharmacyRecordsForm, DateSelectionForm, StockCardsForm, \
    UnitSuppliedForm, BeginningBalanceForm, PositiveAdjustmentsForm, \
    UnitIssuedForm, NegativeAdjustmentForm, ExpiredUnitsForm, ExpiredForm, ExpiryTrackingForm, StockManagementForm, \
    S11FormAvailabilityForm, S11FormEndorsedForm, WorkPlanForm, PharmacyAuditTeamForm
from apps.pharmacy.models import StockCards, UnitSupplied, BeginningBalance, \
    PositiveAdjustments, UnitIssued, NegativeAdjustment, ExpiredUnits, Expired, ExpiryTracking, \
    StockManagement, S11FormAvailability, S11FormEndorsed, WorkPlan, TableNames, PharmacyRecords, Registers, \
    PharmacyAuditTeam


def get_query_params(request, form, selected_facility, selected_date):
    # Set the initial values for the common form fields
    quarter_form_initial = {'quarter': request.session['selected_quarter']}
    year_form_initial = {'year': request.session['selected_year']}
    register_form_initial = {"register_name": request.session['register_name']}
    facility_form_initial = {"name": selected_facility.name}

    try:
        date_form_initial = {
            "date": selected_date.strftime('%Y-%m-%d')}  # Convert selected_date to string
    except AttributeError:
        date_form_initial = {"date": selected_date}

    # Additional form data
    comments_form_initial = {"comments": form.cleaned_data['comments']}
    last_month_copy_form_initial = {"last_month_copy": form.cleaned_data['last_month_copy']}
    currently_in_use_form_initial = {"currently_in_use": form.cleaned_data['currently_in_use']}
    register_available_form_initial = {
        "register_available": form.cleaned_data['register_available']}

    # Add the form data to the query parameters
    query_params = {
        'quarter_form': quarter_form_initial,
        'year_form': year_form_initial,
        'register_form': register_form_initial,
        'date_form': date_form_initial,
        'facility_form': facility_form_initial,
        'comments_form': comments_form_initial,
        'last_month_copy_form': last_month_copy_form_initial,
        'currently_in_use_form': currently_in_use_form_initial,
        'register_available_form': register_available_form_initial,
    }

    return query_params


def choose_facilities_pharmacy(request):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    quarter_form = QuarterSelectionForm(request.POST or None)
    year_form = YearSelectionForm(request.POST or None)
    facility_form = FacilitySelectionForm(request.POST or None)
    date_form = DateSelectionForm(request.POST or None)
    if request.method == "POST":
        if quarter_form.is_valid() and year_form.is_valid() and date_form.is_valid() and facility_form.is_valid():
            selected_quarter = quarter_form.cleaned_data['quarter']
            selected_facility = facility_form.cleaned_data['name']
            selected_year = year_form.cleaned_data['year']
            selected_date = date_form.cleaned_data['date']
            # Generate the URL for the redirect
            url = reverse('add_pharmacy_records',
                          kwargs={"register_name": "None", 'quarter': selected_quarter, 'year': selected_year,
                                  'pk': selected_facility.id, 'date': selected_date})

            return redirect(url)
    context = {
        "quarter_form": quarter_form,
        "year_form": year_form,
        "facility_form": facility_form,
        "date_form": date_form,
        "title": "Supply Chain Spot Check Dashboard (Register/Records)"
    }
    return render(request, 'pharmacy/add_facilities_data_inventory.html', context)


@login_required(login_url='login')
def add_pharmacy_records(request, register_name=None, quarter=None, year=None, pk=None, date=None):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    date_form = DateSelectionForm(request.POST or None)
    form = PharmacyRecordsForm(request.POST or None)
    selected_quarter = quarter

    selected_year = year

    # register_name = register_name

    # Set the values in the session if available
    if selected_quarter is not None:
        request.session['selected_quarter'] = selected_quarter
    if selected_year is not None:
        request.session['selected_year'] = selected_year
    if register_name is not None:
        request.session['register_name'] = register_name

    facility, created = Facilities.objects.get_or_create(id=pk)
    facility_name = facility

    period_check, created = Period.objects.get_or_create(quarter=quarter, year=year)
    quarter_year_id = period_check.id

    def get_expected_records():
        # Get the model class from the models_to_check dictionary
        register_names = PharmacyRecords.objects.filter(
            facility_name__id=pk,
            quarter_year__id=quarter_year_id
        ).values_list('register_name__register_name', flat=True).distinct()

        filtered_data = list(register_names)
        return filtered_data

    filtered_data = get_expected_records()
    expected_register_names = ["Malaria Commodities DAR (MoH 645)",
                               "ARV Daily Activity Register (DAR) (MOH 367A) or WebADT",
                               "ARV F-MAPS (MOH 729B)", "DADR-Anti TB register",
                               "Family Planning Commodities Daily Activity Register (DAR) (MOH 512)",
                               "Delivery notes file"]
    missing = [item for item in expected_register_names if item not in filtered_data]
    if len(missing) == 0:
        messages.success(request, f"All data for {facility_name} {period_check} is successfully saved! "
                                  f"Please select a different facility.")
        return redirect("choose_facilities_pharmacy")

    if register_name == "None":
        # Redirect to the URL with the first missing item as the report_name
        url = reverse('add_pharmacy_records',
                      kwargs={"register_name": missing[0], 'quarter': quarter, 'year': year, 'pk': pk, 'date': date})
        return redirect(url)

    # Initialize the commodity_questions dictionary
    commodity_questions = {
        register_name: [
            'Does the facility have a Malaria Commodities DAR (MoH 645) register? If not, please specify which '
            'register is used to capture dispensing of Malaria commodities in the comment section.',
            'Is the Malaria Commodity DAR (MoH 645) currently being used by the facility?',
            'Does the facility has a copy of the Malaria Consumption Data Report and Requisition (CDRR) '
            '(MOH743) that was prepared in the last month of the review period?',
            'If the facility has the Malaria CDRR for the last month of the review period, please indicate the '
            'date when it was submitted (DD/MM/YY)'
        ] if register_name == "Malaria Commodities DAR (MoH 645)" else [
            'Is there a MANUAL ARV Daily Activity Register (DAR) (MOH 367A) or an electronic dispensing tool '
            '(WebADT) in this facility? Specify which one in the comments section',
            'Is the MANUAL ARV Daily Activity Register (DAR) (MOH 367A) or an electronic dispensing tool '
            '(WebADT) currently in use?',
            'Does the facility have a copy of the ARV F-CDRR (MOH 730B) that was prepared for the last month of '
            'the review period',
            'If “Yes”, when was the ARV F-CDRR (MOH 730B) for the last month of the review period submitted?'
            '(DD/MM/YY)',
        ] if register_name == 'ARV Daily Activity Register (DAR) (MOH 367A) or WebADT' else [
            'Is there a DADR-Anti TB register in this facility? If no, specifiy which register is used '
            'to capture dispensing of TB commodities in the comment section',
            'Is the DADR-Anti TB register currently in use?',
            'Does the facility have a copy of the Anti TB F-CDRR that was prepared for the last month of the '
            'review period?',
            'If “Yes”, when was the Anti TB F-CDRR for the last month of the review period submitted?'
        ] if register_name == "DADR-Anti TB register" else [
            'Is there a Family Planning Commodities Daily Activity Register (DAR) (MOH 512) in this facility? If '
            'no, specifiy which register is used to capture dispensing of Family Planning commodities in the '
            'comment section',
            'Is the Family Planning Commodities DAR (MOH 512 or other) currently in use',
            'Does the facility have a copy of the Family Planning Commodity Report (F-CDRR MOH 747A) that was '
            'prepared and submitted for the last month of the review period?',
            'If “Yes”, when was the FP CDRR for the last month of the review period submitted?'
        ] if register_name == "Family Planning Commodities Daily Activity Register (DAR) (MOH 512)" else [
            'Does the facility have a copy of the ARV F-MAPS (MOH 729B) that was prepared for the last month of '
            'the review period?',
            'Is the ARV F-MAPS (MOH 729B) currently being used by the facility?',
            'Does the facility have a copy of the ARV F-MAPS (MOH 729B) that was prepared for the last month of '
            'the review period?',
            'If the facility has the ARV F-MAPS (MOH 729B) for the last month of the review period, please indicate'
            ' the date when it was submitted'
        ] if register_name == "ARV F-MAPS (MOH 729B)" else [
            "Are delivery notes from MEDS / KEMSA for ART maintained in a separate file from S11s, and are they "
            "arranged chronologically?",
            "Is the file containing delivery notes currently being used by the facility?",
            "Does the facility have a copy of the delivery notes for commodities received during the last month "
            "of the review period?",
            "If the facility has the delivery notes for the last month of the review period, please indicate the "
            "date when the commodities were last received."
        ]
    }
    # Check if the request method is POST and the submit_dta button was pressed
    if 'submit_data' in request.POST:
        # Create an instance of the DataVerificationForm with the submitted data
        form = PharmacyRecordsForm(request.POST)
        # Check if the form data is valid
        if form.is_valid():
            facility, created = Facilities.objects.get_or_create(id=pk)
            facility_name = facility
            selected_facility = facility_name
            selected_date = date
            # if date_form_initial:
            #     selected_date = date_form_initial['date']

            context = {
                "form": form,
                "register_name": register_name,
                "commodity_questions": commodity_questions,
                # "register_form_initial": register_form_initial,

                "quarter": quarter,
                "year": year,
                "facility_id": pk,
                "date": date,
                "filtered_data": filtered_data
            }
            # for form in form.forms:
            register_available = form.cleaned_data.get('register_available')
            currently_in_use = form.cleaned_data.get('currently_in_use')
            last_month_copy = form.cleaned_data.get('last_month_copy')
            date_report_submitted = form.cleaned_data.get('date_report_submitted')
            comments = form.cleaned_data.get('comments')
            today = timezone.now().date()

            if register_available == 'No':
                if comments == "":
                    if register_name != "Delivery notes file":
                        error_message = f"Please specify which register is used instead of {register_name}"
                        form.add_error('comments', error_message)
                        return render(request, 'pharmacy/add_pharmacy_commodities.html', context)
                    else:
                        error_message = f"Please specify how {facility_name} stores delivery notes."
                        form.add_error('comments', error_message)
                        return render(request, 'pharmacy/add_pharmacy_commodities.html', context)
                if currently_in_use == "Yes":
                    error_message = f"Please confirm whether the register, {register_name}, is available." \
                                    f" The information seems inconsistent."
                    form.add_error('currently_in_use', error_message)
                    return render(request, 'pharmacy/add_pharmacy_commodities.html', context)


            if currently_in_use == 'No':
                if comments == "":
                    error_message = f"Please specify why {register_name} is not in use at {facility_name}"
                    form.add_error('comments', error_message)
                    return render(request, 'pharmacy/add_pharmacy_commodities.html', context)

            if last_month_copy == 'No':
                if comments == "":
                    error_message = f"Please indicate why {facility_name} do not have a copy of the " \
                                    f"{register_name} report that was prepared for the last month of the review period."
                    form.add_error('comments', error_message)
                    return render(request, 'pharmacy/add_pharmacy_commodities.html', context)
                if date_report_submitted is not None:
                    if register_name != "Delivery notes file":
                        error_message = f"Since there was no report submitted for the last month of the review period," \
                                        f" please clear the date you provided."
                        form.add_error('date_report_submitted', error_message)
                    else:
                        error_message = f"Since there was no copy of the commodities received for the last month of " \
                                        f"the review period, please clear the date you provided."
                        form.add_error('date_report_submitted', error_message)

                    return render(request, 'pharmacy/add_pharmacy_commodities.html', context)

            if last_month_copy == "Yes" and date_report_submitted is None:
                if register_name != "Delivery notes file":
                    error_message = f"Please indicate the date when monthly report was submitted."
                    form.add_error('date_report_submitted', error_message)
                else:
                    error_message = f"Please indicate the date when the commodities were last received"
                    form.add_error('date_report_submitted', error_message)
                return render(request, 'pharmacy/add_pharmacy_commodities.html', context)
            if date_report_submitted is not None:
                if date_report_submitted > today:
                    if register_name != "Delivery notes file":
                        error_message = f"Report's submission ({date_report_submitted}) date cannot be greater than " \
                                        f"today\'s date ({today})."
                        form.add_error('date_report_submitted', error_message)
                    else:
                        error_message = f"The date commodities ({date_report_submitted}) were last received cannot be " \
                                        f"greater than today\'s date ({today})."
                        form.add_error('date_report_submitted', error_message)
                    return render(request, 'pharmacy/add_pharmacy_commodities.html', context)


            # Try to save the form data
            try:
                with transaction.atomic():
                    # Get the instance of the form data but don't commit it yet
                    post = form.save(commit=False)
                    # Get or create the period instance
                    period, created = Period.objects.get_or_create(quarter=request.session['selected_quarter'],
                                                                   year=request.session['selected_year'])

                    # Set the quarter_year field of the form data
                    post.quarter_year = period
                    register_name, created = Registers.objects.get_or_create(register_name=request.session['register_name'])
                    post.register_name = register_name
                    # post.register_name = request.session['register_name']
                    post.date_of_interview = selected_date
                    post.facility_name = Facilities.objects.filter(name=selected_facility).first()

                    # Save the form data
                    post.save()
                    filtered_data = get_expected_records()
                    missing = [item for item in expected_register_names if item not in filtered_data]
                    if len(missing) != 0:
                        messages.success(request, f"Data for {facility_name} {period_check} is successfully saved!")
                        # Redirect to the URL with the first missing item as the report_name
                        url = reverse('add_pharmacy_records',
                                      kwargs={"register_name": missing[0], 'quarter': quarter, 'year': year, 'pk': pk,
                                              'date': date})
                        return redirect(url)
                    else:
                        messages.success(request, f"All data for {facility_name} {period_check} is successfully saved! "
                                                  f"Please select a different facility.")
                        return redirect("choose_facilities_pharmacy")
            except DatabaseError:
                messages.error(request,
                               f"Data for {facility_name} {period_check} already exists!")
        else:
            for error in form.errors:
                messages.error(request, form.errors[error])
                return redirect(request.path)

    context = {
        "form": form,
        "register_name": register_name,
        "commodity_questions": commodity_questions,
        "date_form": date_form,
        "report_name": register_name,
        "quarter": quarter,
        "year": year,
        "facility_id": pk,
        "date": date,
        "filtered_data": filtered_data
    }
    return render(request, 'pharmacy/add_pharmacy_commodities.html', context)

def generate_descriptions(report_name):
    if report_name == "stock_cards":
        descriptions = [
            'Is there currently a stock card or electronic record available for?',
            'Does the stock card or electronic record cover the entire period under review, '
            'which began on {start_date} to {end_date}?'
        ]
    elif report_name == "unit_supplied":
        descriptions = [
            'How many units were supplied by MEDS/KEMSA to this facility during the period under review from '
            'delivery notes?',
            'What quantity delivered from MEDS/KEMSA was captured in the bin card?',
        ]
    # elif report_name == "quantity_delivered":
    #     descriptions = [
    #         'How many units were supplied by MEDS/KEMSA to this facility during the period under review from '
    #         'delivery notes?',
    #         'What quantity delivered from MEDS/KEMSA was captured in the bin card?'
    #     ]
    elif report_name == "beginning_balance":
        descriptions = [
            'What was the beginning balance? (At the start of the review period)',
        ]
    # elif report_name == "unit_received":
    #     descriptions = [
    #         'How many units were supplied by MEDS/KEMSA to this facility during the period under review?',
    #     ]
    elif report_name == "s11_form_availability":
        descriptions = [
            'Is there a corresponding S11 form at this facility for each of the positive adjustment transactions?',
            'Is there a corresponding S11 form at this facility for each of the negative adjustment transactions?',
        ]
    elif report_name == "positive_adjustments":
        descriptions = [
            'How many units were received from other facilities (Positive Adjustments) during the period under review?',
            'How many positive adjustment transactions do not have a corresponding S11 form?',
        ]
    elif report_name == "unit_issued":
        descriptions = [
            'How many units were issued from the storage areas to service delivery/dispensing point(s) within '
            'this facility during the period under review?',
        ]
    elif report_name == "negative_adjustment":
        descriptions = [
            'How many units were issued to other facilities (Negative Adjustments) during the period under review?',
            'How many negative adjustment transactions were made on the stock card for transfers to other health '
            'facilities during the period under review?',
            'How many negative adjustment transactions do not have a corresponding S11 form?',
        ]
    elif report_name == "s11_form_endorsed":
        descriptions = [
            'Of the available S11 forms for positive adjustments, how many are endorsed (signed) by someone at this '
            'facility?',
            'Of the available S11 forms for the negative adjustments, how many are endorsed (signed) by someone at '
            'this facility?',
        ]
    elif report_name == "expired":
        descriptions = [
            'Has there been a stock out during the period under review?',
            'Were there any expiries during the period under review?',
            'Are there any expires in the facility?',
        ]
    elif report_name == "expired_units":
        descriptions = [
            'How many days out of stock?',
            'How many expired units  were in the facility during the review period?',
        ]
    elif report_name == "expiry_tracking":
        descriptions = [
            'Is there a current expiry tracking chart/register in this facility (wall chart or electronic)?',
            'Are there units with less than 6 months to expiry?',
            'Are the units (with less than 6 months to expiry) captured on the expiry chart?',
        ]

    elif report_name == "stock_management":
        descriptions = [
            'What is the ending balance on the stock card or electronic record on the last day of the review period?',
            'What was the actual physical count of this on the day of the visit?',
            'What is the stock balance on the stock card or electronic record on the day of the visit?',
            'What quantity was dispensed at this facility based on the DAR/ADT during the review period?',
            'What quantity was dispensed, based the CDRR, at this facility during the review period?',
            'What is the average monthly consumption?'
        ]
    else:
        descriptions = []
    return descriptions


def create_inventory_formset(report_name, request, initial_data):
    # Define a dictionary mapping report names to model and form classes
    report_mapping = {
        "stock_cards": (StockCards, StockCardsForm),
        "unit_supplied": (UnitSupplied, UnitSuppliedForm),
        # "quantity_delivered": (QuantityDelivered, QuantityDeliveredForm),
        "beginning_balance": (BeginningBalance, BeginningBalanceForm),
        # "unit_received": (UnitReceived, UnitReceivedForm),
        "positive_adjustments": (PositiveAdjustments, PositiveAdjustmentsForm),
        "unit_issued": (UnitIssued, UnitIssuedForm),
        "negative_adjustment": (NegativeAdjustment, NegativeAdjustmentForm),
        "expired": (Expired, ExpiredForm),
        "expired_units": (ExpiredUnits, ExpiredUnitsForm),
        "expiry_tracking": (ExpiryTracking, ExpiryTrackingForm),
        "stock_management": (StockManagement, StockManagementForm),
        "s11_form_availability": (S11FormAvailability, S11FormAvailabilityForm),
        "s11_form_endorsed": (S11FormEndorsed, S11FormEndorsedForm),
    }

    if report_name in report_mapping:
        model_class, form_class = report_mapping[report_name]
    else:
        model_class, form_class = report_mapping["stock_cards"]

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

def choose_facilities_inventory(request):
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
    if request.method == "POST":
        if quarter_form.is_valid() and year_form.is_valid() and date_form.is_valid() and facility_form.is_valid():
            selected_quarter = quarter_form.cleaned_data['quarter']
            selected_facility = facility_form.cleaned_data['name']
            selected_year = year_form.cleaned_data['year']
            selected_date = date_form.cleaned_data['date']
            # Generate the URL for the redirect
            url = reverse('add_inventory',
                          kwargs={"report_name": "None", 'quarter': selected_quarter, 'year': selected_year,
                                  'pk': selected_facility.id, 'date': selected_date})

            return redirect(url)
    context = {
        "quarter_form": quarter_form,
        "year_form": year_form,
        "facility_form": facility_form,
        "date_form": date_form,
        "title": "Supply Chain Spot Check Dashboard (Inventory)"
    }
    return render(request, 'pharmacy/add_facilities_data_inventory.html', context)


def add_inventory(request, report_name=None, quarter=None, year=None, pk=None, date=None):
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
    descriptions = generate_descriptions(report_name)
    request.session['descriptions'] = descriptions
    initial_data = [{'description': description} for description in descriptions]
    formset, inventory_form_set, model_class, form_class = create_inventory_formset(report_name, request, initial_data)
    period_check, created = Period.objects.get_or_create(quarter=quarter, year=year)
    quarter_year_id = period_check.id

    facility, created = Facilities.objects.get_or_create(id=pk)
    facility_name = facility

    models_to_check = {
        "stock_cards": StockCards,
        "unit_supplied": UnitSupplied,
        # "quantity_delivered": QuantityDelivered,
        "beginning_balance": BeginningBalance,
        # "unit_received": UnitReceived,
        "positive_adjustments": PositiveAdjustments,
        "unit_issued": UnitIssued,
        "negative_adjustment": NegativeAdjustment,
        "expired_units": ExpiredUnits,
        "expired": Expired,
        "expiry_tracking": ExpiryTracking,
        "s11_form_availability": S11FormAvailability,
        "s11_form_endorsed": S11FormEndorsed,
        "stock_management": StockManagement,
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
    model_names = ['stock_cards', 'unit_supplied', 'beginning_balance',
                   'positive_adjustments', 'unit_issued', 'negative_adjustment', 's11_form_availability',
                   's11_form_endorsed', 'expired', 'expired_units', 'expiry_tracking', 'stock_management']
    missing = [item for item in model_names if item not in filtered_data]
    if len(missing) == 0:
        messages.success(request, f"All data for {facility_name} {period_check} is successfully saved! "
                                  f"Please select a different facility.")
        return redirect("choose_facilities_inventory")

    if report_name == "None":
        # Redirect to the URL with the first missing item as the report_name
        url = reverse('add_inventory',
                      kwargs={"report_name": missing[0], 'quarter': quarter, 'year': year, 'pk': pk, 'date': date})
        return redirect(url)

    if request.method == "POST":
        formset = inventory_form_set(request.POST, initial=initial_data)
        if formset.is_valid():
            selected_date = date
            instances = formset.save(commit=False)
            context = {
                "formset": formset, "quarter_form": quarter_form, "year_form": year_form,
                "facility_form": facility_form,
                "date_form": date_form, "descriptions": descriptions,
                "page_from": request.session.get('page_from', '/'),
                "report_name": missing[0],
                "quarter": quarter,
                "year": year,
                "facility_id": pk,
                "date": date,
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

            for field_to_validate, error_field in fields_to_validate:
                if form_class == StockCardsForm:
                    question_1_value = formset.forms[0].cleaned_data.get(field_to_validate)
                    question_2_value = formset.forms[1].cleaned_data.get(field_to_validate)
                    if question_1_value == 'No' and question_2_value == 'Yes':
                        formset.forms[1].add_error(error_field,
                                                   f"Invalid selection. Can't select 'Yes' if above question is 'No'.")
                elif form_class == ExpiredForm:
                    question_1_value = formset.forms[1].cleaned_data.get(field_to_validate)
                    question_2_value = formset.forms[2].cleaned_data.get(field_to_validate)
                    if question_1_value == 'No' and question_2_value == 'Yes':
                        formset.forms[2].add_error(error_field,
                                                   f"Invalid selection. Can't select 'Yes' if above question is 'No'.")
            ############################################
            # CHECK IF THERE ARE ERRORS IN THE FORMSET #
            ############################################
            if any(form.errors for form in formset.forms):
                # There are form errors in the formset
                return render(request, 'pharmacy/add_system_assessment.html', context)

            #################################################
            # CHECK IF ALL FORMS IN THE FORMSET ARE FILLED  #
            #################################################
            if not all([form.has_changed() for form in formset.forms]):
                for form in formset.forms:
                    if not form.has_changed():
                        for field in form.fields:
                            if field != "comments":
                                form.add_error(field, "This field is required.")
                return render(request, 'pharmacy/add_system_assessment.html', context)
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
                            if report_name == "expired":
                                if form.cleaned_data.get(field) == 'Yes' and not form.cleaned_data.get('comments'):
                                    errors = True
                                    error_fields.append(field_name)
                            else:
                                if form.cleaned_data.get(field) == 'No' and not form.cleaned_data.get('comments'):
                                    errors = True
                                    error_fields.append(field_name)

                    if error_fields:
                        if report_name == "expired":
                            error_message = f"Please provide a comment for 'Yes' selection in the following fields: " \
                                            f"{', '.join(error_fields)} "
                            form.add_error('comments', error_message)

                        else:
                            error_message = f"Please provide a comment for 'No' selection in the following fields: " \
                                            f"{', '.join(error_fields)} "
                            form.add_error('comments', error_message)

                if errors:
                    return render(request, 'pharmacy/add_system_assessment.html', context)

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
                        return render(request, 'pharmacy/add_system_assessment.html', context)

                ###########################################################
                # SAVE DATA IF IT DOES NOT EXIST AND THERE IS NO ERRORS!  #
                ###########################################################
                with transaction.atomic():
                    for form, instance in zip(formset.forms, instances):
                        # Set instance fields from form data
                        instance.adult_arv_tdf_3tc_dtg = form.cleaned_data['adult_arv_tdf_3tc_dtg']
                        instance.pead_arv_dtg_10mg = form.cleaned_data['pead_arv_dtg_10mg']
                        instance.paed_arv_abc_3tc_120_60mg = form.cleaned_data['paed_arv_abc_3tc_120_60mg']
                        instance.tb_3hp = form.cleaned_data['tb_3hp']
                        instance.adult_arv_tdf_3tc_dtg = form.cleaned_data['adult_arv_tdf_3tc_dtg']
                        instance.family_planning_rod = form.cleaned_data['family_planning_rod']
                        instance.al_24 = form.cleaned_data['al_24']
                        instance.comments = form.cleaned_data['comments']
                        instance.date_of_interview = selected_date
                        instance.created_by = request.user
                        instance.description = form.cleaned_data['description']
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
                        url = reverse('add_inventory',
                                      kwargs={"report_name": missing[0], 'quarter': quarter, 'year': year, 'pk': pk,
                                              'date': date})
                        return redirect(url)
                    else:
                        messages.success(request, f"All data for {facility_name} {period_check} is successfully saved! "
                                                  f"Please select a different facility.")
                        return redirect("choose_facilities_inventory")

            except DatabaseError:
                messages.error(request,
                               f"Data for {facility_name} {period_check} already exists!")
    context = {
        "formset": formset,
        "report_name": report_name,
        "quarter": quarter,
        "year": year,
        "facility_id": pk,
        "date": date,
        "filtered_data": filtered_data
    }
    return render(request, 'pharmacy/add_system_assessment.html', context)

@login_required(login_url='login')
def create_inventory_work_plans(request, pk, report_name):
    if not request.user.first_name:
        return redirect("profile")

    models_to_check = {
        "stock_cards": StockCards,
        "unit_supplied": UnitSupplied,
        # "quantity_delivered": QuantityDelivered,
        "beginning_balance": BeginningBalance,
        # "unit_received": UnitReceived,
        "positive_adjustments": PositiveAdjustments,
        "unit_issued": UnitIssued,
        "negative_adjustment": NegativeAdjustment,
        "expired_units": ExpiredUnits,
        "expired": Expired,
        "expiry_tracking": ExpiryTracking,
        "s11_form_availability": S11FormAvailability,
        "s11_form_endorsed": S11FormEndorsed,
        "stock_management": StockManagement,
    }

    # Get the model class from the models_to_check dictionary
    model_class = models_to_check[report_name]
    if not model_class:
        return redirect("show_work_plan")  # Handle invalid report_name gracefully

    # Filter the objects based on the conditions
    objects = model_class.objects.filter(id=pk)

    if request.method == 'POST':
        form = WorkPlanForm(request.POST)
        if form.is_valid():
            today = timezone.now().date()
            dqa_work_plan = form.save(commit=False)
            # Choose a specific object from the queryset or iterate over it
            stock_card = objects.first()  # Choose the first object from the queryset
            if stock_card:
                # Get or create the Table instance
                table_name, created = TableNames.objects.get_or_create(model_name=report_name)
                dqa_work_plan.model_name = table_name
                dqa_work_plan.progress = (dqa_work_plan.complete_date - today).days

                # Assign the foreign key field dynamically
                setattr(dqa_work_plan, report_name, stock_card)

                dqa_work_plan.facility_name = stock_card.facility_name
                dqa_work_plan.quarter_year = stock_card.quarter_year
            dqa_work_plan.created_by = request.user
            try:
                dqa_work_plan.save()
            except IntegrityError:
                # Notify the user that the data already exists
                messages.error(request, f'Work plan already exists!')
            return redirect('show_inventory')
    else:
        form = WorkPlanForm()

    context = {
        'form': form,
        'title': 'Add DQA Work Plan',
        'facility': objects,
        "stock_card_data": objects,
        "report_name": report_name,
    }

    return render(request, 'pharmacy/show_commodity_management.html', context)


@login_required(login_url='login')
def show_work_plan(request):
    if not request.user.first_name:
        return redirect("profile")
    objects={}
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

    # quarter_form = QuarterSelectionForm(request.POST or None)
    # year_form = YearSelectionForm(request.POST or None)
    # facility_form = FacilitySelectionForm(request.POST or None)
    selected_facility = None
    selected_quarter_year = None
    work_plan = None
    quarter_year = None
    form = None
    field_values = None
    models_to_check = None
    work_plans = None
    filtered_data = []
    today = datetime.now(timezone.utc).date()

    if quarter_form.is_valid() and year_form.is_valid() and facility_form.is_valid():
        selected_quarter = quarter_form.cleaned_data['quarter']
        selected_year = year_form.cleaned_data['year']
        selected_facility = facility_form.cleaned_data['name']
        year_suffix = selected_year[-2:]
        selected_quarter_year = f"{selected_quarter}-{year_suffix}"
        # Get or create the Period instance
        period, created = Period.objects.get_or_create(quarter=selected_quarter, year=selected_year)
        quarter_year = period

    elif quarter_form_initial != {}:
        selected_facility = facility_form_initial["name"]
        facility, created = Facilities.objects.get_or_create(name=selected_facility)
        selected_facility = facility
        selected_quarter_year = quarter_form_initial['quarter']
        # Get or create the Period instance
        period, created = Period.objects.get_or_create(quarter_year=selected_quarter_year)
        quarter_year = period

    if selected_facility is not None:
        models_to_check = {
            "commodity_records": PharmacyRecords,
            "stock_cards": StockCards,
            "unit_supplied": UnitSupplied,
            "beginning_balance": BeginningBalance,
            "positive_adjustments": PositiveAdjustments,
            "unit_issued": UnitIssued,
            "negative_adjustment": NegativeAdjustment,
            "expired_units": ExpiredUnits,
            "expired": Expired,
            "expiry_tracking": ExpiryTracking,
            "s11_form_availability": S11FormAvailability,
            "s11_form_endorsed": S11FormEndorsed,
            "stock_management": StockManagement,
        }

        model_names = list(models_to_check.keys())

        # Create an empty list to store the filtered objects
        filtered_data = []

        # Iterate over the model names
        for model_name in model_names:
            # Get the model class from the models_to_check dictionary
            model_class = models_to_check[model_name]

            # Filter the objects based on the conditions
            objects = model_class.objects.filter(
                Q(facility_name_id=selected_facility.id) &
                Q(quarter_year__id=quarter_year.id)
            )

            # Append the filtered objects to the list
            filtered_data.extend(objects)

        work_plans = WorkPlan.objects.filter(facility_name_id=selected_facility.id ,
                quarter_year__id=quarter_year.id)
        field_values = []

        # Iterate over the work plans
        for work_plan in work_plans:
            # Iterate over the models in models_to_check dictionary
            for field_name, model in models_to_check.items():
                field_id = getattr(work_plan, field_name + "_id", None)
                if field_id is not None:
                    field_values.append(field_id)

        if request.method == 'POST':
            form = WorkPlanForm(request.POST)
            if form.is_valid():
                dqa_work_plan = form.save(commit=False)
                dqa_work_plan.facility_name = objects.facility_name
                dqa_work_plan.quarter_year = objects.quarter_year.id
                dqa_work_plan.created_by = request.user
                dqa_work_plan.save()
                return redirect('show_dqa_work_plan')
        else:
            form = WorkPlanForm()
        #####################################
        # DECREMENT REMAINING TIME DAILY    #
        #####################################
        if work_plans:
            today = timezone.now().date()
            for workplan in work_plans:
                work_plans.progress=0
                work_plans.progress = (workplan.complete_date - today).days
    context = {
        'form': form,
        'title': 'Work Plan',
        'title2': 'Inventory Management',
        "stock_card_data": filtered_data,
        "work_plans": work_plans,
        "models_to_check": models_to_check,
        "field_values": field_values,
        "year_form": year_form,
        "facility_form": facility_form,
        "quarter_form": quarter_form,
        "selected_facility":selected_facility,
        # "quarter_year":quarter_year.astype(str).split(" ")[0]+"-"+quarter_year.split(" ")[-1][-2:]
        "quarter_year":selected_quarter_year
    }
    return render(request, 'pharmacy/show_commodity_management.html', context)


def create_df(df, title, row_index):
    data = []
    for i in range(1, 7):
        stock_card_tld = df.iloc[row_index, i]
        data.append(int(stock_card_tld))
    # Create DataFrame
    df7 = pd.DataFrame(data, columns=[title])
    df7 = df7.T
    return df7


def add_new_row(a, division_row, title):
    division_row = division_row.tolist()
    division_row.insert(0, title)
    division_row = pd.DataFrame(division_row).T.reset_index(drop=True)
    division_row = division_row.set_index(0)
    division_row.columns = [0, 1, 2, 3, 4, 5]
    a = pd.concat([a, division_row])
    return a


def divide_rows(a,num_index, deno_index):
    division_row = pd.Series(index=a.columns)

    # Iterate over the columns
    for col in a.columns:
        numerator = a.iloc[num_index, col]
        denominator = a.iloc[deno_index, col]

        # Check if the denominator is non-zero
        if denominator != 0:
            division_row[col] = round((numerator / denominator) * 100, 1)
        else:
            division_row[col] = 0
    return division_row

def calculate_supply_chain_kpis(df, expected_description_order):
    # Replace values in the DataFrame
    df = df.replace({"No": 0, "Yes": 100})

    # Convert columns to integer type
    df[df.columns[1:]] = df[df.columns[1:]].astype(int)

    # Set 'description' column as categorical
    df['description'] = pd.Categorical(df['description'], categories=expected_description_order, ordered=True)

    # Sort the DataFrame by 'description'
    df.sort_values('description', inplace=True)

    # Create DataFrames df1, df2, df3
    df1 = create_df(df, 'Stock card available', 0)
    df2 = create_df(df, 'in bin cards', 3)
    df3 = create_df(df, 'supp kemsa', 2)

    # Concatenate df1, df2, df3 into a single DataFrame 'a'
    a = pd.concat([df1, df2, df3])

    division_row = divide_rows(a, 1, 2)

    a = add_new_row(a, division_row, "Delivery Captured on Stock Card")

    # Create DataFrames df4, df5
    df4 = create_df(df, 'physical count', 25)
    df5 = create_df(df, 'stock card balance', 26)

    # Concatenate a, df4, df5 into a single DataFrame 'a'
    a = pd.concat([a, df4, df5])
    division_row = divide_rows(a,4, 5)

    a = add_new_row(a, division_row, "Stock balance accuracy")

    # Create DataFrames df6, df7, df8, df9, df10, df11
    df6 = create_df(df, 'begining bal', 4)
    df7 = create_df(df, 'kemsa supply', 5)
    df8 = create_df(df, 'received from other facilities', 6)
    df9 = create_df(df, 'units issued to SDPs', 8)
    df10 = create_df(df, 'units issued to other facilities', 11)
    df11 = create_df(df, 'units expired', 13)

    # Concatenate a, df6, df7, df8, df9, df10, df11 into a single DataFrame 'a'
    a = pd.concat([a, df6, df7, df8, df9, df10, df11])

    division_row = pd.Series(index=a.columns)

    # Iterate over the columns
    for col in a.columns:
        numerator = a.iloc[4, col]
        denominator = (a.iloc[7, col] + a.iloc[8, col] + a.iloc[9, col]) - (
                a.iloc[10, col] + a.iloc[11, col] + a.iloc[12, col])

        # Check if the denominator is non-zero
        if denominator != 0:
            division_row[col] = round((numerator / denominator) * 100, 1)
        else:
            division_row[col] = 0

    a = add_new_row(a, division_row, "Transaction recording accuracy")

    # Create DataFrames df12,df13
    df12 = create_df(df, 'captured in the bin card', 3)
    df13 = create_df(df, 'quantity supplied', 2)
    a = pd.concat([a, df13, df12])

    # Create a new row for the division 'Delivered in full'
    division_row = divide_rows(a,15, 14)

    a = add_new_row(a, division_row, "Delivered in full")

    # Reset index, rename columns, and filter unwanted rows
    a = a.reset_index()
    a.columns = list(df.columns)
    a = a[~a['description'].str.contains('in bin cards|supp kemsa|physical count|stock card balance|'
                                         'begining bal|kemsa supply|received from other facilities|'
                                         'units issued to SDPs|units issued to other facilities|units expired|'
                                         'quantity supplied|captured in the bin card')]

    # Get the count of values equal to 100 in each row
    count_100 = (a.iloc[:, 1:] == 100).sum(axis=1)

    # Calculate the division result
    division_result = round(count_100 / (a.shape[1] - 1), 2)

    # Add the new column 'Facility score' to the DataFrame
    a['Facility score'] = division_result

    # Multiply all values in the "Facility score" column
    product = a['Facility score'].prod()

    # Create a new row with the product value
    new_row = ['Stock Record Validity'] + [0] * (a.shape[1] - 2) + [product]
    new_row = pd.DataFrame(new_row).T.reset_index(drop=True)
    # Replace values in the DataFrame
    new_row.columns = list(df.columns) + ['Facility score']

    # Concatenate new_row to the DataFrame 'a'
    a = pd.concat([a, new_row])

    # Rename the 'description' column to 'Focus area'
    a = a.rename(
        columns={"description": "Focus area", "tld_90": "TLD 90s", "dtg_10": "DTG 10", "abc_3tc": "ABC/3TC 120/60",
                 "3hp": "3HP", "fp": "IMPLANT 1 ROD", "al": "AL 24"})

    # Convert 'Facility score' column to numeric and round to 2 decimal places
    a['Facility score'] = pd.to_numeric(a['Facility score'], errors='coerce').round(2)
    a = a.reset_index(drop=True)

    sort_focus_area = ['Delivered in full', 'Stock card available',
                       'Delivery Captured on Stock Card',
                       'Stock balance accuracy',
                       'Transaction recording accuracy',
                       'Stock Record Validity']
    # Set 'description' column as categorical
    a['Focus area'] = pd.Categorical(a['Focus area'], categories=sort_focus_area, ordered=True)

    # Sort the DataFrame by 'description'
    a.sort_values('Focus area', inplace=True)
    a.index = np.arange(1, len(a) + 1)

    # Final DataFrame 'a'
    return a, sort_focus_area


@login_required(login_url='login')
def show_inventory(request):
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
    facility_form = FacilitySelectionForm(request.POST or None, initial=facility_form_initial)

    # date_form = DateSelectionForm(request.POST or None)

    supply_chain_target_100 = pd.DataFrame()
    sort_focus_area = None
    selected_facility = None
    quarter_year = None

    if quarter_form.is_valid() and year_form.is_valid() and facility_form.is_valid():
        selected_quarter = quarter_form.cleaned_data['quarter']
        selected_year = year_form.cleaned_data['year']
        selected_facility = facility_form.cleaned_data['name']
        year_suffix = selected_year[-2:]
        quarter_year = f"{selected_quarter}-{year_suffix}"

    elif quarter_form_initial != {}:
        selected_facility = facility_form_initial["name"]
        quarter_year = quarter_form_initial['quarter']


    models_to_check = {
        "stock_cards": StockCards,
        "unit_supplied": UnitSupplied,
        "beginning_balance": BeginningBalance,
        "positive_adjustments": PositiveAdjustments,
        "unit_issued": UnitIssued,
        "negative_adjustment": NegativeAdjustment,
        "expired_units": ExpiredUnits,
        "expired": Expired,
        "expiry_tracking": ExpiryTracking,
        "s11_form_availability": S11FormAvailability,
        "s11_form_endorsed": S11FormEndorsed,
        "stock_management": StockManagement,
    }
    model_names = list(models_to_check.keys())

    # Create an empty list to store the filtered objects
    filtered_data = []

    # Iterate over the model names
    for model_name in model_names:
        # Get the model class from the models_to_check dictionary
        model_class = models_to_check[model_name]
        objects = model_class.objects.filter(facility_name__name=selected_facility,
                                             quarter_year__quarter_year=quarter_year
                                             ).order_by('date_created')

        # Append the filtered objects to the list
        filtered_data.extend(objects)

    work_plans = WorkPlan.objects.all()
    if len(filtered_data) == 0 and quarter_year is not None:
        messages.success(request, f"Inventory management data for {selected_facility} {quarter_year} is missing! "
                                  f"Kindly enter data using the form provided in the 'DATA ENTRY' section.")
    field_values = []

    # Iterate over the work plans
    for work_plan in work_plans:
        # Iterate over the models in models_to_check dictionary
        for field_name, model in models_to_check.items():
            field_id = getattr(work_plan, field_name + "_id", None)
            if field_id is not None:
                field_values.append(field_id)
    if len(filtered_data) == 29:
        data = []
        for model_data in filtered_data:
            record = {
                'description': model_data.description,
                'tld_90': model_data.adult_arv_tdf_3tc_dtg,
                'dtg_10': model_data.pead_arv_dtg_10mg,
                'abc_3tc': model_data.paed_arv_abc_3tc_120_60mg,
                '3hp': model_data.tb_3hp,
                'fp': model_data.family_planning_rod,
                'al': model_data.al_24,
            }
            data.append(record)
            # break
        # Create DataFrame
        df = pd.DataFrame(data)
        expected_description_order = ['Is there currently a stock card or electronic record available for?',
                                      'Does the stock card or electronic record cover the entire period under review, which began on {start_date} to {end_date}?',
                                      'How many units were supplied by MEDS/KEMSA to this facility during the period under review from delivery notes?',
                                      'What quantity delivered from MEDS/KEMSA was captured in the bin card?',
                                      'What was the beginning balance? (At the start of the review period)',
                                      'How many units were supplied by MEDS/KEMSA to this facility during the period under review?',
                                      'How many units were received from other facilities (Positive Adjustments) during the period under review?',
                                      'How many positive adjustment transactions do not have a corresponding S11 form?',
                                      'How many units were issued from the storage areas to service delivery/dispensing point(s) within this facility during the period under review?',
                                      'How many units were issued to other facilities (Negative Adjustments) during the period under review?',
                                      'How many negative adjustment transactions were made on the stock card for transfers to other health facilities during the period under review?',
                                      'How many negative adjustment transactions do not have a corresponding S11 form?',
                                      'How many days out of stock?',
                                      'How many expired units  were in the facility during the review period?',
                                      'Has there been a stock out during the period under review?',
                                      'Were there any expiries during the period under review?',
                                      'Are there any expires in the facility?',
                                      'Is there a current expiry tracking chart/register in this facility (wall chart or electronic)?',
                                      'Are there units with less than 6 months to expiry?',
                                      'Are the units (with less than 6 months to expiry) captured on the expiry chart?',
                                      'Is there a corresponding S11 form at this facility for each of the positive adjustment transactions?',
                                      'Is there a corresponding S11 form at this facility for each of the negative adjustment transactions?',
                                      'Of the available S11 forms for positive adjustments, how many are endorsed (signed) by someone at this facility?',
                                      'Of the available S11 forms for the negative adjustments, how many are endorsed (signed) by someone at this facility?',
                                      'What is the ending balance on the stock card or electronic record on the last day of the review period?',
                                      'What was the actual physical count of this on the day of the visit?',
                                      'What is the stock balance on the stock card or electronic record on the day of the visit?',
                                      'What quantity was dispensed at this facility based on the DAR/ADT during the review period?',
                                      'What quantity was dispensed, based the CDRR, at this facility during the review period?',
                                      'What is the average monthly consumption?']

        supply_chain_target_100, sort_focus_area = calculate_supply_chain_kpis(df, expected_description_order)
    context = {
        # 'form': form,
        'title': 'Inventory Management',
        "stock_card_data": filtered_data,
        "quarter_form": quarter_form,
        "year_form": year_form,
        "facility_form": facility_form,
        "models_to_check": models_to_check,
        "field_values": field_values,
        "supply_chain_target_100": supply_chain_target_100,
        "sort_focus_areas": sort_focus_area,
    }

    return render(request, 'pharmacy/show_inventory_management.html', context)


@login_required(login_url='login')
def update_inventory(request, pk, model):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    report_mapping = {
        "stock_cards": (StockCards, StockCardsForm),
        "unit_supplied": (UnitSupplied, UnitSuppliedForm),
        "beginning_balance": (BeginningBalance, BeginningBalanceForm),
        "positive_adjustments": (PositiveAdjustments, PositiveAdjustmentsForm),
        "unit_issued": (UnitIssued, UnitIssuedForm),
        "negative_adjustment": (NegativeAdjustment, NegativeAdjustmentForm),
        "expired": (Expired, ExpiredForm),
        "expired_units": (ExpiredUnits, ExpiredUnitsForm),
        "expiry_tracking": (ExpiryTracking, ExpiryTrackingForm),
        "stock_management": (StockManagement, StockManagementForm),
        "s11_form_availability": (S11FormAvailability, S11FormAvailabilityForm),
        "s11_form_endorsed": (S11FormEndorsed, S11FormEndorsedForm),
    }
    model_class, form_class = report_mapping[model]
    item = model_class.objects.get(id=pk)
    request.session['date_of_interview'] = item.date_of_interview.strftime('%Y-%m-%d')  # Convert date to string
    request.session['model_name_id'] = str(item.model_name.id)  # Convert UUID to string

    if request.method == "POST":
        form = form_class(request.POST, instance=item)
        if form.is_valid():
            instance = form.save(commit=False)
            table_name, created = TableNames.objects.get_or_create(id=uuid.UUID(request.session['model_name_id']))
            instance.model_name = table_name
            # Retrieve the date_of_interview value from the session
            date_of_interview_str = request.session.get('date_of_interview')
            date_of_interview = datetime.strptime(date_of_interview_str, '%Y-%m-%d').date()  # Convert string to date
            # Set the date_of_interview field in the instance
            instance.date_of_interview = date_of_interview
            instance.save()

            messages.success(request,"peter:::::::::::::Record updated successfully!")
            # Set the initial values for the forms
            quarter_form_initial = {'quarter': item.quarter_year.quarter_year}
            year_form_initial = {'year': item.quarter_year.year}
            facility_form_initial = {"name": item.facility_name.name}
            # Redirect to the inventory view with the initial values for the forms
            url = reverse('show_inventory')
            url = f'{url}?quarter_form={quarter_form_initial}&year_form={year_form_initial}&facility_form={facility_form_initial}'
            return redirect(url)
    else:
        form = form_class(instance=item)
    context = {
        "form": form,
        "title": "Update Inventory",
    }
    # return render(request, 'cqi/update_test_of_change.html', context)
    return render(request, 'pharmacy/update inventory.html', context)


@login_required(login_url='login')
def show_commodity_records(request):
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
    facility_form = FacilitySelectionForm(request.POST or None, initial=facility_form_initial)

    # date_form = DateSelectionForm(request.POST or None)

    supply_chain_target_100 = pd.DataFrame()
    sort_focus_area = None
    selected_facility = None
    quarter_year = None

    if quarter_form.is_valid() and year_form.is_valid() and facility_form.is_valid():
        selected_quarter = quarter_form.cleaned_data['quarter']
        selected_year = year_form.cleaned_data['year']
        selected_facility = facility_form.cleaned_data['name']
        year_suffix = selected_year[-2:]
        quarter_year = f"{selected_quarter}-{year_suffix}"

    elif quarter_form_initial != {}:
        selected_facility = facility_form_initial["name"]
        quarter_year = quarter_form_initial['quarter']


    models_to_check = {
        "stock_cards": StockCards,
        "unit_supplied": UnitSupplied,
        "beginning_balance": BeginningBalance,
        "positive_adjustments": PositiveAdjustments,
        "unit_issued": UnitIssued,
        "negative_adjustment": NegativeAdjustment,
        "expired_units": ExpiredUnits,
        "expired": Expired,
        "expiry_tracking": ExpiryTracking,
        "s11_form_availability": S11FormAvailability,
        "s11_form_endorsed": S11FormEndorsed,
        "stock_management": StockManagement,
    }
    pharmacy_records = PharmacyRecords.objects.filter(
        facility_name__name=selected_facility,
        quarter_year__quarter_year=quarter_year
    ).order_by('date_created')

    pharmacy_records_ids = pharmacy_records.values_list('id', flat=True)

    work_plans = WorkPlan.objects.filter(pharmacy_records__in=pharmacy_records_ids)

    pharmacy_records_without_workplans = pharmacy_records.exclude(
        id__in=work_plans.values_list('pharmacy_records', flat=True)).values_list('id', flat=True)

    context = {
        # 'form': form,
        'title': 'Commodity records/registers',
        "pharmacy_records": pharmacy_records,
        "quarter_form": quarter_form,
        "year_form": year_form,
        "facility_form": facility_form,
        "models_to_check": models_to_check,
        "pharmacy_records_without_workplans": pharmacy_records_without_workplans,
        "supply_chain_target_100": supply_chain_target_100,
        "sort_focus_areas": sort_focus_area,
    }

    return render(request, 'pharmacy/show_commodity_management.html', context)


@login_required(login_url='login')
def update_pharmacy_records(request, pk, register_name):
# def update_inventory(request, pk):
    if not request.user.first_name:
        return redirect("profile")


    commodity_questions={}
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
        # Initialize the commodity_questions dictionary
        commodity_questions = {
            register_name: [
                'Does the facility have a Malaria Commodities DAR (MoH 645) register? If not, please specify which '
                'register is used to capture dispensing of Malaria commodities in the comment section.',
                'Is the Malaria Commodity DAR (MoH 645) currently being used by the facility?',
                'Does the facility has a copy of the Malaria Consumption Data Report and Requisition (CDRR) '
                '(MOH743) that was prepared in the last month of the review period?',
                'If the facility has the Malaria CDRR for the last month of the review period, please indicate the '
                'date when it was submitted (DD/MM/YY)'
            ] if register_name == "Malaria Commodities DAR (MoH 645)" else [
                'Is there a MANUAL ARV Daily Activity Register (DAR) (MOH 367A) or an electronic dispensing tool '
                '(WebADT) in this facility? Specify which one in the comments section',
                'Is the MANUAL ARV Daily Activity Register (DAR) (MOH 367A) or an electronic dispensing tool '
                '(WebADT) currently in use?',
                'Does the facility have a copy of the ARV F-CDRR (MOH 730B) that was prepared for the last month of '
                'the review period',
                'If “Yes”, when was the ARV F-CDRR (MOH 730B) for the last month of the review period submitted?'
                '(DD/MM/YY)',
            ] if register_name == 'ARV Daily Activity Register (DAR) (MOH 367A) or WebADT' else [
                'Is there a DADR-Anti TB register in this facility? If no, specifiy which register is used '
                'to capture dispensing of TB commodities in the comment section',
                'Is the DADR-Anti TB register currently in use?',
                'Does the facility have a copy of the Anti TB F-CDRR that was prepared for the last month of the '
                'review period?',
                'If “Yes”, when was the Anti TB F-CDRR for the last month of the review period submitted?'
            ] if register_name == "DADR-Anti TB register" else [
                'Is there a Family Planning Commodities Daily Activity Register (DAR) (MOH 512) in this facility? If '
                'no, specifiy which register is used to capture dispensing of Family Planning commodities in the '
                'comment section',
                'Is the Family Planning Commodities DAR (MOH 512 or other) currently in use',
                'Does the facility have a copy of the Family Planning Commodity Report (F-CDRR MOH 747A) that was '
                'prepared and submitted for the last month of the review period?',
                'If “Yes”, when was the FP CDRR for the last month of the review period submitted?'
            ] if register_name == "Family Planning Commodities Daily Activity Register (DAR) (MOH 512)" else [
                'Does the facility have a copy of the ARV F-MAPS (MOH 729B) that was prepared for the last month of '
                'the review period?',
                'Is the ARV F-MAPS (MOH 729B) currently being used by the facility?',
                'Does the facility have a copy of the ARV F-MAPS (MOH 729B) that was prepared for the last month of '
                'the review period?',
                'If the facility has the ARV F-MAPS (MOH 729B) for the last month of the review period, please indicate'
                ' the date when it was submitted'
            ] if register_name == "ARV F-MAPS (MOH 729B)" else [
                "Are delivery notes from MEDS / KEMSA for ART maintained in a separate file from S11s, and are they "
                "arranged chronologically?",
                "Is the file containing delivery notes currently being used by the facility?",
                "Does the facility have a copy of the delivery notes for commodities received during the last month "
                "of the review period?",
                "If the facility has the delivery notes for the last month of the review period, please indicate the "
                "date when the commodities were last received."
            ]
        }
        request.session['commodity_questions']=commodity_questions
    item = PharmacyRecords.objects.get(id=pk)
    request.session['date_of_interview'] = item.date_of_interview.strftime('%Y-%m-%d')  # Convert date to string
    facility_name=item.facility_name

    if request.method == "POST":
        form = PharmacyRecordsForm(request.POST, instance=item)
        if form.is_valid():
            instance = form.save(commit=False)
            # Initialize the commodity_questions dictionary
            commodity_questions = request.session['commodity_questions']
            context = {
                "form": form,
                "title": "Update commodity records/registers",
                "commodity_questions": commodity_questions,
            }
            template_name='pharmacy/update records.html'
            # for form in form.forms:
            register_available = form.cleaned_data.get('register_available')
            currently_in_use = form.cleaned_data.get('currently_in_use')
            last_month_copy = form.cleaned_data.get('last_month_copy')
            date_report_submitted = form.cleaned_data.get('date_report_submitted')
            comments = form.cleaned_data.get('comments')
            today = timezone.now().date()

            if register_available == 'No':
                if comments == "":
                    if register_name != "Delivery notes file":
                        error_message = f"Please specify which register is used instead of {register_name}"
                        form.add_error('comments', error_message)
                        return render(request, template_name, context)
                    else:
                        error_message = f"Please specify how {facility_name} stores delivery notes."
                        form.add_error('comments', error_message)
                        return render(request, template_name, context)
                if currently_in_use == "Yes":
                    error_message = f"Please confirm whether the register, {register_name}, is available." \
                                    f" The information seems inconsistent."
                    form.add_error('currently_in_use', error_message)
                    return render(request, template_name, context)
            if currently_in_use == 'No':
                if comments == "":
                    error_message = f"Please specify why {register_name} is not in use at {facility_name}"
                    form.add_error('comments', error_message)
                    return render(request, template_name, context)
            if last_month_copy == 'No':
                if comments == "":
                    error_message = f"Please indicate why {facility_name} do not have a copy of the " \
                                    f"{register_name} report that was prepared for the last month of the review period."
                    form.add_error('comments', error_message)
                    return render(request, 'pharmacy/update records.html', context)
                if date_report_submitted is not None:
                    if register_name != "Delivery notes file":
                        error_message = f"Since there was no report submitted for the last month of the review period," \
                                        f" please clear the date you provided."
                        form.add_error('date_report_submitted', error_message)
                    else:
                        error_message = f"Since there was no copy of the commodities received for the last month of " \
                                        f"the review period, please clear the date you provided."
                        form.add_error('date_report_submitted', error_message)

                    return render(request, template_name, context)
            if last_month_copy == "Yes" and date_report_submitted is None:
                if register_name != "Delivery notes file":
                    error_message = f"Please indicate the date when monthly report was submitted."
                    form.add_error('date_report_submitted', error_message)
                else:
                    error_message = f"Please indicate the date when the commodities were last received"
                    form.add_error('date_report_submitted', error_message)
                return render(request, template_name, context)
            if date_report_submitted is not None:
                if date_report_submitted > today:
                    if register_name != "Delivery notes file":
                        error_message = f"Report's submission ({date_report_submitted}) date cannot be greater than " \
                                        f"today\'s date ({today})."
                        form.add_error('date_report_submitted', error_message)
                    else:
                        error_message = f"The date commodities ({date_report_submitted}) were last received cannot be " \
                                        f"greater than today\'s date ({today})."
                        form.add_error('date_report_submitted', error_message)
                    return render(request, template_name, context)

            # # Retrieve the date_of_interview value from the session
            date_of_interview_str = request.session.get('date_of_interview')
            date_of_interview = datetime.strptime(date_of_interview_str, '%Y-%m-%d').date()  # Convert string to date
            # Set the date_of_interview field in the instance
            instance.date_of_interview = date_of_interview

            instance.save()
            # Set the initial values for the forms
            quarter_form_initial = {'quarter': item.quarter_year.quarter_year}
            year_form_initial = {'year': item.quarter_year.year}
            facility_form_initial = {"name": item.facility_name.name}
            # Redirect to the show_commodity_records view with the initial values for the forms
            url = reverse('show_commodity_records')
            url = f'{url}?quarter_form={quarter_form_initial}&year_form={year_form_initial}&facility_form={facility_form_initial}'
            return redirect(url)
    else:
        form = PharmacyRecordsForm(instance=item)
    context = {
        "form": form,
        "title": "Update commodity records/registers",
        "commodity_questions":commodity_questions,
    }
    return render(request, 'pharmacy/update records.html', context)


@login_required(login_url='login')
def create_commodity_work_plans(request, pk):
    if not request.user.first_name:
        return redirect("profile")

    pharmacy_objects = get_object_or_404(PharmacyRecords, id=pk)

    if request.method == 'POST':
        form = WorkPlanForm(request.POST)
        today = timezone.now().date()
        if form.is_valid():
            work_plan = form.save(commit=False)
            work_plan.facility_name = pharmacy_objects.facility_name
            work_plan.quarter_year = pharmacy_objects.quarter_year
            work_plan.pharmacy_records = pharmacy_objects
            work_plan.progress = (work_plan.complete_date - today).days
            try:
                work_plan.save()
            except IntegrityError:
                messages.error(request, 'Work plan already exists!')

            # Set the initial values for the forms
            quarter_form_initial = {'quarter': pharmacy_objects.quarter_year.quarter_year}
            year_form_initial = {'year': pharmacy_objects.quarter_year.year}
            facility_form_initial = {"name": pharmacy_objects.facility_name.name}
            # Redirect to the show_commodity_records view with the initial values for the forms
            url = reverse('show_commodity_records')
            url = f'{url}?quarter_form={quarter_form_initial}&year_form={year_form_initial}&facility_form={facility_form_initial}'
            return redirect(url)
    else:
        form = WorkPlanForm()

    context = {
        'form': form,
        'title': 'Add DQA Work Plan',
        'facility': pharmacy_objects,
        "stock_card_data": [pharmacy_objects],
    }

    return render(request, 'pharmacy/show_commodity_management.html', context)


@login_required(login_url='login')
def update_workplan(request, pk):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    item = WorkPlan.objects.get(id=pk)
    foreign_keys = [
            'model_name',
            'beginning_balance',
            'pharmacy_records',
            'unit_supplied',
            'positive_adjustments',
            'unit_issued',
            'negative_adjustment',
            'expired_units',
            'expired',
            'expiry_tracking',
            's11_form_availability',
            's11_form_endorsed',
            'stock_management',
        ]

    for key in foreign_keys:
        try:
            request.session[f'{key}_id'] = str(getattr(item, key).id)
        except AttributeError:
            request.session[f'{key}_id'] = None

    if request.method == "POST":
        form = WorkPlanForm(request.POST, instance=item)
        today = timezone.now().date()
        if form.is_valid():
            instance = form.save(commit=False)
            instance.progress = (instance.complete_date - today).days
            foreign_key_mapping = {
                'model_name': TableNames,
                'beginning_balance': BeginningBalance,
                'pharmacy_records': PharmacyRecords,
                'unit_supplied': UnitSupplied,
                'positive_adjustments': PositiveAdjustments,
                'unit_issued': UnitIssued,
                'negative_adjustment': NegativeAdjustment,
                'expired_units': ExpiredUnits,
                'expired': Expired,
                'expiry_tracking': ExpiryTracking,
                's11_form_availability': S11FormAvailability,
                's11_form_endorsed': S11FormEndorsed,
                'stock_management': StockManagement
            }

            for key, model_class in foreign_key_mapping.items():
                # Retrieve the model ID from the session for the current key
                model_id = request.session.get(f"{key}_id")
                try:
                    if model_id:
                        # If the model ID exists, retrieve the corresponding foreign object from the model class
                        # using get_or_create, and assign it to the instance's field
                        foreign_obj, created = model_class.objects.get_or_create(id=str(model_id))
                        setattr(instance, key, foreign_obj)
                    else:
                        # If the model ID is None, set the instance's field to None
                        setattr(instance, key, None)
                except (ValidationError, KeyError):
                    # If any validation error or key error occurs, set the instance's field to None
                    setattr(instance, key, None)

            instance.save()

            messages.success(request,"peter:::::::::::::Record updated successfully!")
            # Set the initial values for the forms
            quarter_form_initial = {'quarter': item.quarter_year.quarter_year}
            year_form_initial = {'year': item.quarter_year.year}
            facility_form_initial = {"name": item.facility_name.name}
            # Redirect to the inventory view with the initial values for the forms
            url = reverse('show_work_plan')
            url = f'{url}?quarter_form={quarter_form_initial}&year_form={year_form_initial}&facility_form={facility_form_initial}'
            return redirect(url)
    else:
        form = WorkPlanForm(instance=item)
    context = {
        "form": form,
        "title": "Update Workplan",
    }
    return render(request, 'pharmacy/update workplan.html', context)


@login_required(login_url='login')
def add_audit_team_pharmacy(request, pk, quarter_year):
    if not request.user.first_name:
        return redirect("profile")
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    if request.method == 'POST':
        form = PharmacyAuditTeamForm(request.POST)
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
        form = PharmacyAuditTeamForm()
    audit_team_pharmacy = PharmacyAuditTeam.objects.filter(facility_name__id=pk, quarter_year__quarter_year=quarter_year)
    # disable_update_buttons(request, audit_team_pharmacy)
    context = {
        "form": form,
        "title": "audit team",
        "audit_team": audit_team_pharmacy,
        "quarter_year": quarter_year,
    }
    return render(request, 'pharmacy/add_period.html', context)


@login_required(login_url='login')
def update_audit_team_pharmacy(request, pk):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    item = PharmacyAuditTeam.objects.get(id=pk)
    if request.method == "POST":
        form = PharmacyAuditTeamForm(request.POST, instance=item)
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
            url = reverse('show_audit_team_pharmacy')
            url = f'{url}?quarter_form={quarter_form_initial}&year_form={year_form_initial}&facility_form={facility_form_initial}'
            return redirect(url)
    else:
        form = PharmacyAuditTeamForm(instance=item)
    context = {
        "form": form,
        'title': 'update audit team',
        'facility': item.facility_name.name,
        'mfl_code': item.facility_name.mfl_code,
        'date_modified': item.updated_at,
    }
    return render(request, 'pharmacy/add_period.html', context)


@login_required(login_url='login')
def show_audit_team_pharmacy(request):
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
        audit_team = PharmacyAuditTeam.objects.filter(facility_name__id=selected_facility.id,
                                              quarter_year__quarter_year=quarter_year)
        if audit_team:
            disable_update_buttons(request, audit_team)
        else:
            messages.error(request, f"No audit team data was found in the database for {selected_facility} "
                                    f"{selected_quarter}-FY{year_suffix}.")
    elif facility_form_initial:
        selected_quarter = quarter_form_initial['quarter']
        selected_facility = facility_form_initial['name']
        audit_team = PharmacyAuditTeam.objects.filter(facility_name=Facilities.objects.get(name=selected_facility),
                                              quarter_year__quarter_year=selected_quarter,module="Pharmacy")
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
    return render(request, 'pharmacy/add_period.html', context)