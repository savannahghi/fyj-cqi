import ast
import uuid
from datetime import datetime
import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction, DatabaseError, IntegrityError
from django.db.models import Q
from django.forms import modelformset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect

# Create your views here.
from django.urls import reverse
from django.utils import timezone

from apps.cqi.models import Facilities, Sub_counties, Counties
from apps.cqi.views import bar_chart
from apps.dqa.form import QuarterSelectionForm, YearSelectionForm, FacilitySelectionForm
from apps.dqa.models import Period
from apps.fyj_mentorship.decorators import check_fyj_staff_details_exists, require_full_name
from apps.fyj_mentorship.filters import MentorshipFilter
from apps.fyj_mentorship.forms import FyjStaffDetailsForm, FyjCardersForm, FacilityStaffCardersForm, \
    FacilityStaffDetailsForm, ProgramAreasForm, IntroductionForm, IdentificationGapsForm, PrepareCoachingSessionForm, \
    CoachingSessionForm, FollowUpForm, MentorshipWorkPlanForm, ProgramareaForm
from apps.fyj_mentorship.models import FyjCarders, FacilityStaffCarders, FacilityStaffDetails, ProgramAreas, \
    Introduction, IdentificationGaps, PrepareCoachingSession, CoachingSession, FollowUp, MentorshipWorkPlan, \
    FyjStaffDetails
from apps.labpulse.decorators import group_required
from apps.pharmacy.forms import DateSelectionForm
from apps.pharmacy.models import TableNames


@login_required(login_url='login')
@require_full_name
@group_required(['project_technical_staffs'])
@check_fyj_staff_details_exists
def add_facility_carders(request):

    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
        # request.session['page_from'] = request.session['page_from'] = request.get_full_path()
    form = FacilityStaffCardersForm(request.POST or None)
    carders = FacilityStaffCarders.objects.all()
    if request.method == "POST":
        if form.is_valid():
            try:
                with transaction.atomic():
                    post = form.save(commit=True)
                    carder = form.cleaned_data['carder']
                    post.carder = carder.upper()
                    post.save()
                    messages.error(request, "Record saved successfully!")
            except IntegrityError:
                error_message = f"Carder '{carder}' already exists!"
                messages.error(request, error_message)
                context = {
                    "title": "Add facility staff details",
                    "form": form,
                    "carders": carders
                }
                return render(request, 'fyj_mentorship/add fyj mentorship facilities.html', context)

    context = {
        "title": "Add facility staff carders",
        "form": form,
        "carders": carders
    }
    return render(request, 'fyj_mentorship/add fyj mentorship facilities.html', context)


@login_required(login_url='login')
@require_full_name
@group_required(['project_technical_staffs'])
@check_fyj_staff_details_exists
def add_carders(request):

    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
        # request.session['page_from'] = request.session['page_from'] = request.get_full_path()
    form = FyjCardersForm(request.POST or None)
    carders = FyjCarders.objects.all()

    if request.method == "POST":
        if form.is_valid():
            try:
                with transaction.atomic():
                    post = form.save(commit=True)
                    carder = form.cleaned_data['carder']
                    post.carder = carder.upper()
                    post.save()
                    messages.error(request, "Record saved successfully!")
                    return redirect('add_fyj_staff_details')
            except IntegrityError:
                error_message = f"Carder '{carder}' already exists!"
                messages.error(request, error_message)
                context = {
                    "title": "Add Carder",
                    "form": form,
                    "carders": carders
                }
                return render(request, 'fyj_mentorship/add fyj mentorship facilities.html', context)

    context = {
        "title": "Add Carder",
        "form": form,
        "carders": carders
    }
    return render(request, 'fyj_mentorship/add fyj mentorship facilities.html', context)


@login_required(login_url='login')
@require_full_name
@group_required(['project_technical_staffs'])
@check_fyj_staff_details_exists
def update_facility_carder(request, pk):

    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    item = FacilityStaffCarders.objects.get(id=pk)
    if request.method == "POST":
        form = FacilityStaffCardersForm(request.POST, instance=item)
        if form.is_valid():
            with transaction.atomic():
                post = form.save(commit=True)
                carder = form.cleaned_data['carder']
                post.carder = carder.upper()
                post.save()
                messages.error(request, "Record updated successfully!")
                return HttpResponseRedirect(request.session['page_from'])
    else:
        form = FacilityStaffCardersForm(instance=item)
    context = {
        "form": form,
        "title": "Add facility staff carders",
    }
    return render(request, 'fyj_mentorship/add fyj mentorship facilities.html', context)


@login_required(login_url='login')
@require_full_name
@group_required(['project_technical_staffs'])
@check_fyj_staff_details_exists
def add_program_area(request):

    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
        # request.session['page_from'] = request.session['page_from'] = request.get_full_path()
    form = ProgramAreasForm(request.POST or None)
    program_areas = ProgramAreas.objects.all()

    if request.method == "POST":
        if form.is_valid():
            try:
                with transaction.atomic():
                    post = form.save(commit=True)
                    program_area = form.cleaned_data['program_area']
                    post.program_area = program_area.upper()
                    post.save()
                    messages.error(request, "Record saved successfully!")
                    # return redirect('add_fyj_staff_details')
            except IntegrityError:
                error_message = f"Program area '{program_area.upper()}' already exists!"
                messages.error(request, error_message)
                context = {
                    "title": "Add Program Area",
                    "form": form,
                    "program_areas": program_areas
                }
                return render(request, 'fyj_mentorship/add fyj mentorship facilities.html', context)

    context = {
        "title": "Add Program Area",
        "form": form,
        "program_areas": program_areas
    }
    return render(request, 'fyj_mentorship/add fyj mentorship facilities.html', context)


@login_required(login_url='login')
@require_full_name
@group_required(['project_technical_staffs'])
@check_fyj_staff_details_exists
def show_program_area(request):

    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
        # request.session['page_from'] = request.session['page_from'] = request.get_full_path()

    program_areas = ProgramAreas.objects.all()
    context = {
        "title": "Program Area",
        "program_areas": program_areas
    }
    return render(request, 'fyj_mentorship/add fyj mentorship facilities.html', context)


@login_required(login_url='login')
@require_full_name
@group_required(['project_technical_staffs'])
@check_fyj_staff_details_exists
def update_program_area(request, pk):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    item = ProgramAreas.objects.get(id=pk)
    if request.method == "POST":
        form = ProgramAreasForm(request.POST, instance=item)
        if form.is_valid():
            with transaction.atomic():
                post = form.save(commit=True)
                program_area = form.cleaned_data['program_area']
                post.program_area = program_area.upper()
                post.save()
                messages.error(request, "Record updated successfully!")
                return HttpResponseRedirect(request.session['page_from'])
    else:
        form = ProgramAreasForm(instance=item)
    context = {
        "form": form,
        "title": "Update Program Area",
    }
    return render(request, 'fyj_mentorship/add fyj mentorship facilities.html', context)


@login_required(login_url='login')
@require_full_name
@group_required(['project_technical_staffs'])
@check_fyj_staff_details_exists
def update_carder(request, pk):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    item = FyjCarders.objects.get(id=pk)
    if request.method == "POST":
        form = FyjCardersForm(request.POST, instance=item)
        if form.is_valid():
            with transaction.atomic():
                post = form.save(commit=True)
                carder = form.cleaned_data['carder']
                post.carder = carder.upper()
                post.save()
                messages.error(request, "Record updated successfully!")
                return HttpResponseRedirect(request.session['page_from'])
    else:
        form = FyjCardersForm(instance=item)
    context = {
        "form": form,
        "title": "Update carder",
    }
    return render(request, 'fyj_mentorship/add fyj mentorship facilities.html', context)

@login_required(login_url='login')
@require_full_name
@group_required(['project_technical_staffs'])
def add_fyj_staff_details(request):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    staff_details = {}
    form = FyjStaffDetailsForm(request.POST or None)

    # Check if the user already has a record in the model
    name_id = request.user.id
    existing_record = FyjStaffDetails.objects.filter(name__id=name_id).first()
    show_message = True
    if existing_record:
        staff_details = FyjStaffDetails.objects.all().order_by('carder')
        show_message = False
    if request.method == "POST":
        if form.is_valid():
            if existing_record:
                messages.error(request, "Record already exists!")
                # Display an error message or handle the duplicate record scenario
                context = {
                    "title": "Add FYJ staff details",
                    "form": form,
                    "staff_details": staff_details,
                    "show_message": show_message
                }
                return render(request, 'fyj_mentorship/add fyj mentorship facilities.html', context)
            else:
                form.save()
                messages.error(request, "Record successfully saved")
    context = {
        "title": "Add FYJ staff details",
        "form": form,
        "staff_details": staff_details, "show_message": show_message
    }
    return render(request, 'fyj_mentorship/add fyj mentorship facilities.html', context)


@login_required(login_url='login')
@require_full_name
@group_required(['project_technical_staffs'])
@check_fyj_staff_details_exists
def add_facility_staff_details(request):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    form = FacilityStaffDetailsForm(request.POST or None)
    carders = FacilityStaffDetails.objects.all()
    if request.method == "POST":
        if form.is_valid():
            try:
                with transaction.atomic():
                    post = form.save(commit=True)
                    staff_name = form.cleaned_data['staff_name']
                    post.staff_name = staff_name.upper()
                    post.save()
                    form = FacilityStaffDetailsForm()
                    messages.error(request, "Record updated successfully!")
                # return HttpResponseRedirect(request.session['page_from'])
            except IntegrityError:
                error_message = f"Records with staff name '{staff_name.title()}' already exists!"
                messages.error(request, error_message)
                context = {
                    "title": "Add facility staff details",
                    "form": form,
                    "carders": carders,
                }
                return render(request, 'fyj_mentorship/add fyj mentorship facilities.html', context)

    context = {
        "title": "Add facility staff details",
        "form": form,
        "carders": carders,
    }
    return render(request, 'fyj_mentorship/add fyj mentorship facilities.html', context)


@login_required(login_url='login')
@require_full_name
@group_required(['project_technical_staffs'])
@check_fyj_staff_details_exists
def update_facility_staff_details(request, pk):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    item = FacilityStaffDetails.objects.get(id=pk)
    if request.method == "POST":
        form = FacilityStaffDetailsForm(request.POST, instance=item)
        if form.is_valid():
            try:
                with transaction.atomic():
                    post = form.save(commit=True)
                    staff_name = form.cleaned_data['staff_name']
                    post.staff_name = staff_name.upper()
                    post.save()
                    form = FacilityStaffDetailsForm()
                    messages.error(request, "Record updated successfully!")
                    return HttpResponseRedirect(request.session['page_from'])
            except IntegrityError:
                error_message = f"Staff records '{staff_name}' already exists!"
                messages.error(request, error_message)
                context = {
                    "title": "Add facility staff details",
                    "form": form,
                    # "carders": carders
                }
                return render(request, 'fyj_mentorship/add fyj mentorship facilities.html', context)
    else:
        form = FacilityStaffDetailsForm(instance=item)
    context = {
        "form": form,
        "title": "Add facility staff details",
    }
    return render(request, 'fyj_mentorship/add fyj mentorship facilities.html', context)


@login_required(login_url='login')
@require_full_name
@group_required(['project_technical_staffs'])
@check_fyj_staff_details_exists
def update_fyj_staff_details(request, pk):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    item = FyjStaffDetails.objects.get(id=pk)
    update_message = "update"
    show_message = True
    if request.method == "POST":
        form = FyjStaffDetailsForm(request.POST, instance=item)
        if form.is_valid():
            post = form.save(commit=True)
            post.save()
            messages.error(request, "Record updated successfully!")
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = FyjStaffDetailsForm(instance=item)
    context = {
        "form": form,
        "title": "Add FYJ staff details",
        "update_message": update_message, "show_message": show_message
    }
    return render(request, 'fyj_mentorship/add fyj mentorship facilities.html', context)


@login_required(login_url='login')
@require_full_name
@group_required(['project_technical_staffs'])
@check_fyj_staff_details_exists
def choose_facilities_mentorship(request):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    quarter_form = QuarterSelectionForm(request.POST or None)
    year_form = YearSelectionForm(request.POST or None)
    facility_form = FacilitySelectionForm(request.POST or None)
    date_form = DateSelectionForm(request.POST or None)
    program_area_form = ProgramareaForm(request.POST or None)
    if request.method == "POST":
        if quarter_form.is_valid() and year_form.is_valid() and date_form.is_valid() and facility_form.is_valid() and \
                program_area_form.is_valid():
            selected_quarter = quarter_form.cleaned_data['quarter']
            selected_facility = facility_form.cleaned_data['name']
            selected_year = year_form.cleaned_data['year']
            selected_date = date_form.cleaned_data['date']
            selected_program_area = program_area_form.cleaned_data['program_area']

            # Generate the URL for the redirect
            url = reverse('add_fyj_mentorship',
                          kwargs={"report_name": "None", 'quarter': selected_quarter, 'year': selected_year,
                                  'pk': selected_facility.id, 'date': selected_date,
                                  'program_area': selected_program_area.id})

            return redirect(url)
    context = {
        "quarter_form": quarter_form,
        "year_form": year_form,
        "facility_form": facility_form,
        "date_form": date_form,
        "program_area_form": program_area_form,
        "title": "COACHING/MENTORSHIP CHECKLIST"
    }
    return render(request, 'fyj_mentorship/add fyj mentorship facilities.html', context)


def generate_descriptions(report_name):
    if report_name == "introduction":
        descriptions = [
            "a) Have you made physical contact with the health worker/s to be mentored?"
        ]
    elif report_name == "identification_gaps":
        descriptions = [
            "a) Have gaps/needs been identified together with the health worker/s?",
            "b) Have you agreed on a plan to address the gaps with the health worker/s?"
        ]
    elif report_name == "prepare_coaching_session":
        descriptions = [
            "a) Have you written down all the major/critical knowledge points to be covered or key processes in the "
            "skill to be transferred?",
            "b) Is a date and time scheduled in consultation with the health worker/s?",
            "c) Is the supervisor/ Facility in charge informed of this exercise?",
            "d) Is the Sub-County Program Officer for the Technical Areas informed of the exercise?",
            "e) Are all the materials assembled?",
            "f) Have you checked for recent updates on the subject?",
            "g) Have you identified space for the exercise ( if necessary)",
        ]
    elif report_name == "coaching_session":
        descriptions = [
            "a) Have you established the health worker/s level of knowledge or skills about the subject?",
            "b) Have you discussed the objectives of the session/s with the health worker/s?",
            "c) Have you covered all the critical/major knowledge or skill processes outlined in 3a above? If no, "
            "why? Plan on how to cover the points in a follow up session. ",
            "d) Have you reviewed what the health worker/s have learnt? Do they need extra mentorship for them to "
            "grasp the concept/skills better?"
        ]
    elif report_name == "follow_up":
        descriptions = [
            "a) Have you agreed on follow up plan with the health worker/s? When and how will the follow up be done?",
            "b) Have you given feedback to the supervisor or facility in charge?"
        ]
    else:
        descriptions = []
    return descriptions


def create_inventory_formset(report_name, request, initial_data):
    # Define a dictionary mapping report names to model and form classes
    report_mapping = {
        "introduction": (Introduction, IntroductionForm),
        "identification_gaps": (IdentificationGaps, IdentificationGapsForm),
        "prepare_coaching_session": (PrepareCoachingSession, PrepareCoachingSessionForm),
        "coaching_session": (CoachingSession, CoachingSessionForm),
        "follow_up": (FollowUp, FollowUpForm),
    }

    if report_name in report_mapping:
        model_class, form_class = report_mapping[report_name]
    else:
        model_class, form_class = report_mapping["introduction"]

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
@require_full_name
@group_required(['project_technical_staffs'])
@check_fyj_staff_details_exists
def add_fyj_mentorship(request, report_name=None, quarter=None, year=None, pk=None, date=None, program_area=None):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    quarter_form = QuarterSelectionForm(request.POST or None)
    year_form = YearSelectionForm(request.POST or None)
    facility_form = FacilitySelectionForm(request.POST or None)
    date_form = DateSelectionForm(request.POST or None)
    program_area_form = ProgramareaForm(request.POST or None)
    descriptions = generate_descriptions(report_name)
    request.session['descriptions'] = descriptions
    initial_data = [{'description': description} for description in descriptions]
    formset, inventory_form_set, model_class, form_class = create_inventory_formset(report_name, request, initial_data)
    period_check, created = Period.objects.get_or_create(quarter=quarter, year=year)
    quarter_year_id = period_check.id

    facility, created = Facilities.objects.get_or_create(id=pk)
    facility_name = facility

    selected_program_area, created = ProgramAreas.objects.get_or_create(id=program_area)

    models_to_check = {
        "introduction": Introduction,
        "identification_gaps": IdentificationGaps,
        "prepare_coaching_session": PrepareCoachingSession,
        "coaching_session": CoachingSession,
        "follow_up": FollowUp
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
                Q(quarter_year__id=quarter_year_id) &
                Q(program_area_id=selected_program_area.id)
            )
            if objects:
                # Append the filtered objects to the list
                filtered_data.append(model_name_)
        return filtered_data

    filtered_data = get_data_entered()
    model_names = ['introduction', 'identification_gaps',
                   'prepare_coaching_session', 'coaching_session', 'follow_up',
                   ]
    missing = [item for item in model_names if item not in filtered_data]
    if len(missing) == 0:
        messages.success(request, f"All data for {facility_name} {period_check} for program area "
                                  f"'{selected_program_area}' is successfully saved! "
                                  f"Please select a different facility.")
        # return redirect("choose_facilities_mentorship")
        # Set the initial values for the forms
        quarter_form_initial = {'quarter': quarter}
        year_form_initial = {'year': year}
        facility_form_initial = {"name": facility_name.name}
        url = reverse('show_mentorship')
        url = f'{url}?quarter_form={quarter_form_initial}&year_form={year_form_initial}&facility_form={facility_form_initial}'
        return redirect(url)
    if report_name == "None":
        # Redirect to the URL with the first missing item as the report_name
        url = reverse('add_fyj_mentorship',
                      kwargs={"report_name": missing[0], 'quarter': quarter, 'year': year, 'pk': pk, 'date': date,
                              "program_area": program_area})
        return redirect(url)

    ##################################
    # SHOW MENTORSHIP CHECKLIST DATA #
    ##################################
    models_to_check = {
        "introduction": Introduction,
        "identification_gaps": IdentificationGaps,
        "prepare_coaching_session": PrepareCoachingSession,
        "coaching_session": CoachingSession,
        "follow_up": FollowUp
    }
    model_names = list(models_to_check.keys())
    # Create a dictionary to store the tables
    tables = {}

    # Iterate over the model names
    for model_name in model_names:
        # Get the model class from the models_to_check dictionary
        model_class = models_to_check[model_name]
        objects = model_class.objects.filter(facility_name__id=pk, quarter_year__id=quarter_year_id,
                                             program_area_id=selected_program_area.id).order_by(
            'date_created')

        # Check if there are objects for the model
        if objects.exists():
            # Create a table for the model
            table = []
            for obj in objects:
                # Append the object to the table
                table.append(obj)

            # Add the table to the dictionary with the model name as the key
            tables[model_name] = table
    # # # Pass the description_tables to the template for rendering
    # context = {
    #     'mentorship_tables': tables
    # }

    #############################
    # Hide add work plan button #
    #############################
    work_plans = MentorshipWorkPlan.objects.filter(facility_name_id=pk,
                                                   quarter_year__id=quarter_year_id)
    field_values = []

    # Iterate over the work plans
    for work_plan in work_plans:
        # Iterate over the models in models_to_check dictionary
        for field_name, model in models_to_check.items():
            field_id = getattr(work_plan, field_name + "_id", None)
            if field_id is not None:
                field_values.append(field_id)

    if request.method == "POST":
        formset = inventory_form_set(request.POST, initial=initial_data)
        if formset.is_valid():
            selected_date = date
            # selected_program_area = program_area
            instances = formset.save(commit=False)
            context = {
                "formset": formset, "quarter_form": quarter_form, "year_form": year_form,
                "facility_form": facility_form,
                "date_form": date_form, "descriptions": descriptions, "program_area_form": program_area_form,
                "page_from": request.session.get('page_from', '/'),
                "report_name": missing[0],
                "quarter": quarter,
                "year": year,
                "facility_id": pk,
                "date": date,
                "program_area": program_area,
                "filtered_data": filtered_data
            }
            # #######################################
            # # CHECK IF USER SELECTION IS LOGICAL  #
            # #######################################
            # fields_to_validate = [
            #     ('adult_arv_tdf_3tc_dtg', 'adult_arv_tdf_3tc_dtg'),
            #     ('pead_arv_dtg_10mg', 'pead_arv_dtg_10mg'),
            #     ('paed_arv_abc_3tc_120_60mg', 'paed_arv_abc_3tc_120_60mg'),
            #     ('tb_3hp', 'tb_3hp'),
            #     ('family_planning_rod', 'family_planning_rod'),
            #     ('al_24', 'al_24'),
            # ]

            # for field_to_validate, error_field in fields_to_validate:
            #     if form_class == IntroductionForm:
            #         question_1_value = formset.forms[0].cleaned_data.get(field_to_validate)
            #         question_2_value = formset.forms[1].cleaned_data.get(field_to_validate)
            #         if question_1_value == 'No' and question_2_value == 'Yes':
            #             formset.forms[1].add_error(error_field,
            #                                        f"Invalid selection. Can't select 'Yes' if above question is 'No'.")
            # elif form_class == ExpiredForm:
            #     question_1_value = formset.forms[1].cleaned_data.get(field_to_validate)
            #     question_2_value = formset.forms[2].cleaned_data.get(field_to_validate)
            #     if question_1_value == 'No' and question_2_value == 'Yes':
            #         formset.forms[2].add_error(error_field,
            #                                    f"Invalid selection. Can't select 'Yes' if above question is 'No'.")
            ############################################
            # CHECK IF THERE ARE ERRORS IN THE FORMSET #
            ############################################
            if any(form.errors for form in formset.forms):
                # There are form errors in the formset
                return render(request, 'fyj_mentorship/add_mentorship_data.html', context)

            #################################################
            # CHECK IF ALL FORMS IN THE FORMSET ARE FILLED  #
            #################################################
            if not all([form.has_changed() for form in formset.forms]):
                for form in formset.forms:
                    if not form.has_changed():
                        for field in form.fields:
                            if field != "comments":
                                form.add_error(field, "This field is required.")
                return render(request, 'fyj_mentorship/add_mentorship_data.html', context)
            try:
                errors = False

                # ##############################################
                # # CHECK IF THERE IS A COMMENT FOR ANY 'NO'!  #
                # ##############################################
                fields_to_check = [
                    ('drop_down_options', "Choices"),
                ]

                for form in formset.forms:
                    error_fields = []
                    for field, field_name in fields_to_check:
                        if form.cleaned_data.get(field) == 'No' and not form.cleaned_data.get('comments'):
                            errors = True
                            error_fields.append(field_name)

                    if error_fields:
                        error_message = f"Please provide a comment for 'No' selection."

                        form.add_error('comments', error_message)

                if errors:
                    return render(request, 'fyj_mentorship/add_mentorship_data.html', context)

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
                        return render(request, 'fyj_mentorship/add_mentorship_data.html', context)

                ###########################################################
                # SAVE DATA IF IT DOES NOT EXIST AND THERE IS NO ERRORS!  #
                ###########################################################
                with transaction.atomic():
                    for form, instance in zip(formset.forms, instances):
                        # Set instance fields from form data
                        instance.drop_down_options = form.cleaned_data['drop_down_options']
                        instance.comments = form.cleaned_data['comments']
                        instance.date_of_interview = selected_date
                        instance.program_area = selected_program_area
                        instance.created_by = request.user
                        instance.description = form.cleaned_data['description']
                        instance.facility_name = facility
                        instance.quarter_year = period_check
                        # Get or create the Table instance
                        table_name, created = TableNames.objects.get_or_create(model_name=report_name)
                        instance.model_name = table_name

                        facility_id = Facilities.objects.get(name=facility_name)
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

                    filtered_data = get_data_entered()
                    missing = [item for item in model_names if item not in filtered_data]
                    if len(missing) != 0:
                        messages.success(request, f"Data for {facility_name} {period_check} is successfully saved!")
                        # Redirect to the URL with the first missing item as the report_name
                        url = reverse('add_fyj_mentorship',
                                      kwargs={"report_name": missing[0], 'quarter': quarter, 'year': year, 'pk': pk,
                                              'date': date, "program_area": program_area})
                        return redirect(url)
                    else:
                        messages.success(request, f"All data for {facility_name} {period_check} for program area "
                                                  f"'{selected_program_area}' is successfully saved! "
                                                  f"Please select a different facility.")
                        # return redirect("choose_facilities_mentorship")
                        # url = reverse('add_fyj_mentorship',
                        #               kwargs={"report_name": missing[0], 'quarter': quarter, 'year': year, 'pk': pk,
                        #                       'date': date, "program_area": program_area})
                        # return redirect(url)
                        # Set the initial values for the forms
                        quarter_form_initial = {'quarter': quarter}
                        year_form_initial = {'year': year}
                        facility_form_initial = {"name": facility_name.name}
                        url = reverse('show_mentorship')
                        url = f'{url}?quarter_form={quarter_form_initial}&year_form={year_form_initial}&facility_form={facility_form_initial}'
                        return redirect(url)

            except DatabaseError:
                messages.error(request,
                               f"Data for {facility_name} {period_check} already exists!")
    context = {
        "formset": formset,
        "report_name": report_name,
        "quarter": quarter,
        "year": year,
        "facility_id": pk,
        "date": date, "program_area": program_area,
        "filtered_data": filtered_data,
        "mentorship_tables": tables,
        "field_values": field_values, "selected_program_area": selected_program_area,
    }
    return render(request, 'fyj_mentorship/add_mentorship_data.html', context)


@login_required(login_url='login')
@require_full_name
@group_required(['project_technical_staffs'])
@check_fyj_staff_details_exists
def update_mentorship_checklist(request, pk, model):

    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    report_mapping = {
        "introduction": (Introduction, IntroductionForm),
        "identification_gaps": (IdentificationGaps, IdentificationGapsForm),
        "prepare_coaching_session": (PrepareCoachingSession, PrepareCoachingSessionForm),
        "coaching_session": (CoachingSession, CoachingSessionForm),
        "follow_up": (FollowUp, FollowUpForm),
    }
    model_class, form_class = report_mapping[model]
    item = model_class.objects.get(id=pk)
    request.session['date_of_interview'] = item.date_of_interview.strftime('%Y-%m-%d')  # Convert date to string
    request.session['model_name_id'] = str(item.model_name.id)  # Convert UUID to string
    request.session['program_area_id'] = str(item.program_area.id)  # Convert UUID to string

    if request.method == "POST":
        form = form_class(request.POST, instance=item)
        if form.is_valid():
            formset = form
            instance = form.save(commit=False)
            context = {
                "form": form,
                "title": "Update mentorship checklist",
            }

            ############################################
            # CHECK IF THERE ARE ERRORS IN THE FORM #
            ############################################
            if form.errors:
                # There are form errors in the form
                return render(request, 'fyj_mentorship/update mentorship checklist.html', context)

            #################################################
            # CHECK IF ALL FORM FIELDS ARE FILLED  #
            #################################################
            if not form.has_changed():
                for field in form.fields:
                    if field != "comments" and not form[field].value():
                        form.add_error(field, "This field is required.")
                return render(request, 'fyj_mentorship/update mentorship checklist.html', context)
            # try:
            errors = False

            # ##############################################
            # # CHECK IF THERE IS A COMMENT FOR ANY 'NO'!  #
            # ##############################################
            fields_to_check = [
                ('drop_down_options', "Status"),
            ]

            for field, field_name in fields_to_check:
                if form.cleaned_data.get(field) == 'No' and not form.cleaned_data.get('comments'):
                    errors = True
                    form.add_error('comments', f"Please provide a comment for 'No in the {field_name}' selection.")
                    form.add_error('drop_down_options',
                                   f"Please provide a comment for 'No in the {field_name}' selection.")

            if errors:
                return render(request, 'fyj_mentorship/update mentorship checklist.html', context)
            table_name, created = TableNames.objects.get_or_create(id=uuid.UUID(request.session['model_name_id']))
            instance.model_name = table_name
            # Retrieve the date_of_interview value from the session
            date_of_interview_str = request.session.get('date_of_interview')
            date_of_interview = datetime.strptime(date_of_interview_str, '%Y-%m-%d').date()  # Convert string to date
            # Set the date_of_interview field in the instance
            instance.date_of_interview = date_of_interview
            chosen_program_area, created = ProgramAreas.objects.get_or_create(id=uuid.UUID(request.session[
                                                                                               'program_area_id']))
            instance.program_area = chosen_program_area
            instance.save()

            messages.success(request, "Record updated successfully!")
            # Check if the saved URL contains 'show-mentorship'
            if 'show-mentorship' in request.session['page_from']:
                # Set the initial values for the forms
                quarter_form_initial = {'quarter': item.quarter_year.quarter_year}
                year_form_initial = {'year': item.quarter_year.year}
                facility_form_initial = {"name": item.facility_name.name}
                url = reverse('show_mentorship')
                url = f'{url}?quarter_form={quarter_form_initial}&year_form={year_form_initial}&facility_form={facility_form_initial}'
                return redirect(url)
            else:
                return HttpResponseRedirect(request.session['page_from'])
    else:
        form = form_class(instance=item)
    context = {
        "form": form,
        "title": "Update mentorship checklist",
    }
    return render(request, 'fyj_mentorship/update mentorship checklist.html', context)


@login_required(login_url='login')
@require_full_name
@group_required(['project_technical_staffs'])
@check_fyj_staff_details_exists
def create_mentorship_work_plans(request, pk, report_name):

    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    models_to_check = {
        "introduction": Introduction,
        "identification_gaps": IdentificationGaps,
        "prepare_coaching_session": PrepareCoachingSession,
        "coaching_session": CoachingSession,
        "follow_up": FollowUp
    }

    # Get the model class from the models_to_check dictionary
    model_class = models_to_check[report_name]
    if not model_class:
        return redirect("show_work_plan")  # Handle invalid report_name gracefully

    # Filter the objects based on the conditions
    objects = model_class.objects.filter(id=pk)

    if request.method == 'POST':
        form = MentorshipWorkPlanForm(request.POST)
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
            return HttpResponseRedirect(request.session['page_from'])

    else:
        form = MentorshipWorkPlanForm()

    context = {
        'form': form,
        'title': "Add Mentorship Work Plan",
        'facility': objects,
        "stock_card_data": objects,
        "report_name": report_name,
    }

    return render(request, 'fyj_mentorship/workplan.html', context)


def make_mentorship_charts(df):
    df['staffs'] = df['first_name'] + " " + df['last_name']
    df1 = df.groupby(['County', 'Sub-county', 'Facility', 'mfl_code', 'program_area', 'quarter_year']).count()[
        'description'].reset_index()
    df1['# of mentorship'] = 1
    if 'description' in df1.columns:
        del df1['description']
    ####################################
    # program viz
    ####################################
    program_area_df = df1.groupby('program_area')['# of mentorship'].sum().reset_index()
    program_area_df = program_area_df.sort_values("# of mentorship")
    program_area_df = program_area_df.sort_values('program_area')
    program_area_fig = bar_chart(program_area_df, "program_area", "# of mentorship",
                                 "Number Of Mentorship Conducted Per Program Area")
    ####################################
    # counties viz
    ####################################
    counties_df = df1.groupby('County')['# of mentorship'].sum().reset_index()
    counties_df = counties_df.sort_values('# of mentorship')
    counties_fig = bar_chart(counties_df, "County", "# of mentorship", "Number Of Mentorship Conducted Per County")
    ####################################
    # counties viz
    ####################################
    subcounties_df = df1.groupby('Sub-county')['# of mentorship'].sum().reset_index()
    subcounties_df = subcounties_df.sort_values('# of mentorship')
    subcounties_fig = bar_chart(subcounties_df, f"{subcounties_df.columns[0]}",
                                "# of mentorship", f"Number Of Mentorship Conducted Per {subcounties_df.columns[0]}")
    ####################################
    # facilities viz
    ####################################
    facilities_df = df1.groupby('Facility')['# of mentorship'].sum().reset_index()
    facilities_df = facilities_df.sort_values('# of mentorship')
    if facilities_df.shape[0] > 20:
        facilities_df_ = facilities_df.head(20)
        facilities_fig = bar_chart(facilities_df_, f"{facilities_df.columns[0]}", "# of mentorship",
                                   f"Top 20 Facilities (out of {facilities_df.shape[0]}) for Number of Mentorship "
                                   f"Conducted")
    else:
        facilities_fig = bar_chart(facilities_df, f"{facilities_df.columns[0]}",
                                   "# of mentorship", f"Number Of Mentorship Conducted Per {facilities_df.columns[0]}")
    ####################################
    # quarter_year viz
    ####################################
    quarter_year_df = df1.groupby('quarter_year')['# of mentorship'].sum().reset_index()
    quarter_year_df = quarter_year_df.sort_values('quarter_year')
    quarter_year_fig = bar_chart(quarter_year_df, f"{quarter_year_df.columns[0]}",
                                 "# of mentorship", f"Number Of Mentorship Conducted Per {quarter_year_df.columns[0]}")
    ####################################
    # staff viz
    ####################################

    df2 = \
        df.groupby(['County', 'Sub-county', 'Facility', 'mfl_code', 'program_area', 'quarter_year', 'staffs']).count()[
            'description'].reset_index()
    df2['# of mentorship'] = 1
    if 'description' in df2.columns:
        del df2['description']
    staff_df = df2.groupby('staffs')['# of mentorship'].sum().reset_index()
    staff_df = staff_df.sort_values('staffs')
    staff_fig = bar_chart(staff_df, f"{staff_df.columns[0]}",
                          "# of mentorship", f"Number Of Mentorship Conducted Per {staff_df.columns[0]}")
    ####################################
    # weekly trend viz
    ####################################
    date_df = df.groupby(
        ['County', 'Sub-county', 'Facility', 'mfl_code', 'program_area', 'quarter_year', 'date_of_visit']).count()[
        'description'].reset_index()
    date_df['# of mentorship'] = 1
    if 'description' in date_df.columns:
        del date_df['description']
    date_df = date_df[['date_of_visit', '# of mentorship']]
    date_df = date_df.copy()
    date_df.loc[:, 'date_of_visit'] = pd.to_datetime(date_df['date_of_visit'])

    date_df['weeks'] = date_df['date_of_visit'].dt.strftime('%Y-%U')  # Group by weeks

    date_df['date_of_visit'] = pd.to_datetime(
        date_df['date_of_visit'])  # Convert 'date_of_visit' column to datetime format
    date_df['weeks'] = date_df['date_of_visit'].dt.to_period('W').dt.start_time  # Get the first date of each weeks

    date_df['month'] = date_df['date_of_visit'].dt.strftime('%b-%y')  # Group by month in 'Jun-23' format

    df_new = date_df.groupby(['weeks', 'month'])['# of mentorship'].sum().reset_index()
    df_weekly = date_df.groupby('weeks').count()[
        '# of mentorship'].reset_index()  # Group by weeks and count the number of mentorships
    df_weekly = df_weekly.sort_values('weeks')
    weekly_fig = bar_chart(df_weekly, f"{df_weekly.columns[0]}",
                           "# of mentorship", f"Weekly trend for mentorship sessions")
    ####################################
    # monthly trend viz
    ####################################

    date_df['month_num'] = pd.to_datetime(date_df['month'], format='%b-%y')
    df_monthly = date_df.groupby(['month', 'month_num']).count()[
        '# of mentorship'].reset_index()  # Group by weeks and count the number of mentorships
    df_monthly = df_monthly.sort_values('month_num')
    monthly_fig = bar_chart(df_monthly, f"{df_monthly.columns[0]}",
                            "# of mentorship", f"Monthly trend for mentorship sessions")

    return program_area_fig, counties_fig, subcounties_fig, facilities_fig, quarter_year_fig, staff_fig, weekly_fig, monthly_fig


@login_required(login_url='login')
@require_full_name
@group_required(['project_technical_staffs'])
@check_fyj_staff_details_exists
def show_mentorship(request):
    period = None
    introduction_length = None
    work_plans = {}
    my_filters = {}
    objects = {}
    program_area_fig = None
    counties_fig = None
    subcounties_fig = None
    facilities_fig = None
    quarter_year_fig = None
    staff_fig = None
    weekly_fig = None
    monthly_fig = None

    models_to_check = {
        "introduction": Introduction,
        "identification_gaps": IdentificationGaps,
        "prepare_coaching_session": PrepareCoachingSession,
        "coaching_session": CoachingSession,
        "follow_up": FollowUp
    }
    model_names = list(models_to_check.keys())

    # Create a dictionary to store the tables
    tables = {}

    # Get the quarter and year from the request
    quarter = request.GET.get('quarter')
    year = request.GET.get('year')

    # Get the corresponding quarter_year value from the Period model
    if quarter and year:
        quarter_year = f"{quarter}-{year[2:]}"
        period = Period.objects.get(quarter_year=quarter_year)

    # Iterate over the model names
    for model_name in model_names:
        # Get the model class from the models_to_check dictionary
        model_class = models_to_check[model_name]
        objects = model_class.objects.all().order_by('date_created')
        my_filters = MentorshipFilter(request.GET, queryset=objects)
        objects = my_filters.qs

        # Apply additional filtering based on quarter and year
        if quarter and year:
            objects = objects.filter(quarter_year=period)

        # Check if there are objects for the model
        if objects.exists():
            # Create a table for the model
            table = []
            for obj in objects:
                # Append the object to the table
                table.append(obj)

            # Add the table to the dictionary with the model name as the key
            tables[model_name] = table
    if len(list(tables.keys())) == 5 and 'introduction' in tables:
        try:
            introduction_length = len(tables['introduction'])
            if introduction_length > 1:
                messages.error(request,
                               f"Multiple ({introduction_length}) mentorship checklists found. Please narrow down "
                               f"your filters to display a single mentorship checklist.")
            else:
                # Get the specific mentorship checklist from the table queryset
                introduction_checklist = tables['introduction'][0]

                # Use the details from the checklist to perform additional filtering
                work_plans = MentorshipWorkPlan.objects.filter(
                    facility_name_id=introduction_checklist.facility_name,
                    quarter_year_id=introduction_checklist.quarter_year
                )
        except KeyError:
            messages.error(request, "Mentorship checklist not available")
            introduction_length = 0
    elif introduction_length is None:
        messages.error(request, "Mentorship checklist not available")

    if objects:
        list_of_projects = [
            {'County': x.county.county_name,
             'Sub-county': x.sub_county.sub_counties,
             'Facility': x.facility_name.name,
             'mfl_code': x.facility_name.mfl_code,
             'program_area': x.program_area.program_area,
             'quarter_year': x.quarter_year.quarter_year,
             'description': x.description,
             'choices': x.drop_down_options,
             'comments': x.comments,
             'date_of_visit': x.date_of_interview,
             'first_name': x.created_by.first_name,
             'last_name': x.created_by.last_name,

             } for x in objects
        ]
        # convert data from database to a dataframe
        df = pd.DataFrame(list_of_projects)
        df = df.copy()
        program_area_fig, counties_fig, subcounties_fig, facilities_fig, quarter_year_fig, staff_fig, weekly_fig, \
        monthly_fig = make_mentorship_charts(df)



    #############################
    # Hide add work plan button #
    #############################
    # work_plans = MentorshipWorkPlan.objects.filter(facility_name__name=selected_facility,
    #                                                quarter_year__quarter_year=quarter_year)
    field_values = []

    # Iterate over the work plans
    for work_plan in work_plans:
        # Iterate over the models in models_to_check dictionary
        for field_name, model in models_to_check.items():
            field_id = getattr(work_plan, field_name + "_id", None)
            if field_id is not None:
                field_values.append(field_id)

    context = {
        'title': 'Coaching / Mentorship checklist',
        "models_to_check": models_to_check,
        "field_values": field_values,
        "mentorship_tables": tables, "my_filters": my_filters, "introduction_length": introduction_length,
        "program_area_fig": program_area_fig,
        "counties_fig": counties_fig, "subcounties_fig": subcounties_fig,
        "facilities_fig": facilities_fig, "quarter_year_fig": quarter_year_fig,
        "staff_fig": staff_fig, "weekly_fig": weekly_fig, "monthly_fig": monthly_fig
    }

    return render(request, 'fyj_mentorship/show mentorship.html', context)

@login_required(login_url='login')
@require_full_name
def show_mentorship_work_plan(request):
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
            "introduction": Introduction,
            "identification_gaps": IdentificationGaps,
            "prepare_coaching_session": PrepareCoachingSession,
            "coaching_session": CoachingSession,
            "follow_up": FollowUp
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

        work_plans = MentorshipWorkPlan.objects.filter(facility_name_id=selected_facility.id,
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
            form = MentorshipWorkPlanForm(request.POST)
            if form.is_valid():
                dqa_work_plan = form.save(commit=False)
                dqa_work_plan.facility_name = objects.facility_name
                dqa_work_plan.quarter_year = objects.quarter_year.id
                dqa_work_plan.created_by = request.user
                dqa_work_plan.save()
                return redirect('show_dqa_work_plan')
        else:
            form = MentorshipWorkPlanForm()
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
        "selected_facility": selected_facility,"quarter_year": selected_quarter_year
    }
    return render(request, 'fyj_mentorship/show mentorship workplan.html', context)
