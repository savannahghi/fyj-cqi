import pandas as pd
import numpy as np
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Count
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect

from account.forms import NewUserForm, UpdateUserForm
from .models import QI_Projects
# from .forms import QI_ProjectsForm, Close_projectForm, CreateUserForm, AccountForm
from .forms import QI_ProjectsForm, Close_projectForm, TestedChangeForm, ProjectCommentsForm, ProjectResponsesForm
from .filters import *

import plotly.express as px
import plotly.graph_objects as go
from plotly.offline import plot
import plotly.offline as opy


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


def prepare_viz(list_of_projects, pk):


    # convert data from database to a dataframe
    list_of_projects = pd.DataFrame(list_of_projects)

    list_of_projects = list_of_projects[list_of_projects['department'] == pk].sort_values("achievements")

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
    qi_list = QI_Projects.objects.all()
    # best_performing = TestedChange.objects.filter(achievements__gte=00.0).distinct()
    testedChange = TestedChange.objects.all()

    # my_filters = TestedChangeFilter(request.GET, queryset=best_performing)

    if testedChange:
        best_performing_df = [
            {'project': x.project.project_title,
             'month_year': x.month_year,
             'achievements': x.achievements,
             "project_id": x.project.id,
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

        best_performing['project'] = best_performing['project'] + " (" + best_performing['achievements'].astype(
            int).astype(str) + "%)"
        keys = list(best_performing['project'])
        project_id_values = list(best_performing['project_id'])
        best_performing_dic = dict(zip(keys, project_id_values))
        request.session['project_id_values'] = project_id_values

    if qi_list:
        list_of_projects = [
            {'facility': x.facility,
             'subcounty': x.sub_county.sub_counties,
             'county': x.county.county_name,
             'department': x.departments.department,

             } for x in qi_list
        ]
        # convert data from database to a dataframe
        list_of_projects = pd.DataFrame(list_of_projects)
        list_of_projects_fac = list_of_projects.copy()
        list_of_projects_fac['facility'] = list_of_projects_fac['facility'].str.split(" ").str[0]
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


    form = QI_ProjectsForm()
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

               }
    return render(request, "project/dashboard.html", context)


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
    return render(request, "project/add_project.html", context)


@login_required(login_url='login')
def deep_dive_facilities(request):
    return render(request, "project/deep_dive_facilities.html")


@login_required(login_url='login')
def facilities_landing_page(request):
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
    else:
        facility_proj_performance = {}
        departments_viz = {}
        status_viz = {}

    context = {"qi_list": qi_list, "num_post": num_post, "projects": projects,
               "my_filters": my_filters, "qi_lists": qi_lists,
               "facility_proj_performance": facility_proj_performance,
               "departments_viz": departments_viz,
               "status_viz": status_viz,
               }
    return render(request, "project/facility_landing_page.html", context)


@login_required(login_url='login')
def facility_project(request, pk):
    projects = QI_Projects.objects.filter(facility=pk).order_by("-date_updated")

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
               "title": "Ongoing",
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
    context = {"projects": projects,
               "facility_name": facility_name,
               "title": "Ongoing",
               }
    return render(request, "project/department_projects.html", context)


@login_required(login_url='login')
def department_filter_project(request, pk):
    projects = QI_Projects.objects.filter(departments__department=pk)
    project_id_values = request.session['project_id_values']

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

    pro_perfomance_trial = prepare_viz(list_of_projects, pk)

    facility_name = pk

    context = {"projects": projects,
               "facility_name": facility_name,
               "title": "Ongoing",
               "pro_perfomance_trial": pro_perfomance_trial,

               }
    return render(request, "project/department_filter_projects.html", context)


@login_required(login_url='login')
def facility_filter_project(request, pk):
    projects = QI_Projects.objects.filter(facility=pk).order_by("-date_updated")
    project_id_values = request.session['project_id_values']

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

    facility_name = pk

    context = {"projects": projects,
               "facility_name": facility_name,
               "title": "Ongoing",
               "pro_perfomance_trial": pro_perfomance_trial,

               }
    return render(request, "project/department_filter_projects.html", context)


@login_required(login_url='login')
def qicreator_filter_project(request, pk):
    # projects = QI_Projects.objects.filter(facility=pk).order_by("-date_updated")
    projects = QI_Projects.objects.filter(created_by__username=pk)
    project_id_values = request.session['project_id_values']

    # accessing facility qi projects
    # use two underscore to the field with foreign key
    # list_of_projects = TestedChange.objects.filter(project_id__in=project_id_values).order_by('-achievements')
    testedChange = TestedChange.objects.filter(project__created_by__username=pk)
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
    # pro_perfomance_trial = prepare_viz(list_of_projects, pk)

    facility_name = pk

    context = {"projects": projects,
               "facility_name": facility_name,
               "title": "Ongoing",
               "pro_perfomance_trial": pro_perfomance_trial,

               }
    return render(request, "project/department_filter_projects.html", context)


@login_required(login_url='login')
def county_filter_project(request, pk):
    # projects = QI_Projects.objects.filter(facility=pk).order_by("-date_updated")
    projects = QI_Projects.objects.filter(county__county_name=pk)
    project_id_values = request.session['project_id_values']

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
    print(list_of_projects)

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
    # pro_perfomance_trial = prepare_viz(list_of_projects, pk)

    facility_name = pk

    context = {"projects": projects,
               "facility_name": facility_name,
               "title": "Ongoing",
               "pro_perfomance_trial": pro_perfomance_trial,

               }
    return render(request, "project/department_filter_projects.html", context)


@login_required(login_url='login')
def sub_county_filter_project(request, pk):
    # projects = QI_Projects.objects.filter(facility=pk).order_by("-date_updated")
    projects = QI_Projects.objects.filter(sub_county__sub_counties=pk)
    project_id_values = request.session['project_id_values']

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
    print(list_of_projects)

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
    # pro_perfomance_trial = prepare_viz(list_of_projects, pk)

    facility_name = pk

    context = {"projects": projects,
               "facility_name": facility_name,
               "title": "Ongoing",
               "pro_perfomance_trial": pro_perfomance_trial,

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
    context = {"projects": projects,
               "facility_name": facility_name,
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
def qi_team_members(request):
    User = get_user_model()
    team = User.objects.all()
    context = {"team": team}
    return render(request, "project/qi_team_members.html", context)


@login_required(login_url='login')
def qi_managers(request):
    return render(request, "project/qi_managers.html")


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
    return render(request, "project/resources.html")


def line_chart(df, x_axis, y_axis, title):
    fig = px.line(df, x=x_axis, y=y_axis, text=y_axis, title=title,
                  hover_name=None, hover_data={"tested of change": True,
                                               "achievements": True, })

    fig.update_traces(textposition='top center')
    # fig.add_trace(go.Line(x=df[x_axis], y=df[y_axis], mode='markers'))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)
    fig.add_hline(y=90, line_width=1, line_dash="dash", line_color="green")
    fig.add_hline(y=75, line_width=1, line_dash="dash", line_color="red")
    fig.add_annotation(x=0, y=75,
                       text="75 %",
                       showarrow=True,
                       arrowhead=1)
    fig.add_annotation(x=0.5, y=90,
                       text="90 %",
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
    project_performance = line_chart(df, "month_year", "achievements", title)
    return project_performance


@login_required(login_url='login')
def single_project(request, pk):
    facility_project = QI_Projects.objects.get(id=pk)
    # get other facility projects
    other_projects = QI_Projects.objects.filter(facility=facility_project.facility)
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
    list_of_projects = TestedChange.objects.filter(project_id__facility=facility_project.facility).order_by(
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
