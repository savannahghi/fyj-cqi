# import ast
# import uuid
# from datetime import datetime
# from urllib.parse import urlencode
import ast
import json
import re
import uuid
from datetime import date, datetime
from itertools import chain
from urllib.parse import urlencode

import numpy as np
import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import Q
from django.forms import formset_factory
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
# Create your views here.
from django.urls import reverse
from django.utils import timezone

from apps.cqi.models import Facilities, Sub_counties
from apps.dqa.form import CountySelectionForm, FacilitySelectionForm, HubSelectionForm, ProgramSelectionForm, \
    QuarterSelectionForm, \
    SubcountySelectionForm, \
    YearSelectionForm
from apps.dqa.models import Period
from apps.dqa.views import disable_update_buttons
from apps.labpulse.views import line_chart_median_mean
from apps.pharmacy.forms import BeginningBalanceForm, DateSelectionForm, DeliveryNotesForm, \
    ExpiredForm, \
    ExpiredUnitsForm, \
    ExpiryTrackingForm, FacilityForm, NegativeAdjustmentForm, PharmacyAuditTeamForm, PharmacyRecordsForm, \
    PositiveAdjustmentsForm, QualitativeAntiMalariaForm, QualitativeFpForm, QualitativeInventoryForm, \
    QuantitativeAntiMalariaForm, QuantitativeFpForm, QuantitativeInventoryForm, QuarterSelectForm, \
    S11FormAvailabilityForm, S11FormEndorsedForm, \
    StockCardsForm, \
    StockManagementForm, UnitIssuedForm, UnitSuppliedForm, WorkPlanForm, YearSelectForm
from apps.pharmacy.models import BeginningBalance, DeliveryNotes, Expired, ExpiredUnits, ExpiryTracking, \
    NegativeAdjustment, \
    PharmacyAuditTeam, PharmacyFpModel, PharmacyFpQualitativeModel, PharmacyMalariaModel, \
    PharmacyMalariaQualitativeModel, PharmacyRecords, \
    PositiveAdjustments, \
    Registers, S11FormAvailability, \
    S11FormEndorsed, \
    StockCards, StockManagement, TableNames, UnitIssued, UnitSupplied, WorkPlan
from apps.pharmacy.utils import handle_foreign_keys


# from silk.profiling.profiler import silk_profile


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


@login_required(login_url='login')
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


def validate_form(form, facility):
    register_available = form.cleaned_data.get('register_available')
    last_month_copy = form.cleaned_data.get('last_month_copy')
    comments = form.cleaned_data.get('comments')
    register_name = form.cleaned_data.get('register_name')
    date_report_submitted = form.cleaned_data.get('date_report_submitted')
    today = timezone.now().date()

    if register_available == 'No' and not comments:
        error_message = f"Please specify which register is used instead of {register_name}" if register_name != "Delivery notes file" else f"Please specify how {facility.name} stores delivery notes."
        form.add_error('comments', error_message)
        return False

    if last_month_copy == 'No' and not comments:
        error_message = f"Please indicate why {facility.name} do not have a copy of the {register_name} report that was prepared for the last month of the review period."
        form.add_error('comments', error_message)
        return False

    if date_report_submitted and date_report_submitted > today:
        error_message = (
            f"Report's submission ({date_report_submitted}) date cannot be greater than today's date ({today})."
            if register_name != "Delivery notes file"
            else f"The date commodities ({date_report_submitted}) were last received cannot be "
                 f"greater than today's date ({today})."
        )
        form.add_error('date_report_submitted', error_message)
        return False
    return True


@login_required(login_url='login')
@transaction.atomic
def add_pharmacy_records(request, register_name=None, quarter=None, year=None, pk=None, date=None):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    date_form = DateSelectionForm(request.POST or None)
    form = PharmacyRecordsForm(request.POST or None)
    form1 = PharmacyRecordsForm(request.POST or None, prefix='form1')
    form2 = PharmacyRecordsForm(request.POST or None, prefix='form2')
    form3 = DeliveryNotesForm(request.POST or None, prefix='form3')
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

    missing_in_workplans, combined_records, pharmacy_records = fetch_and_check_workplans(facility_name.name,
                                                                                         period_check.quarter_year)

    def get_expected_records():
        # Get the model class from the models_to_check dictionary
        register_names = PharmacyRecords.objects.filter(
            facility_name__id=pk,
            quarter_year__id=quarter_year_id
        ).values_list('register_name__register_name', flat=True).distinct()

        filtered_data = list(register_names)
        return filtered_data

    filtered_data = get_expected_records()
    # Initialize the commodity_questions dictionary
    commodity_questions = {
        register_name: [[
            'Does the facility have a Malaria Commodities DAR (MoH 645) register? If not, please specify which '
            'register is used to capture dispensing of Malaria commodities in the comment section.',
            'Is the Malaria Commodity DAR (MoH 645) currently being used by the facility?',
            'Does the facility has a copy of the Malaria Consumption Data Report and Requisition (CDRR) '
            '(MOH743) that was prepared in the last month of the review period?',
            'If the facility has the Malaria CDRR for the last month of the review period, please indicate the '
            'date when it was submitted (DD/MM/YY)'
        ], [
            "Are delivery notes from MEDS / KEMSA maintained in a separate file from "
            "S11s, and are they arranged chronologically?",
            "Does the facility have a copy of the delivery notes for commodities last received during the review "
            "period?",
        ]] if register_name == "Malaria Commodities DAR (MoH 645)" else [[
            'Is there a MANUAL ARV Daily Activity Register (DAR) (MOH 367A) or an electronic dispensing tool '
            ' in this facility? Specify which one in the comments section',
            'Is the MANUAL ARV Daily Activity Register (DAR) (MOH 367A) or an electronic dispensing tool '
            ' currently in use?',
            'Does the facility have a copy of the ARV F-CDRR (MOH 730B) that was prepared for the last month of '
            'the review period',
            'If “Yes”, when was the ARV F-CDRR (MOH 730B) for the last month of the review period submitted?'
            '(DD/MM/YY)',
        ], [
            # 'Does the facility have a copy of the ARV F-MAPS (MOH 729B) that was prepared for the last month of '
            # 'the review period?',
            # 'Is the ARV F-MAPS (MOH 729B) currently being used by the facility?',
            # 'Does the facility have a copy of the ARV F-MAPS (MOH 729B) that was prepared for the last month of '
            # 'the review period?',
            'If the facility has the ARV F-MAPS (MOH 729B) for the last month of the review period, please indicate'
            ' the date when it was submitted'
        ], [
            "Are delivery notes from MEDS / KEMSA maintained in a separate file from "
            "S11s, and are they"
            " arranged chronologically?",
            "Does the facility have a copy of the delivery notes for commodities last received during the review "
            "period?",
        ]] if register_name == 'ARV Daily Activity Register (DAR) (MOH 367A) or WebADT'
        else [[
            'Is there a DADR-Anti TB register in this facility? If no, specifiy which register is used '
            'to capture dispensing of TB commodities in the comment section',
            'Is the DADR-Anti TB register currently in use?',
            'Does the facility have a copy of the Anti TB F-CDRR that was prepared for the last month of the '
            'review period?',
            'If “Yes”, when was the Anti TB F-CDRR for the last month of the review period submitted?'
        ], [
            "Are delivery notes from MEDS / KEMSA maintained in a separate file from "
            "S11s, and are they arranged chronologically?",
            "Does the facility have a copy of the delivery notes for commodities last received during the review "
            "period?",
        ]] if register_name == "DADR-Anti TB register" else [[
            'Is there a Family Planning Commodities Daily Activity Register (DAR) (MOH 512) in this facility? If '
            'no, specifiy which register is used to capture dispensing of Family Planning commodities in the '
            'comment section',
            'Is the Family Planning Commodities DAR (MOH 512 or other) currently in use',
            'Does the facility have a copy of the Family Planning Commodity Report (F-CDRR MOH 747A) that was '
            'prepared and submitted for the last month of the review period?',
            'If “Yes”, when was the FP CDRR for the last month of the review period submitted?'
        ], [
            "Are delivery notes from MEDS / KEMSA maintained in a separate file from "
            "S11s, and are they arranged chronologically?",
            "Does the facility have a copy of the delivery notes for commodities last received during the review "
            "period?",
        ]] if register_name == "Family Planning Commodities Daily Activity Register (DAR) (MOH 512)" else [
            "Are delivery notes from MEDS / KEMSA maintained in a separate file from "
            "S11s, and are they arranged chronologically?",
            "Does the facility have a copy of the delivery notes for commodities last received during the review "
            "period?",
        ]
    }
    context = {
        "form": form, 'form1': form1, 'form2': form2, 'form3': form3,
        "register_name": register_name, "missing_in_workplans": missing_in_workplans,
        "combined_records": combined_records,
        "date_form": date_form, "pharmacy_records": pharmacy_records,
        "report_name": register_name, "title": "Supply Chain Spot Check Dashboard (Register/Records)",
        "quarter": quarter,
        "year": year,
        "facility_id": pk,
        "date": date,
        "filtered_data": filtered_data
    }
    expected_register_names = ["Malaria Commodities DAR (MoH 645)",
                               "ARV Daily Activity Register (DAR) (MOH 367A) or WebADT", "DADR-Anti TB register",
                               "Family Planning Commodities Daily Activity Register (DAR) (MOH 512)",
                               ]
    missing = [item for item in expected_register_names if item not in filtered_data]
    if len(missing) == 0:
        messages.success(request, f"All data for {facility_name} {period_check} is successfully saved! "
                                  f"Please select a different facility.")
        # return redirect("choose_facilities_pharmacy")

        return render(request, 'pharmacy/add_pharmacy_commodities.html', context)

    if register_name == "None":
        # Redirect to the URL with the first missing item as the report_name
        url = reverse('add_pharmacy_records',
                      kwargs={"register_name": missing[0], 'quarter': quarter, 'year': year, 'pk': pk, 'date': date})
        return redirect(url)

    # Check if the request method is POST and the submit_dta button was pressed
    if 'submit_data' in request.POST:
        # Create an instance of the DataVerificationForm with the submitted data
        form = PharmacyRecordsForm(request.POST, is_required=True)
        form1 = PharmacyRecordsForm(request.POST, prefix='form1', is_required=True)
        form2 = PharmacyRecordsForm(request.POST, prefix='form2', is_required=False)
        form3 = DeliveryNotesForm(request.POST, prefix='form3')

        if (form1.is_valid() and form2.is_valid() and form3.is_valid()) or (form.is_valid() and form3.is_valid()):
            facility, created = Facilities.objects.get_or_create(id=pk)
            facility_name = facility
            selected_facility = facility_name
            selected_date = date

            context = {
                "form": form, 'form1': form1, 'form2': form2, 'form3': form3,
                "register_name": register_name, "commodity_questions": commodity_questions, "quarter": quarter,
                "year": year, "facility_id": pk, "date": date, "filtered_data": filtered_data
            }
            if register_name == "ARV Daily Activity Register (DAR) (MOH 367A) or WebADT":
                # Validation checks
                if not validate_form(form1, facility):
                    return render(request, 'pharmacy/add_pharmacy_commodities.html', context)

                if not validate_form(form2, facility):
                    return render(request, 'pharmacy/add_pharmacy_commodities.html', context)
            else:
                # Validation checks
                if not validate_form(form, facility):
                    return render(request, 'pharmacy/add_pharmacy_commodities.html', context)
            if not validate_form(form3, facility):
                return render(request, 'pharmacy/add_pharmacy_commodities.html', context)

            def save_form(form, period, selected_date, selected_facility,
                          register_name=request.session['register_name']):
                post = form.save(commit=False)
                post.quarter_year = period
                post.register_name, _ = Registers.objects.get_or_create(register_name=register_name)
                post.date_of_interview = selected_date
                post.facility_name = selected_facility
                post.save()

            # Try to save the form data
            try:
                # Get or create the period instance
                period, created = Period.objects.get_or_create(quarter=request.session['selected_quarter'],
                                                               year=request.session['selected_year'])
                if register_name == "ARV Daily Activity Register (DAR) (MOH 367A) or WebADT":
                    # Save form1
                    save_form(form1, period, selected_date, selected_facility,
                              "ARV Daily Activity Register (DAR) (MOH 367A) or WebADT")

                    # Save form2
                    save_form(form2, period, selected_date, selected_facility, "ARV F-MAPS (MOH 729B)")

                else:
                    save_form(form, period, selected_date, selected_facility)

                save_form(form3, period, selected_date, selected_facility)
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
            for error in [form.errors, form1.errors, form2.errors, form3.errors]:
                messages.error(request, error)
                return redirect(request.path)
    context["commodity_questions"] = commodity_questions
    return render(request, 'pharmacy/add_pharmacy_commodities.html', context)


def generate_descriptions(report_name):
    if "choices" in report_name:
        descriptions = [
            '1. Is there currently a stock card or electronic record available for?',
            '2. Does the stock card or electronic record cover the entire period under review, '
            'which began on {start_date} to {end_date}?',

            '3. Is there a corresponding S11 form at this facility for each of the positive adjustment transactions?',
            '4. Is there a corresponding S11 form at this facility for each of the negative adjustment transactions?',

            '5. Is there a current expiry tracking chart/register in this facility (wall chart or electronic)?',
            '6. Are there units with less than 6 months to expiry?',
            '7. Are the units (with less than 6 months to expiry) captured on the expiry chart?',

            '8. Has there been a stock out during the period under review?',
            '9. Were there any expiries during the period under review?'

        ]
    elif "integers" in report_name:
        descriptions = [
            '1. How many units were supplied by MEDS/KEMSA to this facility during the period under review from '
            'delivery notes?',
            '2. What quantity delivered from MEDS/KEMSA was captured in the bin card?',

            '3. What was the beginning balance? (At the start of the review period)',

            '4. How many units were received from other facilities (Positive Adjustments) during the period under review?',
            '5. How many positive adjustment transactions were made on the stock card for transfers to other health '
            'facilities during the period under review?',
            '6. How many positive adjustment transactions do not have a corresponding S11 form?',

            '7. How many units were issued from the storage areas to service delivery/dispensing point(s) within '
            'this facility during the period under review?',

            '8. How many units were issued to other facilities (Negative Adjustments) during the period under review?',
            '9. How many negative adjustment transactions were made on the stock card for transfers to other health '
            'facilities during the period under review?',
            '10. How many negative adjustment transactions do not have a corresponding S11 form?',

            '11. Of the available S11 forms for positive adjustments, how many are endorsed (signed) by someone at this '
            'facility?',
            '12. Of the available S11 forms for the negative adjustments, how many are endorsed (signed) by someone at '
            'this facility?',

            '13. How many days out of stock?',
            '14. How many expired units  were in the facility during the review period?',

            '15. What is the ending balance on the stock card or electronic record on the last day of the review '
            'period?',
            '16. What was the actual physical count of this on the day of the visit?',
            '17. What is the stock balance on the stock card or electronic record on the day of the visit?',
            '18. What quantity was dispensed at this facility based on the DAR/ADT during the review period?',
            '19. What quantity was dispensed, based the CDRR, at this facility during the review period?',
            '20. What is the average monthly consumption?',
            '21. What number of active clients on ART were reported in MOH 731 in the period?',
            '22. What number of active clients on ART were reported in MOH 729B in the period?',
        ]
        if "Arvs" not in report_name:
            descriptions = descriptions[0:-2]
    else:
        descriptions = []
    return descriptions


def create_inventory_formset(request, initial_data, report_name="Arvs_choices"):
    if report_name == "Arvs_integers":
        inventory_form_set = formset_factory(
            QuantitativeInventoryForm,
            extra=0
        )
    elif report_name == "Arvs_choices":
        inventory_form_set = formset_factory(
            QualitativeInventoryForm,
            extra=0
        )
    elif report_name == "fp_choices":
        inventory_form_set = formset_factory(
            QualitativeFpForm,
            extra=0
        )
    elif report_name == "fp_integers":
        inventory_form_set = formset_factory(
            QuantitativeFpForm,
            extra=0
        )
    elif report_name == "malaria_choices":
        inventory_form_set = formset_factory(
            QualitativeAntiMalariaForm,
            extra=0
        )
    elif report_name == "malaria_integers":
        inventory_form_set = formset_factory(
            QuantitativeAntiMalariaForm,
            extra=0
        )
    else:
        raise ValueError(f"Unexpected report_name: {report_name}")

    formset = inventory_form_set(
        request.POST or None,
        initial=initial_data
    )

    return formset, inventory_form_set


@login_required(login_url='login')
def choose_facilities_inventory(request):
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
                          kwargs={"report_name": "Arvs_choices", 'quarter': selected_quarter, 'year': selected_year,
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


def validate_formset(formset, validation_rules):
    form_errors = False
    num_questions = len(formset)  # Total number of questions in the formset

    for rule_name, rule_func in validation_rules.items():
        # Extract the relevant data for this rule
        data = {form.prefix: form.cleaned_data for form in formset}

        # Apply the rule
        is_valid, error_messages = rule_func(data)

        if not is_valid:
            # Add errors to the specific fields in the forms
            for form_index, field_errors in error_messages.items():
                for field, error_message in field_errors.items():
                    formset[form_index].add_error(field, error_message)
            form_errors = True

    return form_errors


def validate_question_pairs(data, fields_to_check, question_pairs):
    """
    Validate that if the first question in a pair is 'No', the second can't be 'Yes'.

    :param data: Dictionary of form data
    :param fields_to_check: List of field names to check
    :param question_pairs: List of tuples, each containing the indices of two questions to compare
    """
    error_messages = {}

    for field in fields_to_check:
        for q1_index, q2_index in question_pairs:
            q1_value = data[f'form-{q1_index}'].get(field)
            q2_value = data[f'form-{q2_index}'].get(field)

            if q1_value == 'No' and q2_value == 'Yes':
                error_message = f"Invalid selection. 'No' in question {q1_index + 1} can't be followed by 'Yes' in question {q2_index + 1}."
                error_messages[q1_index] = error_messages.get(q1_index, {})
                error_messages[q1_index][field] = error_message
                error_messages[q2_index] = error_messages.get(q2_index, {})
                error_messages[q2_index][field] = error_message

    return len(error_messages) == 0, error_messages


def validate_pharmacy_formset(request, formset, template_name, context, fields_to_check, question_pairs):
    """
    Validates a pharmacy formset.

    Args:
    request (HttpRequest): The current request object.
    formset (FormSet): The formset to validate.
    template_name (str): The name of the template to render if validation fails.
    context (dict): The context dictionary to pass to the template.
    fields_to_check (list): List of field names to check in the validation.
    question_pairs (list): List of tuples representing pairs of questions to compare.

    Returns:
    HttpResponse: Renders the template with errors if validation fails, otherwise returns None.
    """
    validation_rules = {
        'validate_question_pairs': lambda data: validate_question_pairs(data, fields_to_check, question_pairs),
    }

    form_errors = validate_formset(formset, validation_rules)

    if form_errors:
        context['form_errors'] = form_errors
        return render(request, template_name, context)

    return None


def get_data_entered(model_names, pk, quarter_year_id, models_to_check):
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


def check_remaining(request, model_names, pk, quarter_year_id, facility_name, period_check, models_to_check):
    filtered_data = get_data_entered(model_names, pk, quarter_year_id, models_to_check)
    model_names = ['stock_cards', 'unit_supplied', 'beginning_balance',
                   'positive_adjustments', 'unit_issued', 'negative_adjustment', 's11_form_availability',
                   's11_form_endorsed', 'expired', 'expired_units', 'expiry_tracking', 'stock_management',
                   'family_planning_choice', 'Anti_malaria_choice', 'family_planning_int', 'Anti_malaria_int']
    missing = [item for item in model_names if item not in filtered_data]

    arvs_choice_fields = ['stock_cards', 's11_form_availability', 'expiry_tracking', 'expired']
    arvs_integer_fields = ['unit_supplied', 'beginning_balance', 'positive_adjustments', 'unit_issued',
                           'negative_adjustment', 's11_form_endorsed', 'expired_units', 'stock_management']

    fp_choice_fields = ['family_planning_choice']
    fp_integer_fields = ['family_planning_int']

    mal_choice_fields = ['Anti_malaria_choice']
    mal_integer_fields = ['Anti_malaria_int']
    show_buttons = {
        'Arvs_choices': any(field in missing for field in arvs_choice_fields),
        'Arvs_integers': any(field in missing for field in arvs_integer_fields),
        'fp_choices': any(field in missing for field in fp_choice_fields),
        'fp_integers': any(field in missing for field in fp_integer_fields),
        'malaria_choices': any(field in missing for field in mal_choice_fields),
        'malaria_integers': any(field in missing for field in mal_integer_fields),
    }
    return show_buttons, filtered_data, missing


def get_next_report(show_buttons):
    button_order = ['Arvs_choices', 'fp_choices', 'malaria_choices', 'Arvs_integers', 'fp_integers',
                    'malaria_integers']
    for button in button_order:
        if show_buttons[button]:
            return button
    return None  # Return None if all buttons are False


@login_required(login_url='login')
@transaction.atomic
def add_inventory(request, report_name=None, quarter=None, year=None, pk=None, date=None):
    # TODO: WILL NEED TODO REFACTOR WorkPlanForm OPTIMIZE THIS VIEW
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    quarter_form = QuarterSelectionForm(request.POST or None)
    year_form = YearSelectionForm(request.POST or None)
    facility_form = FacilitySelectionForm(request.POST or None)
    date_form = DateSelectionForm(request.POST or None)
    descriptions = generate_descriptions(report_name)

    period_check, created = Period.objects.get_or_create(quarter=quarter, year=year)
    quarter_year_id = period_check.id

    facility, created = Facilities.objects.get_or_create(id=pk)
    facility_name = facility

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
        "family_planning_int": PharmacyFpModel,
        "family_planning_choice": PharmacyFpQualitativeModel,
        "Anti_malaria_int": PharmacyMalariaModel,
        "Anti_malaria_choice": PharmacyMalariaQualitativeModel,
    }
    model_names = list(models_to_check.keys())

    show_buttons, filtered_data, missing = check_remaining(request, model_names, pk, quarter_year_id, facility_name,
                                                           period_check, models_to_check)
    if len(missing) == 0:
        messages.success(request, f"All data for {facility_name} {period_check} is successfully saved! "
                                  f"Please select a different facility.")
        return redirect("choose_facilities_inventory")

    next_report = get_next_report(show_buttons)

    # Check if the requested report is available
    if not show_buttons.get(report_name, False):
        # Find the first available report
        available_report = next((key for key, value in show_buttons.items() if value), None)

        if available_report:
            # Redirect to the first available report
            messages.info(request,
                          f"The requested report '{report_name}' is not available.")
            return redirect('add_inventory', report_name=available_report, quarter=quarter, year=year, pk=pk, date=date)
        else:
            # No reports are available
            messages.warning(request, "No reports are currently available.")
            return redirect('choose_facilities_inventory')

    request.session['descriptions'] = descriptions
    initial_data = [{'description': description} for description in descriptions]
    formset, inventory_form_set = create_inventory_formset(request, initial_data, report_name)

    if request.method == "POST":
        if formset.is_valid():
            context = {
                "formset": formset, "quarter_form": quarter_form,
                "year_form": year_form, "facility_form": facility_form,
                "date_form": date_form, "descriptions": descriptions,
                "page_from": request.session.get('page_from', '/'),
                "report_name": report_name, "show_buttons": show_buttons,
                "quarter": quarter, "year": year, "facility_id": pk, "date": date,
                "filtered_data": filtered_data
            }

            for index, form in enumerate(formset):
                form_errors = False  # Flag to check if any form has errors
                try:
                    if form.is_valid() and "Arvs" in report_name:
                        data = {
                            'quarter_year': period_check,
                            'facility_name': facility,
                            'date_of_interview': date,
                            'description': form.cleaned_data['description'],
                            'adult_arv_tdf_3tc_dtg': form.cleaned_data.get('adult_arv_tdf_3tc_dtg'),
                            'pead_arv_dtg_10mg': form.cleaned_data.get('pead_arv_dtg_10mg'),
                            'pead_arv_dtg_50mg': form.cleaned_data.get('pead_arv_dtg_50mg'),
                            'paed_arv_abc_3tc_120_60mg': form.cleaned_data.get('paed_arv_abc_3tc_120_60mg'),
                            'tb_3hp': form.cleaned_data.get('tb_3hp'),
                            'r_inh': form.cleaned_data.get('r_inh'),
                            'comments': form.cleaned_data.get('comments')
                        }
                        if report_name == "Arvs_integers":
                            if index < 2:
                                table_name, created = TableNames.objects.get_or_create(model_name="unit_supplied")
                                data['model_name'] = table_name
                                UnitSupplied.objects.create(**data)
                            elif index == 2:
                                table_name, created = TableNames.objects.get_or_create(model_name="beginning_balance")
                                data['model_name'] = table_name
                                BeginningBalance.objects.create(**data)
                            elif 3 <= index <= 4:
                                table_name, created = TableNames.objects.get_or_create(
                                    model_name="positive_adjustments")
                                data['model_name'] = table_name
                                PositiveAdjustments.objects.create(**data)
                            elif index == 5:
                                table_name, created = TableNames.objects.get_or_create(model_name="unit_issued")
                                data['model_name'] = table_name
                                UnitIssued.objects.create(**data)
                            elif 6 <= index <= 8:
                                table_name, created = TableNames.objects.get_or_create(model_name="negative_adjustment")
                                data['model_name'] = table_name
                                NegativeAdjustment.objects.create(**data)
                            elif 9 <= index <= 10:
                                table_name, created = TableNames.objects.get_or_create(model_name="s11_form_endorsed")
                                data['model_name'] = table_name
                                S11FormEndorsed.objects.create(**data)
                            elif 11 <= index <= 12:
                                table_name, created = TableNames.objects.get_or_create(model_name="expired_units")
                                data['model_name'] = table_name
                                ExpiredUnits.objects.create(**data)
                            else:
                                table_name, created = TableNames.objects.get_or_create(model_name="stock_management")
                                data['model_name'] = table_name
                                StockManagement.objects.create(**data)
                        elif report_name == "Arvs_choices":
                            fields_to_check = ['adult_arv_tdf_3tc_dtg', 'pead_arv_dtg_10mg',
                                               'pead_arv_dtg_50mg', 'paed_arv_abc_3tc_120_60mg',
                                               'tb_3hp', 'r_inh']  # Add all relevant fields here
                            question_pairs = [(0, 1)]  # Add all pairs of questions to compare
                            if index < 2:
                                validation_result = validate_pharmacy_formset(request, formset,
                                                                              'pharmacy/add_system_assessment.html',
                                                                              context, fields_to_check, question_pairs)
                                if validation_result:
                                    return validation_result

                                if not form_errors:
                                    table_name, created = TableNames.objects.get_or_create(model_name="stock_cards")
                                    data['model_name'] = table_name
                                    StockCards.objects.create(**data)
                            elif 2 <= index < 4:
                                validation_result = validate_pharmacy_formset(request, formset,
                                                                              'pharmacy/add_system_assessment.html',
                                                                              context, fields_to_check, question_pairs)
                                if validation_result:
                                    return validation_result

                                if not form_errors:
                                    table_name, created = TableNames.objects.get_or_create(
                                        model_name="s11_form_availability")
                                    data['model_name'] = table_name
                                    S11FormAvailability.objects.create(**data)
                            elif 4 <= index < 7:
                                validation_result = validate_pharmacy_formset(request, formset,
                                                                              'pharmacy/add_system_assessment.html',
                                                                              context, fields_to_check, question_pairs)
                                if validation_result:
                                    return validation_result

                                if not form_errors:
                                    table_name, created = TableNames.objects.get_or_create(
                                        model_name="s11_form_availability")
                                    data['model_name'] = table_name
                                    ExpiryTracking.objects.create(**data)
                            else:
                                validation_result = validate_pharmacy_formset(request, formset,
                                                                              'pharmacy/add_system_assessment.html',
                                                                              context, fields_to_check, question_pairs)
                                if validation_result:
                                    return validation_result

                                if not form_errors:
                                    table_name, created = TableNames.objects.get_or_create(model_name="expired")
                                    data['model_name'] = table_name
                                    Expired.objects.create(**data)
                    elif form.is_valid() and "fp" in report_name:
                        data = {
                            'quarter_year': period_check,
                            'facility_name': facility,
                            'date_of_interview': date,
                            'description': form.cleaned_data['description'],
                            'family_planning_rod': form.cleaned_data.get('family_planning_rod'),
                            'family_planning_rod2': form.cleaned_data.get('family_planning_rod2'),
                            'dmpa_im': form.cleaned_data.get('dmpa_im'),
                            'dmpa_sc': form.cleaned_data.get('dmpa_sc'),
                            'comments': form.cleaned_data.get('comments')
                        }
                        if report_name == "fp_integers":
                            table_name, created = TableNames.objects.get_or_create(model_name="family_planning")
                            data['model_name'] = table_name
                            PharmacyFpModel.objects.create(**data)
                        else:
                            fields_to_check = ['family_planning_rod', 'family_planning_rod2',
                                               'dmpa_im', 'dmpa_sc']  # Add all relevant fields here
                            question_pairs = [(0, 1)]  # Add all pairs of questions to compare

                            validation_result = validate_pharmacy_formset(request, formset,
                                                                          'pharmacy/add_system_assessment.html',
                                                                          context, fields_to_check, question_pairs)
                            if validation_result:
                                return validation_result

                            if not form_errors:
                                table_name, created = TableNames.objects.get_or_create(model_name="family_planning")
                                data['model_name'] = table_name
                                PharmacyFpQualitativeModel.objects.create(**data)
                    elif form.is_valid() and "malaria" in report_name:
                        data = {
                            'quarter_year': period_check,
                            'facility_name': facility,
                            'date_of_interview': date,
                            'description': form.cleaned_data['description'],
                            'al_24': form.cleaned_data.get('al_24'),
                            'al_6': form.cleaned_data.get('al_6'),
                            'comments': form.cleaned_data.get('comments')
                        }

                        if report_name == "malaria_integers":
                            table_name, created = TableNames.objects.get_or_create(model_name="anti_malaria")
                            data['model_name'] = table_name
                            PharmacyMalariaModel.objects.create(**data)
                        else:
                            fields_to_check = ['al_6', 'al_24']  # Add all relevant fields here
                            question_pairs = [(0, 1)]  # Add all pairs of questions to compare

                            validation_result = validate_pharmacy_formset(request, formset,
                                                                          'pharmacy/add_system_assessment.html',
                                                                          context, fields_to_check, question_pairs)
                            if validation_result:
                                return validation_result

                            if not form_errors:
                                table_name, created = TableNames.objects.get_or_create(model_name="anti_malaria")
                                data['model_name'] = table_name
                                PharmacyMalariaQualitativeModel.objects.create(**data)
                                # All forms are valid, proceed with success message and redirect
                                # messages.success(request, 'Record saved successfully!')
                except IntegrityError:
                    messages.success(request, 'Data already exist!')
                    url = reverse('add_inventory',
                                  kwargs={"report_name": next_report, 'quarter': quarter, 'year': year, 'pk': pk,
                                          'date': date})
                    return redirect(url)

            show_buttons, filtered_data, missing = check_remaining(request, model_names, pk, quarter_year_id,
                                                                   facility_name,
                                                                   period_check, models_to_check)
            if len(missing) == 0:
                messages.success(request, f"All data for {facility_name} {period_check} is successfully saved! "
                                          f"Please select a different facility.")
                return redirect("choose_facilities_inventory")
            next_report = get_next_report(show_buttons)
            if next_report:
                messages.success(request, 'Record saved successfully!')
                url = reverse('add_inventory',
                              kwargs={"report_name": next_report, 'quarter': quarter, 'year': year, 'pk': pk,
                                      'date': date})
                return redirect(url)

    context = {
        "formset": formset, "report_name": report_name, "quarter": quarter, "year": year, "facility_id": pk,
        "date": date, "show_buttons": show_buttons, "filtered_data": filtered_data
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
    objects = {}
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

        work_plans = WorkPlan.objects.filter(facility_name_id=selected_facility.id,
                                             quarter_year__id=quarter_year.id
                                             )
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
                work_plans.progress = 0
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
        "selected_facility": selected_facility,
        "quarter_year": selected_quarter_year
    }
    return render(request, 'pharmacy/show_commodity_management.html', context)


def create_df(df, title, row_index):
    data = []
    try:
        for i in range(1, len(df.columns)):
            stock_card_tld = df.iloc[row_index, i]
            if pd.isna(stock_card_tld):
                data.append(0)
            else:
                data.append(int(stock_card_tld))
    except IndexError:
        for i in range(1, 7):
            stock_card_tld = df.iloc[row_index, i]
            if pd.isna(stock_card_tld):
                data.append(0)
            else:
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
    division_row.columns = a.columns
    a = pd.concat([a, division_row])
    return a


def divide_rows(a, num_index, deno_index):
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


def calculate_facility_score(a, ideal_target=100, dqa_type="facility"):
    # Get the count of values equal to 100 in each row
    count_100 = (a.iloc[:, 1:] == ideal_target).sum(axis=1)
    count_nas = (a.iloc[:, 1:] == 9999).sum(axis=1)

    # Calculate the division result
    division_result = round(count_100 / (a.shape[1] - 1 - count_nas), 2)
    # Add the new column 'Facility mean score' to the DataFrame
    a[f'{dqa_type.title()} mean score'] = division_result * 100
    return a


def group_and_merge(df, float_cols):
    yes_no_rows = [
        row for row in df['description'].to_list() if "there" in row.lower()
                                                      or "are the" in row.lower() or "does the" in row.lower()
    ]
    boolean_df = df[df['description'].isin(yes_no_rows)]
    grouped_boolean_df = boolean_df.groupby('description')[float_cols].mean().reset_index()
    float_cols = grouped_boolean_df.select_dtypes(include=['float']).columns

    # Convert float columns to integers
    grouped_boolean_df[float_cols] = grouped_boolean_df[float_cols].astype(int)
    non_boolean_df = df[~df['description'].isin(yes_no_rows)]
    grouped_non_boolean_df = non_boolean_df.groupby('description')[float_cols].sum().reset_index()
    df = pd.concat([grouped_boolean_df, grouped_non_boolean_df]).reset_index(drop=True)
    return df


def process_levels(df, expected_description_order):
    """
    Process levels in a DataFrame and calculate supply chain KPIs.

    Parameters:
        df (pd.DataFrame): Input DataFrame containing level information
        expected_description_order (list): List of expected description orders

    Returns:
        pd.DataFrame: Concatenated DataFrame with level-specific supply chain KPIs

    """
    # Initialize list to store level-specific DataFrames
    levels_dfs = sort_focus_area = []
    facility_mean = 0

    # Iterate over unique levels in sorted order
    for level in sorted(df['level'].unique()):
        # Filter DataFrame for current level
        level_df = df[df['level'] == level]

        # Check if level has at least 29 rows
        if level_df.shape[0] >= 29:
            # Calculate supply chain KPIs for current level
            supply_chain_target_100, sort_focus_area, facility_mean = calculate_supply_chain_kpis(level_df,
                                                                                                  expected_description_order)

            # Add 'Entity' column with level and mean score
            supply_chain_target_100.insert(0, 'Entity', f"{level}")

            # Find columns containing 'mean score'
            mean_score_cols = [col for col in supply_chain_target_100.columns if "mean score" in col]

            # Rename 'mean score' column
            supply_chain_target_100 = supply_chain_target_100.rename(
                columns={mean_score_cols[0]: "Focus Area Mean Score"})
            # Add 'Overall mean' column with level and mean score
            supply_chain_target_100["Overall Entity Mean"] = facility_mean

            # Append level-specific DataFrame to list
            levels_dfs.append(supply_chain_target_100)

    # Concatenate level-specific DataFrames
    return pd.concat(levels_dfs), sort_focus_area, facility_mean


def calculate_supply_chain_kpis(df, expected_description_order, dqa_type="facility"):
    # Replace values in the DataFrame
    df = df.replace({"No": 0, "Yes": 100, "N/A": 9999, np.nan: 9999})
    df['description'] = df['description'].apply(lambda x: re.sub(r'^\d+\.\s*', '', x))

    # Convert columns to integer type
    # Identify float columns
    # float_cols = df.select_dtypes(include=['float']).columns
    float_cols = df.columns[1:]

    # Convert float columns to integers
    df[float_cols] = df[float_cols].astype(int)
    # df[df.columns[1:]] = df[df.columns[1:]].astype(int)
    df = group_and_merge(df, float_cols)

    # Set 'description' column as categorical
    df['description'] = pd.Categorical(df['description'], categories=expected_description_order, ordered=True)
    # df.to_csv("df.csv", index=False)

    # Sort the DataFrame by 'description'
    df.sort_values('description', inplace=True)
    df = df[df['description'].notnull()]

    # Create DataFrames df1, df2, df3
    df1 = create_df(df, 'Stock card available', 0)
    df2 = create_df(df, 'in bin cards', 4)
    df3 = create_df(df, 'supp kemsa', 3)

    # Concatenate df1, df2, df3 into a single DataFrame 'a'
    a = pd.concat([df1, df2, df3])

    division_row = divide_rows(a, 1, 2)

    a = add_new_row(a, division_row, "Delivery Captured on Stock Card")

    # Create DataFrames df4, df5
    df4 = create_df(df, 'physical count', 10)
    df5 = create_df(df, 'stock card balance', 9)

    # Concatenate a, df4, df5 into a single DataFrame 'a'
    a = pd.concat([a, df4, df5])
    division_row = divide_rows(a, 4, 5)

    a = add_new_row(a, division_row, "Stock balance accuracy")

    # Create DataFrames df6, df7, df8, df9, df10, df11
    df6 = create_df(df, 'begining bal', 2)
    df7 = create_df(df, 'kemsa supply', 3)
    df8 = create_df(df, 'received from other facilities', 5)
    df9 = create_df(df, 'units issued to SDPs', 6)
    df10 = create_df(df, 'units issued to other facilities', 7)
    df11 = create_df(df, 'units expired', 8)
    df_end_bal = create_df(df, 'ending balance on bin card', 9)

    # Concatenate a, df6, df7, df8, df9, df10, df11 into a single DataFrame 'a'
    a = pd.concat([a, df6, df7, df8, df9, df10, df11, df_end_bal])

    division_row = pd.Series(index=a.columns)

    # Iterate over the columns
    for col in a.columns:
        numerator = a.iloc[13, col]
        denominator = (a.iloc[7, col] + a.iloc[8, col] + a.iloc[9, col]) - (
                a.iloc[10, col] + a.iloc[11, col] + a.iloc[12, col])

        # Check if the denominator is non-zero
        if denominator != 0:
            division_row[col] = round((numerator / denominator) * 100, 1)
        else:
            division_row[col] = 0

    a = add_new_row(a, division_row, "Transaction recording accuracy")

    # Create a new row for the division 'Delivered in full'
    division_row = pd.Series(index=a.columns)

    # Iterate over the columns
    for col in a.columns:
        numerator = a.iloc[5, col] - a.iloc[4, col]
        denominator = a.iloc[4, col]

        # Check if the denominator is non-zero
        if denominator != 0:
            division_row[col] = round((numerator / denominator) * 100, 1)
        else:
            division_row[col] = 0
    a = add_new_row(a, division_row, "Inventory variation")

    # a = add_new_row(a, division_row, "Delivered in full")
    df_cdrr = create_df(df, 'CDRR', 19)
    df_dar = create_df(df, 'DAR', 18)
    a = pd.concat([a, df_dar, df_cdrr])

    division_row = pd.Series(index=a.columns)

    # Iterate over the columns
    for col in a.columns:
        numerator = a.iloc[17, col] - a.iloc[16, col]

        denominator = a.iloc[7, col] + a.iloc[8, col] + a.iloc[9, col]

        # Check if the denominator is non-zero
        if denominator != 0:
            division_row[col] = round((numerator / denominator) * 100, 2)
        else:
            division_row[col] = 0

    a = add_new_row(a, division_row, "DAR vs CDRR Quantity Dispensed")

    # Reset index, rename columns, and filter unwanted rows
    a = a.reset_index()
    # df.to_csv("df_col.csv", index=False)
    # a.to_csv("a_col.csv", index=False)
    a.columns = list(df.columns)
    a = a[~a['description'].str.contains('in bin cards|supp kemsa|physical count|stock card balance|'
                                         'begining bal|kemsa supply|received from other facilities|'
                                         'units issued to SDPs|units issued to other facilities|units expired|'
                                         'quantity supplied|captured in the bin card|ending balance on bin card')]
    a = a[(a['description'] != "DAR") & (a['description'] != "CDRR")]
    last_two_rows = a[a["description"].str.contains("Inventory variation|DAR vs CDRR Quantity Dispensed")]
    a = a[~a["description"].str.contains("Inventory variation|DAR vs CDRR Quantity Dispensed")]
    a = calculate_facility_score(a, dqa_type=dqa_type)
    last_two_rows = calculate_facility_score(last_two_rows, ideal_target=0, dqa_type=dqa_type)
    a = pd.concat([a, last_two_rows])
    # Multiply all values in the "Facility mean score" column
    facility_mean = a[f'{dqa_type.title()} mean score'].mean().astype(float)
    facility_mean = round(facility_mean, 2)

    # Rename the 'description' column to 'Focus area'
    a = a.rename(
        columns={"description": "Focus area", "tld_90": "TLD 90s", "dtg_10": "DTG 10", "abc_3tc": "ABC/3TC 120/60",
                 "3hp": "3HP", "fp": "IMPLANT 1 ROD", "al_24": "AL 24", "dtg_50": "DTG 50", "fp_1_rod": "FP 1 Rod",
                 "fp_2_rods": "FP 2 Rods", "al_6": "AL 6", "rh_75_50": "RH 75/50"})

    # Convert 'Facility mean score' column to numeric and round to 2 decimal places
    a[f'{dqa_type.title()} mean score'] = pd.to_numeric(a[f'{dqa_type.title()} mean score'], errors='coerce')
    a = a.rename(columns={f"{dqa_type.title()} mean score": f"{dqa_type.title()} mean score: {facility_mean} %"})
    a = a.reset_index(drop=True)

    sort_focus_area = ['Delivered in full', 'Stock card available',
                       'Delivery Captured on Stock Card',
                       'Stock balance accuracy',
                       'Transaction recording accuracy',
                       'Stock Record Validity', 'Inventory variation',
                       'DAR vs CDRR Quantity Dispensed'
                       ]

    # Set 'description' column as categorical
    a['Focus area'] = pd.Categorical(a['Focus area'], categories=sort_focus_area, ordered=True)

    # Sort the DataFrame by 'description'
    a.sort_values('Focus area', inplace=True)
    a.index = np.arange(1, len(a) + 1)
    a = a.replace({"No": 0, "Yes": 100, 9999: ""})

    # Final DataFrame 'a'
    return a, sort_focus_area, facility_mean


def process_filtered_data(filtered_data):
    # Define field mappings
    field_mappings = {
        'default': {
            'description': 'description',
            'tld_90': 'adult_arv_tdf_3tc_dtg',
            'dtg_10': 'pead_arv_dtg_10mg',
            'dtg_50': 'pead_arv_dtg_50mg',
            'abc_3tc': 'paed_arv_abc_3tc_120_60mg',
            '3hp': 'tb_3hp',
            'rh_75_50': 'r_inh',
        },
        'mal': {
            'description': 'description',
            'al_24': 'al_24',
            'al_6': 'al_24',
        },
        'fp': {
            'description': 'description',
            'fp_1_rod': 'family_planning_rod',
            'fp_2_rods': 'family_planning_rod',
        }
    }

    # Process the filtered data
    data_dict = {key: [] for key in ['default', 'mal', 'fp']}

    for model_name, model_objects in filtered_data.items():
        category = 'mal' if 'mal' in model_name else 'fp' if 'fp' in model_name else 'default'
        mapping = field_mappings[category]

        data_dict[category].extend([
            {new_key: getattr(model_data, old_key) for new_key, old_key in mapping.items()}
            for model_data in model_objects
        ])

    # Create DataFrames
    dfs = {key: pd.DataFrame(value) for key, value in data_dict.items() if value}

    # Clean description column
    for df in dfs.values():
        df['description'] = df['description'].apply(lambda x: re.sub(r'^\d+\.\s*', '', x))

    # Merge DataFrames
    df = dfs.get('default', pd.DataFrame())
    for other_df in ['fp', 'mal']:
        if other_df in dfs:
            df = df.merge(dfs[other_df], on="description", how="left")
    expected_description_order = [
        'Is there currently a stock card or electronic record available for?',
        'Does the stock card or electronic record cover the entire period under review, which began on {'
        'start_date} to {end_date}?',
        'What was the beginning balance? (At the start of the review period)',
        'How many units were supplied by MEDS/KEMSA to this facility during the period under review from delivery '
        'notes?',
        'What quantity delivered from MEDS/KEMSA was captured in the bin card?',
        'How many units were received from other facilities (Positive Adjustments) during the period under review?',
        'How many units were issued from the storage areas to service delivery/dispensing point(s) within this '
        'facility during the period under review?',
        'How many units were issued to other facilities (Negative Adjustments) during the period under review?',
        'How many expired units  were in the facility during the review period?',
        'What is the ending balance on the stock card or electronic record on the last day of the review period?',
        'What was the actual physical count of this on the day of the visit?',
        'What is the average monthly consumption?',
        'How many positive adjustment transactions were made on the stock card for transfers to other health '
        'facilities during the period under review?',
        'How many positive adjustment transactions do not have a corresponding S11 form?',
        'How many negative adjustment transactions were made on the stock card for transfers to other health '
        'facilities during the period under review?',
        'How many negative adjustment transactions do not have a corresponding S11 form?',
        'Of the available S11 forms for positive adjustments, how many are endorsed (signed) by someone at this '
        'facility?',
        'Of the available S11 forms for the negative adjustments, how many are endorsed (signed) by someone at '
        'this facility?',
        'What quantity was dispensed at this facility based on the DAR/ADT during the review period?',
        'What quantity was dispensed, based the CDRR, at this facility during the review period?',
        'Has there been a stock out during the period under review?',
        'How many days out of stock?',
        'Were there any expiries during the period under review?',
    ]

    return df, expected_description_order


def prepare_dataframe(dataframe, column_mapping={}):
    # Reset the index to add row numbers
    dataframe = dataframe.reset_index(drop=True)
    # Add a new column for row numbers
    dataframe.index = dataframe.index + 1  # This makes the row numbers start from 1 instead of 0
    dataframe.index.name = 'No.'  # This names the index column
    dataframe = dataframe.reset_index()
    dataframe = dataframe.rename(columns=column_mapping)
    return dataframe


def generate_html_table(dataframe):
    # Generate HTML table
    dataframe_html = dataframe.fillna("-").to_html(
        classes='table table-responsive table-striped table-hover small-table',
        index=False,
        escape=False
    )

    # Remove the inline style from the header row
    dataframe_html = re.sub(r'<tr style="text-align: right;">', '<tr>', dataframe_html)

    return dataframe_html


def filter_models_by_facility_and_quarter(models_to_check, selected_facility, quarter_year):
    """
        Filter models based on facility name and quarter year.
        """
    return {
        model_name: model.objects.filter(
            facility_name__name=selected_facility,
            quarter_year__quarter_year=quarter_year,
            # quarter_year__year__gte=2025
        ).order_by('date_created')
        for model_name, model in models_to_check.items()
    }


def get_field_values_from_work_plans(work_plans, models_to_check):
    """
    Extract field values from work plans based on model names.
    """
    return [
        getattr(work_plan, f"{field_name}_id")
        for work_plan in work_plans
        for field_name in models_to_check
        if getattr(work_plan, f"{field_name}_id", None) is not None
    ]


def find_most_recent_item(filtered_data):
    """
    Find the most recent item across all filtered querysets.
    """
    most_recent_item = None
    most_recent_date = None

    for queryset in filtered_data.values():
        if queryset.exists():
            latest_item = queryset.latest('date_modified')
            if most_recent_date is None or latest_item.date_modified > most_recent_date:
                most_recent_item = latest_item
                most_recent_date = latest_item.date_modified

    return most_recent_item, most_recent_date


def check_missing_data(request, filtered_data, selected_facility, quarter_year):
    """
    Check if filtered data is missing and display a message.
    """
    if not any(filtered_data.values()) and quarter_year is not None:
        messages.success(
            request,
            f"Inventory management data for {selected_facility} {quarter_year} is missing! "
            f"Kindly enter data using the form provided in the 'DATA ENTRY' section."
        )


def process_inventory_data(request, selected_facility, quarter_year, MODELS_TO_CHECK):
    """
    Main function to process inventory data.
    """
    # Step 1: Filter models by facility and quarter
    filtered_data = filter_models_by_facility_and_quarter(MODELS_TO_CHECK, selected_facility, quarter_year)

    # Step 2: Check for missing data
    check_missing_data(request, filtered_data, selected_facility, quarter_year)

    # Step 3: Get field values from work plans
    work_plans = WorkPlan.objects.all()
    field_values = get_field_values_from_work_plans(work_plans, MODELS_TO_CHECK)

    # Step 4: Find the most recent item
    most_recent_item, most_recent_date = find_most_recent_item(filtered_data)

    return filtered_data, field_values, most_recent_item, most_recent_date


def handle_selected_facility(selected_facility, filtered_data):
    """
    Handle logic when a facility is selected.
    """
    if selected_facility and any(queryset.exists() for queryset in filtered_data.values()):
        df, expected_description_order = process_filtered_data(filtered_data)

        supply_chain_target_100, sort_focus_area, facility_mean = calculate_supply_chain_kpis(
            df, expected_description_order
        )

        # Rename columns
        column_mapping = {
            "description": "Description", "tld_90": "TLD 90s", "dtg_10": "DTG 10", "abc_3tc": "ABC/3TC 120/60",
            "3hp": "3HP", "fp": "IMPLANT 1 ROD", "al_24": "AL 24", "dtg_50": "DTG 50", "fp_1_rod": "FP 1 Rod",
            "fp_2_rods": "FP 2 Rods", "al_6": "AL 6", "rh_75_50": "RH 75/50"
        }

        df = prepare_dataframe(df, column_mapping)
        df_html = generate_html_table(df)
    else:
        df_html = ""
        supply_chain_target_100 = pd.DataFrame()
        sort_focus_area = None
        facility_mean = 0

    return df_html, supply_chain_target_100, sort_focus_area, facility_mean


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

    # Define the models to check
    MODELS_TO_CHECK = {
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
        "pharmacy_fp": PharmacyFpModel,
        "pharmacy_fp_qualitative": PharmacyFpQualitativeModel,
        "pharmacy_malaria_qualitative": PharmacyMalariaQualitativeModel,
        "pharmacy_malaria": PharmacyMalariaModel,
    }

    # Example usage
    filtered_data, field_values, most_recent_item, most_recent_date = process_inventory_data(request, selected_facility,
                                                                                             quarter_year,
                                                                                             MODELS_TO_CHECK)


    df_html, supply_chain_target_100, sort_focus_area, facility_mean = handle_selected_facility(selected_facility,
                                                                                                filtered_data)

    context = {
        'title': 'Inventory Management', "stock_card_data": filtered_data, "df_html": df_html,
        "quarter_form": quarter_form, 'most_recent_item': most_recent_item, "year_form": year_form,
        "facility_form": facility_form, "models_to_check": MODELS_TO_CHECK,
        "field_values": field_values, "supply_chain_target_100": supply_chain_target_100,
        "facility_mean": facility_mean, "sort_focus_areas": sort_focus_area,
    }

    return render(request, 'pharmacy/show_inventory_management.html', context)


# Function to create a custom sort key from quarter_year
def sort_key(quarter_year):
    """
    Create a custom sort key based on the quarter_year.

    Parameters:
        quarter_year (str): The quarter and year in the format "QtrX-YY".

    Returns:
        int: The custom sort key based on the year and quarter.
    """
    quarter, year = quarter_year.split('-')
    year = int('20' + year)  # Assuming all years are in the 2000s
    quarter_number = int(quarter[-1])  # Extract the quarter number
    return year * 10 + quarter_number


def prepare_trend(df, col, new_col_name, selected_facility):
    """
    Prepare quarterly trend data for plotting.

    Parameters:
        df (DataFrame): The DataFrame containing quarterly data.
        col (str): The column name to group by for quarterly trends.
        new_col_name (str): The new column name to be used in the resulting DataFrame.
        selected_facility (bool): Indicator whether a specific facility is selected (True) or all facilities are selected (False).

    Returns:
        figure: The Plotly line chart figure showing the quarterly trend.
    """
    quarterly_df = df.drop_duplicates(subset=["facility", "quarter_year"], keep="first")
    # Group by quarter_year and count the occurrences of date_of_interview
    quarterly_df = quarterly_df.groupby([col])["date_of_interview"].count().reset_index()

    # Sort the DataFrame by the custom sort key
    quarterly_trend_df = quarterly_df.sort_values(by=col, key=lambda x: x.map(sort_key))

    # Add "FY" to the year part in the quarter_year column
    quarterly_trend_df[col] = quarterly_trend_df[col].apply(
        lambda x: f"{x.split('-')[0]}-FY{x.split('-')[1]}")

    # Rename columns for clarity
    quarterly_trend_df.columns = [new_col_name, "Number of DQAs"]
    total_dqas = quarterly_trend_df['Number of DQAs'].sum()
    if selected_facility:
        selected_facility_name = ""
    else:
        selected_facility_name = "All Facilities"

    quarterly_trend_fig = line_chart_median_mean(quarterly_trend_df, new_col_name, "Number of DQAs",
                                                 f"Quarterly DQAs Trend: {selected_facility_name} (Number of DQAs = {total_dqas})",
                                                 xaxis_title="Quarter Year (FY)")
    return quarterly_trend_fig


# @silk_profile(name='get_location_details')
def get_location_details(facility_id):
    # Retrieve the facility object
    facility = get_object_or_404(Facilities, id=facility_id)

    # Get the Sub_counties related to the facility
    sub_counties = Sub_counties.objects.filter(facilities=facility)

    # Initialize lists to store county and hub names
    counties_list = []
    hub_list = []

    # Iterate through the related Sub_counties to get counties and hubs
    for sub_county in sub_counties:
        counties_list.extend(sub_county.counties.values_list('county_name', flat=True))
        hub_list.extend(sub_county.hub.values_list('hub', flat=True))

    # Remove duplicates from the lists
    counties_list = list(set(counties_list))
    hub_list = list(set(hub_list))

    return counties_list, hub_list, sub_counties


def fetch_data(model_class, quarter_year, facility=None):
    """
    Fetch data for the specified model class, quarter_year, and optional facility.
    """
    filters = {'quarter_year__quarter_year': quarter_year}
    if facility:
        filters['facility_name__name'] = facility

    objects = model_class.objects.filter(**filters).order_by('date_created')
    data = list(model_class.objects.all().values(
        'facility_name__name', 'facility_name', 'description', 'adult_arv_tdf_3tc_dtg', 'pead_arv_dtg_10mg',
        'paed_arv_abc_3tc_120_60mg', 'tb_3hp', 'family_planning_rod', 'al_24', 'quarter_year__quarter_year',
        'date_of_interview', 'comments', 'created_by__username', 'modified_by__username', 'date_created',
        'date_modified'
    ))
    return objects, data


def create_dataframes(filter_list, data):
    """
    Create and append DataFrame to the filtered data list.
    """
    df = pd.DataFrame(data)
    filter_list.append(df)


@login_required(login_url='login')
def dqa_dashboard(request, dqa_type=None):
    if not request.user.first_name:
        return redirect("profile")

    # Handle form submissions
    quarter_form = QuarterSelectForm(request.POST or None)
    year_form = YearSelectForm(request.POST or None)
    selected_quarter = "Qtr1"
    selected_year = "2021"
    if quarter_form.is_valid():
        selected_quarter = quarter_form.cleaned_data['quarter']

    if year_form.is_valid():
        selected_year = year_form.cleaned_data['year']

    facility_form = FacilityForm(request.POST or None, selected_year=selected_year, selected_quarter=selected_quarter)

    hub_form = HubSelectionForm(request.POST or None)
    subcounty_form = SubcountySelectionForm(request.POST or None)
    county_form = CountySelectionForm(request.POST or None)
    program_form = ProgramSelectionForm(request.POST or None)

    supply_chain_target_100 = pd.DataFrame()
    sort_focus_area = selected_facility = quarter_year = mean_score = quarterly_trend_fig = None
    facility_mean = 0

    models_to_check = {
        "stock_cards": StockCards, "unit_supplied": UnitSupplied,
        "beginning_balance": BeginningBalance, "positive_adjustments": PositiveAdjustments,
        "unit_issued": UnitIssued, "negative_adjustment": NegativeAdjustment,
        "expired_units": ExpiredUnits, "expired": Expired,
        "expiry_tracking": ExpiryTracking, "s11_form_availability": S11FormAvailability,
        "s11_form_endorsed": S11FormEndorsed, "stock_management": StockManagement,
    }
    model_names = list(models_to_check.keys())

    # Create an empty list to store the filtered objects
    filtered_data = []
    filtered_data_all = []

    if dqa_type == "facility":
        if quarter_form.is_valid() and year_form.is_valid() and facility_form.is_valid():
            selected_quarter = quarter_form.cleaned_data['quarter']
            selected_year = year_form.cleaned_data['year']
            selected_facility = facility_form.cleaned_data['name']
        else:
            # Use default quarter and year if forms are not valid
            selected_quarter = "default_quarter"
            selected_year = "default_year"
            selected_facility = None

        year_suffix = selected_year[-2:]
        quarter_year = f"{selected_quarter}-{year_suffix}"
        for model_name in model_names:
            model_class = models_to_check[model_name]
            objects, data_all = fetch_data(model_class, quarter_year, selected_facility)
            filtered_data.extend(objects)
            create_dataframes(filtered_data_all, data_all)

    if len(filtered_data) >= 29:
        df = pd.concat(filtered_data_all)
        df = df.rename(columns={"facility_name__name": "facility", "quarter_year__quarter_year": "quarter_year"})
        if selected_facility:
            selected_facility_name = selected_facility.name
            df = df[df['facility'] == selected_facility_name]
        # if
        quarterly_trend_fig = prepare_trend(df, "quarter_year", "Quarter Year", selected_facility)

        data = []
        for model_data in filtered_data:
            record = {
                'level': model_data.facility_name.name,
                'description': model_data.description,
                'tld_90': model_data.adult_arv_tdf_3tc_dtg,
                'dtg_10': model_data.pead_arv_dtg_10mg,
                'abc_3tc': model_data.paed_arv_abc_3tc_120_60mg,
                '3hp': model_data.tb_3hp,
                'fp': model_data.family_planning_rod,
                'al': model_data.al_24,
            }
            data.append(record)

        # Create DataFrame
        df = pd.DataFrame(data)

        expected_description_order = [
            'Is there currently a stock card or electronic record available for?',
            'Does the stock card or electronic record cover the entire period under review, '
            'which began on {start_date} to {end_date}?',
            'How many units were supplied by MEDS/KEMSA to this facility during the period '
            'under review from delivery notes?',
            'What quantity delivered from MEDS/KEMSA was captured in the bin card?',
            'What was the beginning balance? (At the start of the review period)',
            'How many units were supplied by MEDS/KEMSA to this facility during the period '
            'under review?',
            'How many units were received from other facilities (Positive Adjustments) '
            'during the period under review?',
            'How many positive adjustment transactions do not have a corresponding S11 form?',
            'How many units were issued from the storage areas to service '
            'delivery/dispensing point(s) within this facility during the period under '
            'review?',
            'How many units were issued to other facilities (Negative Adjustments) during '
            'the period under review?',
            'How many negative adjustment transactions were made on the stock card for '
            'transfers to other health facilities during the period under review?',
            'How many negative adjustment transactions do not have a corresponding S11 form?',
            'How many days out of stock?',
            'How many expired units  were in the facility during the review period?',
            'Has there been a stock out during the period under review?',
            'Were there any expiries during the period under review?',
            'Are there any expires in the facility?',
            'Is there a current expiry tracking chart/register in this facility (wall chart '
            'or electronic)?',
            'Are there units with less than 6 months to expiry?',
            'Are the units (with less than 6 months to expiry) captured on the expiry chart?',
            'Is there a corresponding S11 form at this facility for each of the positive '
            'adjustment transactions?',
            'Is there a corresponding S11 form at this facility for each of the negative '
            'adjustment transactions?',
            'Of the available S11 forms for positive adjustments, how many are endorsed ('
            'signed) by someone at this facility?',
            'Of the available S11 forms for the negative adjustments, how many are endorsed '
            '(signed) by someone at this facility?',
            'What is the ending balance on the stock card or electronic record on the last '
            'day of the review period?',
            'What was the actual physical count of this on the day of the visit?',
            'What is the stock balance on the stock card or electronic record on the day of '
            'the visit?',
            'What quantity was dispensed at this facility based on the DAR/ADT during the '
            'review period?',
            'What quantity was dispensed, based the CDRR, at this facility during the '
            'review period?',
            'What is the average monthly consumption?'
        ]

        supply_chain_target_100, sort_focus_area, facility_mean = process_levels(df, expected_description_order)
        supply_chain_target_100['facility_index'] = supply_chain_target_100.groupby("Entity").ngroup() + 1
        supply_chain_target_100 = supply_chain_target_100.set_index("facility_index")

    context = {
        "hub_form": hub_form, "mean_score": f"{dqa_type.title()} mean score",
        "subcounty_form": subcounty_form, "county_form": county_form, "program_form": program_form,
        'title': 'Inventory Management', "dqa_type": dqa_type, "stock_card_data": filtered_data,
        "quarter_form": quarter_form, "year_form": year_form, "facility_form": facility_form,
        "models_to_check": models_to_check, "supply_chain_target_100": supply_chain_target_100,
        "facility_mean": facility_mean, "sort_focus_areas": sort_focus_area,

        "quarterly_trend_fig": quarterly_trend_fig
    }

    return render(request, 'pharmacy/dqa_dashboard.html', context)


# def get_filtered_facilities(request):
#     selected_year = request.GET.get('year')
#     selected_quarter = request.GET.get('quarter')
#
# models_to_check = [
#     StockCards, UnitSupplied, BeginningBalance, PositiveAdjustments,
#     UnitIssued, NegativeAdjustment, ExpiredUnits, Expired, ExpiryTracking,
#     S11FormAvailability, S11FormEndorsed, StockManagement,
# ]
#
#     facility_ids = set()
#     for model in models_to_check:
#         facility_ids.update(
#             model.objects.filter(quarter_year__quarter_year=f"{selected_quarter}-{selected_year[-2:]}")
#             .values_list('facility_name_id', flat=True)
#         )
#
#     facilities = Facilities.objects.filter(id__in=facility_ids)
#     facilities_list = [{'id': facility.id, 'name': facility.name} for facility in facilities]
#     return JsonResponse(facilities_list, safe=False)


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

            messages.success(request, "Record updated successfully!")
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


def fetch_and_check_workplans(selected_facility, quarter_year):
    """
    Fetches pharmacy_records and delivery_notes_records for a given facility and quarter year,
    checks for missing WorkPlan entries, and returns combined records.

    :param selected_facility: The name of the selected facility.
    :param quarter_year: The quarter year to filter records.
    :return: A tuple containing (missing_in_workplans, combined_records).
    """
    # Fetch pharmacy_records and delivery_notes_records
    pharmacy_records = PharmacyRecords.objects.filter(
        facility_name__name=selected_facility,
        quarter_year__quarter_year=quarter_year
    ).order_by('date_created')

    delivery_notes_records = DeliveryNotes.objects.filter(
        facility_name__name=selected_facility,
        quarter_year__quarter_year=quarter_year
    )

    # Get IDs for pharmacy_records and delivery_notes_records
    pharmacy_record_ids = pharmacy_records.values_list('id', flat=True)
    delivery_note_ids = delivery_notes_records.values_list('id', flat=True)

    # Fetch WorkPlan objects linked to pharmacy_records and delivery_notes
    work_plans_pharmacy = WorkPlan.objects.filter(pharmacy_records__in=pharmacy_record_ids)
    work_plans_delivery_notes = WorkPlan.objects.filter(delivery_notes__in=delivery_note_ids)

    # Find pharmacy_records and delivery_notes without WorkPlan
    pharmacy_records_without_workplans = pharmacy_records.exclude(
        id__in=work_plans_pharmacy.values_list('pharmacy_records', flat=True)
    ).values_list('id', flat=True)

    delivery_notes_without_workplans = delivery_notes_records.exclude(
        id__in=work_plans_delivery_notes.values_list('delivery_notes', flat=True)
    ).values_list('id', flat=True)

    # Combine the two querysets into a list
    missing_in_workplans = list(chain(delivery_notes_without_workplans, pharmacy_records_without_workplans))

    # Combine pharmacy_records and delivery_notes_records into a single list
    combined_records = list(chain(pharmacy_records, delivery_notes_records))
    combined_records.sort(key=lambda x: x.register_name.register_name)

    return missing_in_workplans, combined_records, pharmacy_records


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

    # Fetch pharmacy_records and delivery_notes_records
    pharmacy_records = PharmacyRecords.objects.filter(
        facility_name__name=selected_facility,
        quarter_year__quarter_year=quarter_year
    ).order_by('date_created')

    delivery_notes_records = DeliveryNotes.objects.filter(
        facility_name__name=selected_facility,
        quarter_year__quarter_year=quarter_year
    )

    # Get IDs for pharmacy_records and delivery_notes_records
    pharmacy_record_ids = pharmacy_records.values_list('id', flat=True)
    delivery_note_ids = delivery_notes_records.values_list('id', flat=True)

    # Fetch WorkPlan objects linked to pharmacy_records and delivery_notes
    work_plans_pharmacy = WorkPlan.objects.filter(pharmacy_records__in=pharmacy_record_ids)
    work_plans_delivery_notes = WorkPlan.objects.filter(delivery_notes__in=delivery_note_ids)

    # Find pharmacy_records and delivery_notes without WorkPlan
    pharmacy_records_without_workplans = pharmacy_records.exclude(
        id__in=work_plans_pharmacy.values_list('pharmacy_records', flat=True)
    ).values_list('id', flat=True)

    delivery_notes_without_workplans = delivery_notes_records.exclude(
        id__in=work_plans_delivery_notes.values_list('delivery_notes', flat=True)
    ).values_list('id', flat=True)

    # Combine the two querysets into a list
    missing_in_workplans = list(chain(delivery_notes_without_workplans, pharmacy_records_without_workplans))

    # Combine pharmacy_records and delivery_notes_records into a single queryset (if compatible)
    combined_records = list(chain(pharmacy_records, delivery_notes_records))
    combined_records.sort(key=lambda x: x.register_name.register_name)

    if selected_facility:
        facility, created = Facilities.objects.get_or_create(name=selected_facility)
        period, created = Period.objects.get_or_create(quarter_year=quarter_year)

        work_plans = WorkPlan.objects.filter(facility_name_id=facility.id,
                                             quarter_year__id=period.id
                                             )
    else:
        work_plans = {}
        facility = None
        period = None

    # Prepare context
    context = {
        'title': 'Commodity records/registers',
        "pharmacy_records": pharmacy_records, "work_plans": work_plans,
        # "delivery_notes_records": delivery_notes_records,
        "quarter_form": quarter_form,
        "combined_records": combined_records,
        "missing_in_workplans": missing_in_workplans,
        "year_form": year_form,
        "facility_form": facility_form,
        "models_to_check": models_to_check,
        # "delivery_notes_without_workplans": delivery_notes_without_workplans,
        "supply_chain_target_100": supply_chain_target_100,
        "sort_focus_areas": sort_focus_area,
        "selected_facility": facility,
        "quarter_year": period
    }

    return render(request, 'pharmacy/show_commodity_management.html', context)


@login_required(login_url='login')
def update_pharmacy_records(request, pk, register_name):
    # def update_inventory(request, pk):
    if not request.user.first_name:
        return redirect("profile")

    commodity_questions = {}
    try:
        item = PharmacyRecords.objects.get(id=pk)
    except ObjectDoesNotExist:
        item = DeliveryNotes.objects.get(id=pk)
    model_name = item.__class__.__name__

    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
        commodity_questions = {
            register_name: [
                "Are delivery notes from MEDS / KEMSA maintained in a separate file "
                "from S11s, and are they arranged chronologically?",
                "Does the facility have a copy of the delivery notes for commodities last received during the review "
                "period?",
            ] if model_name == "DeliveryNotes" else [
                'Does the facility have a Malaria Commodities DAR (MoH 645) register? If not, please specify which '
                'register is used to capture dispensing of Malaria commodities in the comment section.',
                'Is the Malaria Commodity DAR (MoH 645) currently being used by the facility?',
                'Does the facility has a copy of the Malaria Consumption Data Report and Requisition (CDRR) '
                '(MOH743) that was prepared in the last month of the review period?',
                'If the facility has the Malaria CDRR for the last month of the review period, please indicate the '
                'date when it was submitted (DD/MM/YY)'
            ] if register_name == "Malaria Commodities DAR (MoH 645)" else [
                'Is there a MANUAL ARV Daily Activity Register (DAR) (MOH 367A) or an electronic dispensing tool '
                ' in this facility? Specify which one in the comments section',
                'Is the MANUAL ARV Daily Activity Register (DAR) (MOH 367A) or an electronic dispensing tool '
                ' currently in use?',
                'Does the facility have a copy of the ARV F-CDRR (MOH 730B) that was prepared for the last month of '
                'the review period',
                'If “Yes”, when was the ARV F-CDRR (MOH 730B) for the last month of the review period submitted?'
                '(DD/MM/YY)',
            ] if register_name == 'ARV Daily Activity Register (DAR) (MOH 367A) or WebADT' else [
                'Is there a DADR-Anti TB register in this facility? If no, specify which register is used '
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
                'If the facility has the ARV F-MAPS (MOH 729B) for the last month of the review period, please indicate'
                ' the date when it was submitted'
            ] if register_name == "ARV F-MAPS (MOH 729B)" else [
                "Are delivery notes from MEDS / KEMSA maintained in a separate file "
                "from S11s, and are they arranged chronologically?",
                "Does the facility have a copy of the delivery notes for commodities last received during the review "
                "period?"]
        }
        request.session['commodity_questions'] = commodity_questions

    request.session['date_of_interview'] = item.date_of_interview.strftime('%Y-%m-%d')  # Convert date to string
    facility_name = item.facility_name

    if request.method == "POST":
        if model_name == "DeliveryNotes":
            form = DeliveryNotesForm(request.POST, instance=item)
        elif "F-MAPS" in register_name:
            form = PharmacyRecordsForm(request.POST, instance=item, is_required=False)
        else:
            form = PharmacyRecordsForm(request.POST, instance=item, is_required=True)

        if form.is_valid():
            instance = form.save(commit=False)
            # Initialize the commodity_questions dictionary
            commodity_questions = request.session['commodity_questions']

            context = {
                "form": form, "register_name": register_name,
                "title": "Update commodity records/registers",
                "commodity_questions": commodity_questions,
            }
            if not validate_form(form, facility_name):
                return render(request, 'pharmacy/add_pharmacy_commodities.html', context)

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
    else:
        form = PharmacyRecordsForm(instance=item)

    context = {
        "form": form, "register_name": register_name, "model_name": model_name,
        "title": "Update commodity records/registers",
        "commodity_questions": commodity_questions,
    }
    return render(request, 'pharmacy/update records.html', context)


def get_joined_values_from_json(json_str):
    """
    Extracts 'value' fields from a JSON array of objects and joins them into a comma-separated string.

    Args:
        json_str (str): JSON string representing an array of objects with 'value' keys

    Returns:
        str: Comma-separated string of values
    """
    items = json.loads(json_str)
    return ', '.join(item['value'] for item in items)


@login_required(login_url='login')
def create_commodity_work_plans(request, pk):
    # Redirect if user doesn't have a first name
    if not request.user.first_name:
        return redirect("profile")

    # Try to fetch the object from PharmacyRecords or DeliveryNotes
    try:
        fetched_objects = get_object_or_404(PharmacyRecords, id=pk)
    except Http404:
        fetched_objects = get_object_or_404(DeliveryNotes, id=pk)

    if request.method == 'POST':
        form = WorkPlanForm(request.POST)
        today = timezone.now().date()

        if form.is_valid():
            work_plan = form.save(commit=False)
            work_plan.facility_name = fetched_objects.facility_name
            work_plan.quarter_year = fetched_objects.quarter_year
            responsible_persons_json = form.cleaned_data['responsible_person']
            work_plan.responsible_person = get_joined_values_from_json(responsible_persons_json)
            try:
                work_plan.pharmacy_records = fetched_objects
            except ValueError:
                work_plan.delivery_notes = fetched_objects
            work_plan.progress = (work_plan.complete_date - today).days

            try:
                work_plan.save()
                messages.success(request, 'Work plan created successfully!')
            except IntegrityError:
                messages.error(request, 'A work plan for this record already exists!')

            # Set initial values for the forms
            initial_data = {
                'quarter_form': {'quarter': fetched_objects.quarter_year.quarter_year},
                'year_form': {'year': fetched_objects.quarter_year.year},
                'facility_form': {'name': fetched_objects.facility_name.name},
            }

            # Redirect to the show_commodity_records view with initial values
            url = reverse('show_commodity_records')
            url = f'{url}?{urlencode(initial_data)}'
            return redirect(url)
    else:
        form = WorkPlanForm()

    context = {
        'form': form,
        'title': 'Add DQA Work Plan',
        'facility': fetched_objects, "fetched_objects": fetched_objects,
        "stock_card_data": [fetched_objects],
    }

    return render(request, 'pharmacy/show_commodity_management.html', context)


# def create_commodity_work_plans(request, pk):
#     if not request.user.first_name:
#         return redirect("profile")
#
#     try:
#         pharmacy_objects = get_object_or_404(PharmacyRecords, id=pk)
#     except:
#         pharmacy_objects = get_object_or_404(DeliveryNotes, id=pk)
#
#     if request.method == 'POST':
#         form = WorkPlanForm(request.POST)
#         today = timezone.now().date()
#         if form.is_valid():
#             work_plan = form.save(commit=False)
#             work_plan.facility_name = pharmacy_objects.facility_name
#             work_plan.quarter_year = pharmacy_objects.quarter_year
#             work_plan.pharmacy_records = pharmacy_objects
#             work_plan.progress = (work_plan.complete_date - today).days
#             try:
#                 work_plan.save()
#             except IntegrityError:
#                 messages.error(request, 'Work plan already exists!')
#
#             # Set the initial values for the forms
#             quarter_form_initial = {'quarter': pharmacy_objects.quarter_year.quarter_year}
#             year_form_initial = {'year': pharmacy_objects.quarter_year.year}
#             facility_form_initial = {"name": pharmacy_objects.facility_name.name}
#             # Redirect to the show_commodity_records view with the initial values for the forms
#             url = reverse('show_commodity_records')
#             url = f'{url}?quarter_form={quarter_form_initial}&year_form={year_form_initial}&facility_form={facility_form_initial}'
#             return redirect(url)
#     else:
#         form = WorkPlanForm()
#
#     context = {
#         'form': form,
#         'title': 'Add DQA Work Plan',
#         'facility': pharmacy_objects,
#         "stock_card_data": [pharmacy_objects],
#     }
#
#     return render(request, 'pharmacy/show_commodity_management.html', context)


@login_required(login_url='login')
def update_workplan(request, pk):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    item = WorkPlan.objects.get(id=pk)
    #############################################################
    # Handle foreign keys
    #############################################################
    foreign_key_mapping = {
        'pharmacy_records': PharmacyRecords,
        'delivery_notes': DeliveryNotes,
    }
    # Handle foreign keys
    item = handle_foreign_keys(request, item, foreign_key_mapping)

    if request.method == "POST":
        form = WorkPlanForm(request.POST, instance=item)
        today = timezone.now().date()
        if form.is_valid():
            instance = form.save(commit=False)
            instance.progress = (instance.complete_date - today).days
            #############################################################
            # Handle foreign keys
            #############################################################
            instance = handle_foreign_keys(request, instance, foreign_key_mapping)

            instance.save()
            messages.success(request, "Record updated successfully!")
            # Set the initial values for the forms
            quarter_form_initial = {'quarter': item.quarter_year.quarter_year}
            year_form_initial = {'year': item.quarter_year.year}
            facility_form_initial = {"name": item.facility_name.name}
            # Redirect to the inventory view with the initial values for the forms
            url = reverse('pharmacy_show_work_plan')
            url = f'{url}?quarter_form={quarter_form_initial}&year_form={year_form_initial}&facility_form={facility_form_initial}'
            return redirect(url)
    else:
        form = WorkPlanForm(instance=item)
    context = {
        "form": form, "fetched_object": item,
        "title": "Update Workplan",
    }
    return render(request, 'pharmacy/update workplan.html', context)


@login_required(login_url='login')
def add_audit_team_pharmacy(request, pk, quarter_year):
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
    audit_team_pharmacy = PharmacyAuditTeam.objects.filter(facility_name__id=pk,
                                                           quarter_year__quarter_year=quarter_year)
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
                                                      quarter_year__quarter_year=selected_quarter, module="Pharmacy")
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
