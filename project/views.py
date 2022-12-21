import os.path

import pandas as pd
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage

from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db import IntegrityError
from django.db.models import Count
from django.forms import forms

from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.shortcuts import render, redirect

from account.forms import UpdateUserForm
from cqi_fyj import settings

from .forms import QI_ProjectsForm, TestedChangeForm, ProjectCommentsForm, ProjectResponsesForm, \
    QI_ProjectsSubcountyForm, QI_Projects_countyForm, QI_Projects_hubForm, QI_Projects_programForm, Qi_managersForm, \
    DepartmentForm, CategoryForm, Sub_countiesForm, FacilitiesForm, CountiesForm, ResourcesForm, Qi_team_membersForm
from .filters import *

import plotly.express as px


# Create your views here.

def pagination_(request, item_list):
    page = request.GET.get('page', 1)

    paginator = Paginator(item_list, 10)
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
        print("df_heads:::::::::::")
        print(df_heads)

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
        # print(qi_mans)
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
        # print(qi_mans)

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
        form = QI_ProjectsForm(request.POST)
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
                if sub_county_list[0] == county.sub_counties_id:
                    post.county = Counties.objects.get(id=county.counties_id)
            # save
            post.save()
            # redirect back to the page the user was from after saving the form
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = QI_ProjectsForm()
    context = {"form": form}
    return render(request, "project/add_project.html", context)


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
                if sub_county_list[0] == county.sub_counties_id:
                    post.county = Counties.objects.get(id=county.counties_id)
            # save
            post.save()
            # redirect back to the page the user was from after saving the form
            return HttpResponseRedirect(request.session['page_from'])
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
    return render(request, "project/add_qi_manager.html", context)


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

    context = {"qi_list": qi_list, "num_post": num_post, "projects": projects,
               "my_filters": my_filters, "qi_lists": qi_lists,
               "facility_proj_performance": facility_proj_performance,
               "departments_viz": departments_viz,
               "status_viz": status_viz,
               "tracked_projects":tracked_projects,
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
               "tracked_projects":tracked_projects,
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
               "tracked_projects":tracked_projects,
               }
    return render(request, "project/department_projects.html", context)


@login_required(login_url='login')
def department_filter_project(request, pk):
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

    context = {"projects": projects,
               "facility_name": facility_name,
               "title": "Ongoing",
               "pro_perfomance_trial": pro_perfomance_trial,

               }
    return render(request, "project/department_filter_projects.html", context)


@login_required(login_url='login')
def qi_managers_filter_project(request, pk):
    print(pk)
    pro_perfomance_trial = {}
    manager_name=[]

    projects = QI_Projects.objects.filter(qi_manager__id=pk)
    print(projects)
    if projects:
        list_of_projects = [
            {
                'qi_manager_email': x.qi_manager.email,
            } for x in projects
        ]
        list_of_projects_ = pd.DataFrame(list_of_projects)
        print("list_of_projects_::::")
        print(list_of_projects_)

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
        print(list_of_projects_)
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
            print("list_of_projects_:::: name")
            manager_name = list(list_of_projects_['qi_manager'].unique())[0]
            print(list_of_projects_)

    # difference
    number_of_projects_created = projects.count()
    number_of_projects_with_test_of_change = len(pro_perfomance_trial)
    difference = number_of_projects_created - number_of_projects_with_test_of_change

    print("pro_perfomance_trial.....")
    print(pro_perfomance_trial)

    context = {"projects": projects,
               "facility_name": manager_name,
               "title": "",
               "pro_perfomance_trial": pro_perfomance_trial,
               "difference": difference

               }
    return render(request, "project/department_filter_projects.html", context)


@login_required(login_url='login')
def facility_filter_project(request, pk):
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
        print(f"pro_perfomance_trial keys: {keys}")

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
        # print("facility_filter_project::::")
        # print(df_heads)
        #
        # print("list(df_heads['project_id'])::::")
        # print(list(df_heads['project_id']))
        all_other_projects_trend = []
        keys = []
        for project in list(df_heads['project_id']):
            keys.append(project)
            print(f"project: {project}")
            # filter dfs based on the order of the best performing projects
            if isinstance(project, str):
                all_other_projects_trend.append(
                    prepare_trends(list_of_projects[list_of_projects['project_id'] == project], project))
            else:
                all_other_projects_trend.append(
                    prepare_trends(list_of_projects[list_of_projects['project_id'] == project]))

        # print("all_other_projects_trend:::")
        # print(all_other_projects_trend)

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
               "difference":difference,

               }
    return render(request, "project/department_filter_projects.html", context)


@login_required(login_url='login')
def qicreator_filter_project(request, pk):
    pro_perfomance_trial = {}
    # projects = QI_Projects.objects.filter(facility=pk).order_by("-date_updated")
    pk = str(pk).lower()
    projects = QI_Projects.objects.filter(created_by__username=pk)
    # print(projects)
    # project_id_values = request.session['project_id_values']

    # accessing facility qi projects
    # use two underscore to the field with foreign key
    # list_of_projects = TestedChange.objects.filter(project_id__in=project_id_values).order_by('-achievements')
    testedChange = TestedChange.objects.filter(project__created_by__username=pk)
    # print(testedChange)
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
               "difference": difference

               }
    return render(request, "project/department_filter_projects.html", context)


@login_required(login_url='login')
def county_filter_project(request, pk):
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
               "difference":difference,

               }
    return render(request, "project/department_filter_projects.html", context)


@login_required(login_url='login')
def sub_county_filter_project(request, pk):
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
               "difference":difference,

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
               "tracked_projects":tracked_projects
               }
    return render(request, "project/qi_creators.html", context)


@login_required(login_url='login')
def qi_managers_projects(request, pk):
    projects = QI_Projects.objects.filter(qi_manager__id=pk)
    facility_name = [i.qi_manager for i in projects]
    tracked_projects = TestedChange.objects.values_list('project_id', flat=True)

    context = {"projects": projects,
               "facility_name": facility_name[0],
               "tracked_projects":tracked_projects,
               }
    return render(request, "project/qi_creators.html", context)


@login_required(login_url='login')
def completed_closed(request, pk):
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
               "title": "Completed or Closed",
               }
    return render(request, "project/department_projects.html", context)


@login_required(login_url='login')
def ongoing(request, pk):
    projects = QI_Projects.objects.filter(measurement_status=pk)

    facility_name = pk
    context = {"projects": projects,
               "facility_name": facility_name,
               "title": "Strated or Ongoing",
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
               "tracked_projects":tracked_projects,
               # "title": "Completed or Closed",
               }
    return render(request, "project/department_projects.html", context)


@login_required(login_url='login')
def tested_change(request, pk):
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
        "form": form
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
    return render(request, 'project/update_test_of_change.html', context)


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
def add_qi_team_member(request):
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        form = Qi_team_membersForm(request.POST)
        if form.is_valid():
            form.save()

            # redirect back to the page the user was from after saving the form
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = Qi_team_membersForm()
    context = {"form": form,
               "title": "add qi team member",
               }
    return render(request, "project/add_program_project.html", context)


@login_required(login_url='login')
def update_qi_team_member(request, pk):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    item = Qi_team_members.objects.get(id=pk)
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
    }
    return render(request, 'project/add_program_project.html', context)


@login_required(login_url='login')
def qi_team_members(request):
    # # User = get_user_model()
    # # team = User.objects.all()
    # context = {"team": team}

    qi_teams = Qi_team_members.objects.all()

    # qi_managers_list = Qi_managers.objects.all()
    projects = QI_Projects.objects.all()
    #
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
        } for x in projects
    ]
    qi_team_members_with_projects = pd.DataFrame(list_of_projects)
    qi_team_members_with_projects['First name'] = qi_team_members_with_projects['First name'].str.title()
    qi_team_members_with_projects['Last name'] = qi_team_members_with_projects['Last name'].str.title()

    # # pandas count frequency of column value in another dataframe column
    # qi_managers_with_projects["Projects Supervising"] = qi_managers_with_projects["First name"].map(
    #     qi_managers_with_projects["First name"].value_counts()).fillna(0).astype(int)
    # qi_managers_with_projects = qi_managers_with_projects.groupby(
    #     ['First name', 'Last name', 'Email', 'Phone Number', 'Designation', 'Date created']).max(
    #     "Projects Supervising").reset_index()

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
        } for x in qi_teams
    ]
    # convert data from database to a dataframe
    qi_team_members_df = pd.DataFrame(list_of_projects)

    merged_df = qi_team_members_with_projects.merge(qi_team_members_df, how='left', on=['Email', 'Phone Number'])
    # merged_df=qi_team_members_with_projects.merge(qi_team_members_df,how='left')

    # print(merged_df.columns)
    merged_df = merged_df[['First name_x', 'Last name_x', 'Email', 'Phone Number', 'User_id',
                           'QI_team_member_id',
                           'Designation', 'Date created_x', 'Facility_x']]
    merged_df = merged_df.rename(
        columns={"First name_x": "First name", "Last name_x": "Last name", "Facility_x": "Facility",
                 "Date created_x": "Date created"})

    # # pandas count frequency of column value in another dataframe column
    merged_df["Projects created"] = merged_df["User_id"].map(
        merged_df["User_id"].value_counts()).fillna(0).astype(int)

    #
    merged_df['Facility'] = merged_df['Facility'].astype(str)
    qi_team_members_with_projects = merged_df.groupby(
        ['First name', 'Last name', 'Email', 'Phone Number', 'Designation', 'Date created', "Facility"]).max(
        "Projects created").reset_index()

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

    del qi_team_members_with_projects['User_id']
    # del qi_team_members_without_projects['Date created']
    qi_team_members_ = pd.concat([qi_team_members_with_projects, qi_team_members_without_projects])
    # print("qi_team_members_")
    qi_team_members_ = qi_team_members_.sort_values("Facility")
    qi_team_members_.reset_index(drop=True, inplace=True)
    qi_team_members_.index += 1

    # qi_managers = qi_managers.sort_values("Projects Supervising", ascending=False).reset_index()
    # qi_managers.reset_index(drop=True, inplace=True)
    # qi_managers.index += 1
    # # del qi_managers['QI_manager id']
    # del qi_managers['index']
    # # print(qi_managers)
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


@login_required(login_url='login')
def qi_managers(request):
    qi_managers_list = Qi_managers.objects.all()
    qi_managers_ = QI_Projects.objects.all()

    # Get df for QI managers with projects
    list_of_projects = [
        {
            # {'project_ids': x.id,
            'First name': x.qi_manager.first_name,
            'Last name': x.qi_manager.last_name,
            'Email': x.qi_manager.email,
            'Phone Number': x.qi_manager.phone_number,
            'QI_manager_id': x.qi_manager.id,
            'Designation': x.qi_manager.designation,
            'Date created': x.qi_manager.date_created,
        } for x in qi_managers_
    ]
    qi_managers_with_projects = pd.DataFrame(list_of_projects)
    # print("qi_managers_with_projects")
    # print(qi_managers_with_projects)
    # pandas count frequency of column value in another dataframe column
    qi_managers_with_projects["Projects Supervising"] = qi_managers_with_projects["First name"].map(
        qi_managers_with_projects["First name"].value_counts()).fillna(0).astype(int)
    qi_managers_with_projects = qi_managers_with_projects.groupby(
        ['First name', 'Last name', 'Email', 'Phone Number', 'Designation', 'Date created']).max(
        "Projects Supervising").reset_index()

    # Get df for QI managers with projects
    list_of_projects = [
        {
            # {'project_ids': x.id,
            'First name': x.first_name,
            'Last name': x.last_name,
            'Email': x.email,
            'Phone Number': x.phone_number,

            'QI_manager_id': x.id,
            'Designation': x.designation,
            'Date created': x.date_created,
        } for x in qi_managers_list
    ]
    # convert data from database to a dataframe
    qi_managers_without_projects = pd.DataFrame(list_of_projects)
    qi_managers_without_projects["Projects Supervising"] = 0
    qi_managers_without_projects = qi_managers_without_projects[
        ~qi_managers_without_projects['QI_manager_id'].isin(list(qi_managers_with_projects['QI_manager_id']))]

    # Join df for all QI managers with and without
    qi_managers = pd.concat([qi_managers_with_projects, qi_managers_without_projects])
    qi_managers = qi_managers.sort_values("Projects Supervising", ascending=False).reset_index()
    qi_managers.reset_index(drop=True, inplace=True)
    qi_managers.index += 1
    # del qi_managers['QI_manager id']
    del qi_managers['index']
    # print(qi_managers)

    context = {
        "qi_managers_list": qi_managers_list,
        "qi_managers": qi_managers,
    }
    return render(request, "project/qi_managers.html", context)


@login_required(login_url='login')
def archived(request):
    return render(request, "project/archived.html")


@login_required(login_url='login')
def audit_trail(request):
    return render(request, "project/audit_trail.html")


@login_required(login_url='login')
def comments(request):
    all_comments = ProjectComments.objects.all().order_by('-comment_updated')
    all_responses = ProjectResponses.objects.values_list('comment_id', flat=True)
    context = {
        "all_comments": all_comments,
        "all_responses": all_responses,
    }
    return render(request, "project/comments.html", context)


@login_required(login_url='login')
def comments_no_response(request):
    all_comments = ProjectComments.objects.all().order_by('-comment_updated')
    all_responses = ProjectResponses.objects.values_list('comment_id', flat=True)
    context = {
        "all_comments": all_comments,
        "all_responses": all_responses,
    }
    return render(request, "project/comments_no_response.html", context)


@login_required(login_url='login')
def comments_with_response(request):
    all_comments = ProjectComments.objects.all().order_by('-comment_updated')
    all_responses = ProjectResponses.objects.values_list('comment_id', flat=True)
    context = {
        "all_comments": all_comments,
        "all_responses": all_responses,
    }
    return render(request, "project/comments_with_response.html", context)


@login_required(login_url='login')
def single_project_comments(request, pk):
    all_comments = ProjectComments.objects.filter(qi_project_title__id=pk).order_by('-comment_updated')

    all_responses = ProjectResponses.objects.filter(comment__qi_project_title_id=pk).order_by('-response_updated_date')

    all_responses_ids = ProjectResponses.objects.values_list('comment_id', flat=True)

    facility_project = QI_Projects.objects.get(id=pk)

    pro_owner = facility_project.projectcomments_set.all()
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
        "all_responses": all_responses,
        "facility_project": facility_project,
        "all_responses_ids": all_responses_ids,

    }
    return render(request, "project/single_comment.html", context)


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
    form = ResourcesForm(instance=item)
    if request.method == "POST":
        form = ResourcesForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(request.session['page_from'])
    # else:
    #     form = ResourcesForm(instance=item)
    context = {
        "form": form,
        "title": "Update Resource",
    }
    return render(request, 'project/update_resource.html', context)


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
    context = {"all_resources": all_resources}
    return render(request, "project/resources.html", context)


def line_chart(df, x_axis, y_axis, title):
    fig = px.line(df, x=x_axis, y=y_axis, text=y_axis, title=title,
                  hover_name=None, hover_data={"tested of change": True,
                                               "achievements (%)": True, }
                  )

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
                       arrowhead=1)
    fig.add_annotation(x=0.5, y=90,
                       text="90 %",
                       showarrow=True,
                       arrowhead=1)
    fig.add_annotation(x=0, y=50,
                       text="50 %",
                       showarrow=True,
                       arrowhead=1)
    fig.update_layout({
        'plot_bgcolor': 'rgba(0, 0, 0, 0)',
        'paper_bgcolor': 'rgba(0, 0, 0, 0)',
    })
    # fig.update_traces(texttemplate='%{text:.s}')

    return fig.to_html()


def bar_chart_horizontal(df, x_axis, y_axis, title):
    # df[x_axis]=df[x_axis].str.split(" ").str[0]

    fig = px.bar(df, x=y_axis, y=x_axis, text=y_axis, title=title, orientation='h'
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

    fig = px.bar(df, x=x_axis, y=y_axis, text=y_axis, title=title,
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


@login_required(login_url='login')
def single_project(request, pk):
    facility_project = QI_Projects.objects.get(id=pk)
    # get other facility projects
    other_projects = QI_Projects.objects.filter(facility_name=facility_project.facility_name)
    # Hit db once
    test_of_change_qs = TestedChange.objects.all()
    # check comments
    all_comments = ProjectComments.objects.filter(qi_project_title__id=facility_project.id).order_by('-comment_updated')

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

        print(f"list_of_projects['project'].unique() : {list_of_projects['project'].unique()}")

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

        project_performance = prepare_trends(df)

        facility_proj_performance = bar_chart(df_other_projects, "department(s)", "total projects", "facility projects")

        context = {"facility_project": facility_project, "test_of_change": changes,
                   "project_performance": project_performance, "facility_proj_performance": facility_proj_performance,
                   "pro_perfomance_trial": pro_perfomance_trial, "form": form, "all_comments": all_comments}

    else:
        project_performance = {}
        facility_proj_performance = {}
        context = {"facility_project": facility_project, "test_of_change": changes,
                   "project_performance": project_performance, "facility_proj_performance": facility_proj_performance,
                   "pro_perfomance_trial": pro_perfomance_trial, "form": form, "all_comments": all_comments}

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
