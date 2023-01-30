# import os.path
from datetime import datetime, timezone
from itertools import tee

import pandas as pd
# from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
# from django.core.files.storage import FileSystemStorage
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist

from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db import IntegrityError, transaction
# from django.db.models import Count, Q
# from django.forms import forms
from django.db.models import Count, Q, F
# from django.utils import timezone
from django.db.transaction import atomic
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404

from account.forms import UpdateUserForm
# from cqi_fyj import settings

from .forms import QI_ProjectsForm, TestedChangeForm, ProjectCommentsForm, ProjectResponsesForm, \
    QI_ProjectsSubcountyForm, QI_Projects_countyForm, QI_Projects_hubForm, QI_Projects_programForm, Qi_managersForm, \
    DepartmentForm, CategoryForm, Sub_countiesForm, FacilitiesForm, CountiesForm, ResourcesForm, Qi_team_membersForm, \
    ArchiveProjectForm, QI_ProjectsConfirmForm, StakeholderForm, MilestoneForm, ActionPlanForm, Lesson_learnedForm, \
    BaselineForm, CommentForm, HubForm, SustainmentPlanForm
from .filters import *

import plotly.express as px


# Create your views here.

def pagination_(request, item_list, item_number=10):
    page = request.GET.get('page', 1)

    paginator = Paginator(item_list, item_number)
    try:
        items = paginator.page(page)
    except PageNotAnInteger:
        items = paginator.page(1)
    except EmptyPage:
        items = paginator.page(paginator.num_pages)
    return items


def prepare_viz(list_of_projects, pk, col):
    # TODO: CHECK IF THIS FUNCTION CAN BE USED TO OPTIMIZE THE CODE
    # convert data from database to a dataframe
    list_of_projects = pd.DataFrame(list_of_projects)

    list_of_projects = list_of_projects[list_of_projects[col] == pk].sort_values("achievements")

    # keys = list_of_projects['department'].unique()

    dfs = []
    for department in list_of_projects[col].unique():
        a = list_of_projects[list_of_projects[col] == department]
        a = a.sort_values("month_year", ascending=False)
        dfs.append(a)

    dicts = {}
    keys = list_of_projects[col].unique()
    values = dfs
    for i in range(len(keys)):
        dicts[keys[i]] = values[i]

    if list_of_projects.shape[0] != 0:
        dicts = {}
        keys = list_of_projects['project_id'].unique()

        values = list_of_projects['project'].unique()
        for i in range(len(keys)):
            dicts[keys[i]] = values[i]

        lst = []
        for i in list_of_projects['project_id'].unique():
            # get the first rows of the dfs
            a = list_of_projects[list_of_projects['project_id'] == i].sort_values("month_year", ascending=False)
            # append them in a list
            lst.append(a.head(1))

        # concat and sort them by project id
        df_heads = pd.concat(lst).sort_values("achievements", ascending=False)

        all_other_projects_trend = []
        for project in list(df_heads['project_id']):
            # filter dfs based on the order of the best performing projects
            if isinstance(project, str):
                all_other_projects_trend.append(
                    prepare_trends(list_of_projects[list_of_projects['project_id'] == project], project))
            else:
                all_other_projects_trend.append(
                    prepare_trends(list_of_projects[list_of_projects['project_id'] == project]))

        pro_perfomance_trial = dict(zip(keys, all_other_projects_trend))
    else:
        pro_perfomance_trial = {}
    return pro_perfomance_trial


def prepare_bar_chart_from_df(list_of_projects, col, title, projects=None):
    list_of_projects = list_of_projects[col].value_counts().rename_axis(col).reset_index(name='counts')
    list_of_projects = list_of_projects.T
    list_of_projects.columns = list_of_projects.iloc[0]
    list_of_projects = list_of_projects.iloc[1:]
    if projects is not None:
        list_of_projects['All QI projects'] = projects
    list_of_projects = list_of_projects.T.reset_index().sort_values("counts")
    facility_proj_performance = bar_chart(list_of_projects, col, "counts", title)
    return facility_proj_performance


def prepare_bar_chart_horizontal_from_df(list_of_projects, col, title, projects=None):
    list_of_projects = list_of_projects[col].value_counts().rename_axis(col).reset_index(name='counts')
    list_of_projects = list_of_projects.T
    list_of_projects.columns = list_of_projects.iloc[0]
    list_of_projects = list_of_projects.iloc[1:]
    if projects is not None:
        list_of_projects['All QI projects'] = projects
    list_of_projects = list_of_projects.T.reset_index().sort_values("counts")
    facility_proj_performance = bar_chart_horizontal(list_of_projects, col, "counts", title)
    return facility_proj_performance


@login_required(login_url='login')
def dashboard(request):
    facility_qi_projects = None
    subcounty_qi_projects = None
    county_qi_projects = None
    department_qi_projects = None
    best_performing_dic = None
    dicts = None
    testedChange_current = None
    qi_mans = None
    project_id_values = []

    qi_list = QI_Projects.objects.all()

    sub_qi_list = Subcounty_qi_projects.objects.all()
    county_qi_list = County_qi_projects.objects.all()

    # hub_qi_list = Hub_qi_projects.objects.all()
    # program_qi_list = Program_qi_projects.objects.all()

    # best_performing = TestedChange.objects.filter(achievements__gte=00.0).distinct()
    testedChange = TestedChange.objects.all()
    # testedChange = TestedChange.objects.annotate(total_projects=Count("project"))

    # my_filters = TestedChangeFilter(request.GET, queryset=best_performing)

    if testedChange:
        best_performing_df = [
            {'project': x.project.project_title,
             'month_year': x.month_year,
             'achievements': x.achievements,
             "project_id": x.project.id,
             "project_qi_manager": x.project.qi_manager,
             "department": x.project.departments,
             "facility": x.project.facility_name.facilities,
             } for x in testedChange
        ]
        # convert data from database to a dataframe
        best_performing = pd.DataFrame(best_performing_df).sort_values("month_year", ascending=False)
        dfs = []
        for project in best_performing['project'].unique():
            a = best_performing[best_performing['project'] == project]
            a = a.sort_values("month_year", ascending=False)
            dfs.append(a.head(1))
        best_performing = pd.concat(dfs)

        best_performing = best_performing.sort_values("achievements", ascending=False)
        # best_performing = best_performing[best_performing['achievements'] >=10]
        qi_mans = best_performing.copy()
        best_performing['project'] = best_performing['project'] + " (" + best_performing['achievements'].astype(
            int).astype(str) + "%)"

        qi_mans['achievements'] = qi_mans['achievements'].astype(int).astype(str) + " %"
        qi_mans['facility'] = qi_mans['facility'].str.replace(" ", "_")
        qi_mans.reset_index(drop=True, inplace=True)
        qi_mans.index += 1
        qi_mans = qi_mans[['project_qi_manager', 'facility', 'project', 'achievements', 'department']]
        qi_mans = qi_mans.rename(columns={"project_qi_manager": "Project QI Manager",
                                          "project": "Project", "facility": "Facility",
                                          "department": "Department", "achievements": "Achievements"})

        keys = list(best_performing['project'])
        project_id_values = list(best_performing['project_id'])
        best_performing_dic = dict(zip(keys, project_id_values))
        request.session['project_id_values'] = project_id_values

    if sub_qi_list:
        list_of_projects = [
            {'subcounty': x.sub_county.sub_counties,
             'county': x.county.county_name,
             'department': x.department.department,
             } for x in sub_qi_list
        ]
        # convert data from database to a dataframe
        list_of_projects = pd.DataFrame(list_of_projects)
        list_of_projects_sub = list_of_projects.copy()
        list_of_projects_sub['subcounty'] = list_of_projects_sub['subcounty']
    else:
        list_of_projects_sub = pd.DataFrame(columns=['subcounty', 'county', 'department'])

    if county_qi_list:
        list_of_projects = [
            {'county': x.county.county_name,
             'department': x.department.department,
             } for x in county_qi_list
        ]
        # convert data from database to a dataframe
        list_of_projects = pd.DataFrame(list_of_projects)
        list_of_projects_county = list_of_projects.copy()
        list_of_projects_county['county'] = list_of_projects_county['county']
    else:
        list_of_projects_county = pd.DataFrame(columns=['county', 'department'])

    if qi_list:
        list_of_projects = [
            {'facility': x.facility_name,
             'subcounty': x.sub_county.sub_counties,
             'county': x.county.county_name,
             'department': x.departments.department,
             } for x in qi_list
        ]
        # convert data from database to a dataframe
        list_of_projects = pd.DataFrame(list_of_projects)
        list_of_projects_fac = list_of_projects.copy()
        list_of_projects_fac['facility'] = list_of_projects_fac['facility'].astype(str).str.split(" ").str[0]

        list_of_projects = pd.concat([list_of_projects_fac, list_of_projects_sub, list_of_projects_county])

        facility_qi_projects = prepare_bar_chart_from_df(list_of_projects_fac, 'facility',
                                                         f"{len(list_of_projects_fac['facility'].unique())} "
                                                         f"Facilities implementing QI initiatives")

        subcounty_qi_projects = prepare_bar_chart_from_df(list_of_projects, 'subcounty',
                                                          f"{len(list_of_projects['subcounty'].unique())} "
                                                          f"Subcounties implementing QI initiatives")

        county_qi_projects = prepare_bar_chart_from_df(list_of_projects, 'county',
                                                       f"{len(list_of_projects['county'].unique())} "
                                                       f"Counties implementing QI initiatives")
        department_qi_projects = prepare_bar_chart_from_df(list_of_projects, 'department',
                                                           "Number of departments implementing specific QI initiatives")
    else:
        facility_qi_projects = {}
        subcounty_qi_projects = {}

    # accessing facility qi projects
    # use two underscore to the field with foreign key
    try:
        testedChange_current = TestedChange.objects.filter(project_id__in=project_id_values).order_by('-achievements')

        # my_filters = TestedChangeFilter(request.GET, queryset=list_of_projects)
        # list_of_projects = my_filters.qs
        list_of_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.project_id,
             'tested of change': x.tested_change,
             'facility': x.project,
             'project': x.project.project_title,
             'department': x.project.departments.department,
             } for x in testedChange_current
        ]

        # convert data from database to a dataframe
        list_of_projects = pd.DataFrame(list_of_projects)
        keys = sorted(list_of_projects['department'].unique())
        values = sorted(list_of_projects['department'].unique())
        testedChange_current = dict(zip(keys, values))
        # keys = list_of_projects['department'].unique()

        dfs = []
        for department in list_of_projects['department'].unique():
            a = list_of_projects[list_of_projects['department'] == department]
            a = a.sort_values("month_year", ascending=False)
            dfs.append(a)

        dicts = {}
        keys = list_of_projects['department'].unique()
        values = dfs
        for i in range(len(keys)):
            dicts[keys[i]] = values[i]

        if list_of_projects.shape[0] != 0:
            dicts = {}
            keys = list_of_projects['project_id'].unique()
            values = list_of_projects['project'].unique()
            for i in range(len(keys)):
                dicts[keys[i]] = values[i]

            lst = []

            for i in list_of_projects['project_id'].unique():
                # get the first rows of the dfs
                a = list_of_projects[list_of_projects['project_id'] == i].sort_values("month_year", ascending=False)
                # append them in a list
                lst.append(a.head(1))

            # concat and sort them by project id
            df_heads = pd.concat(lst).sort_values("achievements", ascending=False)

            all_other_projects_trend = []
            for project in list(df_heads['project_id']):
                # filter dfs based on the order of the best performing projects
                all_other_projects_trend.append(
                    prepare_trends(list_of_projects[list_of_projects['project_id'] == project], project))

            pro_perfomance_trial = dict(zip(keys, all_other_projects_trend))

        else:
            pro_perfomance_trial = {}
    except:
        pro_perfomance_trial = None

    form = QI_ProjectsForm()
    # QI MANAGERS
    qi_managers = Qi_managers.objects.all()

    context = {"form": form,
               "facility_qi_projects": facility_qi_projects,
               "subcounty_qi_projects": subcounty_qi_projects,
               "county_qi_projects": county_qi_projects,
               "department_qi_projects": department_qi_projects,
               "best_performing": best_performing_dic,
               "pro_perfomance_trial": pro_perfomance_trial,
               # "my_filters":my_filters,
               "dicts": dicts,
               "qi_list": qi_list,
               "testedChange_current": testedChange_current,
               "testedChange": testedChange,
               "qi_managers": qi_managers,
               "qi_mans": qi_mans,
               "project_id_values": project_id_values,

               }
    return render(request, "project/dashboard.html", context)


@login_required(login_url='login')
def update_qi_managers(request, pk):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    item = Qi_managers.objects.get(id=pk)
    if request.method == "POST":
        form = Qi_managersForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = Qi_managersForm(instance=item)
    context = {
        "form": form,
        "title": "Update QI manager details",
    }
    return render(request, 'project/update.html', context)


@login_required(login_url='login')
def add_project(request):
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        form = QI_ProjectsConfirmForm(request.POST)
        county_form = QI_Projects_countyForm(request.POST)
        if form.is_valid() and county_form.is_valid():
            # form.save()
            # # do not save first, wait to update foreign key
            post = form.save(commit=False)
            # get clean data from the form
            facility_name = form.cleaned_data['facility_name']

            facility_id = Facilities.objects.get(facilities=facility_name)
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
            # save
            post.save()
            county_form.save()

            # redirect back to the page the user was from after saving the form
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = QI_ProjectsConfirmForm()
        county_form = QI_Projects_countyForm()
    context = {"form": form, "county_form": county_form}
    return render(request, "project/add_project.html", context)


def choose_project_level(request):
    return render(request, "project/choose_project.html")


@login_required(login_url='login')
def add_project_facility(request):
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        form = QI_ProjectsForm(request.POST, prefix='banned')
        if form.is_valid():
            # form.save()
            # # do not save first, wait to update foreign key
            post = form.save(commit=False)
            # get clean data from the form
            facility_name = form.cleaned_data['facility_name']

            facility_id = Facilities.objects.get(facilities=facility_name)
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
                try:
                    if sub_county_list[0] == county.sub_counties_id:
                        post.county = Counties.objects.get(id=county.counties_id)
                except IndexError as e:
                    text = f"""<h1 class="display-5 fw-bold text-primary" >Kindly update sub county for {facility_name}!</h1>"""
                    return HttpResponse(text)

            # save
            post.save()

            # Save many-to-many relationships
            form.save_m2m()
            # redirect back to the page the user was from after saving the form
            # return HttpResponseRedirect(request.session['page_from'])
            return redirect("facilities_landing_page")
    else:
        form = QI_ProjectsForm(prefix='banned')

    context = {"form": form}
    return render(request, "project/add_facility_project.html", context)


@login_required(login_url='login')
def add_qi_manager(request):
    title = "ADD QI MANAGER"
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        form = Qi_managersForm(request.POST, prefix='expected')
        try:
            if form.is_valid():
                form.save()
                return HttpResponseRedirect(request.session['page_from'])
                # form = Qi_managersForm(prefix='expected')
        except IntegrityError as e:
            text = """<h1 class="display-5 fw-bold text-primary" >Email already exist!</h1>"""
            return HttpResponse(text)
    else:
        form = Qi_managersForm(prefix='expected')
    context = {"form": form, "title": title}
    return render(request, "project/add_qi_manager.html", context)


@login_required(login_url='login')
def add_department(request):
    title = "ADD DEPARTMENT"
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        form = DepartmentForm(request.POST)
        try:
            if form.is_valid():
                form.save()
                return HttpResponseRedirect(request.session['page_from'])
                # form = Qi_managersForm(prefix='expected')
        except IntegrityError as e:
            text = """<h1 class="display-5 fw-bold text-primary" >Department already exist!</h1>"""
            return HttpResponse(text)
    else:
        form = DepartmentForm()
    context = {"form": form, "title": title}
    return render(request, "project/add_qi_manager.html", context)


@login_required(login_url='login')
def add_category(request):
    title = "ADD PROJECT CATEGORY"
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        form = CategoryForm(request.POST)
        try:
            if form.is_valid():
                form.save()
                return HttpResponseRedirect(request.session['page_from'])
                # form = Qi_managersForm(prefix='expected')
        except IntegrityError as e:
            text = """<h1 class="display-5 fw-bold text-primary" >Category already exist!</h1>"""
            return HttpResponse(text)
    else:
        form = CategoryForm()
    context = {"form": form, "title": title}
    return render(request, "project/add_qi_manager.html", context)


@login_required(login_url='login')
def add_subcounty(request):
    title = "ADD SUB-COUNTY"
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        form = Sub_countiesForm(request.POST)
        try:
            if form.is_valid():
                form.save()
                return HttpResponseRedirect(request.session['page_from'])
                # form = Qi_managersForm(prefix='expected')
        except IntegrityError as e:
            text = """<h1 class="display-5 fw-bold text-primary" >Sub-county already exist!</h1>"""
            return HttpResponse(text)
    else:
        form = Sub_countiesForm()
    context = {"form": form, "title": title}
    return render(request, "project/add_subcounty.html", context)


def sub_counties_list(request):
    # TODO: add other insights like number of ongoing projects,
    sub_counties = Sub_counties.objects.all().order_by('counties__county_name')
    context = {'sub_counties': sub_counties}
    return render(request, 'project/sub_counties_list.html', context)


def update_fields(request):
    if request.method == "POST":
        form = Sub_countiesForm(request.POST)
        try:
            if form.is_valid():
                form.save()
                return HttpResponseRedirect(request.session['page_from'])
                # form = Qi_managersForm(prefix='expected')
        except IntegrityError as e:
            text = """<h1 class="display-5 fw-bold text-primary" >Sub-county already exist!</h1>"""
            return HttpResponse(text)
    else:
        form = Sub_countiesForm()
    context = {"form": form, "title": "UPDATE SUBCOUNTY"}
    return render(request, 'project/update_project_fields.html', context)


@login_required(login_url='login')
def update_sub_counties(request, pk):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    sub_counties = get_object_or_404(Sub_counties, pk=pk)
    form = Sub_countiesForm(request.POST or None, instance=sub_counties)

    if request.method == 'POST':
        if form.is_valid():
            form.save()

            # Save many-to-many relationships
            form.save_m2m()
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = Sub_countiesForm(instance=sub_counties)
    context = {
        "title": "Update sub counties",
        "form": form
    }

    return render(request, 'project/update.html', context)

@login_required(login_url='login')
def update_hub(request, pk):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    hub = get_object_or_404(Hub, pk=pk)
    form = HubForm(request.POST or None, instance=hub)

    if request.method == 'POST':
        if form.is_valid():
            form.save()

            # Save many-to-many relationships
            form.save_m2m()
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = HubForm(instance=hub)
    context = {
        "title": "Update hub",
        "form": form
    }

    return render(request, 'project/update.html', context)


@login_required(login_url='login')
def add_facility(request):
    title = "ADD FACILITY"
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        form = FacilitiesForm(request.POST)

        try:
            if form.is_valid():
                form.save()
                return HttpResponseRedirect(request.session['page_from'])
                # form = Qi_managersForm(prefix='expected')
        except IntegrityError as e:
            text = """<h1 class="display-5 fw-bold text-primary" >Facility already exist!</h1>"""
            return HttpResponse(text)
    else:
        form = FacilitiesForm()
    context = {"form": form, "title": title}
    return render(request, "project/add_qi_manager.html", context)


def add_hub(request):
    title = "ADD HUB"
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        form = HubForm(request.POST)

        try:
            if form.is_valid():
                form.save()
                return HttpResponseRedirect(request.session['page_from'])
                # form = Qi_managersForm(prefix='expected')
        except IntegrityError as e:
            text = """<h1 class="display-5 fw-bold text-primary" >Facility already exist!</h1>"""
            return HttpResponse(text)
    else:
        form = HubForm()
    context = {"form": form, "title": title}
    return render(request, "project/add_qi_manager.html", context)


@login_required(login_url='login')
def add_county(request):
    title = "ADD COUNTY"
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        form = CountiesForm(request.POST)
        try:
            if form.is_valid():
                form.save()
                return HttpResponseRedirect(request.session['page_from'])
                # form = Qi_managersForm(prefix='expected')
        except IntegrityError as e:
            text = """<h1 class="display-5 fw-bold text-primary" >County already exist!</h1>"""
            return HttpResponse(text)

    else:
        form = CountiesForm()
    context = {"form": form, "title": title}
    return render(request, "project/add_qi_manager.html", context)


@login_required(login_url='login')
def add_resources(request):
    title = "ADD RESOURCES"
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        form = ResourcesForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(request.session['page_from'])
            # form = Qi_managersForm(prefix='expected')
    else:
        form = ResourcesForm()
    context = {"form": form, "title": title}
    return render(request, "project/add_qi_manager.html", context)


@login_required(login_url='login')
def add_project_subcounty(request):
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        form = QI_ProjectsSubcountyForm(request.POST)
        if form.is_valid():
            # form.save()
            # # do not save first, wait to update foreign key
            post = form.save(commit=False)
            # get clean data from the form
            sub_county_name = form.cleaned_data['sub_county']

            sub_county_id = Sub_counties.objects.get(sub_counties=sub_county_name)

            # https://stackoverflow.com/questions/14820579/how-to-query-directly-the-table-created-by-django-for-a-manytomany-relation
            all_counties = Sub_counties.counties.through.objects.all()

            for county in all_counties:
                if sub_county_id.id == county.sub_counties_id:
                    post.county = Counties.objects.get(id=county.counties_id)
            # save
            post.save()
            # redirect back to the page the user was from after saving the form
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = QI_ProjectsSubcountyForm()
    context = {"form": form}
    return render(request, "project/add_subcounty_project.html", context)


@login_required(login_url='login')
def add_project_county(request):
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        form = QI_Projects_countyForm(request.POST)
        if form.is_valid():
            form.save()
            # redirect back to the page the user was from after saving the form
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = QI_Projects_countyForm()
    context = {"form": form}
    return render(request, "project/add_county_project.html", context)


@login_required(login_url='login')
def add_project_hub(request):
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        form = QI_Projects_hubForm(request.POST)
        if form.is_valid():
            form.save()
            # redirect back to the page the user was from after saving the form
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = QI_Projects_hubForm()
    context = {"form": form}
    return render(request, "project/add_hub_project.html", context)


@login_required(login_url='login')
def add_project_program(request):
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        form = QI_Projects_programForm(request.POST)
        if form.is_valid():
            form.save()

            # redirect back to the page the user was from after saving the form
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = QI_Projects_programForm()
    context = {"form": form}
    return render(request, "project/add_program_project.html", context)


@login_required(login_url='login')
def update_project(request, pk):
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    project = QI_Projects.objects.get(id=pk)
    if request.method == "POST":
        form = QI_ProjectsForm(request.POST, request.FILES, instance=project)
        if form.is_valid():
            # form.save()
            # # do not save first, wait to update foreign key
            post = form.save(commit=False)
            # get clean data from the form
            facility_name = form.cleaned_data['facility_name']
            measurement_status = form.cleaned_data['measurement_status']

            facility_id = Facilities.objects.get(facilities=facility_name)
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
            # save
            post.save()

            # Save many-to-many relationships
            form.save_m2m()

            if measurement_status == "Completed or Closed":
                return redirect("lesson_learnt")
            else:
                # redirect back to the page the user was from after saving the form
                return HttpResponseRedirect(request.session['page_from'])
    else:
        form = QI_ProjectsForm(instance=project)
    context = {"form": form}
    return render(request, "project/add_facility_project.html", context)


@login_required(login_url='login')
def deep_dive_facilities(request):
    return render(request, "project/deep_dive_facilities.html")


@login_required(login_url='login')
def archived(request):
    facility_proj_performance = None
    departments_viz = None
    status_viz = None
    pro_perfomance_trial = None
    dicts = None
    dicts = None

    qi_list = QI_Projects.objects.all().order_by('-date_updated')
    num_post = QI_Projects.objects.filter(created_by=request.user).count()
    projects = QI_Projects.objects.count()
    my_filters = QiprojectFilter(request.GET, queryset=qi_list)
    qi_lists = my_filters.qs
    qi_list = pagination_(request, qi_lists)
    # Get a list of tracked qi projects
    tracked_projects = TestedChange.objects.values_list('project_id', flat=True)
    # Get a list of archived qi projects
    archived_projects = ArchiveProject.objects.filter(archive_project=True).values_list('qi_project_id', flat=True)

    # CREATE DF for ARCHIVED PROJECTS
    archived_projects_qs = ArchiveProject.objects.filter(archive_project=True)

    if archived_projects_qs:
        try:
            list_of_projects = [
                {
                    'qi_project': x.qi_project.facility_name.facilities,
                    'qi_project_id': x.qi_project.id,
                    'qi_project_title': x.qi_project.project_title,
                } for x in archived_projects_qs
            ]
            # convert data from database to a dataframe
            list_of_projects_archived = pd.DataFrame(list_of_projects)
        except:
            list_of_projects_archived = pd.DataFrame(columns=['qi_project', 'qi_project_id', 'qi_project_title'])

        project_id_values = list(list_of_projects_archived['qi_project_id'].unique())

        # try:
        testedChange_current = TestedChange.objects.filter(project_id__in=project_id_values).order_by(
            '-achievements')

        # my_filters = TestedChangeFilter(request.GET, queryset=list_of_projects)
        # list_of_projects = my_filters.qs
        list_of_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.project_id,
             'tested of change': x.tested_change,
             'facility': x.project,
             'project': x.project.project_title,
             'department': x.project.departments.department,
             } for x in testedChange_current
        ]

        # convert data from database to a dataframe
        list_of_projects = pd.DataFrame(list_of_projects)

        dfs = []
        for project in list_of_projects['project_id'].unique():
            a = list_of_projects[list_of_projects['project_id'] == project]
            a = a.sort_values("project_id", ascending=False)
            dfs.append(a)

        if list_of_projects.shape[0] != 0:
            dicts = {}
            keys = list_of_projects['project_id'].unique()
            values = dfs
            for i in range(len(keys)):
                dicts[keys[i]] = values[i]

            lst = []
            for i in list_of_projects['project_id'].unique():
                # get the first rows of the dfs
                a = list_of_projects[list_of_projects['project_id'] == i].sort_values("month_year", ascending=False)
                # append them in a list
                lst.append(a.head(1))

            # concat and sort them by project id
            df_heads = pd.concat(lst).sort_values("achievements", ascending=False)

            all_other_projects_trend = []
            keys = []
            for project in list(df_heads['project_id']):
                keys.append(project)
                # filter dfs based on the order of the best performing projects
                all_other_projects_trend.append(
                    prepare_trends(list_of_projects[list_of_projects['project_id'] == project]))

            dicts = {}
            for i in range(len(keys)):
                dicts[keys[i]] = all_other_projects_trend[i]

            a = list_of_projects[list_of_projects['project_id'] == 4]
            a = prepare_trends(a)
            pro_perfomance_trial = dict(zip(keys, all_other_projects_trend))

        else:
            pro_perfomance_trial = {}

    context = {"qi_list": qi_list, "num_post": num_post, "projects": projects,
               "my_filters": my_filters, "qi_lists": qi_lists,
               # "facility_proj_performance": facility_proj_performance,
               # "departments_viz": departments_viz,
               # "status_viz": status_viz,
               "tracked_projects": tracked_projects,
               "archived_projects": archived_projects,
               "pro_perfomance_trial": pro_perfomance_trial,
               # "a": a,
               "dicts": dicts,
               }
    return render(request, "project/archived.html", context)
    # return render(request, "project/closed_trial.html", context)


def pair_iterable_for_delta_changes(iterable):
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


@login_required(login_url='login')
def facilities_landing_page(request):
    facility_proj_performance = None
    departments_viz = None
    status_viz = None

    qi_list = QI_Projects.objects.all().order_by('-date_updated')
    num_post = QI_Projects.objects.filter(created_by=request.user).count()
    projects = QI_Projects.objects.count()
    my_filters = QiprojectFilter(request.GET, queryset=qi_list)
    qi_lists = my_filters.qs
    qi_list = pagination_(request, qi_lists)

    if qi_lists:
        list_of_projects = [
            {'measurement_frequency': x.measurement_frequency,
             } for x in qi_lists
        ]
        # convert data from database to a dataframe
        list_of_projects = pd.DataFrame(list_of_projects)

        facility_proj_performance = prepare_bar_chart_from_df(list_of_projects, 'measurement_frequency',
                                                              "QI Measurement frequency", projects)

        list_of_departments = [
            {'department': x.departments.department,
             } for x in qi_lists
        ]
        list_of_departments = pd.DataFrame(list_of_departments)
        departments_viz = prepare_bar_chart_from_df(list_of_departments, "department", "QI per department", projects)

        list_of_departments = [
            {'status': x.measurement_status,
             } for x in qi_lists
        ]
        list_of_departments = pd.DataFrame(list_of_departments)
        status_viz = prepare_bar_chart_from_df(list_of_departments, "status", "QI projects status", projects)

    tracked_projects = TestedChange.objects.values_list('project_id', flat=True)
    # Get a list of archived qi projects
    archived_projects = ArchiveProject.objects.filter(archive_project=True).values_list('qi_project_id', flat=True)

    # # Get the change history for the QI_Projects model
    # history = QI_Projects.history.all()
    # changes = []
    # # Loop through the history and compare the differences between each record and the previous one
    # for i, record in enumerate(history):
    #     if i > 0:
    #         prev_record = history[i - 1]
    #         delta = record.diff_against(prev_record)
    #         for change in delta.changes:
    #             # Add the change data to the changes list
    #             changes.append({
    #                 'field': change.field,
    #                 'old': change.old,
    #                 'new': change.new,
    #                 'date': record.history_date,
    #                 'user': record.history_user,
    #             })
    # Pass the changes data to the template as context
    context = {"qi_list": qi_list, "num_post": num_post, "projects": projects,
               "my_filters": my_filters, "qi_lists": qi_lists,
               "facility_proj_performance": facility_proj_performance,
               "departments_viz": departments_viz,
               "status_viz": status_viz,
               "tracked_projects": tracked_projects,
               "archived_projects": archived_projects,
               }
    return render(request, "project/facility_landing_page.html", context)


@login_required(login_url='login')
def facility_project(request, pk):
    projects = QI_Projects.objects.filter(facility_name__facilities=pk).order_by("-date_updated")

    facility_name = pk

    # qi_list = QI_Projects.objects.all().order_by('-date_updated')
    # num_post = QI_Projects.objects.filter(created_by=request.user).count()
    # if request.method=="POST":
    #     search=request.POST['searched']
    #     search=QI_Projects.objects.filter(facility__contains=search)
    #     projects = None
    #     context = {"qi_list": qi_list, "num_post": num_post,"projects":projects,
    #                "search":search
    #                }
    #     return render(request, "project/facility_landing_page.html", context)
    # else:
    #     projects = QI_Projects.objects.count()

    #     context = {"qi_list": qi_list, "num_post": num_post, "projects": projects,
    #
    #                }
    #     return render(request, "project/facility_landing_page.html", context)
    # projects = QI_Projects.objects.count()
    # my_filters = QiprojectFilter(request.GET,queryset=qi_list)
    # qi_list=my_filters.qs
    tracked_projects = TestedChange.objects.values_list('project_id', flat=True)
    context = {"projects": projects,
               "facility_name": facility_name,
               "title": "Ongoing",
               "tracked_projects": tracked_projects,
               }
    return render(request, "project/facility_projects.html", context)


@login_required(login_url='login')
def department_project(request, pk):
    projects = QI_Projects.objects.filter(departments__department=pk)

    facility_name = pk

    # qi_list = QI_Projects.objects.all().order_by('-date_updated')
    # num_post = QI_Projects.objects.filter(created_by=request.user).count()
    # if request.method=="POST":
    #     search=request.POST['searched']
    #     search=QI_Projects.objects.filter(facility__contains=search)
    #     projects = None
    #     context = {"qi_list": qi_list, "num_post": num_post,"projects":projects,
    #                "search":search
    #                }
    #     return render(request, "project/facility_landing_page.html", context)
    # else:
    #     projects = QI_Projects.objects.count()

    #     context = {"qi_list": qi_list, "num_post": num_post, "projects": projects,
    #
    #                }
    #     return render(request, "project/facility_landing_page.html", context)
    # projects = QI_Projects.objects.count()
    # my_filters = QiprojectFilter(request.GET,queryset=qi_list)
    # qi_list=my_filters.qs
    tracked_projects = TestedChange.objects.values_list('project_id', flat=True)
    context = {"projects": projects,
               "facility_name": facility_name,
               "title": "Ongoing",
               "tracked_projects": tracked_projects,
               }
    return render(request, "project/department_projects.html", context)


@login_required(login_url='login')
def department_filter_project(request, pk):
    projects_tracked = []
    projects = QI_Projects.objects.filter(departments__department=pk)
    # project_id_values = request.session['project_id_values']

    # accessing facility qi projects
    # use two underscore to the field with foreign key
    # list_of_projects = TestedChange.objects.filter(project_id__in=project_id_values).order_by('-achievements')
    testedChange = TestedChange.objects.all()
    # my_filters = TestedChangeFilter(request.GET, queryset=list_of_projects)
    # list_of_projects = my_filters.qs
    list_of_projects = [
        {'achievements': x.achievements,
         'month_year': x.month_year,
         'project_id': x.project_id,
         'tested of change': x.tested_change,

         'facility': x.project.facility_name,
         'project': x.project.project_title,
         'department': x.project.departments.department,
         } for x in testedChange
    ]

    pro_perfomance_trial = prepare_viz(list_of_projects, pk, "department")

    facility_name = pk

    # convert data from database to a dataframe
    list_of_projects = pd.DataFrame(list_of_projects)
    keys = list_of_projects['project_id'].unique()
    projects_tracked = keys

    # difference
    number_of_projects_created = projects.count()
    number_of_projects_with_test_of_change = len(pro_perfomance_trial)
    difference = number_of_projects_created - number_of_projects_with_test_of_change

    context = {"projects": projects,
               "facility_name": facility_name,
               "title": "Ongoing",
               "pro_perfomance_trial": pro_perfomance_trial,
               "difference": difference,
               "projects_tracked": projects_tracked,

               }
    return render(request, "project/department_filter_projects.html", context)


@login_required(login_url='login')
def qi_managers_filter_project(request, pk):
    pro_perfomance_trial = {}
    manager_name = []
    projects_tracked = []

    projects = QI_Projects.objects.filter(qi_manager__id=pk)
    if projects:
        list_of_projects = [
            {
                'qi_manager_email': x.qi_manager.email,
            } for x in projects
        ]
        list_of_projects_ = pd.DataFrame(list_of_projects)

    # project_id_values = request.session['project_id_values']

    # accessing facility qi projects
    # use two underscore to the field with foreign key
    # list_of_projects = TestedChange.objects.filter(project_id__in=project_id_values).order_by('-achievements')
    # testedChange = TestedChange.objects.all()
    testedChange = TestedChange.objects.filter(project__qi_manager__id=pk)
    # my_filters = TestedChangeFilter(request.GET, queryset=list_of_projects)
    # list_of_projects = my_filters.qs

    if testedChange:
        list_of_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.project_id,
             'tested of change': x.tested_change,

             'facility': x.project.facility_name,
             'project': x.project.project_title,
             'qi_manager': x.project.qi_manager.first_name,
             'qi_manager_email': x.project.qi_manager.email,
             } for x in testedChange
        ]
        list_of_projects_ = pd.DataFrame(list_of_projects)
        keys = list_of_projects_['project_id'].unique()
        projects_tracked = keys

        manager_name = list(list_of_projects_['qi_manager'].unique())[0]

        pro_perfomance_trial = prepare_viz(list_of_projects, manager_name, "qi_manager")
    else:
        manager = Qi_managers.objects.filter(id=pk)
        if manager:
            list_of_projects = [
                {
                    'qi_manager': x.first_name,
                } for x in manager
            ]
            list_of_projects_ = pd.DataFrame(list_of_projects)
            manager_name = list(list_of_projects_['qi_manager'].unique())[0]

    # difference
    number_of_projects_created = projects.count()
    number_of_projects_with_test_of_change = len(pro_perfomance_trial)
    difference = number_of_projects_created - number_of_projects_with_test_of_change

    context = {"projects": projects,
               "facility_name": manager_name,
               "title": "",
               "pro_perfomance_trial": pro_perfomance_trial,
               "difference": difference,
               "projects_tracked": projects_tracked,

               }
    return render(request, "project/department_filter_projects.html", context)


@login_required(login_url='login')
def facility_filter_project(request, pk):
    projects_tracked = []
    projects = QI_Projects.objects.filter(facility_name__facilities=pk).order_by("-date_updated")
    # project_id_values = request.session['project_id_values']

    # accessing facility qi projects
    # use two underscore to the field with foreign key
    # list_of_projects = TestedChange.objects.filter(project_id__in=project_id_values).order_by('-achievements')
    testedChange = TestedChange.objects.filter(project__facility_name__facilities=pk)
    # my_filters = TestedChangeFilter(request.GET, queryset=list_of_projects)
    # list_of_projects = my_filters.qs
    list_of_projects = [
        {'achievements': x.achievements,
         'month_year': x.month_year,
         'project_id': x.project_id,
         'tested of change': x.tested_change,

         'facility': x.project.facility_name,
         'project': x.project.project_title,
         'department': x.project.departments.department,
         } for x in testedChange
    ]

    # convert data from database to a dataframe
    list_of_projects = pd.DataFrame(list_of_projects)

    # list_of_projects = list_of_projects[list_of_projects['facility'] == f"{pk}"].sort_values("achievements")

    # keys = list_of_projects['department'].unique()

    dfs = []
    for department in list_of_projects['department'].unique():
        a = list_of_projects[list_of_projects['department'] == department]
        a = a.sort_values("month_year", ascending=False)
        dfs.append(a)

    dicts = {}
    keys = list_of_projects['department'].unique()
    values = dfs
    for i in range(len(keys)):
        dicts[keys[i]] = values[i]

    if list_of_projects.shape[0] != 0:
        dicts = {}
        keys = list_of_projects['project_id'].unique()
        projects_tracked = keys
        values = list_of_projects['project'].unique()
        for i in range(len(keys)):
            dicts[keys[i]] = values[i]

        lst = []
        for i in list_of_projects['project_id'].unique():
            # get the first rows of the dfs
            a = list_of_projects[list_of_projects['project_id'] == i].sort_values("month_year", ascending=False)
            # append them in a list
            lst.append(a.head(1))

        # concat and sort them by project id
        df_heads = pd.concat(lst).sort_values("achievements", ascending=False)
        all_other_projects_trend = []
        keys = []
        for project in list(df_heads['project_id']):
            keys.append(project)
            # filter dfs based on the order of the best performing projects
            if isinstance(project, str):
                all_other_projects_trend.append(
                    prepare_trends(list_of_projects[list_of_projects['project_id'] == project], project))
            else:
                all_other_projects_trend.append(
                    prepare_trends(list_of_projects[list_of_projects['project_id'] == project]))

        pro_perfomance_trial = dict(zip(keys, all_other_projects_trend))
    else:
        pro_perfomance_trial = {}

    facility_name = pk

    # difference
    number_of_projects_created = projects.count()
    number_of_projects_with_test_of_change = len(pro_perfomance_trial)
    difference = number_of_projects_created - number_of_projects_with_test_of_change

    context = {"projects": projects,
               "facility_name": facility_name,
               "title": "Ongoing",
               "pro_perfomance_trial": pro_perfomance_trial,
               "difference": difference,
               "projects_tracked": projects_tracked,

               }
    return render(request, "project/department_filter_projects.html", context)


@login_required(login_url='login')
def qicreator_filter_project(request, pk):
    pro_perfomance_trial = {}
    projects_tracked = []
    # projects = QI_Projects.objects.filter(facility=pk).order_by("-date_updated")
    pk = str(pk).lower()
    projects = QI_Projects.objects.filter(created_by__username=pk)
    # project_id_values = request.session['project_id_values']

    # accessing facility qi projects
    # use two underscore to the field with foreign key
    # list_of_projects = TestedChange.objects.filter(project_id__in=project_id_values).order_by('-achievements')
    testedChange = TestedChange.objects.filter(project__created_by__username=pk)
    # my_filters = TestedChangeFilter(request.GET, queryset=list_of_projects)
    # list_of_projects = my_filters.qs
    if testedChange:
        list_of_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.project_id,
             'tested of change': x.tested_change,

             'facility': x.project.facility_name,
             'project': x.project.project_title,
             'department': x.project.departments.department,
             } for x in testedChange
        ]

        # convert data from database to a dataframe
        list_of_projects = pd.DataFrame(list_of_projects)

        # list_of_projects = list_of_projects[list_of_projects['facility'] == f"{pk}"].sort_values("achievements")

        # keys = list_of_projects['department'].unique()

        dfs = []
        for department in list_of_projects['department'].unique():
            a = list_of_projects[list_of_projects['department'] == department]
            a = a.sort_values("month_year", ascending=False)
            dfs.append(a)

        dicts = {}
        keys = list_of_projects['department'].unique()
        values = dfs
        for i in range(len(keys)):
            dicts[keys[i]] = values[i]

        if list_of_projects.shape[0] != 0:
            dicts = {}
            keys = list_of_projects['project_id'].unique()
            projects_tracked = keys

            values = list_of_projects['project'].unique()
            for i in range(len(keys)):
                dicts[keys[i]] = values[i]

            lst = []
            for i in list_of_projects['project_id'].unique():
                # get the first rows of the dfs
                a = list_of_projects[list_of_projects['project_id'] == i].sort_values("month_year", ascending=False)
                # append them in a list
                lst.append(a.head(1))

            # concat and sort them by project id
            df_heads = pd.concat(lst).sort_values("achievements", ascending=False)

            all_other_projects_trend = []
            for project in list(df_heads['project_id']):
                # filter dfs based on the order of the best performing projects
                all_other_projects_trend.append(
                    prepare_trends(list_of_projects[list_of_projects['project_id'] == project], project))

            pro_perfomance_trial = dict(zip(keys, all_other_projects_trend))
        else:
            pro_perfomance_trial = {}
        # pro_perfomance_trial = prepare_viz(list_of_projects, pk,col)

    facility_name = pk

    # difference
    number_of_projects_created = projects.count()
    number_of_projects_with_test_of_change = len(pro_perfomance_trial)
    difference = number_of_projects_created - number_of_projects_with_test_of_change

    context = {"projects": projects,
               "facility_name": facility_name,
               "title": "Ongoing",
               "pro_perfomance_trial": pro_perfomance_trial,
               "difference": difference,
               "projects_tracked": projects_tracked,

               }
    return render(request, "project/department_filter_projects.html", context)


@login_required(login_url='login')
def county_filter_project(request, pk):
    projects_tracked = []
    # projects = QI_Projects.objects.filter(facility=pk).order_by("-date_updated")
    projects = QI_Projects.objects.filter(county__county_name=pk)
    # project_id_values = request.session['project_id_values']

    # accessing facility qi projects
    # use two underscore to the field with foreign key
    # list_of_projects = TestedChange.objects.filter(project_id__in=project_id_values).order_by('-achievements')
    testedChange = TestedChange.objects.filter(project__county__county_name=pk)
    # my_filters = TestedChangeFilter(request.GET, queryset=list_of_projects)
    # list_of_projects = my_filters.qs
    list_of_projects = [
        {'achievements': x.achievements,
         'month_year': x.month_year,
         'project_id': x.project_id,
         'tested of change': x.tested_change,

         'facility': x.project.facility_name,
         'project': x.project.project_title,
         'department': x.project.county.county_name,
         } for x in testedChange
    ]

    # convert data from database to a dataframe
    list_of_projects = pd.DataFrame(list_of_projects)

    # list_of_projects = list_of_projects[list_of_projects['facility'] == f"{pk}"].sort_values("achievements")

    # keys = list_of_projects['department'].unique()

    dfs = []
    for department in list_of_projects['department'].unique():
        a = list_of_projects[list_of_projects['department'] == department]
        a = a.sort_values("month_year", ascending=False)
        dfs.append(a)

    dicts = {}
    keys = list_of_projects['department'].unique()
    values = dfs
    for i in range(len(keys)):
        dicts[keys[i]] = values[i]

    if list_of_projects.shape[0] != 0:
        dicts = {}
        keys = list_of_projects['project_id'].unique()
        projects_tracked = keys
        values = list_of_projects['project'].unique()
        for i in range(len(keys)):
            dicts[keys[i]] = values[i]

        lst = []
        for i in list_of_projects['project_id'].unique():
            # get the first rows of the dfs
            a = list_of_projects[list_of_projects['project_id'] == i].sort_values("month_year", ascending=False)
            # append them in a list
            lst.append(a.head(1))

        # concat and sort them by project id
        df_heads = pd.concat(lst).sort_values("achievements", ascending=False)

        all_other_projects_trend = []
        keys = []
        for project in list(df_heads['project_id']):
            keys.append(project)
            # filter dfs based on the order of the best performing projects
            if isinstance(project, str):
                all_other_projects_trend.append(
                    prepare_trends(list_of_projects[list_of_projects['project_id'] == project], project))
            else:
                all_other_projects_trend.append(
                    prepare_trends(list_of_projects[list_of_projects['project_id'] == project]))

        pro_perfomance_trial = dict(zip(keys, all_other_projects_trend))
    else:
        pro_perfomance_trial = {}
    # pro_perfomance_trial = prepare_viz(list_of_projects, pk,col)

    facility_name = pk

    # difference
    number_of_projects_created = projects.count()
    number_of_projects_with_test_of_change = len(pro_perfomance_trial)
    difference = number_of_projects_created - number_of_projects_with_test_of_change

    context = {"projects": projects,
               "facility_name": facility_name,
               "title": "Ongoing",
               "pro_perfomance_trial": pro_perfomance_trial,
               "difference": difference,
               "projects_tracked": projects_tracked,

               }
    return render(request, "project/department_filter_projects.html", context)


@login_required(login_url='login')
def sub_county_filter_project(request, pk):
    projects_tracked = []
    # projects = QI_Projects.objects.filter(facility=pk).order_by("-date_updated")
    projects = QI_Projects.objects.filter(sub_county__sub_counties=pk)
    # project_id_values = request.session['project_id_values']

    # accessing facility qi projects
    # use two underscore to the field with foreign key
    # list_of_projects = TestedChange.objects.filter(project_id__in=project_id_values).order_by('-achievements')
    testedChange = TestedChange.objects.filter(project__sub_county__sub_counties=pk)
    # my_filters = TestedChangeFilter(request.GET, queryset=list_of_projects)
    # list_of_projects = my_filters.qs
    list_of_projects = [
        {'achievements': x.achievements,
         'month_year': x.month_year,
         'project_id': x.project_id,
         'tested of change': x.tested_change,

         'facility': x.project.facility_name,
         'project': x.project.project_title,
         'department': x.project.county.county_name,
         } for x in testedChange
    ]

    # convert data from database to a dataframe
    list_of_projects = pd.DataFrame(list_of_projects)

    # list_of_projects = list_of_projects[list_of_projects['facility'] == f"{pk}"].sort_values("achievements")

    # keys = list_of_projects['department'].unique()

    dfs = []
    for department in list_of_projects['department'].unique():
        a = list_of_projects[list_of_projects['department'] == department]
        a = a.sort_values("month_year", ascending=False)
        dfs.append(a)

    dicts = {}
    keys = list_of_projects['department'].unique()
    values = dfs
    for i in range(len(keys)):
        dicts[keys[i]] = values[i]

    if list_of_projects.shape[0] != 0:
        dicts = {}
        keys = list_of_projects['project_id'].unique()
        projects_tracked = keys

        values = list_of_projects['project'].unique()
        for i in range(len(keys)):
            dicts[keys[i]] = values[i]

        lst = []
        for i in list_of_projects['project_id'].unique():
            # get the first rows of the dfs
            a = list_of_projects[list_of_projects['project_id'] == i].sort_values("month_year", ascending=False)
            # append them in a list
            lst.append(a.head(1))

        # concat and sort them by project id
        df_heads = pd.concat(lst).sort_values("achievements", ascending=False)

        all_other_projects_trend = []
        keys = []
        for project in list(df_heads['project_id']):
            keys.append(project)
            # filter dfs based on the order of the best performing projects
            if isinstance(project, str):
                all_other_projects_trend.append(
                    prepare_trends(list_of_projects[list_of_projects['project_id'] == project], project))
            else:
                all_other_projects_trend.append(
                    prepare_trends(list_of_projects[list_of_projects['project_id'] == project]))

        pro_perfomance_trial = dict(zip(keys, all_other_projects_trend))
    else:
        pro_perfomance_trial = {}
    # pro_perfomance_trial = prepare_viz(list_of_projects, pk,col)

    facility_name = pk
    # difference
    number_of_projects_created = projects.count()
    number_of_projects_with_test_of_change = len(pro_perfomance_trial)
    difference = number_of_projects_created - number_of_projects_with_test_of_change

    context = {"projects": projects,
               "facility_name": facility_name,
               "title": "Ongoing",
               "pro_perfomance_trial": pro_perfomance_trial,
               "difference": difference,
               "projects_tracked": projects_tracked,

               }
    return render(request, "project/department_filter_projects.html", context)


@login_required(login_url='login')
def canceled_projects(request, pk):
    projects = QI_Projects.objects.filter(measurement_status=pk)
    facility_name = pk
    context = {"projects": projects,
               "facility_name": facility_name,
               "title": "Canceled"
               }
    return render(request, "project/department_projects.html", context)


@login_required(login_url='login')
def not_started(request, pk):
    projects = QI_Projects.objects.filter(measurement_status=pk)
    facility_name = pk
    context = {"projects": projects,
               "facility_name": facility_name,
               "title": "Not started"
               }
    return render(request, "project/department_projects.html", context)


def postponed(request, pk):
    projects = QI_Projects.objects.filter(measurement_status=pk)
    facility_name = pk

    # qi_list = QI_Projects.objects.all().order_by('-date_updated')
    # num_post = QI_Projects.objects.filter(created_by=request.user).count()
    # if request.method=="POST":
    #     search=request.POST['searched']
    #     search=QI_Projects.objects.filter(facility__contains=search)
    #     projects = None
    #     context = {"qi_list": qi_list, "num_post": num_post,"projects":projects,
    #                "search":search
    #                }
    #     return render(request, "project/facility_landing_page.html", context)
    # else:
    #     projects = QI_Projects.objects.count()

    #     context = {"qi_list": qi_list, "num_post": num_post, "projects": projects,
    #
    #                }
    #     return render(request, "project/facility_landing_page.html", context)
    # projects = QI_Projects.objects.count()
    # my_filters = QiprojectFilter(request.GET,queryset=qi_list)
    # qi_list=my_filters.qs
    context = {"projects": projects,
               "facility_name": facility_name,
               "title": "Postponed"
               }
    return render(request, "project/department_projects.html", context)


@login_required(login_url='login')
def qi_creator(request, pk):
    projects = QI_Projects.objects.filter(created_by__username=pk)

    facility_name = pk
    tracked_projects = TestedChange.objects.values_list('project_id', flat=True)
    context = {"projects": projects,
               "facility_name": facility_name,
               "tracked_projects": tracked_projects
               }
    return render(request, "project/qi_creators.html", context)


@login_required(login_url='login')
def qi_managers_projects(request, pk):
    projects = QI_Projects.objects.filter(qi_manager__id=pk)
    facility_name = [i.qi_manager for i in projects]
    tracked_projects = TestedChange.objects.values_list('project_id', flat=True)

    context = {"projects": projects,
               "facility_name": facility_name[0],
               "tracked_projects": tracked_projects,
               }
    return render(request, "project/qi_creators.html", context)


@login_required(login_url='login')
def completed_closed(request, pk):
    projects = QI_Projects.objects.filter(measurement_status=pk)
    facility_name = pk
    context = {"projects": projects,
               "facility_name": facility_name,
               "title": "Completed or Closed",
               }
    return render(request, "project/department_projects.html", context)


@login_required(login_url='login')
def lesson_learnt(request):
    """
    This view handles the display of all the lesson_learnt and their related qi_project information.
    It uses the Lesson_learned model to retrieve all the lesson_learnt and annotates the queryset
    to include the number of qi_team_members for each lesson_learnt using the Count() method.
    The annotated queryset is then passed to the template as the context variable 'lesson_learnt'.
    The template then renders this information in a table format displaying the project title and number of QI team
    members per qi_project.

    The annotate() method is then used to add an additional field to the queryset, called num_members.

    The Count() function is used to count the number of related qi_team_members for each lesson_learnt. The argument
    passed to the Count function is the related field name "project_name__qi_team_members" that is used to count the
    number of related qi_team_members for each lesson_learnt.
    """
    # lesson_learnt = Lesson_learned.objects.all().order_by('-date_created')
    # projects = lesson_learnt.select_related('project_name')

    # Retrieve all the lesson_learnt from the Lesson_learned model and Create context variable 'lesson_learnt' with the
    # annotated queryset
    lesson_learnt = Lesson_learned.objects.annotate(num_members=Count('project_name__qi_team_members'))

    # facility_name = pk
    context = {"lesson_learnt": lesson_learnt,
               # "projects": projects,
               # "lesson_learnt":lesson_learnt,

               }
    return render(request, "project/lesson_learnt.html", context)


@login_required(login_url='login')
def add_lesson_learnt(request, pk):
    project = QI_Projects.objects.get(id=pk)
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        form = Lesson_learnedForm(request.POST)
        if form.is_valid():
            # form.save()
            post = form.save(commit=False)
            post.project_name = project
            post.created_by = request.user
            post.save()
            messages.success(request, f"Lesson learnt for {post.project_name} added successfully.")
            # redirect back to the page the user was from after saving the form
            # return HttpResponseRedirect(request.session['page_from'])
            return redirect("lesson_learnt")
    else:
        form = Lesson_learnedForm()
    context = {"form": form,
               "qi_project": project,
               "title": "ADD",
               }

    return render(request, "project/add_lesson_learnt.html", context)


@login_required(login_url='login')
def update_lesson_learnt(request, pk):
    lesson_learnt = Lesson_learned.objects.get(id=pk)
    project = QI_Projects.objects.get(id=lesson_learnt.project_name_id)
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        form = Lesson_learnedForm(request.POST, instance=lesson_learnt)
        if form.is_valid():
            form.save()
            # post = form.save(commit=False)
            # post.project_name = project
            # post.created_by = request.user
            # post.save()
            # messages.success(request, f"Lesson learnt for {post.project_name} added successfully.")
            # redirect back to the page the user was from after saving the form
            # return HttpResponseRedirect(request.session['page_from'])
            return redirect("lesson_learnt")
    else:
        form = Lesson_learnedForm(instance=lesson_learnt)
    context = {"form": form,
               "qi_project": project,
               "title": "UPDATE",
               }

    return render(request, "project/add_lesson_learnt.html", context)


@login_required(login_url='login')
def delete_lesson_learnt(request, pk):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    item = Lesson_learned.objects.get(id=pk)
    if request.method == "POST":
        item.delete()

        return HttpResponseRedirect(request.session['page_from'])
    context = {
        "test_of_changes": item
    }
    return render(request, 'project/delete_test_of_change.html', context)


@login_required(login_url='login')
def ongoing(request, pk):
    projects = QI_Projects.objects.filter(measurement_status=pk)

    facility_name = pk
    context = {"projects": projects,
               "facility_name": facility_name,
               "title": "Started or Ongoing",
               }
    return render(request, "project/department_projects.html", context)


@login_required(login_url='login')
def measurement_frequency(request, pk):
    projects = QI_Projects.objects.filter(measurement_frequency=pk)

    facility_name = pk

    # qi_list = QI_Projects.objects.all().order_by('-date_updated')
    # num_post = QI_Projects.objects.filter(created_by=request.user).count()
    # if request.method=="POST":
    #     search=request.POST['searched']
    #     search=QI_Projects.objects.filter(facility__contains=search)
    #     projects = None
    #     context = {"qi_list": qi_list, "num_post": num_post,"projects":projects,
    #                "search":search
    #                }
    #     return render(request, "project/facility_landing_page.html", context)
    # else:
    #     projects = QI_Projects.objects.count()

    #     context = {"qi_list": qi_list, "num_post": num_post, "projects": projects,
    #
    #                }
    #     return render(request, "project/facility_landing_page.html", context)
    # projects = QI_Projects.objects.count()
    # my_filters = QiprojectFilter(request.GET,queryset=qi_list)
    # qi_list=my_filters.qs
    tracked_projects = TestedChange.objects.values_list('project_id', flat=True)
    context = {"projects": projects,
               "facility_name": facility_name,
               "tracked_projects": tracked_projects,
               # "title": "Completed or Closed",
               }
    return render(request, "project/department_projects.html", context)


@login_required(login_url='login')
def toggle_archive_project(request, project_id):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    try:
        # Get the QI_Projects object from the given qi_project_id
        qi_project = QI_Projects.objects.get(id=project_id)

        # Get the ArchiveProject object associated with the given qi_project
        archive_project = ArchiveProject.objects.get(qi_project=qi_project)

        # Toggle the booleanfield archive_project
        if archive_project.archive_project:
            archive_project.archive_project = False
        else:
            archive_project.archive_project = True

        # Save the changes
        archive_project.save()
    except:
        # create if not in the database
        form = ArchiveProjectForm(request.POST, request.FILES)
        if form.is_valid():
            # do not save first, wait to update foreign key
            post = form.save(commit=False)
            # get project primary key
            post.qi_project = QI_Projects.objects.get(id=project_id)
            # Archive the project
            post.archive_project = True
            # save
            post.save()

    return HttpResponseRedirect(request.session['page_from'])


@login_required(login_url='login')
def tested_change(request, pk):
    qi_project = QI_Projects.objects.get(id=pk)
    facility = qi_project.facility_name
    subcounty = qi_project.sub_county
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    if request.method == "POST":
        form = TestedChangeForm(request.POST)
        if form.is_valid():
            # do not save first, wait to update foreign key
            post = form.save(commit=False)
            # get project primary key
            post.project = QI_Projects.objects.get(id=pk)
            # save
            post.save()
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = TestedChangeForm(instance=request.user)
    context = {
        "form": form,
        "qi_project": qi_project,
    }
    return render(request, 'project/add_tested_change.html', context)


@login_required(login_url='login')
def update_test_of_change(request, pk):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    item = TestedChange.objects.get(id=pk)
    if request.method == "POST":
        form = TestedChangeForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = TestedChangeForm(instance=item)
    context = {
        "form": form,
        "title": "Update test of change",
    }
    # return render(request, 'project/update_test_of_change.html', context)
    return render(request, 'project/add_qi_manager.html', context)


@login_required(login_url='login')
def delete_test_of_change(request, pk):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    item = TestedChange.objects.get(id=pk)
    if request.method == "POST":
        item.delete()

        return HttpResponseRedirect(request.session['page_from'])
    context = {
        "test_of_changes": item
    }
    return render(request, 'project/delete_test_of_change.html', context)


@login_required(login_url='login')
def delete_response(request, pk):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    item = ProjectResponses.objects.get(id=pk)
    if request.method == "POST":
        item.delete()

        return HttpResponseRedirect(request.session['page_from'])
    context = {
        "test_of_changes": item
    }
    return render(request, 'project/delete_test_of_change.html', context)


@login_required(login_url='login')
def delete_resource(request, pk):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    item = Resources.objects.get(id=pk)
    if request.method == "POST":
        item.delete()

        return HttpResponseRedirect(request.session['page_from'])
    context = {
        "test_of_changes": item
    }
    return render(request, 'project/delete_test_of_change.html', context)


@login_required(login_url='login')
def update_profile(request):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    # item = NewUser.objects.get(id=pk)
    if request.method == "POST":
        form = UpdateUserForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = UpdateUserForm(instance=request.user)
    context = {
        "form": form
    }
    return render(request, 'account/update_profile.html', context)


@login_required(login_url='login')
def deep_dive_chmt(request):
    return render(request, "project/deep_dive_chmt.html")
    # return render(request, "project/calendar.html")


@login_required(login_url='login')
def add_qi_team_member(request, pk):
    facility_project = QI_Projects.objects.get(id=pk)
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        form = Qi_team_membersForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.facility = Facilities.objects.get(id=facility_project.facility_name_id)
            post.qi_project = facility_project
            post.created_by = request.user
            post.save()
            # redirect back to the page the user was from after saving the form
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = Qi_team_membersForm()
    context = {"form": form,
               "title": "add qi team member",
               "qi_project": facility_project,
               }
    return render(request, "project/add_qi_teams.html", context)


@login_required(login_url='login')
def delete_qi_team_member(request, pk):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    item = Qi_team_members.objects.get(id=pk)
    if request.method == "POST":
        item.delete()

        return HttpResponseRedirect(request.session['page_from'])
    context = {
        "test_of_changes": item
    }
    return render(request, 'project/delete_test_of_change.html', context)


@login_required(login_url='login')
def update_qi_team_member(request, pk):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    item = Qi_team_members.objects.get(id=pk)
    qi_project = QI_Projects.objects.get(id=item.qi_project_id)
    if request.method == "POST":
        form = Qi_team_membersForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = Qi_team_membersForm(instance=item)
    context = {
        "form": form,
        "title": "update details of a qi team member",
        "qi_project": qi_project,
    }
    return render(request, 'project/add_qi_teams.html', context)


@login_required(login_url='login')
def qi_team_members(request):
    # # User = get_user_model()
    # # team = User.objects.all()
    # context = {"team": team}

    qi_teams = Qi_team_members.objects.all()

    # qi_managers_list = Qi_managers.objects.all()
    projects = QI_Projects.objects.all()
    #
    if projects:
        # Get df for QI team members with QI projects
        list_of_projects = [
            {
                # {'project_ids': x.id,
                'First name': x.created_by.first_name,
                'Last name': x.created_by.last_name,
                'Email': x.created_by.email,
                'Phone Number': x.created_by.phone_number,
                'User_id': x.created_by.id,
                'QI project id': x.id,
                'Date created': x.created_by.date_joined,
                'Facility': x.facility_name,
                'created_by': x.created_by_id,
                # TODO : INCLUDE CREATED BY COLUMN SO THAT USER ON QI TEAM MEMBER TABLE CAN ONLY DELETE MEMBER
                #  THEY CREATED
            } for x in projects
        ]
        qi_team_members_with_projects = pd.DataFrame(list_of_projects)
        qi_team_members_with_projects['First name'] = qi_team_members_with_projects['First name'].str.title()
        qi_team_members_with_projects['Last name'] = qi_team_members_with_projects['Last name'].str.title()
    else:
        qi_team_members_with_projects = pd.DataFrame(columns=['First name', 'Last name', 'Email', 'Phone Number',
                                                              'User_id', 'QI project id', 'Date created', 'Facility',
                                                              'created_by'])
    # # pandas count frequency of column value in another dataframe column
    # qi_managers_with_projects["Projects Supervising"] = qi_managers_with_projects["First name"].map(
    #     qi_managers_with_projects["First name"].value_counts()).fillna(0).astype(int)
    # qi_managers_with_projects = qi_managers_with_projects.groupby(
    #     ['First name', 'Last name', 'Email', 'Phone Number', 'Designation', 'Date created']).max(
    #     "Projects Supervising").reset_index()

    if qi_teams:
        # Get df for QI managers with projects
        list_of_projects = [
            {
                # {'project_ids': x.id,
                'First name': x.first_name,
                'Last name': x.last_name,
                'Email': x.email,
                'Phone Number': x.phone_number,

                'QI_team_member_id': x.id,
                'Designation': x.designation,
                'Date created': x.date_created,
                'Facility': x.facility.facilities,
                "created_by": x.created_by
            } for x in qi_teams
        ]
        # convert data from database to a dataframe
        qi_team_members_df = pd.DataFrame(list_of_projects)
    else:
        qi_team_members_df = pd.DataFrame(columns=['First name', 'Last name', 'Email', 'Phone Number',
                                                   'QI_team_member_id', 'Designation', 'Date created', 'Facility',
                                                   'created_by'])

    merged_df = qi_team_members_with_projects.merge(qi_team_members_df, how='left', on=['Email', 'Phone Number'])
    # merged_df=qi_team_members_with_projects.merge(qi_team_members_df,how='left')
    merged_df = merged_df[['First name_x', 'Last name_x', 'Email', 'Phone Number', 'User_id',
                           'QI_team_member_id',
                           'Designation', 'Date created_x', 'Facility_x', 'created_by_x']]
    merged_df = merged_df.rename(
        columns={"First name_x": "First name", "Last name_x": "Last name", "Facility_x": "Facility",
                 "Date created_x": "Date created", 'created_by_x': "created_by"})

    # # pandas count frequency of column value in another dataframe column
    merged_df["Projects created"] = merged_df["User_id"].map(
        merged_df["User_id"].value_counts()).fillna(0).astype(int)

    #
    merged_df['Facility'] = merged_df['Facility'].astype(str)
    qi_team_members_with_projects = merged_df.groupby(
        ['First name', 'Last name', 'Email', 'Phone Number', 'Designation', 'Date created', "Facility",
         'created_by']).max("Projects created").reset_index()

    # without projects
    qi_team_members_without_projects = qi_team_members_df.copy()
    qi_team_members_without_projects["Projects created"] = 0
    qi_team_members_without_projects = qi_team_members_without_projects[
        ~qi_team_members_without_projects['QI_team_member_id'].isin(list(merged_df['QI_team_member_id']))]

    qi_team_members_without_projects_ = qi_team_members_df.copy()
    # qi_team_members_without_projects_["Projects created"] = 0
    qi_team_members_without_projects_ = qi_team_members_without_projects_[
        qi_team_members_without_projects_['QI_team_member_id'].isin(list(merged_df['QI_team_member_id']))]

    #
    # Join df for all QI managers with and without

    if 'User_id' in qi_team_members_with_projects.columns:
        del qi_team_members_with_projects['User_id']
    # del qi_team_members_without_projects['Date created']
    qi_team_members_ = pd.concat([qi_team_members_with_projects, qi_team_members_without_projects])
    qi_team_members_ = qi_team_members_.sort_values("Facility")
    qi_team_members_.reset_index(drop=True, inplace=True)
    qi_team_members_.index += 1

    # qi_managers = qi_managers.sort_values("Projects Supervising", ascending=False).reset_index()
    # qi_managers.reset_index(drop=True, inplace=True)
    # qi_managers.index += 1
    # # del qi_managers['QI_manager id']
    # del qi_managers['index']
    #
    # context = {
    #     "qi_managers_list": qi_managers_list,
    #     "qi_managers": qi_managers,
    # }
    context = {
        "qi_teams": qi_teams,
        "qi_team_members_": qi_team_members_
    }
    return render(request, "project/qi_team_members.html", context)


# @login_required(login_url='login')
# def qi_team_members_view(request):
#     """
#     A view that displays the first name, last name, email, and number of projects
#     for each QI manager in a table.
#     """
#     # Get a queryset of QI managers, annotated with the number of projects they are supervising
#     # and ordered by the number of projects in descending order
#     qi_team_members = Qi_team_members.objects.annotate(
#         num_projects=Count('qi_project')
#     ).order_by('-num_projects')
#     print(qi_team_members)
#
#     # Create the context variable to pass to the template
#     context = {
#         'qi_team_members': qi_team_members,
#     }
#
#     # Render the template with the context variable
#     return render(request, 'project/qi_team_members.html', context)
@login_required(login_url='login')
def qi_team_members_view(request):
    # """
    # Retrieves all Qi_team_members associated with each user, then it counts the number of `qi_project` objects
    # associated with each user and store the number of projects into the num_projects.
    # Returns the template of qi_team_members with the data of the number of projects for each user
    # """
    # Retrieve all Qi_team_members and their associated user, counts the number of qi_project per user and order by user
    # team_members = Qi_team_members.objects.values(
    #     'user__first_name','user__last_name','user__email','user__phone_number','choose_qi_team_member_level','user__id'
    # ).annotate(num_projects=Count('qi_project')).order_by('user')

    """
    Get the data of qi team members with the number of projects created and participated.
    :return: Queryset of qi team members with the number of projects created and participated
    """
    team_members = Qi_team_members.objects.values(
        'user__first_name', 'user__last_name', 'user__email', 'user__phone_number', 'choose_qi_team_member_level',
        'user__id', 'user__username',
    ).annotate(num_participating_projects=Count('qi_project'),
               num_created_projects=Count('created_by', filter=Q(created_by=F('user')))).order_by('user')

    # TODO: INCLUDE PROJECTS CREATED BUT USER NOT A TEAM MEMBER

    # team_members = NewUser.objects.values(
    #     'first_name', 'last_name', 'email', 'phone_number', 'id', 'username'
    # ).annotate(num_created_projects=Count('qi_projects')).annotate(
    #     num_participating_projects=Count('qi_team_members__qi_projects', filter=~Q(qi_projects__created_by=F('id'))))

    # team_members = Qi_team_members.objects.values('user__id').annotate(
    #     num_created_projects=Count('created_by', filter=Q(created_by=F('user')))
    # )

    # Render the template with the queryset of data
    return render(request, 'project/qi_team_members.html', {'team_members': team_members})


@login_required(login_url='login')
def qi_team_involved(request, pk):
    projects = Qi_team_members.objects.filter(user__id=pk)

    facility_name = pk

    context = {"projects": projects,
               "facility_name": facility_name,

               }
    return render(request, "project/qi_team_involved.html", context)


# @login_required(login_url='login')
# def qi_managers(request):
#     qi_managers_list = Qi_managers.objects.all()
#     qi_managers_ = QI_Projects.objects.all()
#
#     if qi_managers_:
#         # Get df for QI managers with projects
#         list_of_projects = [
#             {
#                 # {'project_ids': x.id,
#                 'First name': x.qi_manager.first_name,
#                 'Last name': x.qi_manager.last_name,
#                 'Email': x.qi_manager.email,
#                 'Phone Number': x.qi_manager.phone_number,
#                 'QI_manager_id': x.qi_manager.id,
#                 'Designation': x.qi_manager.designation,
#                 'Date created': x.qi_manager.date_created,
#             } for x in qi_managers_
#         ]
#         qi_managers_with_projects = pd.DataFrame(list_of_projects)
#         # pandas count frequency of column value in another dataframe column
#         qi_managers_with_projects["Projects Supervising"] = qi_managers_with_projects["First name"].map(
#             qi_managers_with_projects["First name"].value_counts()).fillna(0).astype(int)
#         qi_managers_with_projects = qi_managers_with_projects.groupby(
#             ['First name', 'Last name', 'Email', 'Phone Number', 'Designation', 'Date created']).max(
#             "Projects Supervising").reset_index()
#     else:
#         qi_managers_with_projects = pd.DataFrame(columns=['First name', 'Last name', 'Email', 'Phone Number',
#                                                           'QI_manager_id', 'Designation', 'Date created',
#                                                           'Projects Supervising'])
#
#     if qi_managers_list:
#         # Get df for QI managers with projects
#         list_of_projects = [
#             {
#                 # {'project_ids': x.id,
#                 'First name': x.first_name,
#                 'Last name': x.last_name,
#                 'Email': x.email,
#                 'Phone Number': x.phone_number,
#
#                 'QI_manager_id': x.id,
#                 'Designation': x.designation,
#                 'Date created': x.date_created,
#             } for x in qi_managers_list
#         ]
#         # convert data from database to a dataframe
#         qi_managers_without_projects = pd.DataFrame(list_of_projects)
#         qi_managers_without_projects["Projects Supervising"] = 0
#         qi_managers_without_projects = qi_managers_without_projects[
#             ~qi_managers_without_projects['QI_manager_id'].isin(list(qi_managers_with_projects['QI_manager_id']))]
#     else:
#         qi_managers_without_projects = pd.DataFrame(columns=['First name', 'Last name', 'Email', 'Phone Number',
#                                                              'QI_manager_id', 'Designation', 'Date created',
#                                                              'Projects Supervising'])
#
#     # Join df for all QI managers with and without
#     qi_managers = pd.concat([qi_managers_with_projects, qi_managers_without_projects])
#     qi_managers = qi_managers.sort_values("Projects Supervising", ascending=False).reset_index()
#     qi_managers.reset_index(drop=True, inplace=True)
#     qi_managers.index += 1
#     # del qi_managers['QI_manager id']
#     if 'index' in qi_managers.columns:
#         del qi_managers['index']
#
#     context = {
#         "qi_managers_list": qi_managers_list,
#         "qi_managers": qi_managers,
#     }
#     return render(request, "project/qi_managers.html", context)


@login_required(login_url='login')
def qi_managers_view(request):
    """
    A view that displays the first name, last name, email, and number of projects
    for each QI manager in a table.
    """
    # Get a queryset of QI managers, annotated with the number of projects they are supervising
    # and ordered by the number of projects in descending order
    qi_managers = Qi_managers.objects.annotate(num_projects=Count('qi_projects')).order_by('-num_projects')

    # Create the context variable to pass to the template
    context = {
        'qi_managers': qi_managers
    }

    # Render the template with the context variable
    return render(request, 'project/qi_managers.html', context)


@login_required(login_url='login')
def audit_trail(request):
    return render(request, "project/audit_trail.html")


# @login_required(login_url='login')
# def comments(request):
#     # all_comments = ProjectComments.objects.all().order_by('-comment_updated')
#     all_comments = ProjectComments.objects.all().prefetch_related('qi_project_title__qi_team_members').order_by(
#         '-comment_updated')
#
#     all_responses = ProjectResponses.objects.values_list('comment_id', flat=True)
#     context = {
#         "all_comments": all_comments,
#         "all_responses": all_responses,
#     }
#     return render(request, "project/comments.html", context)


@login_required(login_url='login')
def comments_no_response(request):
    """
    This view retrieves all comments that are either parent comments or comments that don't have any parent comment.
    It uses the Comment model and filters out comments that have a parent comment. The filtered comments are then
    returned to the 'project/comments_no_response.html' template to be displayed.
    """
    # Get all comments that have a parent_id of None or are null and exclude any comments whose id is in the list of
    # parent_id of comments that have a parent_id that is not None or null.
    all_comments = Comment.objects.filter(Q(parent_id=None) | Q(parent_id__isnull=True)).exclude(
        id__in=Comment.objects.filter(~Q(parent_id=None) & ~Q(parent_id__isnull=True)).values_list("parent_id",
                                                                                                   flat=True))



    context = {
        "all_comments": all_comments,
        "title": "Comments without responses"
    }
    return render(request, "project/comments.html", context)


@login_required(login_url='login')
def comments_with_response(request):
    all_comments = Comment.objects.filter(
        id__in=Comment.objects.exclude(parent_id=None).values_list("parent_id", flat=True)
    ).prefetch_related('qi_project_title__qi_team_members').order_by('-comment_updated')
    context = {
        "all_comments": all_comments,
        "title":"Comments with responses"
    }
    return render(request, "project/comments.html", context)


@login_required(login_url='login')
def single_project_comments(request, pk):
    #  retrieve all related ProjectResponses for each comment along with the comment, in a single query and you can
    #  access the responses directly from the comment obj.
    all_comments = ProjectComments.objects.filter(
        qi_project_title__id=pk).prefetch_related('projectresponses_set').select_related(
        'qi_project_title', 'commented_by').order_by('-comment_updated')

    facility_project = QI_Projects.objects.get(id=pk)

    if request.method == "POST":
        form = ProjectCommentsForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.qi_project_title = facility_project
            post.commented_by = request.user
            post.save()
            form = ProjectCommentsForm()
    else:
        form = ProjectCommentsForm()

    context = {
        "all_comments": all_comments,
        "form": form,
        "facility_project": facility_project
    }
    return render(request, "project/single_comment.html", context)


# def single_project_comments(request, pk):
#     all_comments = ProjectComments.objects.filter(qi_project_title__id=pk).order_by('-comment_updated')
#
#     all_responses = ProjectResponses.objects.filter(comment__qi_project_title_id=pk).order_by('-response_updated_date')
#
#     all_responses_ids = ProjectResponses.objects.values_list('comment_id', flat=True)
#
#     facility_project = QI_Projects.objects.get(id=pk)
#
#     # pro_owner = facility_project.projectcomments_set.all()
#     if request.method == "POST":
#         form = ProjectCommentsForm(request.POST)
#         if form.is_valid():
#             post = form.save(commit=False)
#             # get project primary key
#             post.qi_project_title = QI_Projects.objects.get(project_title=facility_project.project_title)
#             post.commented_by = NewUser.objects.get(username=request.user)
#             # save
#             post.save()
#             # show empty form
#             form = ProjectCommentsForm()
#     else:
#         form = ProjectCommentsForm()
#
#     context = {
#         "all_comments": all_comments,
#         "form": form,
#         "all_responses": all_responses,
#         "facility_project": facility_project,
#         "all_responses_ids": all_responses_ids,
#
#     }
#     return render(request, "project/single_comment.html", context)


@login_required(login_url='login')
def update_comments(request, pk):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    item = ProjectComments.objects.get(id=pk)
    if request.method == "POST":
        form = ProjectCommentsForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = ProjectCommentsForm(instance=item)
    context = {
        "form": form,
        "title": "Update Comment",
    }
    return render(request, 'project/update_test_of_change.html', context)


@login_required(login_url='login')
def update_resource(request, pk):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    item = Resources.objects.get(id=pk)
    if request.method == "POST":
        form = ResourcesForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = ResourcesForm(instance=item)
    context = {
        "form": form,
        "title": "Update Resource",
    }
    return render(request, 'project/update.html', context)


@login_required(login_url='login')
def comments_response(request, pk):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    all_comments = ProjectResponses.objects.filter(id=pk).order_by('-response_updated_date')

    # facility_project = QI_Projects.objects.get(id=pk)
    if request.method == "POST":
        form = ProjectResponsesForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            # get project primary key
            post.comment = ProjectComments.objects.get(id=pk)
            post.response_by = NewUser.objects.get(username=request.user)
            # save
            post.save()
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = ProjectResponsesForm()

    context = {
        "all_comments": all_comments,
        "form": form,

    }
    return render(request, "project/response.html", context)


@login_required(login_url='login')
def project_responses(request, pk):
    all_comments = ProjectResponses.objects.filter(qi_project_title__id=pk).order_by('-comment_updated')

    facility_project = QI_Projects.objects.get(id=pk)
    if request.method == "POST":
        form = ProjectCommentsForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            # get project primary key
            post.qi_project_title = QI_Projects.objects.get(project_title=facility_project.project_title)
            post.commented_by = NewUser.objects.get(username=request.user)
            # save
            post.save()
            # show empty form
            form = ProjectCommentsForm()
    else:
        form = ProjectCommentsForm()

    context = {
        "all_comments": all_comments,
        "form": form,

    }
    return render(request, "project/single_comment.html", context)


@login_required(login_url='login')
def update_response(request, pk):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    item = ProjectResponses.objects.get(id=pk)
    if request.method == "POST":
        form = ProjectResponsesForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = ProjectResponsesForm(instance=item)
    context = {
        "form": form,
        "title": "Update Comment",
    }
    return render(request, 'project/update.html', context)


@login_required(login_url='login')
def resources(request):
    all_resources = Resources.objects.all()

    my_filters = ResourcesFilter(request.GET, queryset=all_resources)
    qi_lists = my_filters.qs
    qi_list = pagination_(request, qi_lists)

    context = {"all_resources": all_resources, "my_filters": my_filters, "qi_lists": qi_lists, }
    return render(request, "project/resources.html", context)


def line_chart(df, x_axis, y_axis, title):
    fig = px.line(df, x=x_axis, y=y_axis, text=y_axis, title=title, height=300,
                  hover_name=None, hover_data={"tested of change": True,
                                               "achievements (%)": True, }
                  )

    fig.update_traces(textfont_size=14, textfont_family="Arial", textfont_color='brown', textposition='top center')
    # fig.add_trace(go.Line(x=df[x_axis], y=df[y_axis], mode='markers'))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)
    fig.add_hline(y=90, line_width=1, line_dash="dash", line_color="green")
    fig.add_hline(y=50, line_width=1, line_dash="dash", line_color="red")
    fig.add_hline(y=75, line_width=1, line_dash="dash", line_color="#bcbd22")
    fig.add_annotation(x=0.25, y=75,
                       text="75 %",
                       showarrow=True,
                       arrowhead=1,
                       font=dict(
                           size=7
                       )
                       )
    fig.add_annotation(x=0.5, y=90,
                       text="90 %",
                       showarrow=True,
                       arrowhead=1,
                       font=dict(
                           size=7
                       ))
    fig.add_annotation(x=0, y=50,
                       text="50 %",
                       showarrow=True,
                       arrowhead=1,
                       font=dict(
                           size=7
                       ))
    fig.update_layout({
        'plot_bgcolor': 'rgba(0, 0, 0, 0)',
        'paper_bgcolor': 'rgba(0, 0, 0, 0)',
    })
    fig.update_yaxes(rangemode="tozero")
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

    # fig.update_traces(textfont_size=14,textfont_color='red',textfont_weight='bold')
    # fig.update_traces(texttemplate='%{text:.s}')

    return fig.to_html()


def line_chart_no_targets(df, x_axis, y_axis, title):
    fig = px.line(df, x=x_axis, y=y_axis, text=y_axis, title=title, height=500,
                  hover_name=None, hover_data={"tested of change": True,
                                               "achievements (%)": True, }
                  )
    fig.update_traces(textfont_size=14, textfont_family="Arial", textfont_color='brown', textposition='top center')
    fig.update_traces(textposition='top center')
    # fig.add_trace(go.Line(x=df[x_axis], y=df[y_axis], mode='markers'))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)
    fig.add_hline(y=90, line_width=1, line_dash="dash", line_color="green")
    fig.add_hline(y=50, line_width=1, line_dash="dash", line_color="red")
    fig.add_hline(y=75, line_width=1, line_dash="dash", line_color="#bcbd22")
    fig.add_annotation(x=0.25, y=75,
                       text="75 %",
                       showarrow=True,
                       arrowhead=1,
                       font=dict(
                           size=7
                       )
                       )
    fig.add_annotation(x=0.5, y=90,
                       text="90 %",
                       showarrow=True,
                       arrowhead=1,
                       font=dict(
                           size=7
                       ))
    fig.add_annotation(x=0, y=50,
                       text="50 %",
                       showarrow=True,
                       arrowhead=1,
                       font=dict(
                           size=7
                       ))
    fig.update_layout({
        'plot_bgcolor': 'rgba(0, 0, 0, 0)',
        'paper_bgcolor': 'rgba(0, 0, 0, 0)',
    })
    fig.update_yaxes(rangemode="tozero")
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
    # fig.update_traces(texttemplate='%{text:.s}')

    return fig.to_html()


def bar_chart_horizontal(df, x_axis, y_axis, title):
    # df[x_axis]=df[x_axis].str.split(" ").str[0]

    fig = px.bar(df, x=y_axis, y=x_axis, text=y_axis, title=title, orientation='h', height=300,
                 # hover_name=x_axis,  hover_data={
                 #                                        "tested of change":True,
                 #                                        "achievements":True,}
                 )
    # fig.update_traces(textposition='top center')
    # fig.add_trace(go.Line(x=df[x_axis], y=df[y_axis], mode='markers'))
    # fig.update_xaxes(showgrid=False)
    # fig.update_yaxes(showgrid=False)
    # # fig.add_hline(y=90, line_width=1, line_dash="dash", line_color="green")
    # # fig.add_hline(y=75, line_width=1, line_dash="dash", line_color="red")
    # fig.update_layout({
    #     'plot_bgcolor': 'rgba(0, 0, 0, 0)',
    #     'paper_bgcolor': 'rgba(0, 0, 0, 0)',
    # })
    # fig.update_traces(texttemplate='%{text:.s}')

    return fig.to_html()


def bar_chart(df, x_axis, y_axis, title):
    # df[x_axis]=df[x_axis].str.split(" ").str[0]

    fig = px.bar(df, x=x_axis, y=y_axis, text=y_axis, title=title, height=300
                 # hover_name=x_axis,  hover_data={
                 #                                        "tested of change":True,
                 #                                        "achievements":True,}
                 )
    # fig.update_traces(textposition='top center')
    # fig.add_trace(go.Line(x=df[x_axis], y=df[y_axis], mode='markers'))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)
    # fig.add_hline(y=90, line_width=1, line_dash="dash", line_color="green")
    # fig.add_hline(y=75, line_width=1, line_dash="dash", line_color="red")
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
    )
    # fig.update_traces(texttemplate='%{text:.s}')

    return fig.to_html()


def prepare_trends(df, title=""):
    df = df.copy()
    df['achievements'] = df['achievements'].astype(int)
    df = df.sort_values("month_year")
    df['month_year'] = df['month_year'].astype(str) + "."
    df = df.rename(columns={"achievements": "achievements (%)"})
    project_performance = line_chart(df, "month_year", "achievements (%)", title)
    return project_performance


def prepare_trends_big_size(df, title=""):
    df = df.copy()
    df['achievements'] = df['achievements'].astype(int)
    df = df.sort_values("month_year")
    df['month_year'] = df['month_year'].astype(str) + "."
    df = df.rename(columns={"achievements": "achievements (%)"})
    project_performance = line_chart_no_targets(df, "month_year", "achievements (%)", title)
    return project_performance


@login_required(login_url='login')
def single_project(request, pk):
    try:
        all_archived = ArchiveProject.objects.filter(archive_project=True).values_list('qi_project_id', flat=True)
    except:
        all_archived = []

    facility_project = QI_Projects.objects.get(id=pk)
    if not facility_project.process_analysis:
        facility_project.process_analysis = 'media/images/default.png'
    # get other All projects
    other_projects = QI_Projects.objects.filter(facility_name=facility_project.facility_name)
    # Hit db once
    test_of_change_qs = TestedChange.objects.all()
    # check comments
    all_comments = ProjectComments.objects.filter(qi_project_title__id=facility_project.id).order_by('-comment_updated')

    # get qi team members for this project
    qi_teams = Qi_team_members.objects.filter(qi_project__id=pk)
    qi_teams = pagination_(request, qi_teams)
    # get milestones for this project
    milestones = Milestone.objects.filter(qi_project__id=pk)
    # # get action plan for this project
    action_plan = ActionPlan.objects.filter(qi_project__id=pk).order_by('-percent_completed', 'progress')
    action_plans = pagination_(request, action_plan)

    # get baseline image for this project
    try:
        baseline = Baseline.objects.filter(qi_project__id=pk).latest('date_created')
    except Baseline.DoesNotExist:
        baseline = None

    # if not baseline.baseline_status:
    #     baseline.baseline_status = 'media/images/default.png'

    # This work the same way
    # baseline = Baseline.objects.filter(qi_project__id=pk).order_by('-date_created').first()

    # print(baseline)

    today = datetime.now(timezone.utc).date()
    action_plans = pagination_(request, action_plan)

    # use date filter and get the timestamp first and then subtract the timestamps of both dates to get the difference
    # in seconds and then convert it to days.
    for plan in action_plans:
        plan.progress = (plan.due_date - today).days

    if request.method == "POST":
        form = ProjectCommentsForm(request.POST)
        # stakeholderform = StakeholderForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            # get project primary key
            post.qi_project_title = QI_Projects.objects.get(project_title=facility_project.project_title)
            post.commented_by = NewUser.objects.get(username=request.user.username)
            # save
            post.save()
            # show empty form
            form = ProjectCommentsForm()
    else:
        form = ProjectCommentsForm()
        # stakeholderform = StakeholderForm()

    # accessing facility qi projects
    # use two underscore to the field with foreign key
    list_of_projects = TestedChange.objects.filter(project_id__facility_name=facility_project.facility_name).order_by(
        '-month_year')
    list_of_projects = [
        {'month_year': x.month_year,
         'project_id': x.project_id,
         'tested of change': x.tested_change,
         'achievements': x.achievements,
         'facility': x.project,
         'project': x.project.project_title,
         } for x in list_of_projects
    ]
    # convert data from database to a dataframe
    list_of_projects = pd.DataFrame(list_of_projects)
    if list_of_projects.shape[0] != 0:
        dicts = {}
        keys = list_of_projects['project_id'].unique()
        values = list_of_projects['project'].unique()
        for i in range(len(keys)):
            dicts[keys[i]] = values[i]

        all_other_projects_trend = []
        for project in list_of_projects['project'].unique():
            all_other_projects_trend.append(
                prepare_trends(list_of_projects[list_of_projects['project'] == project], project))

        pro_perfomance_trial = dict(zip(keys, all_other_projects_trend))
    else:
        pro_perfomance_trial = {}

    # assign it to a dataframe using list comprehension
    other_projects = [
        {'department(s)': x.departments.department,
         'project category': x.project_category,
         'id': x.id,
         } for x in other_projects
    ]
    # convert data from database to a dataframe
    df_other_projects = pd.DataFrame(other_projects)
    df_other_projects['total projects'] = 1

    changes = test_of_change_qs.filter(project_id=pk).order_by('-month_year')
    # assign it to a dataframe using list comprehension
    changes_data = [
        {'month_year': x.month_year,
         'tested of change': x.tested_change,
         'achievements': x.achievements,
         } for x in changes
    ]
    # convert data from database to a dataframe
    df = pd.DataFrame(changes_data)
    if df.shape[0] != 0:
        df_other_projects = df_other_projects.groupby('department(s)').sum()['total projects']
        df_other_projects = df_other_projects.reset_index().sort_values('total projects', ascending=False)

        project_performance = prepare_trends_big_size(df)

        facility_proj_performance = bar_chart(df_other_projects, "department(s)", "total projects", "All projects")

        context = {"facility_project": facility_project, "test_of_change": changes,
                   "project_performance": project_performance, "facility_proj_performance": facility_proj_performance,
                   "pro_perfomance_trial": pro_perfomance_trial, "form": form, "all_comments": all_comments,
                   "all_archived": all_archived,
                   # "stakeholderform": stakeholderform,
                   "qi_teams": qi_teams,
                   "milestones": milestones, "action_plans": action_plans, "today": today, "baseline": baseline}

    else:
        project_performance = {}
        facility_proj_performance = {}
        context = {"facility_project": facility_project, "test_of_change": changes,
                   "project_performance": project_performance, "facility_proj_performance": facility_proj_performance,
                   "pro_perfomance_trial": pro_perfomance_trial, "form": form, "all_comments": all_comments,
                   "all_archived": all_archived,
                   # "stakeholderform": stakeholderform,
                   "qi_teams": qi_teams,
                   "milestones": milestones, "action_plans": action_plans, "today": today, "baseline": baseline, }

    return render(request, "project/individual_qi_project.html", context)


@login_required(login_url='login')
def untracked_projects(request):
    all_projects = QI_Projects.objects.all()
    tracked_projects = TestedChange.objects.values_list('project_id', flat=True)
    context = {
        "all_projects": all_projects,
        "all_responses": tracked_projects,
    }
    return render(request, "project/untracked_projects.html", context)


def add_stake_holders(request, pk):
    facility_project = QI_Projects.objects.get(id=pk)

    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        stakeholderform = StakeholderForm(request.POST)
        if stakeholderform.is_valid():
            post = stakeholderform.save(commit=False)

            post.facility = Facilities.objects.get(facilities=facility_project.facility_name)
            post.save()
            # return HttpResponseRedirect(request.session['page_from'])
            return redirect(request.session['page_from'])
    else:
        stakeholderform = StakeholderForm()
    context = {"stakeholderform": stakeholderform,

               }
    return render(request, 'project/stakeholders.html', context)


def add_baseline_image(request, pk):
    facility_project = QI_Projects.objects.get(id=pk)

    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        baselineform = BaselineForm(request.POST, request.FILES)
        if baselineform.is_valid():
            post = baselineform.save(commit=False)
            #
            post.facility = Facilities.objects.get(facilities=facility_project.facility_name)
            post.qi_project = facility_project
            post.save()
            # return HttpResponseRedirect(request.session['page_from'])
            return redirect(request.session['page_from'])
    else:
        baselineform = BaselineForm()
    context = {"form": baselineform,

               }
    return render(request, 'project/baseline_images.html', context)


@login_required(login_url='login')
def update_baseline(request, pk):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    item = Baseline.objects.get(qi_project__id=pk)
    qi_project = QI_Projects.objects.get(id=pk)
    if request.method == "POST":
        form = BaselineForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = BaselineForm(instance=item)
    context = {
        "form": form,
        "title": "Update baseline status",
        "qi_project": qi_project,
    }
    return render(request, 'project/add_milestones.html', context)


@login_required(login_url='login')
def delete_project(request, pk):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    item = QI_Projects.objects.get(id=pk)
    if request.method == "POST":
        item.delete()

        return redirect("facilities_landing_page")
    context = {
        "test_of_changes": item
    }
    return render(request, 'project/delete_test_of_change.html', context)


@login_required(login_url='login')
def delete_comment(request, pk):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    item = ProjectComments.objects.get(id=pk)
    if request.method == "POST":
        item.delete()

        return redirect("facilities_landing_page")
    context = {
        "test_of_changes": item
    }
    return render(request, 'project/delete_test_of_change.html', context)


# @login_required(login_url='login')
# def close_project(request, pk):
#     # check the page user is from
#     if request.method == "GET":
#         request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
#     project = close_project.objects.get(id=pk)
#     if request.method == "POST":
#         form = QI_ProjectsForm(request.POST, instance=project)
#         if form.is_valid():
#             form.save()
#             # redirect back to the page the user was from after saving the form
#             return HttpResponseRedirect(request.session['page_from'])
#     else:
#         form = Close_projectForm(instance=project)
#     context = {"form": form}
#     return render(request, "project/close_project.html", context)

# def login_page(request):
#     if request.method == "POST":
#         form = CreateUserForm(request.POST)
#         if form.is_valid():
#             form.save()
#             return redirect("dashboard")
#     else:
#         form = CreateUserForm()
#     context = {"form": form}
#     return render(request, "project/login_page.html", context)


# def register_page(request):
#     form = UserCreationForm()
# #     if request.method == "POST":
# #         form = CreateUserForm(request.POST)
# #         if form.is_valid():
# #             form.save()
# #             redirect("dashboard")
#     context = {"form": form}
#     return render(request, "project/login_page.html", context)


# def view_history(request):
# # Get the Qi_team_members object you want to track changes for
# qi_team_member = Qi_team_members.objects.get(pk=1)
#
# # Get the change history for the object
# history = qi_team_member.history.all()
#
# # Loop through the history and print the change details
# for change in history:
#     print('Changed field:', change.field_name)
#     print('Old value:', change.old_value)
#     print('New value:', change.new_value)
#     print('Change reason:', change.history_change_reason)
#     print('---')
# context = {'history_records': history_records}
# return render(request, 'project/facility_landing_page.html', context)

@login_required(login_url='login')
def add_project_milestone(request, pk):
    title = "ADD PROJECT MILESTONE"
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    facility_project = QI_Projects.objects.get(id=pk)
    qi_project = QI_Projects.objects.get(id=pk)

    if request.method == "POST":
        form = MilestoneForm(request.POST)
        # try:
        if form.is_valid():
            post = form.save(commit=False)
            post.facility = Facilities.objects.get(id=facility_project.facility_name_id)
            post.qi_project = qi_project
            post.created_by = request.user
            post.save()
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = MilestoneForm()
    context = {"form": form, "title": title, "qi_project": qi_project, }
    return render(request, "project/add_milestones.html", context)


@login_required(login_url='login')
def update_milestone(request, pk):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    item = Milestone.objects.get(id=pk)
    qi_project = QI_Projects.objects.get(id=pk)
    if request.method == "POST":
        form = MilestoneForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = MilestoneForm(instance=item)
    context = {
        "form": form,
        "title": "Update Project Milestone",
        "qi_project": qi_project,
    }
    return render(request, 'project/add_milestones.html', context)


@login_required(login_url='login')
def delete_milestone(request, pk):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    item = Milestone.objects.get(id=pk)
    if request.method == "POST":
        item.delete()

        return HttpResponseRedirect(request.session['page_from'])
    context = {
        "test_of_changes": item
    }
    return render(request, 'project/delete_test_of_change.html', context)


@login_required(login_url='login')
def add_corrective_action(request, pk):
    # facility_project = QI_Projects.objects.get(id=pk)
    facility_project = get_object_or_404(QI_Projects, id=pk)
    qi_team_members = Qi_team_members.objects.filter(qi_project=facility_project)
    qi_project = QI_Projects.objects.get(id=pk)

    facility = facility_project.facility_name

    qi_projects = facility_project

    today = timezone.now().date()
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        form = ActionPlanForm(facility, qi_projects, request.POST)
        if form.is_valid():
            # form.save()
            post = form.save(commit=False)
            post.facility = Facilities.objects.get(id=facility_project.facility_name_id)
            post.qi_project = qi_project
            post.created_by = request.user
            #
            post.progress = (post.due_date - today).days
            post.timeframe = (post.due_date - post.start_date).days
            post.save()

            # Save many-to-many relationships
            form.save_m2m()
            # redirect back to the page the user was from after saving the form
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = ActionPlanForm(facility, qi_projects)
    context = {"form": form,
               "title": "Add Action Plan",
               "qi_team_members": qi_team_members,
               "qi_project": qi_project,
               }
    return render(request, "project/add_qi_manager.html", context)


@login_required(login_url='login')
def update_action_plan(request, pk):
    # facility_project = get_object_or_404(QI_Projects, id=pk)
    # qi_team_members = Qi_team_members.objects.filter(qi_project=facility_project)
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    action_plan = ActionPlan.objects.get(id=pk)
    facility = action_plan.facility
    qi_projects = action_plan.qi_project

    qi_project = QI_Projects.objects.get(id=action_plan.qi_project_id)
    qi_team_members = Qi_team_members.objects.filter(qi_project=action_plan.qi_project)
    if request.method == "POST":
        form = ActionPlanForm(facility, qi_projects, request.POST, instance=action_plan)
        if form.is_valid():
            # responsible = form.cleaned_data['responsible']
            post = form.save(commit=False)
            today = timezone.now().date()
            post.progress = (post.due_date - today).days
            post.timeframe = (post.due_date - post.start_date).days
            # post.responsible.set(responsible)
            post.save()

            # Save many-to-many relationships
            form.save_m2m()
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = ActionPlanForm(facility, qi_projects, instance=action_plan)
    context = {
        "form": form,
        "qi_team_members": qi_team_members,
        "title": "Update Action Plan",
        "qi_project": qi_project,
    }
    return render(request, 'project/add_qi_manager.html', context)


@login_required(login_url='login')
def delete_action_plan(request, pk):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    item = ActionPlan.objects.get(id=pk)
    if request.method == "POST":
        item.delete()

        return HttpResponseRedirect(request.session['page_from'])
    context = {
        "test_of_changes": item
    }
    return render(request, 'project/delete_test_of_change.html', context)




@login_required(login_url='login')
def create_comment(request, pk):
    # set comment as none
    comment = None
    try:
        # this will allow creating a reply from show comments page
        comment = Comment.objects.get(id=pk)
    except ObjectDoesNotExist:
        # this will allow creating a comment from show single project page
        qi_project = QI_Projects.objects.get(id=pk)
    if request.method == "POST":
        form = CommentForm(request.POST)
        if form.is_valid():
            content = form.cleaned_data['content']
            parent_id = form.cleaned_data.get('parent_id')
            try:
                # Atomic will ensure data consistency, concurrency control, isolation and performance
                with transaction.atomic():
                    if parent_id:
                        parent_comment = Comment.objects.get(id=parent_id)
                        Comment.objects.create(content=content, parent=parent_comment,
                                               parent_id=request.POST.get('parent'))
                    else:
                        if comment is not None:
                            Comment.objects.create(content=content, author=request.user,
                                                   parent_id=request.POST.get('parent'),
                                                   qi_project_title=comment.qi_project_title)
                        else:
                            Comment.objects.create(content=content, author=request.user,
                                                   qi_project_title=qi_project)

            except ObjectDoesNotExist:
                form.add_error('parent_id', 'Parent comment does not exist')
            except PermissionDenied:
                form.add_error(None, 'You do not have permission to create a comment')
            else:
                # try:
                # return redirect("show_project_comments", pk=pk)
                return redirect(request.META.get('HTTP_REFERER'))
    else:
        form = CommentForm()
    return render(request, 'project/create_comment.html', {'form': form})


def update_comments(request, pk):
    comment = Comment.objects.get(id=pk)
    project = QI_Projects.objects.get(id=comment.qi_project_title_id)
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            # post = form.save(commit=False)
            # post.project_name = project
            # post.created_by = request.user
            # post.save()
            # messages.success(request, f"Lesson learnt for {post.project_name} added successfully.")
            # redirect back to the page the user was from after saving the form
            return HttpResponseRedirect(request.session['page_from'])
            # return redirect("lesson_learnt")
    else:
        form = CommentForm(instance=comment)
    context = {"form": form,
               "qi_project": project,
               # "title": "UPDATE",
               }

    return render(request, "project/add_lesson_learnt.html", context)


def delete_comments(request, pk):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    item = Comment.objects.get(id=pk)
    if request.method == "POST":
        item.delete()

        return HttpResponseRedirect(request.session['page_from'])
    context = {
        "test_of_changes": item
    }
    return render(request, 'project/delete_test_of_change.html', context)


def show_project_comments(request, pk):
    project = QI_Projects.objects.filter(id=pk).first()
    try:
        comments = Comment.objects.filter(qi_project_title_id=pk, parent_id=None).order_by('-created_at')
    except:
        comments = None

    if not comments:
        comments = Comment.objects.filter(id=pk).order_by('-created_at')
    context = {'all_comments': comments,"title":"COMMENTS","qi_project":project,}
    return render(request, 'project/comments_trial.html', context)


def show_all_comments(request):
    # all_comments = ProjectComments.objects.all().order_by('-comment_updated')
    all_comments = Comment.objects.filter(parent_id=None).prefetch_related('qi_project_title__qi_team_members').order_by(
        '-comment_updated')




    print(all_comments)

    context = {
        "all_comments": all_comments,
        "title": "All comments"
    }
    return render(request, "project/comments.html", context)


def like_dislike(request, pk):
    """
    A view function that handles the liking and disliking of a comment.
    When a user clicks the "like" or "dislike" button on a comment, a POST request is sent to this view.
    The view then increments the appropriate field on the comment (likes or dislikes) and saves the comment.
    It then redirects the user back to the previous page.
    If the request is not a POST request, the user is redirected back to the previous page.
    """
    # Get the comment that is being liked/disliked
    comment = Comment.objects.get(id=pk)

    # Check if the request is a POST request
    if request.method == 'POST':
        # check if the user has already liked or disliked the comment
        like_dislike = LikeDislike.objects.filter(user=request.user, comment=comment).first()
        if like_dislike:
            if like_dislike.like:
                comment.likes -= 1
                comment.save()
                like_dislike.delete()
                messages.info(request, 'Removed your like')
            else:
                comment.dislikes -= 1
                comment.save()
                like_dislike.delete()
                messages.info(request, 'Removed your dislike')

            return redirect(request.META.get('HTTP_REFERER'))

        # check if the request user is the author of the comment
        if request.user.id == comment.author.id:
            messages.info(request, 'You can not like or dislike your own comment')
            return redirect(request.META.get('HTTP_REFERER'))

        # check if the user has already liked or disliked the comment
        if LikeDislike.objects.filter(user=request.user, comment=comment).exists():
            messages.info(request, 'You have already liked or disliked this comment')
            return redirect(request.META.get('HTTP_REFERER'))
        else:
            if 'like' in request.POST:
                LikeDislike.objects.create(user=request.user, comment=comment, like=True)
                comment.likes += 1
            elif 'dislike' in request.POST:
                LikeDislike.objects.create(user=request.user, comment=comment, like=False)
                comment.dislikes += 1
            comment.save()
            return redirect(request.META.get('HTTP_REFERER'))
    else:
        return redirect(request.META.get('HTTP_REFERER'))



@login_required(login_url='login')
def add_sustainmentplan(request,pk):
    # qi_project=QI_Projects.objects.get(id=pk)
    # lesson=Lesson_learned.objects.filter(project_name=qi_project)
    qi_project = QI_Projects.objects.filter(id=pk).first()
    if not qi_project:
        raise Http404("Project does not exist")
    lesson = Lesson_learned.objects.filter(project_name=qi_project)

    title = "ADD SUSTAINMENT PLAN"
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        form = SustainmentPlanForm(request.POST)

        # try:
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = SustainmentPlanForm()
    context = {"form": form, "title": title,"qi_project":qi_project,"lesson_learnt":lesson,}
    return render(request, "project/add_qi_manager.html", context)

