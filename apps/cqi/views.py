# import os.path
import csv
import itertools
from datetime import datetime
from itertools import tee, chain

import inflect
import pandas as pd
# from django.contrib.auth import get_user_model
from django.apps import apps
from django.contrib.auth.decorators import login_required
# from django.core.files.storage import FileSystemStorage
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist

from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db import IntegrityError, transaction
# from django.db.models import Count, Q
# from django.forms import forms
from django.db.models import Count, Q, F, Sum
from django.urls import reverse
from django.utils import timezone
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404

from apps.account.forms import UpdateUserForm
# from config import settings

from .forms import QI_ProjectsForm, TestedChangeForm, ProjectCommentsForm, ProjectResponsesForm, \
    QI_ProjectsSubcountyForm, QI_Projects_countyForm, QI_Projects_hubForm, QI_Projects_programForm, Qi_managersForm, \
    DepartmentForm, CategoryForm, Sub_countiesForm, FacilitiesForm, CountiesForm, ResourcesForm, Qi_team_membersForm, \
    ArchiveProjectForm, QI_ProjectsConfirmForm, StakeholderForm, MilestoneForm, ActionPlanForm, Lesson_learnedForm, \
    BaselineForm, CommentForm, HubForm, SustainmentPlanForm, ProgramForm, RootCauseImagesForm, TriggerForm, \
    BestPerformingForm, ShowTriggerForm
from .filters import *

import plotly.express as px
from plotly.offline import plot
from io import BytesIO
from reportlab.pdfgen import canvas


@transaction.atomic
def load_data(request):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == 'POST':
        file = request.FILES['file']
        # Read the data from the an excel file into a pandas DataFrame
        keyword = "faci"
        xls_file = pd.ExcelFile(file)
        sheet_names = [sheet for sheet in xls_file.sheet_names if keyword.upper() in sheet.upper()]
        if sheet_names:
            dfs = pd.read_excel(file, sheet_name=sheet_names)
            df = pd.concat([df.assign(sheet_name=name) for name, df in dfs.items()])
            df = df[list(df.columns[:2])]
            if len(df.columns) == 2:
                df.fillna(0, inplace=True)
                df[df.columns[0]] = df[df.columns[0]].astype(int)
                df[df.columns[1]] = df[df.columns[1]].astype(str)
                # Iterate over each row in the DataFrame
                for index, row in df.iterrows():
                    mfl_code = row[df.columns[0]]
                    name = row[df.columns[1]]
                    try:
                        # either create a new facility object if it doesn't exist in the database, or retrieve the
                        # existing facility object if it does. If the facility already exists, the name is updated
                        # and the object is saved.
                        facility, created = Facilities.objects.get_or_create(
                            id=uuid.uuid4(),  # use a new UUID as the primary key
                            defaults={'mfl_code': mfl_code, 'name': name},
                        )
                        if not created:
                            # Facility already exists, update the name
                            facility.name = name
                            facility.save()
                    except IntegrityError as e:
                        pass
                messages.success(request, f'Data successfully saved in the database!')
                return redirect('show_data_verification')
            else:
                # Notify the user that the data is incorrect
                messages.error(request, f'Kindly confirm if {file} has all data columns. The file has'
                                        f'{len(df.columns)} columns')
                redirect('load_data')
        else:
            # Notify the user that the data already exists
            messages.error(request, f"Uploaded file (with data) should have a worksheet named 'facility'.")
            redirect('load_data')

    return render(request, 'dqa/upload.html')


# Create your views here.
def download_pdf(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="lessons.pdf"'
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.setTitle('Lessons Learned Report')
    p.setFont('Helvetica', 24)
    p.drawString(100, 750, 'Lessons Learned Report')

    p.setFont('Helvetica', 14)
    p.drawString(100, 700, 'Project Name')
    p.drawString(300, 700, 'Problem or Opportunity')
    p.drawString(100, 650, 'Key Successes')
    p.drawString(300, 650, 'Challenges')
    p.drawString(100, 600, 'Best Practices')
    p.drawString(300, 600, 'Recommendations')
    p.drawString(100, 550, 'Resources')
    p.drawString(300, 550, 'Created By')
    p.drawString(100, 500, 'Modified By')
    p.drawString(300, 500, 'Future Plans')
    p.drawString(100, 450, 'Date Created')
    p.drawString(300, 450, 'Date Modified')

    p.setFont('Helvetica', 12)
    lessons = Lesson_learned.objects.all()
    y = 400
    for lesson in lessons:
        p.drawString(100, y, str(lesson.project_name).encode('utf-8'))
        p.drawString(300, y, str(lesson.problem_or_opportunity).encode('utf-8'))
        p.drawString(100, y - 50, str(lesson.key_successes).encode('utf-8'))
        p.drawString(300, y - 50, str(lesson.challenges).encode('utf-8'))
        p.drawString(100, y - 100, str(lesson.best_practices).encode('utf-8'))
        p.drawString(300, y - 100, str(lesson.recommendations).encode('utf-8'))
        p.drawString(100, y - 150, str(lesson.resources).encode('utf-8'))
        p.drawString(300, y - 150, str(lesson.created_by).encode('utf-8'))
        p.drawString(100, y - 200, str(lesson.modified_by).encode('utf-8'))
        p.drawString(300, y - 200, str(lesson.future_plans).encode('utf-8'))
        p.drawString(100, y - 250, str(lesson.date_created).encode('utf-8'))
        p.drawString(300, y - 250, str(lesson.date_modified).encode('utf-8'))
        y -= 300

    p.showPage()
    p.save()
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response


def download_lessons(request):
    if not request.user.first_name:
        return redirect("profile")
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="lessons.csv"'

    writer = csv.writer(response)
    writer.writerow(['Program Project', 'Facility Project', 'Problem or Opportunity', 'Key Successes',
                     'Challenges', 'Best Practices', 'Recommendations',
                     'Resources', 'Created By', 'Modified By',
                     'Future Plans', 'Date Created', 'Date Modified'])

    lessons = Lesson_learned.objects.all()
    for lesson in lessons:
        writer.writerow([lesson.program, lesson.project_name, lesson.problem_or_opportunity,
                         lesson.key_successes, lesson.challenges,
                         lesson.best_practices, lesson.recommendations,
                         lesson.resources, lesson.created_by, lesson.modified_by,
                         lesson.future_plans, lesson.date_created, lesson.date_modified])

    return response


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
    if "department" == col.lower():
        list_of_projects = list_of_projects[list_of_projects[col] == pk].sort_values("achievements")
    # else:
    # list_of_projects = list_of_projects[list_of_projects[col] == pk].sort_values("achievements")
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

        values = list_of_projects['cqi'].unique()
        # for i in range(len(keys)):
        #     dicts[keys[i]] = values[i]
        for key, value in zip(keys, values):
            dicts[key] = value

        lst = []
        for i in list_of_projects['project_id'].unique():
            # get the first rows of the dfs
            a = list_of_projects[list_of_projects['project_id'] == i].sort_values("month_year", ascending=False)
            # append them in a list
            lst.append(a.head(1))

        # concat and sort them by cqi id
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
    return pro_perfomance_trial


def prepare_bar_chart_from_df(list_of_projects, col, title, projects=None):
    list_of_projects = list_of_projects[col].value_counts().rename_axis(col).reset_index(name='counts')
    list_of_projects = list_of_projects.T
    list_of_projects.columns = list_of_projects.iloc[0]
    list_of_projects = list_of_projects.iloc[1:]
    if projects is not None:
        list_of_projects['All QI projects'] = projects
    list_of_projects = list_of_projects.T.reset_index().sort_values("counts", ascending=False)

    if "facility" in list_of_projects.columns:
        # filter top 20 facilities
        facility_proj_performance = bar_chart(list_of_projects.head(20), col, "counts", title)
    else:
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


def create_df(qi_list, col1):
    list_of_projects = [
        {col1: x.county.county_name if hasattr(x, 'county') else x.hub.hub if hasattr(x,
                                                                                      'hub') else x.program.program,
         'department': x.departments.department,
         } for x in qi_list
    ]
    # convert data from database to a dataframe
    list_of_projects = pd.DataFrame(list_of_projects)
    list_of_projects_county = list_of_projects.copy()
    list_of_projects_county[col1] = list_of_projects_county[col1]
    return list_of_projects_county


def prepare_bar_charts_dashboard(list_of_projects):
    p = inflect.engine()

    # get number of unique subcounties and counties
    num_subcounties = list_of_projects['subcounty'].nunique()
    num_counties = list_of_projects['county'].nunique()
    num_hubs = list_of_projects['hub'].nunique()
    num_programs = list_of_projects['program'].nunique()

    # prepare chart titles
    subcounty_title = f"{num_subcounties} {p.plural('subcounty', num_subcounties)} implementing QI initiatives"
    county_title = f"{num_counties} {p.plural('county', num_counties)} implementing QI initiatives"
    hub_title = f"{num_hubs} {p.plural('hub', num_hubs)} implementing QI initiatives"
    program_title = f"{num_programs} {p.plural('program', num_programs)} implementing QI initiatives"

    # create charts
    subcounty_qi_projects = prepare_bar_chart_from_df(list_of_projects, 'subcounty', subcounty_title)
    county_qi_projects = prepare_bar_chart_from_df(list_of_projects, 'county', county_title)
    hub_qi_projects = prepare_bar_chart_from_df(list_of_projects, 'hub', hub_title)
    program_qi_projects = prepare_bar_chart_from_df(list_of_projects, 'program', program_title)

    return subcounty_qi_projects, county_qi_projects, hub_qi_projects, program_qi_projects


def create_project_dataframes(county_qi_list, hub_qi_list, program_qi_list):
    list_of_projects_county = create_df(county_qi_list, "county") if county_qi_list else pd.DataFrame(
        columns=['county', 'department'])
    list_of_projects_hub = create_df(hub_qi_list, "hub") if hub_qi_list else pd.DataFrame(
        columns=['hub', 'department'])
    list_of_projects_program = create_df(program_qi_list, "program") if program_qi_list else pd.DataFrame(
        columns=['program', 'department'])
    return list_of_projects_county, list_of_projects_hub, list_of_projects_program


@login_required(login_url='login')
def dashboard(request):
    if not request.user.first_name:
        return redirect("profile")
    facility_qi_projects = None
    subcounty_qi_projects = None
    county_qi_projects = None
    hub_qi_projects = None
    program_qi_projects = None
    department_qi_projects = None
    best_performing_dic = None
    dicts = None
    testedChange_current = None
    qi_mans = None
    project_id_values = []
    percentage_form = BestPerformingForm(request.POST or None, initial={'percentage': '50'})
    if percentage_form.is_valid():
        selected_percentage = percentage_form.cleaned_data['percentage']
    else:
        selected_percentage = 50

    qi_list = QI_Projects.objects.all()

    sub_qi_list = Subcounty_qi_projects.objects.all()
    county_qi_list = County_qi_projects.objects.all()

    hub_qi_list = Hub_qi_projects.objects.all()
    program_qi_list = Program_qi_projects.objects.all()

    # selects related objects and filters based on the availability of project types
    tested_change = TestedChange.objects.select_related(
        "project",
        "program_project",
        "hub_project",
        "subcounty_project",
        "county_project"
    ).filter(
        Q(project__isnull=False) | Q(program_project__isnull=False) |
        Q(hub_project__isnull=False) | Q(subcounty_project__isnull=False) |
        Q(county_project__isnull=False)
    )
    # Initialize empty list to store project data
    projects = []
    # Loop through each TestedChange object
    for tc in tested_change:
        if tc.project is not None:
            project_type = "cqi"
            project = tc.project
        elif tc.program_project is not None:
            project_type = "program"
            project = tc.program_project
        elif tc.hub_project is not None:
            project_type = "program"
            project = tc.hub_project
        elif tc.subcounty_project is not None:
            project_type = "program"
            project = tc.subcounty_project
        elif tc.county_project is not None:
            project_type = "program"
            project = tc.county_project
        # Append project data to the list of projects
        projects.append({
            "cqi": project.project_title,
            "month_year": tc.month_year,
            "achievements": tc.achievements,
            "project_id": project.id,
            "project_qi_manager": project.qi_manager,
            "department": project.departments,
            "facility": (
                project.facility_name.name if hasattr(project, "facility_name") else (
                    project.program.program if hasattr(project, "program") else (
                        project.hub.hub if hasattr(project, "hub") else (
                            project.sub_county.sub_counties if hasattr(project, "sub_county") else (
                                project.county.county_name if hasattr(project, "county") else None
                            )
                        )
                    )
                )
            ),
            "project_type": project_type,
        })

    best_performing_df = pd.DataFrame(projects)

    # convert data from database to a dataframe
    if best_performing_df.shape[0] > 0:
        best_performing = pd.DataFrame(best_performing_df).sort_values("month_year", ascending=False)

        dfs = []
        for project in best_performing['cqi'].unique():
            a = best_performing[best_performing['cqi'] == project]
            a = a.sort_values("month_year", ascending=False)
            dfs.append(a.head(1))
        best_performing = pd.concat(dfs)

        best_performing = best_performing.sort_values("achievements", ascending=False)

        best_performing = best_performing[best_performing['achievements'] >= int(selected_percentage)]
        qi_mans = best_performing.copy()
        best_performing['cqi'] = best_performing['cqi'] + " (" + best_performing['achievements'].astype(
            int).astype(str) + "%)"

        qi_mans['achievements'] = qi_mans['achievements'].astype(int).astype(str) + " %"
        qi_mans['facility'] = qi_mans['facility'].str.replace(" ", "_")
        qi_mans.reset_index(drop=True, inplace=True)
        qi_mans.index += 1
        qi_mans = qi_mans[['project_qi_manager', 'facility', 'cqi', 'achievements', 'department']]
        qi_mans = qi_mans.rename(columns={"project_qi_manager": "Project QI Manager",
                                          "cqi": "Project", "facility": "Location",
                                          "department": "Department", "achievements": "Achievements"})

        keys = list(best_performing['cqi'])
        project_id_values = list(best_performing['project_id'])
        best_performing_dic = dict(zip(keys, project_id_values))
        request.session['project_id_values'] = str(project_id_values)
    else:
        best_performing_df = None

    if sub_qi_list:
        list_of_projects = [
            {'subcounty': x.sub_county.sub_counties,
             'county': x.county.county_name,
             'department': x.departments.department,
             } for x in sub_qi_list
        ]
        # convert data from database to a dataframe
        list_of_projects = pd.DataFrame(list_of_projects)
        list_of_projects_sub = list_of_projects.copy()
        list_of_projects_sub['subcounty'] = list_of_projects_sub['subcounty']
    else:
        list_of_projects_sub = pd.DataFrame(columns=['subcounty', 'county', 'department'])

    list_of_projects_county, list_of_projects_hub, list_of_projects_program = create_project_dataframes(
        county_qi_list, hub_qi_list, program_qi_list)
    if qi_list:
        list_of_projects = [
            {'facility': x.facility_name,
             'subcounty': x.sub_county.sub_counties,
             'hub': x.hub.hub,
             'county': x.county.county_name,
             'department': x.departments.department,
             } for x in qi_list
        ]
        # convert data from database to a dataframe
        list_of_projects = pd.DataFrame(list_of_projects)
        list_of_projects_fac = list_of_projects.copy()
        list_of_projects_fac['facility'] = list_of_projects_fac['facility'].astype(str).str.split(" ").str[0]

        list_of_projects = pd.concat([list_of_projects_fac, list_of_projects_sub, list_of_projects_county,
                                      list_of_projects_hub, list_of_projects_program
                                      ])
        if list_of_projects_fac['facility'].nunique() > 20:
            facility_qi_projects = prepare_bar_chart_from_df(list_of_projects_fac, 'facility',
                                                             f"Top 20 facilities out of "
                                                             f"{list_of_projects_fac['facility'].nunique()} "
                                                             f"implementing QI initiatives")
        elif list_of_projects_fac['facility'].nunique() > 1:
            facility_qi_projects = prepare_bar_chart_from_df(list_of_projects_fac, 'facility',
                                                             f"{list_of_projects_fac['facility'].nunique()} "
                                                             f"facilities implementing QI initiatives")
        else:
            facility_qi_projects = prepare_bar_chart_from_df(list_of_projects_fac, 'facility',
                                                             f"{list_of_projects_fac['facility'].nunique()} "
                                                             f"facility implementing QI initiatives")
        subcounty_qi_projects, county_qi_projects, hub_qi_projects, program_qi_projects = prepare_bar_charts_dashboard(
            list_of_projects)

        department_qi_projects = prepare_bar_chart_from_df(list_of_projects, 'department',
                                                           "Departments implementing specific QI initiatives")
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
             'cqi': x.project.project_title,
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
            values = list_of_projects['cqi'].unique()
            for i in range(len(keys)):
                dicts[keys[i]] = values[i]

            lst = []

            for i in list_of_projects['project_id'].unique():
                # get the first rows of the dfs
                a = list_of_projects[list_of_projects['project_id'] == i].sort_values("month_year", ascending=False)
                # append them in a list
                lst.append(a.head(1))

            # concat and sort them by cqi id
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
               "hub_qi_projects": hub_qi_projects,
               "program_qi_projects": program_qi_projects,
               "department_qi_projects": department_qi_projects,
               "best_performing": best_performing_dic,
               "pro_perfomance_trial": pro_perfomance_trial,
               # "my_filters":my_filters,
               "dicts": dicts,
               "qi_list": qi_list,
               "testedChange_current": testedChange_current,
               # "testedChange": testedChange,
               "qi_managers": qi_managers,
               "qi_mans": qi_mans,
               "project_id_values": project_id_values,
               "percentage_form": percentage_form,
               "selected_percentage": selected_percentage,

               }
    return render(request, "project/dashboard.html", context)


@login_required(login_url='login')
def update_qi_managers(request, pk):
    if not request.user.first_name:
        return redirect("profile")
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
    if not request.user.first_name:
        return redirect("profile")
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        form = QI_ProjectsConfirmForm(request.POST)
        county_form = QI_Projects_countyForm(request.POST)
        trigger_form = TriggerForm(request.POST)
        if form.is_valid() and county_form.is_valid() and trigger_form.is_valid():
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
            trigger_form.save()

            # redirect back to the page the user was from after saving the form
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = QI_ProjectsConfirmForm()
        county_form = QI_Projects_countyForm()
        trigger_form = ShowTriggerForm()
    context = {"form": form, "county_form": county_form, "trigger_form": trigger_form}
    return render(request, "project/add_project.html", context)

@login_required(login_url='login')
def choose_project_level(request):
    return render(request, "project/choose_project.html")


@login_required(login_url='login')
def add_project_facility(request):
    if not request.user.first_name:
        return redirect("profile")
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
            return redirect('single_project', post.id)
    else:
        form = QI_ProjectsForm(prefix='banned')

    context = {"form": form, "title": "facility"}
    return render(request, "project/add_facility_project.html", context)


@login_required(login_url='login')
def add_qi_manager(request):
    if not request.user.first_name:
        return redirect("profile")
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
    if not request.user.first_name:
        return redirect("profile")
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
    if not request.user.first_name:
        return redirect("profile")
    title = "ADD PROJECT COMPONENT"
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
    if not request.user.first_name:
        return redirect("profile")
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

@login_required(login_url='login')
def sub_counties_list(request):
    if not request.user.first_name:
        return redirect("profile")
    # TODO: add other insights like number of ongoing projects,
    sub_counties = Sub_counties.objects.all().order_by('counties__county_name')
    context = {'sub_counties': sub_counties}
    return render(request, 'project/sub_counties_list.html', context)

@login_required(login_url='login')
def update_fields(request):
    if not request.user.first_name:
        return redirect("profile")
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
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    sub_counties = get_object_or_404(Sub_counties, pk=pk)
    form = Sub_countiesForm(request.POST or None, instance=sub_counties)

    if request.method == 'POST':
        if form.is_valid():
            form.save()

            # # Save many-to-many relationships
            # form.save_m2m()
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
    if not request.user.first_name:
        return redirect("profile")
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
    if not request.user.first_name:
        return redirect("profile")
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
def add_hub(request):
    if not request.user.first_name:
        return redirect("profile")
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
    if not request.user.first_name:
        return redirect("profile")
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
    if not request.user.first_name:
        return redirect("profile")
    title = "ADD RESOURCES"
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        form = ResourcesForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.uploaded_by = request.user
            post.save()
            return HttpResponseRedirect(request.session['page_from'])
            # form = Qi_managersForm(prefix='expected')
    else:
        form = ResourcesForm()
    context = {"form": form, "title": title}
    return render(request, "project/add_qi_manager.html", context)


@login_required(login_url='login')
def add_project_subcounty(request):
    if not request.user.first_name:
        return redirect("profile")
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
            # return HttpResponseRedirect(request.session['page_from'])
            # Redirect the user to the detail page of the newly created object
            return redirect('single_project_subcounty', post.id)
    else:
        form = QI_ProjectsSubcountyForm()
    context = {"form": form, "title": "sub_county"}
    # return render(request, "project/add_subcounty_project.html", context)
    return render(request, "project/add_facility_project.html", context)


@login_required(login_url='login')
def add_project_county(request):
    if not request.user.first_name:
        return redirect("profile")
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        form = QI_Projects_countyForm(request.POST)
        if form.is_valid():
            project = form.save()
            project_id = project.id  # Get the ID of the newly created project
            project_url = reverse('single_project_county', args=[project_id])  # Construct the URL of the project page
            return redirect(project_url)  # Redirect the user to the project page
    else:
        form = QI_Projects_countyForm()
    context = {"form": form, "title": "county"}
    return render(request, "project/add_facility_project.html", context)


@login_required(login_url='login')
def add_project_hub(request):
    if not request.user.first_name:
        return redirect("profile")
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        form = QI_Projects_hubForm(request.POST)
        if form.is_valid():
            # form.save()
            project = form.save()
            project_id = project.id  # Get the ID of the newly created project
            project_url = reverse('single_project_hub', args=[project_id])  # Construct the URL of the project page
            return redirect(project_url)  # Redirect the user to the project page
            # redirect back to the page the user was from after saving the form
            # return HttpResponseRedirect(request.session['page_from'])
    else:
        form = QI_Projects_hubForm()
    context = {"form": form, "title": "hub"}
    return render(request, "project/add_facility_project.html", context)


@login_required(login_url='login')
def add_project_program(request):
    if not request.user.first_name:
        return redirect("profile")
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        form = QI_Projects_programForm(request.POST)
        if form.is_valid():
            project = form.save()
            project_id = project.id  # Get the ID of the newly created project
            project_url = reverse('single_project_program', args=[project_id])  # Construct the URL of the project page
            return redirect(project_url)  # Redirect the user to the project page
    else:
        form = QI_Projects_programForm()
    context = {"form": form, "title": "program"}
    return render(request, "project/add_facility_project.html", context)


@login_required(login_url='login')
def add_program(request):
    if not request.user.first_name:
        return redirect("profile")
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        form = ProgramForm(request.POST)
        if form.is_valid():
            form.save()

            # redirect back to the page the user was from after saving the form
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = ProgramForm()
    context = {"form": form, "title": "ADD PROGRAM"}
    return render(request, "project/add_qi_manager.html", context)


@login_required(login_url='login')
def add_trigger(request):
    if not request.user.first_name:
        return redirect("profile")
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        form = TriggerForm(request.POST)
        if form.is_valid():
            form.save()

            # redirect back to the page the user was from after saving the form
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = TriggerForm()
    context = {"form": form, "title": "ADD TRIGGER"}
    return render(request, "project/add_qi_manager.html", context)


@login_required(login_url='login')
def update_project(request, pk, program_name=None, facility_name=None, subcounty_name=None, hub_name=None,
                   county_name=None):
    if not request.user.first_name:
        return redirect("profile")
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    if facility_name:
        project = QI_Projects.objects.get(id=pk, facility_name__name=facility_name)
        title = "facility"
    elif program_name:
        project = Program_qi_projects.objects.get(id=pk, program__program=program_name)
        title = "program"
    elif subcounty_name:
        project = Subcounty_qi_projects.objects.get(id=pk, sub_county__sub_counties=subcounty_name)
        title = "subcounty"
    elif county_name:
        project = County_qi_projects.objects.get(id=pk, county__county_name=county_name)
        title = "county"
    elif hub_name:
        project = Hub_qi_projects.objects.get(id=pk, hub__hub=hub_name)
        title = "hub"

    if request.method == "POST":
        if title == "facility":
            form = QI_ProjectsForm(request.POST, request.FILES, instance=project)
        elif title == "program":
            form = QI_Projects_programForm(request.POST, request.FILES, instance=project)
        elif title == "subcounty":
            form = QI_ProjectsSubcountyForm(request.POST, request.FILES, instance=project)
        elif title == "county":
            form = QI_Projects_countyForm(request.POST, request.FILES, instance=project)
        elif title == "hub":
            form = QI_Projects_hubForm(request.POST, request.FILES, instance=project)
        if form.is_valid():
            # form.save()
            # # do not save first, wait to update foreign key
            post = form.save(commit=False)
            measurement_status = form.cleaned_data['measurement_status']
            # get clean data from the form
            if title == "facility":
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
            elif title == "program":
                facility_name = form.cleaned_data['program']
                facility_id = Program.objects.get(program=facility_name)
                # TRY TO HANDLE PROGRAM_QI_PROJECTS MODEL
                post.program = facility_id
            elif title == "subcounty":
                subcounty_name_ = form.cleaned_data['sub_county']
                facility_id = Sub_counties.objects.get(sub_counties=subcounty_name_)
                # TRY TO HANDLE PROGRAM_QI_PROJECTS MODEL
                post.sub_county = facility_id
            elif title == "county":
                facility_name = form.cleaned_data['county']
                facility_id = Counties.objects.get(county_name=facility_name)
                # TRY TO HANDLE PROGRAM_QI_PROJECTS MODEL
                post.program = facility_id
            elif title == "hub":
                facility_name = form.cleaned_data['hub']
                facility_id = Hub.objects.get(hub=facility_name)
                # TRY TO HANDLE PROGRAM_QI_PROJECTS MODEL
                post.program = facility_id

            # save
            post.save()

            # Save many-to-many relationships
            form.save_m2m()

            if measurement_status == "Completed-or-Closed":
                messages.error(request, "The CQI project has been successfully completed, achieving its objective of "
                                        "improving the quality of our services. As a result, we are closing the project "
                                        "and moving on to new initiatives. If you have any questions or require further "
                                        "information, please contact our admin team who will be happy to assist you. "
                                        "Thank you for your support throughout the project."
                               )
                return redirect('completed_closed', pk='Completed-or-Closed')
            else:
                # redirect back to the page the user was from after saving the form
                return HttpResponseRedirect(request.session['page_from'])
    else:
        if title == "facility":
            form = QI_ProjectsForm(instance=project)
        elif title == "program":
            form = QI_Projects_programForm(instance=project)
        elif title == "subcounty":
            form = QI_ProjectsSubcountyForm(instance=project)
        elif title == "county":
            form = QI_Projects_countyForm(instance=project)
        elif title == "hub":
            form = QI_Projects_hubForm(instance=project)
    context = {"form": form, "title": title, 'update': "update"}
    return render(request, "project/add_facility_project.html", context)


@login_required(login_url='login')
def deep_dive_facilities(request):
    if not request.user.first_name:
        return redirect("profile")
    return render(request, "project/deep_dive_facilities.html")

@login_required(login_url='login')
def make_archive_charts(list_of_projects):
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

        # concat and sort them by cqi id
        df_heads = pd.concat(lst).sort_values("achievements", ascending=False)
        keys = [project for project in list(df_heads['project_id'])]

        all_other_projects_trend = []
        for project in list_of_projects['cqi'].unique():
            all_other_projects_trend.append(
                prepare_trends(list_of_projects[list_of_projects['cqi'] == project], project))
        dicts = {}
        for i in range(len(keys)):
            dicts[keys[i]] = all_other_projects_trend[i]
        pro_perfomance_trial = dict(zip(keys, all_other_projects_trend))
        return pro_perfomance_trial, dicts

@login_required(login_url='login')
def archived(request):
    if not request.user.first_name:
        return redirect("profile")
    facility_proj_performance = None
    departments_viz = None
    status_viz = None
    pro_perfomance_trial = None
    dicts = None
    dicts = None

    # qi_list = QI_Projects.objects.all().order_by('-date_updated')
    # my_filters = QiprojectFilter(request.GET, queryset=qi_list)
    # qi_lists = my_filters.qs
    # qi_list = pagination_(request, qi_lists)

    # projects = QI_Projects.objects.all().order_by('-date_updated')
    # subcounty_projects = Subcounty_qi_projects.objects.all().order_by('-date_updated')
    # county_projects = County_qi_projects.objects.all().order_by('-date_updated')
    # hub_projects = Hub_qi_projects.objects.all().order_by('-date_updated')
    # program_projects = Program_qi_projects.objects.all().order_by('-date_updated')

    try:
        # Get a list of archived qi projects
        archived_projects_ = ArchiveProject.objects.filter(
            Q(qi_project_id__isnull=False) |
            Q(program_id__isnull=False) |
            Q(county_id__isnull=False) |
            Q(hub_id__isnull=False) |
            Q(subcounty_id__isnull=False),
            archive_project=True
        ).values_list('qi_project_id', 'program_id', 'county_id', 'hub_id', 'subcounty_id')

        archived_projects = [item for project in archived_projects_ for item in project if item is not None]

        # Apply filters to each of the 5 models
        qi_projects = QI_Projects.objects.filter(id__in=archived_projects).order_by('-date_updated')
        qi_filter = QiprojectFilter(request.GET, queryset=qi_projects)
        filtered_qi_projects = qi_filter.qs

        subcounty_projects = Subcounty_qi_projects.objects.filter(id__in=archived_projects).order_by('-date_updated')
        subcounty_filter = SubcountyQiprojectFilter(request.GET, queryset=subcounty_projects)
        filtered_subcounty_projects = subcounty_filter.qs

        county_projects = County_qi_projects.objects.filter(id__in=archived_projects).order_by('-date_updated')
        county_filter = CountyQiprojectFilter(request.GET, queryset=county_projects)
        filtered_county_projects = county_filter.qs

        hub_projects = Hub_qi_projects.objects.filter(id__in=archived_projects).order_by('-date_updated')
        hub_filter = HubQiprojectFilter(request.GET, queryset=hub_projects)
        filtered_hub_projects = hub_filter.qs

        program_projects = Program_qi_projects.objects.filter(id__in=archived_projects).order_by('-date_updated')
        program_filter = ProgramQiprojectFilter(request.GET, queryset=program_projects)
        filtered_program_projects = program_filter.qs

        # all_projects = list(chain(projects, subcounty_projects, hub_projects, county_projects, program_projects))
        all_projects = list(chain(filtered_qi_projects, filtered_subcounty_projects, filtered_county_projects,
                                  filtered_hub_projects, filtered_program_projects))
        # TODO: FINALIZE ON THE FILTER AND PAGINATION

        # Paginate the concatenated queryset
        paginator = Paginator(all_projects, 10)  # 10 items per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        # Apply pagination to the concatenated result
        filtered_projects = pagination_(request, all_projects)

        # concatenated_projects = concatenate_filters(filtered_qi_projects, filtered_subcounty_projects,
        #                                             filtered_county_projects, filtered_hub_projects,
        #                                             filtered_program_projects)
        # paginator = paginate(concatenated_projects)

        # Get a list of tracked qi projects
        tracked_projects_ = TestedChange.objects.filter(
            Q(project_id__isnull=False) |
            Q(program_project__isnull=False) |
            Q(county_project__isnull=False) |
            Q(hub_project__isnull=False) |
            Q(subcounty_project__isnull=False)
        ).values_list('project_id', 'program_project_id', 'county_project_id', 'hub_project_id', 'subcounty_project_id')

        tracked_projects = [item for project in tracked_projects_ for item in project if item is not None]
        # Get a list of archived qi projects
        archived_projects_ = ArchiveProject.objects.filter(
            Q(qi_project_id__isnull=False) |
            Q(program_id__isnull=False) |
            Q(county_id__isnull=False) |
            Q(hub_id__isnull=False) |
            Q(subcounty_id__isnull=False),
            archive_project=True
        ).values_list('qi_project_id', 'program_id', 'county_id', 'hub_id', 'subcounty_id')

        archived_projects = [item for project in archived_projects_ for item in project if item is not None]

        testedChange_current = TestedChange.objects.filter(
            Q(project_id__in=archived_projects) |
            Q(program_project_id__in=archived_projects) |
            Q(subcounty_project_id__in=archived_projects) |
            Q(county_project_id__in=archived_projects) |
            Q(hub_project_id__in=archived_projects)
        ).order_by('-achievements')

        # my_filters = TestedChangeFilter(request.GET, queryset=list_of_projects)
        # list_of_projects = my_filters.qs

        facility_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.project_id,
             'tested of change': x.tested_change,
             'facility': x.project,
             'cqi': x.project.project_title if x.project else None,
             'department': x.project.departments.department if x.project else None,
             } for x in testedChange_current
        ]
        subcounty_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.subcounty_project_id,
             'tested of change': x.tested_change,
             'facility': x.subcounty_project,
             'cqi': x.subcounty_project.project_title if x.subcounty_project else None,
             'department': x.subcounty_project.departments.department if x.subcounty_project else None,
             } for x in testedChange_current
        ]
        # county_projects = [
        #     {'achievements': x.achievements,
        #      'month_year': x.month_year,
        #      'project_id': x.county_project_id,
        #      'tested of change': x.tested_change,
        #      'facility': x.county_project,
        #      'cqi': x.county_project.project_title if x.county_project else None,
        #      'department': x.county_project.departments.department if x.county_project else None,
        #      } for x in testedChange_current
        # ]
        # program_projects = [
        #     {'achievements': x.achievements,
        #      'month_year': x.month_year,
        #      'project_id': x.program_project_id,
        #      'tested of change': x.tested_change,
        #      'facility': x.program_project,
        #      'cqi': x.program_project.project_title if x.program_project else None,
        #      'department': x.program_project.departments.department if x.program_project else None,
        #      } for x in testedChange_current
        # ]
        # hub_projects = [
        #     {'achievements': x.achievements,
        #      'month_year': x.month_year,
        #      'project_id': x.hub_project_id,
        #      'tested of change': x.tested_change,
        #      'facility': x.hub_project,
        #      'cqi': x.hub_project.project_title if x.hub_project else None,
        #      'department': x.hub_project.departments.department if x.hub_project else None,
        #      } for x in testedChange_current
        # ]

        # convert data from database to a dataframe
        facility_projects_df = pd.DataFrame(facility_projects)
        subcounty_projects_df = pd.DataFrame(subcounty_projects)
        county_projects_df = pd.DataFrame(county_projects)
        hub_projects_df = pd.DataFrame(hub_projects)
        program_projects_df = pd.DataFrame(program_projects)
        all_projects_df = pd.concat([facility_projects_df, subcounty_projects_df, county_projects_df,
                                     hub_projects_df, program_projects_df])
        list_of_projects = all_projects_df[all_projects_df['cqi'].notnull()]

        if list_of_projects.shape[0] > 0:
            pro_perfomance_trial, dicts = make_archive_charts(list_of_projects)
    except:
        all_projects = None
        qi_filter = None
        filtered_projects = None
        tracked_projects = None
        archived_projects = None
        pro_perfomance_trial = None

    context = {"qi_list": all_projects,
               "my_filters": qi_filter,
               "qi_lists": filtered_projects,
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


def pair_iterable_for_delta_changes(iterable):
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


@login_required(login_url='login')
def facilities_landing_page(request, project_type):
    if not request.user.first_name:
        return redirect("profile")
    facility_proj_performance = None
    departments_viz = None
    status_viz = None
    if project_type == "facility":
        qi_list = QI_Projects.objects.all().order_by('-date_updated')
        num_post = QI_Projects.objects.filter(created_by=request.user).count()
        projects = QI_Projects.objects.count()
        my_filters = QiprojectFilter(request.GET, queryset=qi_list)
        tracked_projects = TestedChange.objects.values_list('project_id', flat=True)
        archived_projects = ArchiveProject.objects.filter(archive_project=True).values_list('qi_project_id', flat=True)
    elif project_type == "program":
        qi_list = Program_qi_projects.objects.all().order_by('-date_updated')
        num_post = Program_qi_projects.objects.filter(created_by=request.user).count()
        projects = Program_qi_projects.objects.count()
        my_filters = ProgramQiprojectFilter(request.GET, queryset=qi_list)
        tracked_projects = TestedChange.objects.values_list('program_project_id', flat=True)
        archived_projects = ArchiveProject.objects.filter(archive_project=True).values_list('program_id', flat=True)
    elif project_type == "subcounty":
        qi_list = Subcounty_qi_projects.objects.all().order_by('-date_updated')
        num_post = Subcounty_qi_projects.objects.filter(created_by=request.user).count()
        projects = Subcounty_qi_projects.objects.count()
        my_filters = SubcountyQiprojectFilter(request.GET, queryset=qi_list)
        tracked_projects = TestedChange.objects.values_list('subcounty_project_id', flat=True)
        archived_projects = ArchiveProject.objects.filter(archive_project=True).values_list('subcounty_id', flat=True)
    elif project_type == "county":
        qi_list = County_qi_projects.objects.all().order_by('-date_updated')
        num_post = County_qi_projects.objects.filter(created_by=request.user).count()
        projects = County_qi_projects.objects.count()
        my_filters = CountyQiprojectFilter(request.GET, queryset=qi_list)
        tracked_projects = TestedChange.objects.values_list('county_project_id', flat=True)
        archived_projects = ArchiveProject.objects.filter(archive_project=True).values_list('county_id', flat=True)
    elif project_type == "hub":
        qi_list = Hub_qi_projects.objects.all().order_by('-date_updated')
        num_post = Hub_qi_projects.objects.filter(created_by=request.user).count()
        projects = Hub_qi_projects.objects.count()
        my_filters = HubQiprojectFilter(request.GET, queryset=qi_list)
        tracked_projects = TestedChange.objects.values_list('hub_project_id', flat=True)
        archived_projects = ArchiveProject.objects.filter(archive_project=True).values_list('hub_id', flat=True)
    qi_lists = my_filters.qs
    qi_list = pagination_(request, qi_lists)

    def prepare_landing_page(qi_lists):
        # if qi_lists:
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
        departments_viz = prepare_bar_chart_from_df(list_of_departments, "department", "QI per department",
                                                    projects)

        list_of_departments = [
            {'status': x.measurement_status,
             } for x in qi_lists
        ]
        list_of_departments = pd.DataFrame(list_of_departments)
        status_viz = prepare_bar_chart_from_df(list_of_departments, "status", "QI projects status", projects)
        return facility_proj_performance, departments_viz, status_viz

    if qi_lists:
        facility_proj_performance, departments_viz, status_viz = prepare_landing_page(qi_lists)
    # Pass the changes data to the template as context
    context = {"qi_list": qi_list, "num_post": num_post, "projects": projects,
               "my_filters": my_filters, "qi_lists": qi_lists,
               "facility_proj_performance": facility_proj_performance,
               "departments_viz": departments_viz,
               "status_viz": status_viz,
               "tracked_projects": tracked_projects,
               "archived_projects": archived_projects,
               "project_type": project_type,
               }
    return render(request, "project/facility_landing_page.html", context)


@login_required(login_url='login')
def program_landing_page(request):
    if not request.user.first_name:
        return redirect("profile")
    facility_proj_performance = None
    departments_viz = None
    status_viz = None

    qi_list = Program_qi_projects.objects.all().order_by('-date_updated')
    num_post = Program_qi_projects.objects.filter(created_by=request.user).count()
    projects = Program_qi_projects.objects.count()
    my_filters = ProgramQiprojectFilter(request.GET, queryset=qi_list)
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
    # Pass the changes data to the template as context
    context = {"qi_list": qi_list, "num_post": num_post, "projects": projects,
               "my_filters": my_filters, "qi_lists": qi_lists,
               "facility_proj_performance": facility_proj_performance,
               "departments_viz": departments_viz,
               "status_viz": status_viz,
               "tracked_projects": tracked_projects,
               "archived_projects": archived_projects,
               "title": "program"
               }
    return render(request, "project/facility_landing_page.html", context)


@login_required(login_url='login')
def facility_project(request, pk, project_type):
    if not request.user.first_name:
        return redirect("profile")
    if project_type == "facility":
        projects = QI_Projects.objects.filter(facility_name__id=pk).order_by("-date_updated")
        facility_name = projects.first().facility_name.name
        tracked_projects = TestedChange.objects.values_list('project_id', flat=True)
    elif project_type == "program":
        projects = Program_qi_projects.objects.filter(program__id=pk).order_by("-date_updated")
        facility_name = projects.first().program.program
        tracked_projects = TestedChange.objects.values_list('program_project_id', flat=True)
    elif project_type == "subcounty":
        projects = Subcounty_qi_projects.objects.filter(sub_county__id=pk).order_by("-date_updated")
        facility_name = projects.first().sub_county.sub_counties
        tracked_projects = TestedChange.objects.values_list('subcounty_project_id', flat=True)
    elif project_type == "county":
        projects = County_qi_projects.objects.filter(county__id=pk).order_by("-date_updated")
        facility_name = projects.first().county.county_name
        tracked_projects = TestedChange.objects.values_list('county_project_id', flat=True)
    elif project_type == "hub":
        projects = Hub_qi_projects.objects.filter(hub__id=pk).order_by("-date_updated")
        facility_name = projects.first().hub.hub
        tracked_projects = TestedChange.objects.values_list('hub_project_id', flat=True)
    context = {"projects": projects,
               "facility_name": facility_name,
               "title": "Ongoing",
               "tracked_projects": tracked_projects,
               "project_type": project_type,
               }
    return render(request, "project/facility_projects.html", context)


@login_required(login_url='login')
def department_project(request, pk):
    if not request.user.first_name:
        return redirect("profile")
    projects = QI_Projects.objects.filter(departments__id=pk)

    facility_name = projects.first().departments

    # qi_list = QI_Projects.objects.all().order_by('-date_updated')
    # num_post = QI_Projects.objects.filter(created_by=request.user).count()
    # if request.method=="POST":
    #     search=request.POST['searched']
    #     search=QI_Projects.objects.filter(facility__contains=search)
    #     projects = None
    #     context = {"qi_list": qi_list, "num_post": num_post,"projects":projects,
    #                "search":search
    #                }
    #     return render(request, "cqi/facility_landing_page.html", context)
    # else:
    #     projects = QI_Projects.objects.count()

    #     context = {"qi_list": qi_list, "num_post": num_post, "projects": projects,
    #
    #                }
    #     return render(request, "cqi/facility_landing_page.html", context)
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
def department_filter_project(request, pk):
    if not request.user.first_name:
        return redirect("profile")
    projects_tracked = []
    projects = QI_Projects.objects.filter(departments__department=pk)
    program_projects = Program_qi_projects.objects.filter(departments__department=pk)
    subcounty_program_projects = Subcounty_qi_projects.objects.filter(departments__department=pk)
    county_program_projects = County_qi_projects.objects.filter(departments__department=pk)
    hub_program_projects = Hub_qi_projects.objects.filter(departments__department=pk)
    all_projects = list(
        chain(projects, subcounty_program_projects, county_program_projects, hub_program_projects, program_projects))
    # projects = projects | program_projects
    # project_id_values = request.session['project_id_values']

    # accessing facility qi projects
    # use two underscore to the field with foreign key
    # list_of_projects = TestedChange.objects.filter(project_id__in=project_id_values).order_by('-achievements')
    testedChange = TestedChange.objects.all()
    # my_filters = TestedChangeFilter(request.GET, queryset=list_of_projects)
    # list_of_projects = my_filters.qs
    facility_name = pk
    number_of_projects_created = len(all_projects)
    try:
        # loop through both models QI_Projects and Program_qi_projects using two separate lists
        qi_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.project_id,
             'tested of change': x.tested_change,

             'facility': x.project.facility_name,
             'cqi': x.project.project_title,
             'department': x.project.departments.department,
             } for x in TestedChange.objects.filter(project__isnull=False)
        ]

        program_qi_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.program_project_id,
             'tested of change': x.tested_change,

             'facility': x.program_project.program.program,
             'cqi': x.program_project.project_title,
             'department': x.program_project.departments.department,
             } for x in TestedChange.objects.filter(program_project__isnull=False)
        ]
        subcounty_qi_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.subcounty_project_id,
             'tested of change': x.tested_change,

             'facility': x.subcounty_project.sub_county.sub_counties,
             'cqi': x.subcounty_project.project_title,
             'department': x.subcounty_project.departments.department,
             } for x in TestedChange.objects.filter(subcounty_project__isnull=False)
        ]
        county_qi_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.county_project_id,
             'tested of change': x.tested_change,

             'facility': x.county_project.county.county_name,
             'cqi': x.county_project.project_title,
             'department': x.county_project.departments.department,
             } for x in TestedChange.objects.filter(county_project__isnull=False)
        ]
        hub_qi_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.hub_project_id,
             'tested of change': x.tested_change,

             'facility': x.hub_project.hub.hub,
             'cqi': x.hub_project.project_title,
             'department': x.hub_project.departments.department,
             } for x in TestedChange.objects.filter(hub_project__isnull=False)
        ]
        # then concatenate the two lists to get a single list of dictionaries
        # Finally, you can create a dataframe from this list of dictionaries.
        qi_projects_df = pd.DataFrame(qi_projects)

        program_qi_projects_df = pd.DataFrame(program_qi_projects)
        subcounty_qi_projects_df = pd.DataFrame(subcounty_qi_projects)
        county_qi_projects_df = pd.DataFrame(county_qi_projects)
        hub_qi_projects_df = pd.DataFrame(hub_qi_projects)

        # program_qi_projects_df.columns = list(qi_projects_df.columns)

        list_of_projects = pd.concat([qi_projects_df,
                                      program_qi_projects_df,
                                      subcounty_qi_projects_df,
                                      county_qi_projects_df,
                                      hub_qi_projects_df
                                      ])
        pro_perfomance_trial = prepare_viz(list_of_projects, pk, "department")

        facility_name = pk

        # convert data from database to a dataframe
        # list_of_projects = pd.DataFrame(list_of_projects)
        keys = list_of_projects['project_id'].unique()
        projects_tracked = keys

        # difference
        number_of_projects_created = len(all_projects)
        number_of_projects_with_test_of_change = len(pro_perfomance_trial)
        difference = number_of_projects_created - number_of_projects_with_test_of_change
    except:
        number_of_projects_created = len(all_projects)
        number_of_projects_with_test_of_change = 0
        difference = number_of_projects_created - number_of_projects_with_test_of_change
        pro_perfomance_trial = None
    context = {"projects": all_projects,
               "facility_name": facility_name,
               "title": "Ongoing",
               "pro_perfomance_trial": pro_perfomance_trial,
               "difference": difference,
               "projects_tracked": projects_tracked,
               "program_projects": program_projects,
               "number_of_projects_created": number_of_projects_created,
               }
    return render(request, "project/department_filter_projects.html", context)


@login_required(login_url='login')
def qi_managers_filter_project(request, pk):
    if not request.user.first_name:
        return redirect("profile")
    projects_tracked = []

    projects = QI_Projects.objects.filter(qi_manager__id=pk)
    subcounty_projects = Subcounty_qi_projects.objects.filter(qi_manager__id=pk)
    county_projects = County_qi_projects.objects.filter(qi_manager__id=pk)
    hub_projects = Hub_qi_projects.objects.filter(qi_manager__id=pk)
    program_projects = Program_qi_projects.objects.filter(qi_manager__id=pk)
    all_projects = list(chain(projects, subcounty_projects, hub_projects, county_projects, program_projects))
    manager_name = all_projects[0].qi_manager
    number_of_projects_created = len(all_projects)
    try:
        qi_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.project_id,
             'tested of change': x.tested_change,

             'facility': x.project.facility_name,
             'cqi': x.project.project_title,
             'qi_manager': x.project.qi_manager.first_name,
             'qi_manager_email': x.project.qi_manager.email,
             } for x in TestedChange.objects.filter(project__qi_manager__id=pk)
        ]
        subcounty_qi_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.subcounty_project_id,
             'tested of change': x.tested_change,

             'facility': x.subcounty_project.sub_county.sub_counties,
             'cqi': x.subcounty_project.project_title,
             'qi_manager': x.subcounty_project.qi_manager.first_name,
             'qi_manager_email': x.subcounty_project.qi_manager.email,
             } for x in TestedChange.objects.filter(subcounty_project__qi_manager__id=pk)
        ]
        program_qi_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.program_project_id,
             'tested of change': x.tested_change,

             'facility': x.program_project.program.program,
             'cqi': x.program_project.project_title,
             'department': x.program_project.departments.department,
             } for x in TestedChange.objects.filter(program_project__qi_manager__id=pk)
        ]

        county_qi_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.county_project_id,
             'tested of change': x.tested_change,

             'facility': x.county_project.county.county_name,
             'cqi': x.county_project.project_title,
             'department': x.county_project.departments.department,
             } for x in TestedChange.objects.filter(county_project__qi_manager__id=pk)
        ]
        hub_qi_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.hub_project_id,
             'tested of change': x.tested_change,

             'facility': x.hub_project.hub.hub,
             'cqi': x.hub_project.project_title,
             'department': x.hub_project.departments.department,
             } for x in TestedChange.objects.filter(hub_project__qi_manager__id=pk)
        ]
        # then concatenate the two lists to get a single list of dictionaries
        # Finally, you can create a dataframe from this list of dictionaries.
        qi_projects_df = pd.DataFrame(qi_projects)
        program_qi_projects_df = pd.DataFrame(program_qi_projects)
        subcounty_qi_projects_df = pd.DataFrame(subcounty_qi_projects)
        county_qi_projects_df = pd.DataFrame(county_qi_projects)
        hub_qi_projects_df = pd.DataFrame(hub_qi_projects)

        list_of_projects = pd.concat([qi_projects_df,
                                      program_qi_projects_df,
                                      subcounty_qi_projects_df,
                                      county_qi_projects_df,
                                      hub_qi_projects_df
                                      ])
        projects_tracked = list_of_projects['project_id'].unique()
        manager_name = list(list_of_projects['qi_manager'].unique())[0]
        pro_perfomance_trial = prepare_viz(list_of_projects, manager_name, "qi_manager")

        # difference
        number_of_projects_created = len(all_projects)
        number_of_projects_with_test_of_change = len(pro_perfomance_trial)
        difference = number_of_projects_created - number_of_projects_with_test_of_change
    except:
        number_of_projects_created = len(all_projects)
        number_of_projects_with_test_of_change = 0
        difference = number_of_projects_created - number_of_projects_with_test_of_change
        pro_perfomance_trial = None

    context = {"projects": all_projects,
               "facility_name": manager_name,
               "title": "",
               "pro_perfomance_trial": pro_perfomance_trial,
               "difference": difference,
               "projects_tracked": projects_tracked,
               "number_of_projects_created": number_of_projects_created,
               }
    return render(request, "project/department_filter_projects.html", context)


@login_required(login_url='login')
def facility_filter_project(request, pk):
    if not request.user.first_name:
        return redirect("profile")
    projects_tracked = []
    projects = QI_Projects.objects.filter(facility_name__name=pk).order_by("-date_updated")
    subcounty_projects = Subcounty_qi_projects.objects.filter(sub_county__sub_counties=pk).order_by("-date_updated")
    county_projects = County_qi_projects.objects.filter(county__county_name=pk).order_by("-date_updated")
    hub_projects = Hub_qi_projects.objects.filter(hub__hub=pk).order_by("-date_updated")
    program_projects = Program_qi_projects.objects.filter(program__program=pk).order_by("-date_updated")
    all_projects = list(chain(projects, subcounty_projects, hub_projects, county_projects, program_projects))

    facility_name = pk
    number_of_projects_created = len(all_projects)
    try:
        qi_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.project_id,
             'tested of change': x.tested_change,

             'facility': x.project.facility_name,
             'cqi': x.project.project_title,
             'department': x.project.departments.department,
             } for x in TestedChange.objects.filter(project__facility_name__name=pk)
        ]
        fac_qi_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.project_id,
             'tested of change': x.tested_change,

             'facility': x.project.hub,
             'cqi': x.project.project_title,
             'department': x.project.departments.department,
             } for x in TestedChange.objects.filter(project__hub__hub=pk)
        ]
        program_qi_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.program_project_id,
             'tested of change': x.tested_change,

             'facility': x.program_project.program.program,
             'cqi': x.program_project.project_title,
             'department': x.program_project.departments.department,
             } for x in TestedChange.objects.filter(program_project__program__program=pk)
        ]
        subcounty_qi_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.subcounty_project_id,
             'tested of change': x.tested_change,

             'facility': x.subcounty_project.sub_county.sub_counties,
             'cqi': x.subcounty_project.project_title,
             'department': x.subcounty_project.departments.department,
             } for x in TestedChange.objects.filter(subcounty_project__sub_county__sub_counties=pk)
        ]
        county_qi_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.county_project_id,
             'tested of change': x.tested_change,

             'facility': x.county_project.county.county_name,
             'cqi': x.county_project.project_title,
             'department': x.county_project.departments.department,
             } for x in TestedChange.objects.filter(county_project__county__county_name=pk)
        ]
        hub_qi_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.hub_project_id,
             'tested of change': x.tested_change,

             'facility': x.hub_project.hub.hub,
             'cqi': x.hub_project.project_title,
             'department': x.hub_project.departments.department,
             } for x in TestedChange.objects.filter(hub_project__hub__hub=pk)
        ]
        # then concatenate the two lists to get a single list of dictionaries
        # Finally, you can create a dataframe from this list of dictionaries.
        qi_projects_df = pd.DataFrame(qi_projects)

        program_qi_projects_df = pd.DataFrame(program_qi_projects)
        subcounty_qi_projects_df = pd.DataFrame(subcounty_qi_projects)
        county_qi_projects_df = pd.DataFrame(county_qi_projects)
        fac_qi_projects_df = pd.DataFrame(fac_qi_projects)

        hub_qi_projects_df = pd.DataFrame(hub_qi_projects)

        list_of_projects = pd.concat([qi_projects_df,
                                      program_qi_projects_df,
                                      subcounty_qi_projects_df,
                                      county_qi_projects_df,
                                      hub_qi_projects_df,
                                      fac_qi_projects_df
                                      ])
        projects_tracked = list_of_projects['project_id'].unique()

        pro_perfomance_trial = prepare_viz(list_of_projects, pk, "facility")

        facility_name = pk

        # difference
        number_of_projects_created = len(all_projects)
        number_of_projects_with_test_of_change = len(pro_perfomance_trial)
        difference = number_of_projects_created - number_of_projects_with_test_of_change
    except:
        number_of_projects_created = len(all_projects)
        number_of_projects_with_test_of_change = 0
        difference = number_of_projects_created - number_of_projects_with_test_of_change
        pro_perfomance_trial = None

    context = {"projects": all_projects,
               "facility_name": facility_name,
               "title": "Ongoing",
               "pro_perfomance_trial": pro_perfomance_trial,
               "difference": difference,
               "projects_tracked": projects_tracked,
               "number_of_projects_created": number_of_projects_created,

               }
    return render(request, "project/department_filter_projects.html", context)


@login_required(login_url='login')
def qicreator_filter_project(request, pk):
    if not request.user.first_name:
        return redirect("profile")
    pro_perfomance_trial = {}
    projects_tracked = []
    # projects = QI_Projects.objects.filter(facility=pk).order_by("-date_updated")
    pk = str(pk).lower()
    projects = QI_Projects.objects.filter(created_by__username=pk)
    subcounty_projects = Subcounty_qi_projects.objects.filter(created_by__username=pk)
    county_projects = County_qi_projects.objects.filter(created_by__username=pk)
    hub_projects = Hub_qi_projects.objects.filter(created_by__username=pk)
    program_projects = Program_qi_projects.objects.filter(created_by__username=pk)
    all_projects = list(chain(projects, subcounty_projects, hub_projects, county_projects, program_projects))
    facility_name = pk
    number_of_projects_created = len(all_projects)
    try:
        list_of_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.project_id,
             'tested of change': x.tested_change,

             'facility': x.project.facility_name,
             'cqi': x.project.project_title,
             'department': x.project.departments.department,
             } for x in TestedChange.objects.filter(project__created_by__username=pk)
        ]
        qi_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.project_id,
             'tested of change': x.tested_change,

             'facility': x.project.facility_name,
             'cqi': x.project.project_title,
             'department': x.project.departments.department,
             } for x in TestedChange.objects.filter(project__created_by__username=pk)
        ]
        fac_qi_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.project_id,
             'tested of change': x.tested_change,

             'facility': x.project.hub,
             'cqi': x.project.project_title,
             'department': x.project.departments.department,
             } for x in TestedChange.objects.filter(project__created_by__username=pk)
        ]
        program_qi_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.program_project_id,
             'tested of change': x.tested_change,

             'facility': x.program_project.program.program,
             'cqi': x.program_project.project_title,
             'department': x.program_project.departments.department,
             } for x in TestedChange.objects.filter(program_project__created_by__username=pk)
        ]
        subcounty_qi_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.subcounty_project_id,
             'tested of change': x.tested_change,

             'facility': x.subcounty_project.sub_county.sub_counties,
             'cqi': x.subcounty_project.project_title,
             'department': x.subcounty_project.departments.department,
             } for x in TestedChange.objects.filter(subcounty_project__created_by__username=pk)
        ]
        county_qi_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.county_project_id,
             'tested of change': x.tested_change,

             'facility': x.county_project.county.county_name,
             'cqi': x.county_project.project_title,
             'department': x.county_project.departments.department,
             } for x in TestedChange.objects.filter(county_project__created_by__username=pk)
        ]
        hub_qi_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.hub_project_id,
             'tested of change': x.tested_change,

             'facility': x.hub_project.hub.hub,
             'cqi': x.hub_project.project_title,
             'department': x.hub_project.departments.department,
             } for x in TestedChange.objects.filter(hub_project__created_by__username=pk)
        ]
        # then concatenate the two lists to get a single list of dictionaries
        # Finally, you can create a dataframe from this list of dictionaries.
        qi_projects_df = pd.DataFrame(qi_projects)

        program_qi_projects_df = pd.DataFrame(program_qi_projects)
        subcounty_qi_projects_df = pd.DataFrame(subcounty_qi_projects)
        county_qi_projects_df = pd.DataFrame(county_qi_projects)
        fac_qi_projects_df = pd.DataFrame(fac_qi_projects)
        hub_qi_projects_df = pd.DataFrame(hub_qi_projects)

        # program_qi_projects_df.columns = list(qi_projects_df.columns)

        list_of_projects = pd.concat([qi_projects_df,
                                      program_qi_projects_df,
                                      subcounty_qi_projects_df,
                                      county_qi_projects_df,
                                      hub_qi_projects_df,
                                      fac_qi_projects_df
                                      ])
        projects_tracked = list_of_projects['project_id'].unique()

        pro_perfomance_trial = prepare_viz(list_of_projects, pk, "facility")

        facility_name = pk

        # difference
        number_of_projects_created = len(all_projects)
        number_of_projects_with_test_of_change = len(pro_perfomance_trial)
        difference = number_of_projects_created - number_of_projects_with_test_of_change
    except:
        number_of_projects_created = len(all_projects)
        number_of_projects_with_test_of_change = 0
        difference = number_of_projects_created - number_of_projects_with_test_of_change
        pro_perfomance_trial = None
    context = {"projects": all_projects,
               "facility_name": facility_name,
               "title": "Ongoing",
               "pro_perfomance_trial": pro_perfomance_trial,
               "difference": difference,
               "projects_tracked": projects_tracked,
               "number_of_projects_created": number_of_projects_created,

               }
    return render(request, "project/department_filter_projects.html", context)


@login_required(login_url='login')
def county_filter_project(request, pk):
    if not request.user.first_name:
        return redirect("profile")
    projects_tracked = []
    # projects = QI_Projects.objects.filter(facility=pk).order_by("-date_updated")
    projects = QI_Projects.objects.filter(county__county_name=pk)
    subcounty_projects = Subcounty_qi_projects.objects.filter(county__county_name=pk)
    county_projects = County_qi_projects.objects.filter(county__county_name=pk)
    all_projects = list(chain(projects, subcounty_projects, county_projects))
    facility_name = pk
    number_of_projects_created = len(all_projects)
    try:
        qi_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.project_id,
             'tested of change': x.tested_change,

             'facility': x.project.county.county_name,
             'cqi': x.project.project_title,
             'department': x.project.departments.department,
             } for x in TestedChange.objects.filter(project__county__county_name=pk)
        ]
        fac_qi_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.project_id,
             'tested of change': x.tested_change,

             'facility': x.project.county.county_name,
             'cqi': x.project.project_title,
             'department': x.project.departments.department,
             } for x in TestedChange.objects.filter(project__county__county_name=pk)
        ]
        subcounty_qi_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.subcounty_project_id,
             'tested of change': x.tested_change,

             'facility': x.subcounty_project.county.county_name,
             'cqi': x.subcounty_project.project_title,
             'department': x.subcounty_project.departments.department,
             } for x in TestedChange.objects.filter(subcounty_project__county__county_name=pk)
        ]
        county_qi_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.county_project_id,
             'tested of change': x.tested_change,

             'facility': x.county_project.county.county_name,
             'cqi': x.county_project.project_title,
             'department': x.county_project.departments.department,
             } for x in TestedChange.objects.filter(county_project__county__county_name=pk)
        ]
        # then concatenate the two lists to get a single list of dictionaries
        # Finally, you can create a dataframe from this list of dictionaries.
        qi_projects_df = pd.DataFrame(qi_projects)

        # program_qi_projects_df = pd.DataFrame(program_qi_projects)
        subcounty_qi_projects_df = pd.DataFrame(subcounty_qi_projects)
        county_qi_projects_df = pd.DataFrame(county_qi_projects)
        fac_qi_projects_df = pd.DataFrame(fac_qi_projects)

        list_of_projects = pd.concat([qi_projects_df,
                                      subcounty_qi_projects_df,
                                      county_qi_projects_df,
                                      fac_qi_projects_df
                                      ])
        projects_tracked = list_of_projects['project_id'].unique()
        pro_perfomance_trial = prepare_viz(list_of_projects, pk, "facility")

        facility_name = pk

        # difference
        number_of_projects_created = len(all_projects)
        number_of_projects_with_test_of_change = len(pro_perfomance_trial)
        difference = number_of_projects_created - number_of_projects_with_test_of_change
    except:
        number_of_projects_created = len(all_projects)
        number_of_projects_with_test_of_change = 0
        difference = number_of_projects_created - number_of_projects_with_test_of_change
        pro_perfomance_trial = None

    context = {"projects": all_projects,
               "facility_name": facility_name,
               "title": "Ongoing",
               "pro_perfomance_trial": pro_perfomance_trial,
               "difference": difference,
               "projects_tracked": projects_tracked,
               "number_of_projects_created": number_of_projects_created,

               }
    return render(request, "project/department_filter_projects.html", context)


@login_required(login_url='login')
def sub_county_filter_project(request, pk):
    if not request.user.first_name:
        return redirect("profile")
    projects_tracked = []
    # projects = QI_Projects.objects.filter(facility=pk).order_by("-date_updated")
    projects = QI_Projects.objects.filter(sub_county__sub_counties=pk)
    subcounty_projects = Subcounty_qi_projects.objects.filter(sub_county__sub_counties=pk)
    all_projects = list(chain(projects, subcounty_projects))
    facility_name = pk
    number_of_projects_created = len(all_projects)
    try:
        qi_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.project_id,
             'tested of change': x.tested_change,

             'facility': x.project.facility_name,
             'cqi': x.project.project_title,
             'department': x.project.departments.department,
             } for x in TestedChange.objects.filter(project__sub_county__sub_counties=pk)
        ]
        subcounty_qi_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.subcounty_project_id,
             'tested of change': x.tested_change,

             'facility': x.subcounty_project.sub_county.sub_counties,
             'cqi': x.subcounty_project.project_title,
             'department': x.subcounty_project.departments.department,
             } for x in TestedChange.objects.filter(subcounty_project__sub_county__sub_counties=pk)
        ]
        qi_projects_df = pd.DataFrame(qi_projects)
        subcounty_qi_projects_df = pd.DataFrame(subcounty_qi_projects)

        list_of_projects = pd.concat([qi_projects_df,
                                      subcounty_qi_projects_df,
                                      ])
        projects_tracked = list_of_projects['project_id'].unique()
        pro_perfomance_trial = prepare_viz(list_of_projects, pk, "facility")

        facility_name = pk
        # difference
        number_of_projects_created = len(all_projects)
        number_of_projects_with_test_of_change = len(pro_perfomance_trial)
        difference = number_of_projects_created - number_of_projects_with_test_of_change
    except:
        number_of_projects_created = len(all_projects)
        number_of_projects_with_test_of_change = 0
        difference = number_of_projects_created - number_of_projects_with_test_of_change
        pro_perfomance_trial = None
    context = {"projects": all_projects,
               "facility_name": facility_name,
               "title": "Ongoing",
               "pro_perfomance_trial": pro_perfomance_trial,
               "difference": difference,
               "projects_tracked": projects_tracked,
               "number_of_projects_created": number_of_projects_created,

               }
    return render(request, "project/department_filter_projects.html", context)


@login_required(login_url='login')
def canceled_projects(request, pk):
    if not request.user.first_name:
        return redirect("profile")
    projects = QI_Projects.objects.filter(measurement_status=pk)
    facility_name = pk
    context = {"projects": projects,
               "facility_name": facility_name,
               "title": "Canceled"
               }
    return render(request, "project/department_projects.html", context)


@login_required(login_url='login')
def not_started(request, pk):
    if not request.user.first_name:
        return redirect("profile")
    projects = QI_Projects.objects.filter(measurement_status=pk)
    facility_name = pk
    context = {"projects": projects,
               "facility_name": facility_name,
               "title": "Not started"
               }
    return render(request, "project/department_projects.html", context)

@login_required(login_url='login')
def postponed(request, pk):
    if not request.user.first_name:
        return redirect("profile")
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
    #     return render(request, "cqi/facility_landing_page.html", context)
    # else:
    #     projects = QI_Projects.objects.count()

    #     context = {"qi_list": qi_list, "num_post": num_post, "projects": projects,
    #
    #                }
    #     return render(request, "cqi/facility_landing_page.html", context)
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
    if not request.user.first_name:
        return redirect("profile")
    projects = QI_Projects.objects.filter(created_by__id=pk)
    program_projects = Program_qi_projects.objects.filter(created_by__id=pk)
    subcounty_projects = Subcounty_qi_projects.objects.filter(created_by__id=pk)
    county_projects = County_qi_projects.objects.filter(created_by__id=pk)
    hub_projects = Hub_qi_projects.objects.filter(created_by__id=pk)

    # Combine all the projects into one iterable
    all_projects = list(chain(projects, subcounty_projects, county_projects, hub_projects, program_projects))

    # Get the first project list and extract username
    username = all_projects[0].created_by.username

    queryset_names = ['project_id', 'program_project_id', 'subcounty_project_id', 'county_project_id', 'hub_project_id']
    all_tracked_projects = [id for queryset_name in queryset_names for id in
                            TestedChange.objects.values_list(queryset_name, flat=True)]

    context = {
        "facility_name": username,
        "tracked_projects": all_tracked_projects,
        "all_projects": all_projects,
        "num_projects": len(all_projects),  # Get the length of all_projects
    }
    return render(request, "project/qi_creators.html", context)


@login_required(login_url='login')
def qi_managers_projects(request, pk):
    if not request.user.first_name:
        return redirect("profile")
    projects = QI_Projects.objects.filter(qi_manager__id=pk)
    subcounty_projects = Subcounty_qi_projects.objects.filter(qi_manager__id=pk)
    county_projects = County_qi_projects.objects.filter(qi_manager__id=pk)
    hub_projects = Hub_qi_projects.objects.filter(qi_manager__id=pk)
    program_projects = Program_qi_projects.objects.filter(qi_manager__id=pk)
    # facility_name = [i.qi_manager for i in projects]
    facility_name = projects.first().qi_manager
    all_projects = list(chain(projects, subcounty_projects, county_projects, hub_projects, program_projects))
    tracked_projects = TestedChange.objects.values_list('project_id', flat=True)
    program_tracked_projects = TestedChange.objects.values_list('program_project_id', flat=True)
    subcounty_tracked_projects = TestedChange.objects.values_list('subcounty_project_id', flat=True)
    county_tracked_projects = TestedChange.objects.values_list('county_project_id', flat=True)
    hub_tracked_projects = TestedChange.objects.values_list('hub_project_id', flat=True)

    context = {"all_projects": all_projects,
               "facility_name": facility_name,
               "tracked_projects": tracked_projects,
               "program_tracked_projects": program_tracked_projects,
               "subcounty_tracked_projects": subcounty_tracked_projects,
               "county_tracked_projects": county_tracked_projects,
               "hub_tracked_projects": hub_tracked_projects,
               }
    return render(request, "project/qi_creators.html", context)


@login_required(login_url='login')
def completed_closed(request, pk):
    if not request.user.first_name:
        return redirect("profile")
    projects = QI_Projects.objects.filter(measurement_status=pk)
    lesson_learnt = Lesson_learned.objects.values_list('project_name_id', flat=True)
    facility_name = pk
    context = {"projects": projects,
               "facility_name": facility_name,
               "title": "Completed or Closed",
               "cqi_level": "facility",
               "lesson_learnt": lesson_learnt,
               }
    return render(request, "project/department_projects.html", context)


@login_required(login_url='login')
def completed_closed_program(request, pk):
    if not request.user.first_name:
        return redirect("profile")
    projects = Program_qi_projects.objects.filter(measurement_status=pk)
    lesson_learnt = Lesson_learned.objects.values_list('program_id', flat=True)
    facility_name = pk
    context = {"projects": projects,
               "facility_name": facility_name,
               "title": "Completed or Closed",
               "cqi_level": "program",
               "lesson_learnt": lesson_learnt,
               }
    return render(request, "project/department_projects.html", context)


@login_required(login_url='login')
def completed_closed_subcounty(request, pk):
    if not request.user.first_name:
        return redirect("profile")
    projects = Subcounty_qi_projects.objects.filter(measurement_status=pk)
    lesson_learnt = Lesson_learned.objects.values_list('subcounty_id', flat=True)
    facility_name = pk
    context = {"projects": projects,
               "facility_name": facility_name,
               "title": "Completed or Closed",
               "cqi_level": "subcounty",
               "lesson_learnt": lesson_learnt,
               }
    return render(request, "project/department_projects.html", context)


@login_required(login_url='login')
def completed_closed_county(request, pk):
    if not request.user.first_name:
        return redirect("profile")
    projects = County_qi_projects.objects.filter(measurement_status=pk)
    lesson_learnt = Lesson_learned.objects.values_list('county_id', flat=True)
    facility_name = pk
    context = {"projects": projects,
               "facility_name": facility_name,
               "title": "Completed or Closed",
               "cqi_level": "county",
               "lesson_learnt": lesson_learnt,
               }
    return render(request, "project/department_projects.html", context)


@login_required(login_url='login')
def completed_closed_hub(request, pk):
    if not request.user.first_name:
        return redirect("profile")
    projects = Hub_qi_projects.objects.filter(measurement_status=pk)
    lesson_learnt = Lesson_learned.objects.values_list('hub_id', flat=True)
    facility_name = pk
    context = {"projects": projects,
               "facility_name": facility_name,
               "title": "Completed or Closed",
               "cqi_level": "hub",
               "lesson_learnt": lesson_learnt,
               }
    return render(request, "project/department_projects.html", context)


@login_required(login_url='login')
def lesson_learnt(request):
    if not request.user.first_name:
        return redirect("profile")
    """
    This view handles the display of all the lesson_learnt and their related qi_project information.
    It uses the Lesson_learned model to retrieve all the lesson_learnt and annotates the queryset
    to include the number of qi_team_members for each lesson_learnt using the Count() method.
    The annotated queryset is then passed to the template as the context variable 'lesson_learnt'.
    The template then renders this information in a table format displaying the cqi title and number of QI team
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
    lesson_learnt = Lesson_learned.objects.annotate(num_members=Count('project_name__qi_team_members'),
                                                    num_members_program=Count('program__qi_team_members'),
                                                    num_members_subcounty=Count('subcounty__qi_team_members'),
                                                    num_members_county=Count('county__qi_team_members'),
                                                    num_members_hub=Count('hub__qi_team_members'),
                                                    )
    facility_plan = SustainmentPlan.objects.values_list("qi_project_id", flat=True)
    program_plan = SustainmentPlan.objects.values_list("program_id", flat=True)
    subcounty_plan = SustainmentPlan.objects.values_list("subcounty_id", flat=True)
    county_plan = SustainmentPlan.objects.values_list("county_id", flat=True)
    hub_plan = SustainmentPlan.objects.values_list("hub_id", flat=True)

    # facility_name = pk
    context = {"lesson_learnt": lesson_learnt,
               "facility_plan": facility_plan,
               "program_plan": program_plan,
               "subcounty_plan": subcounty_plan,
               "county_plan": county_plan,
               "hub_plan": hub_plan,
               # "projects": projects,
               # "lesson_learnt":lesson_learnt,

               }
    return render(request, "project/lesson_learnt.html", context)


@login_required(login_url='login')
def add_lesson_learnt(request, pk, program_name=None, facility_name=None, subcounty_name=None, hub_name=None,
                      county_name=None):
    if not request.user.first_name:
        return redirect("profile")
    if facility_name:
        project_name = QI_Projects.objects.get(id=pk, facility_name__name=facility_name)
        program = None
        qi_project = project_name
        subcounty = None
        county = None
        hub = None
    elif program_name:
        program = Program_qi_projects.objects.get(id=pk, program__program=program_name)
        project_name = None
        qi_project = program
        subcounty = None
        county = None
        hub = None
    elif subcounty_name:
        subcounty = Subcounty_qi_projects.objects.get(id=pk, sub_county__sub_counties=subcounty_name)
        program = None
        project_name = None
        qi_project = subcounty
        county = None
        hub = None
    elif county_name:
        county = County_qi_projects.objects.get(id=pk, county__county_name=county_name)
        program = None
        project_name = None
        qi_project = county
        subcounty = None
        hub = None
    elif hub_name:
        hub = Hub_qi_projects.objects.get(id=pk, hub__hub=hub_name)
        project_name = None
        program = None
        qi_project = hub
        subcounty = None
        county = None
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        form = Lesson_learnedForm(request.POST)
        if form.is_valid():
            # form.save()
            post = form.save(commit=False)
            post.project_name = project_name
            post.program = program
            post.subcounty = subcounty
            post.county = county
            post.hub = hub
            post.created_by = request.user
            post.save()
            messages.success(request, f"Lesson learnt for {post.project_name} added successfully.")
            # redirect back to the page the user was from after saving the form
            # return HttpResponseRedirect(request.session['page_from'])
            return redirect("lesson_learnt")
    else:
        form = Lesson_learnedForm()
    context = {"form": form,
               "qi_project": qi_project,
               "title": "ADD",
               }

    return render(request, "project/add_lesson_learnt.html", context)


@login_required(login_url='login')
def update_lesson_learnt(request, pk, program_name=None, facility_name=None, subcounty_name=None, hub_name=None,
                         county_name=None):
    if not request.user.first_name:
        return redirect("profile")
    lesson_learnt = Lesson_learned.objects.get(id=pk)
    if facility_name:
        project = QI_Projects.objects.get(id=lesson_learnt.project_name_id, facility_name__name=facility_name)
    elif program_name:
        project = Program_qi_projects.objects.get(id=lesson_learnt.program_id, program__program=program_name)
    elif subcounty_name:
        project = Subcounty_qi_projects.objects.get(id=lesson_learnt.subcounty_id,
                                                    sub_county__sub_counties=subcounty_name)
    elif county_name:
        project = County_qi_projects.objects.get(id=lesson_learnt.county_id, county__county_name=county_name)
    elif hub_name:
        project = Hub_qi_projects.objects.get(id=lesson_learnt.hub_id, hub__hub=hub_name)

    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        form = Lesson_learnedForm(request.POST, instance=lesson_learnt)
        if form.is_valid():
            form.save()
            # post = form.save(commit=False)
            # post.project_name = cqi
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
    if not request.user.first_name:
        return redirect("profile")
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
    if not request.user.first_name:
        return redirect("profile")
    projects = QI_Projects.objects.filter(measurement_status=pk)

    facility_name = pk
    context = {"projects": projects,
               "facility_name": facility_name,
               "title": "Started or Ongoing",
               }
    return render(request, "project/department_projects.html", context)


@login_required(login_url='login')
def measurement_frequency(request, pk):
    if not request.user.first_name:
        return redirect("profile")
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
    #     return render(request, "cqi/facility_landing_page.html", context)
    # else:
    #     projects = QI_Projects.objects.count()

    #     context = {"qi_list": qi_list, "num_post": num_post, "projects": projects,
    #
    #                }
    #     return render(request, "cqi/facility_landing_page.html", context)
    # projects = QI_Projects.objects.count()
    # my_filters = QiprojectFilter(request.GET,queryset=qi_list)
    # qi_list=my_filters.qs
    tracked_projects = TestedChange.objects.values_list('project_id', flat=True)
    context = {"projects": projects,
               "facility_name": facility_name,
               "tracked_projects": tracked_projects,
               # "title": "Completed or Closed",
               }
    return render(request, "project/facility_projects.html", context)


@login_required(login_url='login')
def toggle_archive_project(request, pk, program_name=None, facility_name=None, subcounty_name=None, hub_name=None,
                           county_name=None):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    try:
        if facility_name:
            # Get the QI_Projects object from the given qi_project_id
            qi_project = QI_Projects.objects.get(id=pk)

            # Get the ArchiveProject object associated with the given qi_project
            archive_project = ArchiveProject.objects.get(qi_project=qi_project)
        elif program_name:
            # Get the QI_Projects object from the given qi_project_id
            qi_project = Program_qi_projects.objects.get(id=pk)

            # Get the ArchiveProject object associated with the given qi_project
            archive_project = ArchiveProject.objects.get(program=qi_project)
        elif subcounty_name:
            # Get the QI_Projects object from the given qi_project_id
            qi_project = Subcounty_qi_projects.objects.get(id=pk)

            # Get the ArchiveProject object associated with the given qi_project
            archive_project = ArchiveProject.objects.get(subcounty=qi_project)

        elif county_name:
            # Get the QI_Projects object from the given qi_project_id
            qi_project = County_qi_projects.objects.get(id=pk)

            # Get the ArchiveProject object associated with the given qi_project
            archive_project = ArchiveProject.objects.get(county=qi_project)
        elif hub_name:
            # Get the QI_Projects object from the given qi_project_id
            qi_project = Hub_qi_projects.objects.get(id=pk)

            # Get the ArchiveProject object associated with the given qi_project
            archive_project = ArchiveProject.objects.get(hub=qi_project)

        # Toggle the booleanfield archive_project
        if archive_project.archive_project:
            archive_project.archive_project = False
        else:
            archive_project.archive_project = True

        # Save the changes
        archive_project.save()
    except ArchiveProject.DoesNotExist:
        # create if not in the database
        form = ArchiveProjectForm(request.POST, request.FILES)
        if form.is_valid():
            # do not save first, wait to update foreign key
            post = form.save(commit=False)
            # get cqi primary key
            if facility_name:
                post.qi_project = QI_Projects.objects.get(id=pk)
            elif program_name:
                post.program = Program_qi_projects.objects.get(id=pk)
            elif subcounty_name:
                post.subcounty = Subcounty_qi_projects.objects.get(id=pk)
            elif county_name:
                post.county = County_qi_projects.objects.get(id=pk)
            elif hub_name:
                post.hub = Hub_qi_projects.objects.get(id=pk)
            # Archive the cqi
            post.archive_project = True
            # save
            post.save()

            return HttpResponseRedirect(request.session['page_from'])

    return HttpResponseRedirect(request.session['page_from'])


# @login_required(login_url='login')
# def tested_change(request, pk):
#     try:
#         qi_project = QI_Projects.objects.get(id=pk)
#         facility = qi_project.facility_name
#         subcounty = qi_project.sub_county
#         level = 'facility'
#     except:
#         qi_project = Program_qi_projects.objects.get(id=pk)
#         facility = qi_project.program
#         subcounty = None
#         level = 'program'
#
#     if request.method == "GET":
#         request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
#     if request.method == "POST":
#         form = TestedChangeForm(request.POST)
#         if form.is_valid():
#             # do not save first, wait to update foreign key
#             post = form.save(commit=False)
#             # get cqi primary
#             if "facility" in level:
#                 post.project = QI_Projects.objects.get(id=pk)
#             elif "program" in level:
#                 post.program_project = Program_qi_projects.objects.get(id=pk)
#             # save
#             post.save()
#             return HttpResponseRedirect(request.session['page_from'])
#     else:
#         form = TestedChangeForm(instance=request.user)
#     context = {
#         "form": form,
#         "qi_project": qi_project,
#     }
#     return render(request, 'project/add_tested_change.html', context)

@login_required(login_url='login')
def tested_change(request, pk, program_name=None, facility_name=None, subcounty_name=None, hub_name=None,
                  county_name=None):
    if not request.user.first_name:
        return redirect("profile")
    if facility_name:
        qi_project = QI_Projects.objects.get(id=pk, facility_name__name=facility_name)
        facility = qi_project.facility_name
        subcounty = qi_project.sub_county
        level = 'facility'
    elif program_name:
        qi_project = Program_qi_projects.objects.get(id=pk, program__program=program_name)
        facility = qi_project.program
        subcounty = None
        level = 'program'
    elif subcounty_name:
        qi_project = Subcounty_qi_projects.objects.get(id=pk, sub_county__sub_counties=subcounty_name)
        # facility = qi_project.program
        # subcounty = None
        level = 'subcounty'
    elif county_name:
        qi_project = County_qi_projects.objects.get(id=pk, county__county_name=county_name)
        # facility = qi_project.program
        # subcounty = None
        level = 'county'
    elif hub_name:
        qi_project = Hub_qi_projects.objects.get(id=pk, hub__hub=hub_name)
        # facility = qi_project.program
        # subcounty = None
        level = 'hub'

    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    if request.method == "POST":
        form = TestedChangeForm(request.POST)
        if form.is_valid():
            # do not save first, wait to update foreign key
            post = form.save(commit=False)
            # get cqi primary
            if "facility" in level:
                post.project = QI_Projects.objects.get(id=pk)
            elif "program" in level:
                post.program_project = Program_qi_projects.objects.get(id=pk)
            elif "subcounty" in level:
                post.subcounty_project = Subcounty_qi_projects.objects.get(id=pk)
            elif "county" in level:
                post.county_project = County_qi_projects.objects.get(id=pk)
            elif "hub" in level:
                post.hub_project = Hub_qi_projects.objects.get(id=pk)
            # save
            post.save()
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = TestedChangeForm(instance=request.user)
    context = {
        "form": form,
        "qi_project": qi_project,
        "facility_name": facility_name,
        "program_name": program_name,
        "subcounty_name": subcounty_name,
        "county_name": county_name,
        "hub_name": hub_name,
    }
    return render(request, 'project/add_tested_change.html', context)


@login_required(login_url='login')
def update_test_of_change(request, pk):
    if not request.user.first_name:
        return redirect("profile")
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
    # return render(request, 'cqi/update_test_of_change.html', context)
    return render(request, 'project/add_qi_manager.html', context)


@login_required(login_url='login')
def delete_test_of_change(request, pk):
    if not request.user.first_name:
        return redirect("profile")
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
    if not request.user.first_name:
        return redirect("profile")
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
    if not request.user.first_name:
        return redirect("profile")
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
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    # item = CustomUser.objects.get(id=pk)
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
    if not request.user.first_name:
        return redirect("profile")
    return render(request, "project/deep_dive_chmt.html")
    # return render(request, "cqi/calendar.html")


@login_required(login_url='login')
def add_qi_team_member(request, pk, program_name=None, facility_name=None, subcounty_name=None, hub_name=None,
                       county_name=None):
    if not request.user.first_name:
        return redirect("profile")
    # ADAPTED FOR QI_PROJECTS AND PROGRAM_QI_PROJECTS
    if facility_name:
        facility = Facilities.objects.get(name=facility_name)
        program = None
        qi_project = QI_Projects.objects.get(id=pk, facility_name=facility)
        program_qi_project = None
        subcounty_qi_project = None
        county_qi_project = None
        hub_qi_project = None
        qi_projects = qi_project
    elif program_name:
        program = Program.objects.get(program=program_name)
        facility = None
        qi_project = None
        program_qi_project = Program_qi_projects.objects.get(id=pk, program=program)
        subcounty_qi_project = None
        county_qi_project = None
        hub_qi_project = None
        qi_projects = program_qi_project
    elif subcounty_name:
        subcounty = Sub_counties.objects.get(sub_counties=subcounty_name)
        facility = None
        program = None
        qi_project = None
        program_qi_project = None
        subcounty_qi_project = Subcounty_qi_projects.objects.get(id=pk, sub_county=subcounty)
        county_qi_project = None
        hub_qi_project = None
        qi_projects = subcounty_qi_project
    elif county_name:
        county = Counties.objects.get(county_name=county_name)
        facility = None
        program = None
        qi_project = None
        program_qi_project = None
        subcounty_qi_project = None
        county_qi_project = County_qi_projects.objects.get(id=pk, county=county)
        hub_qi_project = None
        qi_projects = county_qi_project
    elif hub_name:
        hub = Hub.objects.get(hub=hub_name)
        facility = None
        program = None
        qi_project = None
        program_qi_project = None
        subcounty_qi_project = None
        county_qi_project = None
        hub_qi_project = Hub_qi_projects.objects.get(id=pk, hub=hub)
        qi_projects = hub_qi_project

    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        form = Qi_team_membersForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.facility = facility
            post.program = program
            post.qi_project = qi_project
            post.program_qi_project = program_qi_project
            post.subcounty_qi_project = subcounty_qi_project
            post.county_qi_project = county_qi_project
            post.hub_qi_project = hub_qi_project
            post.created_by = request.user
            post.save()
            return redirect(request.session['page_from'])
    else:
        form = Qi_team_membersForm()

    context = {"form": form,
               "facility_name": facility_name,
               "program_name": program_name,
               "subcounty_name": subcounty_name,
               "county_name": county_name,
               "hub_name": hub_name,
               "title": "add qi team member",
               "qi_projects": qi_projects,
               }
    return render(request, 'project/add_qi_teams.html', context)


@login_required(login_url='login')
def delete_qi_team_member(request, pk):
    if not request.user.first_name:
        return redirect("profile")
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
def update_qi_team_member(request, pk, program_name=None, facility_name=None, subcounty_name=None, hub_name=None,
                          county_name=None):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    item = Qi_team_members.objects.get(id=pk)
    if facility_name:
        qi_project = QI_Projects.objects.get(id=item.qi_project_id)
        level = "facility"
    elif program_name:
        qi_project = Program_qi_projects.objects.get(id=item.program_id)
        level = "program"
    elif subcounty_name:
        qi_project = Subcounty_qi_projects.objects.get(id=item.subcounty_qi_project_id)
        level = "subcounty"
    elif county_name:
        qi_project = County_qi_projects.objects.get(id=item.county_qi_project_id)
        level = "county"
    elif hub_name:
        qi_project = Hub_qi_projects.objects.get(id=item.hub_qi_project_id)
        level = "hub"

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
        "level": level
    }
    return render(request, 'project/add_qi_teams.html', context)


@login_required(login_url='login')
def qi_team_members(request):
    if not request.user.first_name:
        return redirect("profile")
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
                'QI cqi id': x.id,
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
                                                              'User_id', 'QI cqi id', 'Date created', 'Facility',
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
                'Facility': x.facility.name,
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
#
#     # Create the context variable to pass to the template
#     context = {
#         'qi_team_members': qi_team_members,
#     }
#
#     # Render the template with the context variable
#     return render(request, 'cqi/qi_team_members.html', context)
@login_required(login_url='login')
def qi_team_members_view(request):
    if not request.user.first_name:
        return redirect("profile")
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

    # team_members = CustomUser.objects.values(
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
    if not request.user.first_name:
        return redirect("profile")
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
#     return render(request, "cqi/qi_managers.html", context)


@login_required(login_url='login')
def qi_managers_view(request):
    if not request.user.first_name:
        return redirect("profile")
    """
    A view that displays the first name, last name, email, and number of projects
    for each QI manager in a table.
    """
    # Get a queryset of QI managers, annotated with the number of projects they are supervising
    # and ordered by the number of projects in descending order
    # qi_managers = Qi_managers.objects.annotate(num_projects=Count('qi_projects')).order_by('-num_projects',
    #                                                                                        'date_created')
    qi_managers = Qi_managers.objects.annotate(
        combined_sum=Count('qi_projects', distinct=True) + Count('program_qi_projects', distinct=True) +
                     Count('subcounty_qi_projects', distinct=True) + Count('county_qi_projects', distinct=True) +
                     Count('hub_qi_projects', distinct=True),

    ).order_by('-combined_sum')

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
#     return render(request, "cqi/comments.html", context)


@login_required(login_url='login')
def comments_no_response(request):
    if not request.user.first_name:
        return redirect("profile")
    """
    This view retrieves all comments that are either parent comments or comments that don't have any parent comment.
    It uses the Comment model and filters out comments that have a parent comment. The filtered comments are then
    returned to the 'cqi/comments_no_response.html' template to be displayed.
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
    if not request.user.first_name:
        return redirect("profile")
    all_comments = Comment.objects.filter(
        id__in=Comment.objects.exclude(parent_id=None).values_list("parent_id", flat=True)
    ).prefetch_related('qi_project_title__qi_team_members').order_by('-comment_updated')
    context = {
        "all_comments": all_comments,
        "title": "Comments with responses"
    }
    return render(request, "project/comments.html", context)


@login_required(login_url='login')
def single_project_comments(request, pk):
    if not request.user.first_name:
        return redirect("profile")
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
#             # get cqi primary key
#             post.qi_project_title = QI_Projects.objects.get(project_title=facility_project.project_title)
#             post.commented_by = CustomUser.objects.get(username=request.user)
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
#     return render(request, "cqi/single_comment.html", context)


@login_required(login_url='login')
def update_comments(request, pk):
    if not request.user.first_name:
        return redirect("profile")
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
    if not request.user.first_name:
        return redirect("profile")
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
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    all_comments = ProjectResponses.objects.filter(id=pk).order_by('-response_updated_date')

    # facility_project = QI_Projects.objects.get(id=pk)
    if request.method == "POST":
        form = ProjectResponsesForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            # get cqi primary key
            post.comment = ProjectComments.objects.get(id=pk)
            post.response_by = CustomUser.objects.get(username=request.user)
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
    if not request.user.first_name:
        return redirect("profile")
    all_comments = ProjectResponses.objects.filter(qi_project_title__id=pk).order_by('-comment_updated')

    facility_project = QI_Projects.objects.get(id=pk)
    if request.method == "POST":
        form = ProjectCommentsForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            # get cqi primary key
            post.qi_project_title = QI_Projects.objects.get(project_title=facility_project.project_title)
            post.commented_by = CustomUser.objects.get(username=request.user)
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
    if not request.user.first_name:
        return redirect("profile")
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
    if not request.user.first_name:
        return redirect("profile")
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

    return plot(fig, include_plotlyjs=False, output_type="div")


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

    return plot(fig, include_plotlyjs=False, output_type="div")


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

    return plot(fig, include_plotlyjs=False, output_type="div")


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

    return plot(fig, include_plotlyjs=False, output_type="div")


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
    if not request.user.first_name:
        return redirect("profile")
    # TODO: Include VIZ for QI CREATED PER MONTH,QUARTER,YEAR,(PER FACILITY,HUB,SUB-COUNTY,COUNTY,PROGRAM)
    try:
        all_archived = ArchiveProject.objects.filter(archive_project=True).values_list('qi_project_id', flat=True)
    except:
        all_archived = []

    facility_project = QI_Projects.objects.get(id=pk)
    # if not facility_project.process_analysis:
    #     facility_project.process_analysis = 'staticfiles/images/default.png'
    # get other All projects
    other_projects = QI_Projects.objects.filter(facility_name=facility_project.facility_name)
    # Hit db once
    test_of_change_qs = TestedChange.objects.all()
    # check comments
    all_comments = ProjectComments.objects.filter(qi_project_title__id=facility_project.id).order_by('-comment_updated')

    # get qi team members for this cqi
    qi_teams = Qi_team_members.objects.filter(qi_project__id=pk)
    qi_teams = pagination_(request, qi_teams)
    # get milestones for this cqi
    milestones = Milestone.objects.filter(qi_project__id=pk)
    # # get action plan for this cqi
    action_plan = ActionPlan.objects.filter(qi_project__id=pk).order_by('progress')
    action_plans = pagination_(request, action_plan)

    # get baseline image for this cqi
    try:
        baseline = Baseline.objects.filter(qi_project__id=pk).latest('date_created')
    except Baseline.DoesNotExist:
        baseline = None

    project_images = RootCauseImages.objects.all()
    root_cause_image = project_images.filter(qi_project__id=pk).order_by("date_created")
    project_images = project_images.filter(qi_project__id=pk).count()
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
            # get cqi primary key
            post.qi_project_title = QI_Projects.objects.get(project_title=facility_project.project_title)
            post.commented_by = CustomUser.objects.get(username=request.user.username)
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
         'cqi': x.project.project_title,
         } for x in list_of_projects
    ]
    # convert data from database to a dataframe
    list_of_projects = pd.DataFrame(list_of_projects)
    if list_of_projects.shape[0] != 0:
        dicts = {}
        keys = list_of_projects['project_id'].unique()
        values = list_of_projects['cqi'].unique()
        for i in range(len(keys)):
            dicts[keys[i]] = values[i]
        all_other_projects_trend = []
        for project in list_of_projects['cqi'].unique():
            all_other_projects_trend.append(
                prepare_trends(list_of_projects[list_of_projects['cqi'] == project], project))

        pro_perfomance_trial = dict(zip(keys, all_other_projects_trend))

    else:
        pro_perfomance_trial = {}

    # assign it to a dataframe using list comprehension
    other_projects = [
        {'department(s)': x.departments.department,
         'cqi category': x.project_category,
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
                   "qi_teams": qi_teams,
                   "milestones": milestones, "action_plans": action_plans, "today": today, "baseline": baseline,
                   "title": "facility", "root_cause_images": root_cause_image, "project_images": project_images,
                   "facility_name": "facility_name",

                   }

    else:
        project_performance = {}
        facility_proj_performance = {}
        context = {"facility_project": facility_project, "test_of_change": changes,
                   "project_performance": project_performance, "facility_proj_performance": facility_proj_performance,
                   "pro_perfomance_trial": pro_perfomance_trial, "form": form, "all_comments": all_comments,
                   "all_archived": all_archived,
                   "qi_teams": qi_teams,
                   "milestones": milestones, "action_plans": action_plans, "today": today, "baseline": baseline,
                   "title": "facility", "root_cause_images": root_cause_image, "project_images": project_images,
                   "facility_name": "facility_name", }

    return render(request, "project/individual_qi_project.html", context)


@login_required(login_url='login')
def single_project_program(request, pk):
    if not request.user.first_name:
        return redirect("profile")
    # TODO: Include VIZ for QI CREATED PER MONTH,QUARTER,YEAR,(PER FACILITY,HUB,SUB-COUNTY,COUNTY,PROGRAM)
    try:
        all_archived = ArchiveProject.objects.filter(archive_project=True).values_list('program_id', flat=True)
    except:
        all_archived = []

    facility_project = Program_qi_projects.objects.get(id=pk)
    # if not facility_project.process_analysis:
    #     facility_project.process_analysis = 'staticfiles/images/default.png'
    # get other All projects
    other_projects = Program_qi_projects.objects.filter(program=facility_project.program)
    # Hit db once
    test_of_change_qs = TestedChange.objects.all()
    # check comments
    all_comments = ProjectComments.objects.filter(qi_project_title__id=facility_project.id).order_by('-comment_updated')

    # get qi team members for this cqi
    qi_teams = Qi_team_members.objects.filter(program_qi_project__id=pk)
    qi_teams = pagination_(request, qi_teams)
    # get milestones for this cqi
    milestones = Milestone.objects.filter(program_qi_project__id=pk)
    # # get action plan for this cqi
    action_plan = ActionPlan.objects.filter(program_qi_project__id=pk).order_by('progress')
    action_plans = pagination_(request, action_plan)

    # get baseline image for this cqi
    try:
        baseline = Baseline.objects.filter(program_qi_project__id=pk).latest('date_created')
    except Baseline.DoesNotExist:
        baseline = None

    project_images = RootCauseImages.objects.all()
    root_cause_image = project_images.filter(program_qi_project__id=pk).order_by("date_created")
    project_images = project_images.filter(program_qi_project__id=pk).count()
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
            # get cqi primary key
            post.qi_project_title = Program_qi_projects.objects.get(project_title=facility_project.project_title)
            post.commented_by = CustomUser.objects.get(username=request.user.username)
            # save
            post.save()
            # show empty form
            form = ProjectCommentsForm()
    else:
        form = ProjectCommentsForm()
        # stakeholderform = StakeholderForm()

    # accessing facility qi projects
    # use two underscore to the field with foreign key
    list_of_projects = TestedChange.objects.filter(program_project_id__program=facility_project.program).order_by(
        '-month_year')
    list_of_projects = [
        {'month_year': x.month_year,
         'project_id': x.program_project_id,
         'tested of change': x.tested_change,
         'achievements': x.achievements,
         'facility': x.program_project,
         'cqi': x.program_project.project_title,
         } for x in list_of_projects
    ]
    # convert data from database to a dataframe
    list_of_projects = pd.DataFrame(list_of_projects)
    if list_of_projects.shape[0] != 0:
        dicts = {}
        keys = list_of_projects['project_id'].unique()
        values = list_of_projects['cqi'].unique()
        for i in range(len(keys)):
            dicts[keys[i]] = values[i]
        all_other_projects_trend = []
        for project in list_of_projects['cqi'].unique():
            all_other_projects_trend.append(
                prepare_trends(list_of_projects[list_of_projects['cqi'] == project], project))

        pro_perfomance_trial = dict(zip(keys, all_other_projects_trend))
    else:
        pro_perfomance_trial = {}

    # assign it to a dataframe using list comprehension
    other_projects = [
        {'department(s)': x.departments.department,
         'cqi category': x.project_category,
         'id': x.id,
         } for x in other_projects
    ]
    # convert data from database to a dataframe
    df_other_projects = pd.DataFrame(other_projects)
    df_other_projects['total projects'] = 1

    changes = test_of_change_qs.filter(program_project_id=pk).order_by('-month_year')
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
                   "qi_teams": qi_teams,
                   "milestones": milestones, "action_plans": action_plans, "today": today, "baseline": baseline,
                   "title": "program", "program_name": "program_name", "project_images": project_images,
                   "root_cause_images": root_cause_image}

    else:
        project_performance = {}
        facility_proj_performance = {}
        context = {"facility_project": facility_project, "test_of_change": changes,
                   "project_performance": project_performance, "facility_proj_performance": facility_proj_performance,
                   "pro_perfomance_trial": pro_perfomance_trial, "form": form, "all_comments": all_comments,
                   "all_archived": all_archived,
                   "qi_teams": qi_teams,
                   "milestones": milestones, "action_plans": action_plans, "today": today, "baseline": baseline,
                   "title": "program", "program_name": "program_name", "project_images": project_images,
                   "root_cause_images": root_cause_image}

    return render(request, "project/individual_qi_project.html", context)


@login_required(login_url='login')
def single_project_subcounty(request, pk):
    if not request.user.first_name:
        return redirect("profile")
    # TODO: Include VIZ for QI CREATED PER MONTH,QUARTER,YEAR,(PER FACILITY,HUB,SUB-COUNTY,COUNTY,PROGRAM)
    try:
        all_archived = ArchiveProject.objects.filter(archive_project=True).values_list('subcounty_id', flat=True)
    except:
        all_archived = []

    facility_project = Subcounty_qi_projects.objects.get(id=pk)
    # if not facility_project.process_analysis:
    #     facility_project.process_analysis = 'staticfiles/images/default.png'
    # get other All projects
    other_projects = Subcounty_qi_projects.objects.filter(sub_county=facility_project.sub_county)
    # Hit db once
    test_of_change_qs = TestedChange.objects.all()
    # check comments
    all_comments = ProjectComments.objects.filter(qi_project_title__id=facility_project.id).order_by('-comment_updated')

    # get qi team members for this cqi
    qi_teams = Qi_team_members.objects.filter(subcounty_qi_project__id=pk)
    qi_teams = pagination_(request, qi_teams)
    # get milestones for this cqi
    milestones = Milestone.objects.filter(subcounty_qi_project__id=pk)
    # # get action plan for this cqi
    action_plan = ActionPlan.objects.filter(subcounty_qi_project__id=pk).order_by('progress')
    action_plans = pagination_(request, action_plan)

    # get baseline image for this cqi
    try:
        baseline = Baseline.objects.filter(subcounty_qi_project__id=pk).latest('date_created')
    except Baseline.DoesNotExist:
        baseline = None

    project_images = RootCauseImages.objects.all()
    root_cause_image = project_images.filter(subcounty_qi_project__id=pk).order_by("date_created")
    project_images = project_images.filter(subcounty_qi_project__id=pk).count()
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
            # get cqi primary key
            post.qi_project_title = Subcounty_qi_projects.objects.get(project_title=facility_project.project_title)
            post.commented_by = CustomUser.objects.get(username=request.user.username)
            # save
            post.save()
            # show empty form
            form = ProjectCommentsForm()
    else:
        form = ProjectCommentsForm()
        # stakeholderform = StakeholderForm()

    # accessing facility qi projects
    # use two underscore to the field with foreign key
    list_of_projects = TestedChange.objects.filter(
        subcounty_project_id__sub_county=facility_project.sub_county).order_by(
        '-month_year')
    list_of_projects = [
        {'month_year': x.month_year,
         'project_id': x.subcounty_project_id,
         'tested of change': x.tested_change,
         'achievements': x.achievements,
         'facility': x.subcounty_project,
         'cqi': x.subcounty_project.project_title,
         } for x in list_of_projects
    ]
    # convert data from database to a dataframe
    list_of_projects = pd.DataFrame(list_of_projects)
    if list_of_projects.shape[0] != 0:
        dicts = {}
        keys = list_of_projects['project_id'].unique()
        values = list_of_projects['cqi'].unique()
        for i in range(len(keys)):
            dicts[keys[i]] = values[i]
        all_other_projects_trend = []
        for project in list_of_projects['cqi'].unique():
            all_other_projects_trend.append(
                prepare_trends(list_of_projects[list_of_projects['cqi'] == project], project))

        pro_perfomance_trial = dict(zip(keys, all_other_projects_trend))
    else:
        pro_perfomance_trial = {}

    # assign it to a dataframe using list comprehension
    other_projects = [
        {'department(s)': x.departments.department,
         'cqi category': x.project_category,
         'id': x.id,
         } for x in other_projects
    ]
    # convert data from database to a dataframe
    df_other_projects = pd.DataFrame(other_projects)
    df_other_projects['total projects'] = 1

    changes = test_of_change_qs.filter(subcounty_project_id=pk).order_by('-month_year')
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
                   "qi_teams": qi_teams,
                   "milestones": milestones, "action_plans": action_plans, "today": today, "baseline": baseline,
                   "title": "subcounty", "subcounty_name": "subcounty_name", "project_images": project_images,
                   "root_cause_images": root_cause_image}

    else:
        project_performance = {}
        facility_proj_performance = {}
        context = {"facility_project": facility_project, "test_of_change": changes,
                   "project_performance": project_performance, "facility_proj_performance": facility_proj_performance,
                   "pro_perfomance_trial": pro_perfomance_trial, "form": form, "all_comments": all_comments,
                   "all_archived": all_archived,
                   "qi_teams": qi_teams,
                   "milestones": milestones, "action_plans": action_plans, "today": today, "baseline": baseline,
                   "title": "subcounty", "subcounty_name": "subcounty_name", "project_images": project_images,
                   "root_cause_images": root_cause_image}

    return render(request, "project/individual_qi_project.html", context)


@login_required(login_url='login')
def single_project_county(request, pk):
    if not request.user.first_name:
        return redirect("profile")
    # TODO: Include VIZ for QI CREATED PER MONTH,QUARTER,YEAR,(PER FACILITY,HUB,SUB-COUNTY,COUNTY,PROGRAM)
    try:
        all_archived = ArchiveProject.objects.filter(archive_project=True).values_list('county_id', flat=True)
    except:
        all_archived = []

    facility_project = County_qi_projects.objects.get(id=pk)
    # if not facility_project.process_analysis:
    #     facility_project.process_analysis = 'staticfiles/images/default.png'
    # get other All projects
    other_projects = County_qi_projects.objects.filter(county=facility_project.county)
    # Hit db once
    test_of_change_qs = TestedChange.objects.all()
    # check comments
    all_comments = ProjectComments.objects.filter(qi_project_title__id=facility_project.id).order_by('-comment_updated')

    # get qi team members for this cqi
    qi_teams = Qi_team_members.objects.filter(county_qi_project__id=pk)
    qi_teams = pagination_(request, qi_teams)
    # get milestones for this cqi
    milestones = Milestone.objects.filter(county_qi_project__id=pk)
    # # get action plan for this cqi
    action_plan = ActionPlan.objects.filter(county_qi_project__id=pk).order_by('progress')
    action_plans = pagination_(request, action_plan)

    # get baseline image for this cqi
    try:
        baseline = Baseline.objects.filter(county_qi_project__id=pk).latest('date_created')

    except Baseline.DoesNotExist:
        baseline = None

    project_images = RootCauseImages.objects.all()
    root_cause_image = project_images.filter(county_qi_project__id=pk).order_by("date_created")
    project_images = project_images.filter(county_qi_project__id=pk).count()
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
            # get cqi primary key
            post.qi_project_title = County_qi_projects.objects.get(project_title=facility_project.project_title)
            post.commented_by = CustomUser.objects.get(username=request.user.username)
            # save
            post.save()
            # show empty form
            form = ProjectCommentsForm()
    else:
        form = ProjectCommentsForm()
        # stakeholderform = StakeholderForm()

    # accessing facility qi projects
    # use two underscore to the field with foreign key
    list_of_projects = TestedChange.objects.filter(
        county_project__county=facility_project.county).order_by(
        '-month_year')
    list_of_projects = [
        {'month_year': x.month_year,
         'project_id': x.county_project_id,
         'tested of change': x.tested_change,
         'achievements': x.achievements,
         'facility': x.county_project,
         'cqi': x.county_project.project_title,
         } for x in list_of_projects
    ]
    # convert data from database to a dataframe
    list_of_projects = pd.DataFrame(list_of_projects)
    if list_of_projects.shape[0] != 0:
        dicts = {}
        keys = list_of_projects['project_id'].unique()
        values = list_of_projects['cqi'].unique()
        for i in range(len(keys)):
            dicts[keys[i]] = values[i]
        all_other_projects_trend = []
        for project in list_of_projects['cqi'].unique():
            all_other_projects_trend.append(
                prepare_trends(list_of_projects[list_of_projects['cqi'] == project], project))

        pro_perfomance_trial = dict(zip(keys, all_other_projects_trend))
    else:
        pro_perfomance_trial = {}

    # assign it to a dataframe using list comprehension
    other_projects = [
        {'department(s)': x.departments.department,
         'cqi category': x.project_category,
         'id': x.id,
         } for x in other_projects
    ]
    # convert data from database to a dataframe
    df_other_projects = pd.DataFrame(other_projects)
    df_other_projects['total projects'] = 1

    changes = test_of_change_qs.filter(county_project_id=pk).order_by('-month_year')
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
                   "qi_teams": qi_teams,
                   "milestones": milestones, "action_plans": action_plans, "today": today, "baseline": baseline,
                   "title": "county", "county_name": "county_name", "project_images": project_images,
                   "root_cause_images": root_cause_image}

    else:
        project_performance = {}
        facility_proj_performance = {}
        context = {"facility_project": facility_project, "test_of_change": changes,
                   "project_performance": project_performance, "facility_proj_performance": facility_proj_performance,
                   "pro_perfomance_trial": pro_perfomance_trial, "form": form, "all_comments": all_comments,
                   "all_archived": all_archived,
                   "qi_teams": qi_teams,
                   "milestones": milestones, "action_plans": action_plans, "today": today, "baseline": baseline,
                   "title": "county", "county_name": "county_name", "project_images": project_images,
                   "root_cause_images": root_cause_image}

    return render(request, "project/individual_qi_project.html", context)

@login_required(login_url='login')
def single_project_hub(request, pk):
    if not request.user.first_name:
        return redirect("profile")
    # TODO: Include VIZ for QI CREATED PER MONTH,QUARTER,YEAR,(PER FACILITY,HUB,SUB-COUNTY,COUNTY,PROGRAM)
    try:
        all_archived = ArchiveProject.objects.filter(archive_project=True).values_list('hub_id', flat=True)
    except:
        all_archived = []

    facility_project = Hub_qi_projects.objects.get(id=pk)
    # if not facility_project.process_analysis:
    #     facility_project.process_analysis = 'staticfiles/images/default.png'
    # get other All projects
    other_projects = Hub_qi_projects.objects.filter(hub=facility_project.hub)
    # Hit db once
    test_of_change_qs = TestedChange.objects.all()
    # check comments
    all_comments = ProjectComments.objects.filter(qi_project_title__id=facility_project.id).order_by('-comment_updated')

    # get qi team members for this cqi
    qi_teams = Qi_team_members.objects.filter(hub_qi_project__id=pk)
    qi_teams = pagination_(request, qi_teams)
    # get milestones for this cqi
    milestones = Milestone.objects.filter(hub_qi_project__id=pk)
    # # get action plan for this cqi
    action_plan = ActionPlan.objects.filter(hub_qi_project__id=pk).order_by('progress')
    action_plans = pagination_(request, action_plan)

    # get baseline image for this cqi
    try:
        baseline = Baseline.objects.filter(hub_qi_project__id=pk).latest('date_created')
    except Baseline.DoesNotExist:
        baseline = None

    project_images = RootCauseImages.objects.all()
    root_cause_image = project_images.filter(hub_qi_project__id=pk).order_by("date_created")
    project_images = project_images.filter(hub_qi_project__id=pk).count()
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
            # get cqi primary key
            post.qi_project_title = County_qi_projects.objects.get(project_title=facility_project.project_title)
            post.commented_by = CustomUser.objects.get(username=request.user.username)
            # save
            post.save()
            # show empty form
            form = ProjectCommentsForm()
    else:
        form = ProjectCommentsForm()
        # stakeholderform = StakeholderForm()

    # accessing facility qi projects
    # use two underscore to the field with foreign key
    list_of_projects = TestedChange.objects.filter(
        hub_project__hub=facility_project.hub).order_by(
        '-month_year')
    list_of_projects = [
        {'month_year': x.month_year,
         'project_id': x.hub_project_id,
         'tested of change': x.tested_change,
         'achievements': x.achievements,
         'facility': x.hub_project,
         'cqi': x.hub_project.project_title,
         } for x in list_of_projects
    ]
    # convert data from database to a dataframe
    list_of_projects = pd.DataFrame(list_of_projects)
    if list_of_projects.shape[0] != 0:
        dicts = {}
        keys = list_of_projects['project_id'].unique()
        values = list_of_projects['cqi'].unique()
        # for i in range(len(keys)):
        #     dicts[keys[i]] = values[i]
        for key, value in zip(keys, values):
            dicts[key] = value
        all_other_projects_trend = []
        for project in list_of_projects['cqi'].unique():
            all_other_projects_trend.append(
                prepare_trends(list_of_projects[list_of_projects['cqi'] == project], project))

        pro_perfomance_trial = dict(zip(keys, all_other_projects_trend))
    else:
        pro_perfomance_trial = {}

    # assign it to a dataframe using list comprehension
    other_projects = [
        {'department(s)': x.departments.department,
         'cqi category': x.project_category,
         'id': x.id,
         } for x in other_projects
    ]
    # convert data from database to a dataframe
    df_other_projects = pd.DataFrame(other_projects)
    df_other_projects['total projects'] = 1

    changes = test_of_change_qs.filter(hub_project__id=pk).order_by('-month_year')
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
                   "qi_teams": qi_teams,
                   "milestones": milestones, "action_plans": action_plans, "today": today, "baseline": baseline,
                   "title": "hub", "hub_name": "hub_name", "project_images": project_images,
                   "root_cause_images": root_cause_image}

    else:
        project_performance = {}
        facility_proj_performance = {}
        context = {"facility_project": facility_project, "test_of_change": changes,
                   "project_performance": project_performance, "facility_proj_performance": facility_proj_performance,
                   "pro_perfomance_trial": pro_perfomance_trial, "form": form, "all_comments": all_comments,
                   "all_archived": all_archived,
                   "qi_teams": qi_teams,
                   "milestones": milestones, "action_plans": action_plans, "today": today, "baseline": baseline,
                   "title": "hub", "hub_name": "hub_name", "project_images": project_images,
                   "root_cause_images": root_cause_image}

    return render(request, "project/individual_qi_project.html", context)


@login_required(login_url='login')
def untracked_projects(request, project_type):
    if not request.user.first_name:
        return redirect("profile")
    if project_type == "facility":
        all_projects = QI_Projects.objects.all()
        tracked_projects = TestedChange.objects.values_list('project_id', flat=True)
    elif project_type == "program":
        all_projects = Program_qi_projects.objects.all()
        tracked_projects = TestedChange.objects.values_list('program_project_id', flat=True)
    elif project_type == "subcounty":
        all_projects = Subcounty_qi_projects.objects.all()
        tracked_projects = TestedChange.objects.values_list('subcounty_project_id', flat=True)
    elif project_type == "county":
        all_projects = County_qi_projects.objects.all()
        tracked_projects = TestedChange.objects.values_list('county_project_id', flat=True)
    elif project_type == "hub":
        all_projects = Hub_qi_projects.objects.all()
        tracked_projects = TestedChange.objects.values_list('hub_project_id', flat=True)
    context = {
        "all_projects": all_projects,
        "all_responses": tracked_projects,
        "project_type": project_type,
    }
    return render(request, "project/untracked_projects.html", context)

@login_required(login_url='login')
def add_stake_holders(request, pk):
    if not request.user.first_name:
        return redirect("profile")
    facility_project = QI_Projects.objects.get(id=pk)

    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        stakeholderform = StakeholderForm(request.POST)
        if stakeholderform.is_valid():
            post = stakeholderform.save(commit=False)

            post.facility = Facilities.objects.get(name=facility_project.facility_name)
            post.save()
            # return HttpResponseRedirect(request.session['page_from'])
            return redirect(request.session['page_from'])
    else:
        stakeholderform = StakeholderForm()
    context = {"stakeholderform": stakeholderform,

               }
    return render(request, 'project/stakeholders.html', context)


# @login_required(login_url='login')
# def add_baseline_image(request, pk):
#     # WORKING!
#     try:
#         facility_project = QI_Projects.objects.get(id=pk)
#     except:
#         facility_project = Program_qi_projects.objects.get(id=pk)
#
#     if request.method == "GET":
#         request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
#
#     if request.method == "POST":
#         baselineform = BaselineForm(request.POST, request.FILES)
#         if baselineform.is_valid():
#             post = baselineform.save(commit=False)
#             #
#             try:
#                 post.facility = Facilities.objects.get(name=facility_project.facility_name)
#                 post.program = None
#                 post.qi_project = facility_project
#                 post.program_qi_project = None
#             except:
#                 post.facility = None
#                 post.program = Program.objects.get(program=facility_project.program)
#                 post.program_qi_project = facility_project
#                 post.qi_project = None
#
#             post.save()
#             # return HttpResponseRedirect(request.session['page_from'])
#             return redirect(request.session['page_from'])
#     else:
#         baselineform = BaselineForm()
#     context = {"form": baselineform,
#
#                }
#     return render(request, 'cqi/baseline_images.html', context)

# @login_required(login_url='login')
# def add_baseline_image(request, pk):
#     # WORKING!
#     try:
#         facility_project = QI_Projects.objects.get(id=pk)
#     except:
#         facility_project = Program_qi_projects.objects.get(id=pk)
#
#     if request.method == "GET":
#         request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
#
#     if request.method == "POST":
#         baselineform = BaselineForm(request.POST, request.FILES)
#         if baselineform.is_valid():
#             post = baselineform.save(commit=False)
#             #
#             try:
#                 post.facility = Facilities.objects.get(name=facility_project.facility_name)
#                 post.program = None
#                 post.qi_project = facility_project
#                 post.program_qi_project = None
#             except:
#                 post.facility = None
#                 post.program = Program.objects.get(program=facility_project.program)
#                 post.program_qi_project = facility_project
#                 post.qi_project = None
#
#             post.save()
#             # return HttpResponseRedirect(request.session['page_from'])
#             return redirect(request.session['page_from'])
#     else:
#         baselineform = BaselineForm()
#     context = {"form": baselineform,
#                "title": "ADD BASELINE STATUS"
#
#                }
#     return render(request, 'project/baseline_images.html', context)
@login_required(login_url='login')
def add_baseline_image(request, pk, program_name=None, facility_name=None, subcounty_name=None, hub_name=None,
                       county_name=None):
    if not request.user.first_name:
        return redirect("profile")
    # ADAPTED FOR QI_PROJECTS AND PROGRAM_QI_PROJECTS
    if facility_name:
        facility = Facilities.objects.get(name=facility_name)
        program = None
        qi_project = QI_Projects.objects.get(id=pk, facility_name=facility)
        program_qi_project = None
        subcounty_qi_project = None
        hub_qi_project = None
        county_qi_project = None
    elif program_name:
        program = Program.objects.get(program=program_name)
        facility = None
        qi_project = None
        program_qi_project = Program_qi_projects.objects.get(id=pk, program=program)
        subcounty_qi_project = None
        hub_qi_project = None
        county_qi_project = None
    elif subcounty_name:
        subcounty = Sub_counties.objects.get(sub_counties=subcounty_name)
        program = None
        facility = None
        qi_project = None
        program_qi_project = None
        subcounty_qi_project = Subcounty_qi_projects.objects.get(id=pk, sub_county=subcounty)
        hub_qi_project = None
        county_qi_project = None
    elif county_name:
        county = Counties.objects.get(county_name=county_name)
        program = None
        facility = None
        qi_project = None
        program_qi_project = None
        subcounty_qi_project = None
        hub_qi_project = None
        county_qi_project = County_qi_projects.objects.get(id=pk, county=county)
    elif hub_name:
        hub = Hub.objects.get(hub=hub_name)
        program = None
        facility = None
        qi_project = None
        program_qi_project = None
        subcounty_qi_project = None
        hub_qi_project = Hub_qi_projects.objects.get(id=pk, hub=hub)
        county_qi_project = None

    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        baselineform = BaselineForm(request.POST, request.FILES)
        if baselineform.is_valid():
            post = baselineform.save(commit=False)
            post.facility = facility
            post.program = program
            post.qi_project = qi_project
            post.program_qi_project = program_qi_project
            post.subcounty_qi_project = subcounty_qi_project
            post.hub_qi_project = hub_qi_project
            post.county_qi_project = county_qi_project
            try:
                post.save()
                return HttpResponseRedirect(request.session['page_from'])
            except KeyError as e:
                extension = e.args[0].split('.')[-1]
                allowed_formats = ['jpg', 'jpeg', 'png', 'gif', 'tif', 'tiff']
                if extension in allowed_formats:
                    messages.error(request, f"Failed to save the file. Please try again.")
                else:
                    messages.error(request,
                                   f"Unsupported file format. Please choose a file with one of the following extensions: {', '.join(allowed_formats)}.")
                return HttpResponseRedirect(request.session['page_from'])
    else:
        baselineform = BaselineForm()
    context = {"form": baselineform,
               "title": "ADD BASELINE STATUS",
               "facility_name": facility_name,
               "program_name": program_name,
               "subcounty_name": subcounty_name,
               "county_name": county_name,
               "hub_name": hub_name,
               }
    return render(request, 'project/baseline_images.html', context)


# def my_view(request, pk):
#     """
#     This view handles the retrieval of instances from two different models: `QI_projects` and `Program_qi_projects`.
#     The model to be retrieved is determined by the `model` GET parameter.
#     If the `model` parameter is not found in the list of models or if the instance with the specified primary key
#     does not exist, a 404 error is raised.
#
#     Args:
#         request (django.http.HttpRequest): The request object.
#         pk (int): The primary key of the instance to be retrieved.
#
#     Returns:
#         A response or a rendered template that uses the retrieved instance.
#     """
#     # A dictionary of models, with the model name as the key and the model class as the value.
#     models = {
#         'QI_projects': QI_projects,
#         'Program_qi_projects': Program_qi_projects
#     }
#
#     # Get the model name from the GET request.
#     model = request.GET.get('model')
#     # If the model name is not found in the dictionary, raise a 404 error.
#     if model not in models:
#         raise Http404("Page not found")
#
#     try:
#         # Try to retrieve the instance from the database.
#         instance = models[model].objects.get(pk=pk)
#     except models[model].DoesNotExist:
#         # If the instance does not exist, raise a 404 error.
#         raise Http404("Instance not found")
#
#     # Check the model name and access the correct field name.
#     if model == 'QI_projects':
#         field_name = instance.facility_name
#     elif model == 'Program_qi_projects':
#         field_name = instance.program
#
#     # Render a template or return a response using `field_name`.
#     # ...
#     context = {
#         "form": form,
#         "title": "Update baseline status",
#         "qi_project": qi_project,
#     }
#     return render(request, 'cqi/add_milestones.html', context)
# @login_required(login_url='login')
# def update_baseline(request, pk):
#      working!
#     if request.method == "GET":
#         request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
#     # A dictionary of models, with the model name as the key and the model class as the value.
#     # models = {
#     #     'QI_projects': QI_Projects,
#     #     'Program_qi_projects': Program_qi_projects
#     # }
#     # # Get the model name from the GET request.
#     # model = request.GET.get('model')
#     # # If the model name is not found in the dictionary, raise a 404 error.
#     # if model not in models:
#     #     raise Http404("Page not found")
#     #
#     # try:
#     #     # Try to retrieve the instance from the database.
#     #     instance = models[model].objects.get(pk=pk)
#     # except models[model].DoesNotExist:
#     #     # If the instance does not exist, raise a 404 error.
#     #     raise Http404("Instance not found")
#     #
#     # # Check the model name and access the correct field name.
#     # if model == 'QI_projects':
#     #     # field_name = instance.facility_name
#     #     item = Baseline.objects.get(qi_project__id=pk)
#     # elif model == 'Program_qi_projects':
#     #     # field_name = instance.program
#     #     item=Baseline.objects.get(program_qi_project__id=pk)
#
#
#     try:
#         qi_project = QI_Projects.objects.get(id=pk)
#         item = Baseline.objects.get(qi_project__id=pk)
#     except:
#         qi_project = Program_qi_projects.objects.get(id=pk)
#         item = Baseline.objects.get(program_qi_project__id=pk)
#     if request.method == "POST":
#         form = BaselineForm(request.POST, request.FILES, instance=item)
#         if form.is_valid():
#             form.save()
#             return HttpResponseRedirect(request.session['page_from'])
#     else:
#         form = BaselineForm(instance=item)
#     context = {
#         "form": form,
#         "title": "Update baseline status",
#         # "qi_project": instance,
#         "qi_project": qi_project,
#     }
#     return render(request, 'cqi/add_milestones.html', context)
# def update_baseline(request, pk):
#     model_name = None
#     qi_project = None
#     item = None
#
#     if request.method == "GET":
#         request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
#         model_name = request.GET.get('model')
#
#     if model_name:
#         model = apps.get_model(app_label='app_name', model_name=model_name)
#         try:
#             qi_project = model.objects.get(id=pk)
#             if model_name == "QI_Projects":
#                 item = Baseline.objects.get(qi_project__id=pk)
#             else:
#                 item = Baseline.objects.get(program_qi_project__id=pk)
#         except model.DoesNotExist:
#             raise Http404("Page not found.")
#     else:
#         try:
#             qi_project = QI_Projects.objects.get(id=pk)
#             item = Baseline.objects.get(qi_project__id=pk)
#         except QI_Projects.DoesNotExist:
#             try:
#                 qi_project = Program_qi_projects.objects.get(id=pk)
#                 item = Baseline.objects.get(program_qi_project__id=pk)
#             except Program_qi_projects.DoesNotExist:
#                 raise Http404("Page not found.")
#
#     if request.method == "POST":
#         form = BaselineForm(request.POST, request.FILES, instance=item)
#         if form.is_valid():
#             form.save()
#             return redirect(request.session['page_from'])
#     else:
#         form = BaselineForm(instance=item)
#     context = {
#         "form": form,
#         "title": "Update baseline status",
#         "qi_project": qi_project,
#     }
#     return render(request, 'cqi/add_milestones.html', context)
# from django.apps import apps
# from django.shortcuts import render, HttpResponseRedirect
# from django.http import Http404
# @login_required(login_url='login')
# def update_baseline(request, pk):
#     """
#     View to handle the update of the baseline status of a QI cqi.
#
#     Parameters:
#     - request (HttpRequest): The incoming request object
#     - pk (int): The primary key of the QI cqi
#
#     Returns:
#     - HttpResponse: A template rendering containing the updated baseline status form
#
#     """
#     # Store the name of the model in the GET request
#     model_name = None
#     # Store the instance of the QI cqi
#     qi_project = None
#     # Store the instance of the baseline
#     item = None
#
#     # Handle the GET request
#     if request.method == "GET":
#         # Store the referrer URL in the session
#         request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
#         # Get the model name from the GET request
#         model_name = request.GET.get('model')
#
#     # If the model name is not None, then retrieve the corresponding model
#     if model_name:
#         # Get the model using the app_label and model_name
#         model = apps.get_model(app_label='app_name', model_name=model_name)
#
#         try:
#             # Try to retrieve the instance of the QI cqi using the pk
#             qi_project = model.objects.get(id=pk)
#             # If the model name is 'QI_Projects', then retrieve the baseline using the foreign key 'qi_project'
#             if model_name == "QI_Projects":
#                 item = Baseline.objects.get(qi_project__id=pk)
#             # If the model name is 'Program_qi_projects', then retrieve the baseline using the foreign key
#             # 'program_qi_project'
#             elif model_name == "Program_qi_projects":
#                 item = Baseline.objects.get(program_qi_project__id=pk)
#             elif model_name == "Subcounty_qi_projects":
#                 item = Baseline.objects.get(subcounty_qi_project__id=pk)
#             elif model_name == "County_qi_projects":
#                 item = Baseline.objects.get(county_qi_project__id=pk)
#             # If the model name is 'Hub_qi_projects', then retrieve the baseline using the foreign key 'hub_qi_project'
#             elif model_name == "Hub_qi_projects":
#                 item = Baseline.objects.get(hub_qi_project__id=pk)
#         except model.DoesNotExist:
#             # Raise a 404 error if the QI cqi is not found
#             raise Http404("Page not found.")
#     else:
#         try:
#             # Try to retrieve the instance of the QI cqi using the pk and the 'QI_Projects' model
#             qi_project = QI_Projects.objects.get(id=pk)
#             item = Baseline.objects.get(qi_project__id=pk)
#         except QI_Projects.DoesNotExist:
#             try:
#                 # Try to retrieve the instance of the QI cqi using the pk and the 'Program_qi_projects' model
#                 qi_project = Program_qi_projects.objects.get(id=pk)
#                 item = Baseline.objects.get(program_qi_project__id=pk)
#             except Program_qi_projects.DoesNotExist:
#                 try:
#                     # Try to retrieve the instance of the QI cqi using the pk and the 'Program_qi_projects' model
#                     qi_project = Subcounty_qi_projects.objects.get(id=pk)
#                     item = Baseline.objects.get(program_qi_project__id=pk)
#                 except Subcounty_qi_projects.DoesNotExist:
#                     try:
#                         # Try to retrieve the instance of the QI cqi using the pk and the 'Program_qi_projects' model
#                         qi_project = County_qi_projects.objects.get(id=pk)
#                         item = Baseline.objects.get(program_qi_project__id=pk)
#                     except County_qi_projects.DoesNotExist:
#                         try:
#                             # Try to retrieve the instance of the QI cqi using the pk and the 'Hub_qi_projects' model
#                             qi_project = Hub_qi_projects.objects.get(id=pk)
#                             item = Baseline.objects.get(hub_qi_project__id=pk)
#                         except Hub_qi_projects.DoesNotExist:
#                             raise Http404("Page not found.")
#
#     if request.method == "POST":
#         form = BaselineForm(request.POST, request.FILES, instance=item)
#         if form.is_valid():
#             form.save()
#             return redirect(request.session['page_from'])
#     else:
#         form = BaselineForm(instance=item)
#     context = {
#         "form": form,
#         "title": "Update baseline status",
#         "qi_project": qi_project,
#     }
#     return render(request, 'project/add_milestones.html', context)
@login_required(login_url='login')
def update_baseline(request, pk, program_name=None, facility_name=None, subcounty_name=None, hub_name=None,
                    county_name=None):
    if not request.user.first_name:
        return redirect("profile")
    title = "Update baseline status"
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    if facility_name:
        facility_project = QI_Projects.objects.get(id=pk, facility_name__name=facility_name)
        qi_project = QI_Projects.objects.get(id=pk)
        level = "facility"
    if program_name:
        facility_project = Program_qi_projects.objects.get(id=pk, program__program=program_name)
        qi_project = Program_qi_projects.objects.get(id=pk)
        level = "program"
    if subcounty_name:
        facility_project = Subcounty_qi_projects.objects.get(id=pk, sub_county__sub_counties=subcounty_name)
        qi_project = Subcounty_qi_projects.objects.get(id=pk)
        level = "subcounty"
    if hub_name:
        facility_project = Hub_qi_projects.objects.get(id=pk, hub__hub=hub_name)
        qi_project = Hub_qi_projects.objects.get(id=pk)
        level = "hub"
    if county_name:
        facility_project = County_qi_projects.objects.get(id=pk, county__county_name=county_name)
        qi_project = County_qi_projects.objects.get(id=pk)
        level = "county"

    if request.method == "POST":
        form = BaselineForm(request.POST, request.FILES)
        # try:
        if form.is_valid():
            post = form.save(commit=False)
            if "facility" in level:
                post.facility = None
                post.program = None
                post.qi_project = qi_project
                post.program_qi_project = None
                post.subcounty_qi_project = None
                post.hub_qi_project = None
                post.county_qi_project = None
            elif "program" in level:
                post.facility = None
                post.program = None
                post.qi_project = None
                post.program_qi_project = qi_project
                post.subcounty_qi_project = None
                post.hub_qi_project = None
                post.county_qi_project = None
            elif "subcounty" in level:
                post.facility = None
                post.program = None
                post.qi_project = None
                post.program_qi_project = None
                post.subcounty_qi_project = qi_project
                post.hub_qi_project = None
                post.county_qi_project = None
            elif "county" in level:
                post.facility = None
                post.program = None
                post.qi_project = None
                post.program_qi_project = None
                post.subcounty_qi_project = None
                post.hub_qi_project = None
                post.county_qi_project = qi_project
            elif "hub" in level:
                post.facility = None
                post.program = None
                post.qi_project = None
                post.program_qi_project = None
                post.subcounty_qi_project = None
                post.hub_qi_project = qi_project
                post.county_qi_project = None
            post.created_by = request.user
            try:
                post.save()
                return HttpResponseRedirect(request.session['page_from'])
            except KeyError as e:
                extension = e.args[0].split('.')[-1]
                allowed_formats = ['jpg', 'jpeg', 'png', 'gif', 'tif', 'tiff']
                if extension in allowed_formats:
                    messages.error(request, f"Failed to save the file. Please try again.")
                else:
                    messages.error(request,
                                   f"Unsupported file format. Please choose a file with one of the following extensions: {', '.join(allowed_formats)}.")
                return HttpResponseRedirect(request.session['page_from'])
    else:
        form = BaselineForm(instance=qi_project)
    context = {"form": form, "title": title, "qi_project": qi_project, "level": level,
               "facility_name": facility_name,
               "program_name": program_name,
               }
    return render(request, "project/add_milestones.html", context)

    # return render(request, "project/add_milestones.html", context)


@login_required(login_url='login')
def delete_project(request, pk):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    item = QI_Projects.objects.get(id=pk)
    if request.method == "POST":
        item.delete()

        redirect("facilities_landing_page", project_type="facility")
    context = {
        "test_of_changes": item
    }
    return render(request, 'project/delete_test_of_change.html', context)


@login_required(login_url='login')
def delete_comment(request, pk):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    item = ProjectComments.objects.get(id=pk)
    if request.method == "POST":
        item.delete()

        redirect("facilities_landing_page", project_type="facility")
    context = {
        "test_of_changes": item
    }
    return render(request, 'project/delete_test_of_change.html', context)


# @login_required(login_url='login')
# def close_project(request, pk):
#     # check the page user is from
#     if request.method == "GET":
#         request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
#     cqi = close_project.objects.get(id=pk)
#     if request.method == "POST":
#         form = QI_ProjectsForm(request.POST, instance=cqi)
#         if form.is_valid():
#             form.save()
#             # redirect back to the page the user was from after saving the form
#             return HttpResponseRedirect(request.session['page_from'])
#     else:
#         form = Close_projectForm(instance=cqi)
#     context = {"form": form}
#     return render(request, "cqi/close_project.html", context)

# def login_page(request):
#     if request.method == "POST":
#         form = CreateUserForm(request.POST)
#         if form.is_valid():
#             form.save()
#             return redirect("dashboard")
#     else:
#         form = CreateUserForm()
#     context = {"form": form}
#     return render(request, "cqi/login_page.html", context)


# def register_page(request):
#     form = UserCreationForm()
# #     if request.method == "POST":
# #         form = CreateUserForm(request.POST)
# #         if form.is_valid():
# #             form.save()
# #             redirect("dashboard")
#     context = {"form": form}
#     return render(request, "cqi/login_page.html", context)


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
# return render(request, 'cqi/facility_landing_page.html', context)

# @login_required(login_url='login')
# def add_project_milestone(request, pk):
#     title = "ADD PROJECT MILESTONE"
#     # check the page user is from
#     if request.method == "GET":
#         request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
#     try:
#         facility_project = QI_Projects.objects.get(id=pk)
#         qi_project = QI_Projects.objects.get(id=pk)
#         level = "facility"
#     except:
#         facility_project = Program_qi_projects.objects.get(id=pk)
#         qi_project = Program_qi_projects.objects.get(id=pk)
#         level = "program"
#
#     if request.method == "POST":
#         form = MilestoneForm(request.POST)
#         # try:
#         if form.is_valid():
#             post = form.save(commit=False)
#             if "facility" in level:
#                 post.facility = Facilities.objects.get(id=facility_project.facility_name_id)
#                 post.qi_project = qi_project
#             elif "program" in level:
#                 post.program = Program.objects.get(id=facility_project.program_id)
#                 post.program_qi_project = qi_project
#
#             post.created_by = request.user
#             post.save()
#             return HttpResponseRedirect(request.session['page_from'])
#     else:
#         form = MilestoneForm()
#     context = {"form": form, "title": title, "qi_project": qi_project, "level": level, }
#     return render(request, "project/add_milestones.html", context)
# def add_baseline_image(request, pk, program_name=None, facility_name=None):
#     # ADAPTED FOR QI_PROJECTS AND PROGRAM_QI_PROJECTS
#     if facility_name:
#         facility = Facilities.objects.get(name=facility_name)
#         program = None
#         qi_project = QI_Projects.objects.get(id=pk, facility_name=facility)
#         program_qi_project = None
#     elif program_name:
#         program = Program.objects.get(program=program_name)
#         facility = None
#         qi_project = None
#         program_qi_project = Program_qi_projects.objects.get(id=pk, program=program)
@login_required(login_url='login')
def add_project_milestone(request, pk, program_name=None, facility_name=None, subcounty_name=None, hub_name=None,
                          county_name=None):
    if not request.user.first_name:
        return redirect("profile")
    title = "ADD PROJECT MILESTONE"
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    if facility_name:
        facility_project = QI_Projects.objects.get(id=pk, facility_name__name=facility_name)
        qi_project = QI_Projects.objects.get(id=pk)
        level = "facility"
    elif program_name:
        facility_project = Program_qi_projects.objects.get(id=pk, program__program=program_name)
        qi_project = Program_qi_projects.objects.get(id=pk)
        level = "program"
    elif subcounty_name:
        facility_project = Subcounty_qi_projects.objects.get(id=pk, sub_county__sub_counties=subcounty_name)
        qi_project = Subcounty_qi_projects.objects.get(id=pk)
        level = "subcounty"
    elif county_name:
        facility_project = County_qi_projects.objects.get(id=pk, county__county_name=county_name)
        qi_project = County_qi_projects.objects.get(id=pk)
        level = "county"
    elif hub_name:
        facility_project = Hub_qi_projects.objects.get(id=pk, hub__hub=hub_name)
        qi_project = Hub_qi_projects.objects.get(id=pk)
        level = "hub"

    if request.method == "POST":
        form = MilestoneForm(request.POST)
        # try:
        if form.is_valid():
            post = form.save(commit=False)
            if "facility" in level:
                post.facility = Facilities.objects.get(id=facility_project.facility_name_id)
                post.qi_project = qi_project
            elif "program" in level:
                post.program = Program.objects.get(id=facility_project.program_id)
                post.program_qi_project = qi_project
                # post.facility = None
                # post.qi_project = None
                # post.subcounty_qi_project = None
                # post.county_qi_project = None
                # post.hub_qi_project = None
            elif "subcounty" in level:
                # post.program = Sub_counties.objects.get(id=facility_project.sub_county_id)
                post.subcounty_qi_project = qi_project
            elif "county" in level:
                # post.program = Counties.objects.get(id=facility_project.county_id)
                post.county_qi_project = qi_project
            elif "hub" in level:
                # post.program = Hub.objects.get(id=facility_project.hub_id)
                post.hub_qi_project = qi_project

            post.created_by = request.user
            post.save()
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = MilestoneForm()
    context = {"form": form, "title": title, "qi_project": qi_project, "level": level,
               "facility_name": facility_name,
               "program_name": program_name,
               }
    return render(request, "project/add_milestones.html", context)


@login_required(login_url='login')
def update_milestone(request, pk, program_name=None, facility_name=None, subcounty_name=None, hub_name=None,
                     county_name=None):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    item = Milestone.objects.get(id=pk)
    if facility_name:
        qi_project = QI_Projects.objects.get(id=item.qi_project_id)
    elif program_name:
        qi_project = Program_qi_projects.objects.get(id=item.program_qi_project_id)
    elif subcounty_name:
        qi_project = Subcounty_qi_projects.objects.get(id=item.subcounty_qi_project_id)
    elif county_name:
        qi_project = County_qi_projects.objects.get(id=item.county_qi_project_id)
    elif hub_name:
        qi_project = Hub_qi_projects.objects.get(id=item.hub_qi_project_id)
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
    if not request.user.first_name:
        return redirect("profile")
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
def add_corrective_action(request, pk, program_name=None, facility_name=None, subcounty_name=None, hub_name=None,
                          county_name=None):
    if not request.user.first_name:
        return redirect("profile")
    # facility_project = QI_Projects.objects.get(id=pk)

    if facility_name:
        facility_project = get_object_or_404(QI_Projects, id=pk, facility_name__name=facility_name)
        qi_project = QI_Projects.objects.get(id=pk)
        facility = facility_project.facility_name
        qi_team_members = Qi_team_members.objects.filter(qi_project=facility_project)
        level = "facility"
    elif program_name:
        facility_project = get_object_or_404(Program_qi_projects, id=pk, program__program=program_name)
        qi_project = Program_qi_projects.objects.get(id=pk)
        facility = facility_project.program
        qi_team_members = Qi_team_members.objects.filter(program_qi_project=facility_project)
        level = "program"
    elif subcounty_name:
        facility_project = get_object_or_404(Subcounty_qi_projects, id=pk, sub_county__sub_counties=subcounty_name)
        qi_project = Subcounty_qi_projects.objects.get(id=pk)
        facility = facility_project.sub_county
        qi_team_members = Qi_team_members.objects.filter(subcounty_qi_project=facility_project)
        level = "subcounty"
    elif county_name:
        facility_project = get_object_or_404(County_qi_projects, id=pk, county__county_name=county_name)
        qi_project = County_qi_projects.objects.get(id=pk)
        facility = facility_project.county
        qi_team_members = Qi_team_members.objects.filter(county_qi_project=facility_project)
        level = "county"
    elif hub_name:
        facility_project = get_object_or_404(Hub_qi_projects, id=pk, hub__hub=hub_name)
        qi_project = Hub_qi_projects.objects.get(id=pk)
        facility = facility_project.hub
        qi_team_members = Qi_team_members.objects.filter(hub_qi_project=facility_project)
        level = "hub"

    qi_projects = facility_project

    today = timezone.now().date()
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        form = ActionPlanForm(facility, qi_projects, level, request.POST)
        if form.is_valid():
            # form.save()
            post = form.save(commit=False)
            if level == "facility":
                post.facility = Facilities.objects.get(id=facility_project.facility_name_id)
                post.qi_project = qi_project
                post.program = None
                post.program_qi_project = None
                post.subcounty_qi_project = None
                post.county_qi_project = None
                post.hub_qi_project = None
            elif level == "program":
                post.facility = None
                post.program = Program.objects.get(id=facility_project.program_id)
                post.program_qi_project = qi_project
                post.qi_project = None
                post.subcounty_qi_project = None
                post.county_qi_project = None
                post.hub_qi_project = None
            elif level == "county":
                post.facility = None
                post.program = None
                post.program_qi_project = None
                post.qi_project = None
                post.subcounty_qi_project = None
                post.county_qi_project = qi_project
                post.hub_qi_project = None
            elif level == "subcounty":
                post.facility = None
                post.program = None
                post.program_qi_project = None
                post.qi_project = None
                post.subcounty_qi_project = qi_project
                post.county_qi_project = None
                post.hub_qi_project = None
            elif level == "hub":
                post.facility = None
                post.program = None
                post.program_qi_project = None
                post.subcounty_qi_project = None
                post.county_qi_project = None
                post.hub_qi_project = qi_project

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
        form = ActionPlanForm(facility, qi_projects, level)
    context = {"form": form,
               "title": "Add Action Plan",
               "qi_team_members": qi_team_members,
               "qi_project": qi_project,
               "level": level
               }
    return render(request, "project/add_qi_manager.html", context)


@login_required(login_url='login')
def update_action_plan(request, pk, program_name=None, facility_name=None, subcounty_name=None, hub_name=None,
                       county_name=None):
    if not request.user.first_name:
        return redirect("profile")
    # facility_project = get_object_or_404(QI_Projects, id=pk)
    # qi_team_members = Qi_team_members.objects.filter(qi_project=facility_project)
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    action_plan = ActionPlan.objects.get(id=pk)
    if facility_name:
        facility = action_plan.facility
        qi_projects = action_plan.qi_project

        qi_project = QI_Projects.objects.get(id=action_plan.qi_project_id)
        qi_team_members = Qi_team_members.objects.filter(qi_project=action_plan.qi_project)
        level = "facility"
    elif program_name:
        facility = action_plan.program
        qi_projects = action_plan.program_qi_project

        qi_project = Program_qi_projects.objects.get(id=action_plan.program_qi_project_id)
        qi_team_members = Qi_team_members.objects.filter(program_qi_project=action_plan.qi_project)
        level = "program"

    elif subcounty_name:
        facility = action_plan.subcounty_qi_project.sub_county
        qi_projects = action_plan.subcounty_qi_project
        qi_project = Subcounty_qi_projects.objects.get(id=action_plan.subcounty_qi_project_id)
        qi_team_members = Qi_team_members.objects.filter(subcounty_qi_project=action_plan.qi_project)
        level = "subcounty"
    elif county_name:
        facility = action_plan.county_qi_project.county
        qi_projects = action_plan.county_qi_project

        qi_project = County_qi_projects.objects.get(id=action_plan.county_qi_project_id)
        qi_team_members = Qi_team_members.objects.filter(county_qi_project=action_plan.qi_project)
        level = "county"
    elif hub_name:
        facility = action_plan.hub_qi_project.hub
        qi_projects = action_plan.hub_qi_project

        qi_project = Hub_qi_projects.objects.get(id=action_plan.hub_qi_project_id)
        qi_team_members = Qi_team_members.objects.filter(hub_qi_project=action_plan.qi_project)
        level = "hub"

    if request.method == "POST":
        form = ActionPlanForm(facility, qi_projects, level, request.POST, instance=action_plan)
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
        form = ActionPlanForm(facility, qi_projects, level, instance=action_plan)
    context = {
        "form": form,
        "qi_team_members": qi_team_members,
        "title": "Update Action Plan",
        "qi_project": qi_project,
    }
    return render(request, 'project/add_qi_manager.html', context)


@login_required(login_url='login')
def delete_action_plan(request, pk):
    if not request.user.first_name:
        return redirect("profile")
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


# @login_required(login_url='login')
# def create_comment(request, pk):
#     comment = None
#     qi_project = None
#     program_qi_project = None
#     try:
#         comment = Comment.objects.get(id=pk)
#     except ObjectDoesNotExist:
#         try:
#             qi_project = QI_Projects.objects.get(id=pk)
#         except ObjectDoesNotExist:
#             program_qi_project = Program_qi_projects.objects.get(id=pk)
#     if request.method == "POST":
#         form = CommentForm(request.POST)
#         if form.is_valid():
#             content = form.cleaned_data['content']
#             parent_id = form.cleaned_data.get('parent_id')
#             try:
#                 with transaction.atomic():
#                     if parent_id:
#                         parent_comment = Comment.objects.get(id=parent_id)
#                         Comment.objects.create(content=content, parent=parent_comment,
#                                                parent_id=request.POST.get('parent'))
#                     else:
#                         if comment:
#                             Comment.objects.create(content=content, author=request.user,
#                                                    parent_id=request.POST.get('parent'),
#                                                    qi_project_title=comment.qi_project_title,
#                                                    program_qi_project_title=comment.program_qi_project_title,
#                                                    )
#                         elif qi_project:
#                             Comment.objects.create(content=content, author=request.user, qi_project_title=qi_project)
#                         else:
#                             Comment.objects.create(content=content, author=request.user,
#                                                    program_qi_project_title=program_qi_project)
#             except ObjectDoesNotExist:
#                 form.add_error('parent_id', 'Parent comment does not exist')
#             except PermissionDenied:
#                 form.add_error(None, 'You do not have permission to create a comment')
#             else:
#                 return redirect(request.META.get('HTTP_REFERER'))
#     else:
#         form = CommentForm()
#     return render(request, 'project/create_comment.html', {'form': form})
@login_required(login_url='login')
def create_comment(request, pk, program_name=None, facility_name=None, subcounty_name=None, hub_name=None,
                   county_name=None):
    if not request.user.first_name:
        return redirect("profile")
    comment = None
    qi_project = None
    program_qi_project = None
    subcounty_qi_project = None
    county_qi_project = None
    hub_qi_project = None
    try:
        # if facility_name:
        comment = Comment.objects.get(id=pk)
        # if program_name:
        #     comment = Comment.objects.get(id=pk, program_qi_project_title__program__program=program_name)
    except ObjectDoesNotExist:
        if facility_name:
            qi_project = QI_Projects.objects.get(id=pk, facility_name__name=facility_name)
        elif program_name:
            program_qi_project = Program_qi_projects.objects.get(id=pk, program__program=program_name)
        elif subcounty_name:
            subcounty_qi_project = Subcounty_qi_projects.objects.get(id=pk, sub_county__sub_counties=subcounty_name)
        elif county_name:
            county_qi_project = County_qi_projects.objects.get(id=pk, county__county_name=county_name)
        elif hub_name:
            hub_qi_project = Hub_qi_projects.objects.get(id=pk, hub__hub=hub_name)
    if request.method == "POST":
        form = CommentForm(request.POST)
        if form.is_valid():
            content = form.cleaned_data['content']
            parent_id = form.cleaned_data.get('parent_id')
            try:
                with transaction.atomic():
                    if parent_id:
                        parent_comment = Comment.objects.get(id=parent_id)
                        Comment.objects.create(content=content, parent=parent_comment,
                                               parent_id=request.POST.get('parent'))
                    else:
                        if comment:
                            Comment.objects.create(content=content, author=request.user,
                                                   parent_id=request.POST.get('parent'),
                                                   qi_project_title=comment.qi_project_title,
                                                   program_qi_project_title=comment.program_qi_project_title,
                                                   subcounty_qi_project_title=comment.subcounty_qi_project_title,
                                                   county_project_title=comment.county_project_title,
                                                   hub_qi_project_title=comment.hub_qi_project_title,
                                                   )
                        elif qi_project:
                            Comment.objects.create(content=content, author=request.user, qi_project_title=qi_project)
                        elif program_qi_project:
                            Comment.objects.create(content=content, author=request.user,
                                                   program_qi_project_title=program_qi_project)
                        elif subcounty_qi_project:
                            Comment.objects.create(content=content, author=request.user,
                                                   subcounty_qi_project_title=subcounty_qi_project)
                        elif county_qi_project:
                            Comment.objects.create(content=content, author=request.user,
                                                   county_project_title=county_qi_project)
                        elif hub_qi_project:
                            Comment.objects.create(content=content, author=request.user,
                                                   hub_qi_project_title=hub_qi_project)
            except ObjectDoesNotExist:
                form.add_error('parent_id', 'Parent comment does not exist')
            except PermissionDenied:
                form.add_error(None, 'You do not have permission to create a comment')
            else:
                return redirect(request.META.get('HTTP_REFERER'))
    else:
        form = CommentForm()
    return render(request, 'project/create_comment.html', {'form': form})


#
@login_required(login_url='login')
def update_comments(request, pk):
    if not request.user.first_name:
        return redirect("profile")
    comment = Comment.objects.get(id=pk)

    try:
        project = QI_Projects.objects.get(id=comment.qi_project_title_id)
    except:
        project = Program_qi_projects.objects.get(id=comment.program_qi_project_title_id)
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            # post = form.save(commit=False)
            # post.project_name = cqi
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

@login_required(login_url='login')
def delete_comments(request, pk):
    if not request.user.first_name:
        return redirect("profile")
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


# def show_project_comments(request, pk):
#     try:
#         project = QI_Projects.objects.get(id=pk)
#         level = "facility"
#     except:
#         project = Program_qi_projects.objects.get(id=pk)
#         level = "program"
#
#     if "facility" in level:
#         comments = Comment.objects.filter(qi_project_title_id=pk, parent_id=None).order_by('-created_at')
#     elif "program" in level:
#         try:
#             comments = Comment.objects.filter(program_qi_project_title_id=pk, parent_id=None).order_by('-created_at')
#         except:
#             comments = None
#
#     if not comments:
#         comments = Comment.objects.filter(id=pk).order_by('-created_at')
#     context = {'all_comments': comments, "title": "COMMENTS", "qi_project": project, }
#     return render(request, 'project/comments_trial.html', context)
@login_required(login_url='login')
def show_project_comments(request, pk, program_name=None, facility_name=None, subcounty_name=None, hub_name=None,
                          county_name=None):
    if not request.user.first_name:
        return redirect("profile")
    if facility_name:
        project = QI_Projects.objects.get(id=pk, facility_name__name=facility_name)
        level = "facility"
    elif program_name:
        project = Program_qi_projects.objects.get(id=pk, program__program=program_name)
        level = "program"
    elif subcounty_name:
        project = Subcounty_qi_projects.objects.get(id=pk, sub_county__sub_counties=subcounty_name)
        level = "subcounty"
    elif county_name:
        project = County_qi_projects.objects.get(id=pk, county__county_name=county_name)
        level = "county"
    elif hub_name:
        project = Hub_qi_projects.objects.get(id=pk, hub__hub=hub_name)
        level = "hub"

    if "facility" in level:
        comments = Comment.objects.filter(qi_project_title_id=pk, parent_id=None).order_by('-created_at')
    elif "program" in level:
        try:
            comments = Comment.objects.filter(program_qi_project_title_id=pk, parent_id=None).order_by('-created_at')
        except:
            comments = None
    elif "subcounty" in level:
        try:
            comments = Comment.objects.filter(subcounty_qi_project_title_id=pk, parent_id=None).order_by('-created_at')
        except:
            comments = None
    elif "county" in level:
        try:
            comments = Comment.objects.filter(county_project_title_id=pk, parent_id=None).order_by('-created_at')
        except:
            comments = None
    elif "hub" in level:
        try:
            comments = Comment.objects.filter(hub_qi_project_title_id=pk, parent_id=None).order_by('-created_at')
        except:
            comments = None

    if not comments:
        comments = Comment.objects.filter(id=pk).order_by('-created_at')
    context = {'all_comments': comments, "title": "COMMENTS", "qi_project": project,
               "program_name": program_name,
               "facility_name": facility_name,
               "subcounty_name": subcounty_name,
               "county_name": county_name,
               "hub_name": hub_name,
               }
    return render(request, 'project/comments_trial.html', context)

@login_required(login_url='login')
def show_all_comments(request):
    if not request.user.first_name:
        return redirect("profile")
    # all_comments = ProjectComments.objects.all().order_by('-comment_updated')
    all_comments = Comment.objects.filter(parent_id=None).prefetch_related(
        'qi_project_title__qi_team_members').order_by(
        '-comment_updated')

    context = {
        "all_comments": all_comments,
        "title": "All comments"
    }
    return render(request, "project/comments_trial.html", context)

@login_required(login_url='login')
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
def add_sustainmentplan(request, pk, program_name=None, facility_name=None, subcounty_name=None, hub_name=None,
                        county_name=None):
    if not request.user.first_name:
        return redirect("profile")
    # qi_project=QI_Projects.objects.get(id=pk)
    # lesson=Lesson_learned.objects.filter(project_name=qi_project)
    if facility_name:
        qi_project = QI_Projects.objects.filter(id=pk, facility_name__name=facility_name).first()
        lesson = Lesson_learned.objects.filter(project_name=qi_project)
        program = None
        qi_project_name = qi_project
        subcounty = None
        county = None
        hub = None
    # if not qi_project:
    #     raise Http404("Project does not exist")
    elif program_name:
        qi_project = Program_qi_projects.objects.filter(id=pk, program__program=program_name).first()
        lesson = Lesson_learned.objects.filter(program=qi_project)
        qi_project_name = None
        program = qi_project
        subcounty = None
        county = None
        hub = None
    elif subcounty_name:
        qi_project = Subcounty_qi_projects.objects.filter(id=pk, sub_county__counties=subcounty_name).first()
        lesson = Lesson_learned.objects.filter(subcounty=qi_project)
        qi_project_name = None
        program = None
        subcounty = qi_project
        county = None
        hub = None
    elif county_name:
        qi_project = County_qi_projects.objects.filter(id=pk, county__county_name=county_name).first()
        lesson = Lesson_learned.objects.filter(county=qi_project)
        qi_project_name = None
        program = None
        subcounty = None
        county = qi_project
        hub = None
    elif hub_name:
        qi_project = Hub_qi_projects.objects.filter(id=pk, hub__hub=hub_name).first()
        lesson = Lesson_learned.objects.filter(hub=qi_project)
        qi_project_name = None
        program = None
        subcounty = None
        county = None
        hub = qi_project

    title = "ADD SUSTAINMENT PLAN"
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        form = SustainmentPlanForm(request.POST, request.FILES)

        # try:
        if form.is_valid():
            # TODO: ENSURE ALL FORMS CAN SHOW FORM ERRORS
            post = form.save(commit=False)
            post.created_by = request.user
            post.qi_project = qi_project_name
            post.program = program
            post.subcounty = subcounty
            post.county = county
            post.hub = hub
            post.save()
            # return HttpResponseRedirect(request.session['page_from'])
            return redirect("show_sustainmentPlan")
    else:
        form = SustainmentPlanForm()
    context = {"form": form, "title": title, "qi_project": qi_project, "lesson_learnt": lesson, }
    return render(request, "project/add_qi_manager.html", context)

@login_required(login_url='login')
def show_sustainmentPlan(request):
    if not request.user.first_name:
        return redirect("profile")
    plan = SustainmentPlan.objects.all()

    context = {
        "plan": plan
    }
    return render(request, "project/sustainment_plan.html", context)

@login_required(login_url='login')
def update_sustainable_plan(request, pk, program_name=None, facility_name=None, subcounty_name=None, hub_name=None,
                            county_name=None):
    if not request.user.first_name:
        return redirect("profile")
    item = SustainmentPlan.objects.get(id=pk)
    if facility_name:
        qi_project = QI_Projects.objects.get(id=item.qi_project_id)
    elif program_name:
        qi_project = Program_qi_projects.objects.get(id=item.program_id)
    elif subcounty_name:
        qi_project = Subcounty_qi_projects.objects.get(id=item.subcounty_id)
    elif county_name:
        qi_project = County_qi_projects.objects.get(id=item.county_id)
    elif hub_name:
        qi_project = Hub_qi_projects.objects.get(id=item.hub_id)
    # cqi = QI_Projects.objects.get(id=lesson_learnt.project_name_id)
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        form = SustainmentPlanForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            return redirect("show_sustainmentPlan")
    else:
        form = SustainmentPlanForm(instance=item)
    context = {"form": form,
               "qi_project": qi_project,
               "title": "UPDATE SUSTAINMENT PLAN",
               }

    return render(request, "project/add_qi_manager.html", context)


@login_required(login_url='login')
def delete_sustainable_plan(request, pk):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    item = SustainmentPlan.objects.get(id=pk)
    if request.method == "POST":
        item.delete()

        return HttpResponseRedirect(request.session['page_from'])
    context = {
        "test_of_changes": item
    }
    return render(request, 'project/delete_test_of_change.html', context)


@login_required(login_url='login')
def monthly_data_review(request):
    if not request.user.first_name:
        return redirect("profile")
    return render(request, 'project/monthly_data_review_summary.html')


@login_required(login_url='login')
def add_images(request, pk, program_name=None, facility_name=None, subcounty_name=None, hub_name=None,
               county_name=None):
    if not request.user.first_name:
        return redirect("profile")
    # ADAPTED FOR QI_PROJECTS AND PROGRAM_QI_PROJECTS
    if facility_name:
        facility = Facilities.objects.get(name=facility_name)
        program = None
        qi_project = QI_Projects.objects.get(id=pk, facility_name=facility)
        program_qi_project = None
        subcounty_qi_project = None
        county_qi_project = None
        hub_qi_project = None
    elif program_name:
        program = Program.objects.get(program=program_name)
        facility = None
        qi_project = None
        program_qi_project = Program_qi_projects.objects.get(id=pk, program=program)
        subcounty_qi_project = None
        county_qi_project = None
        hub_qi_project = None
    elif subcounty_name:
        subcounty = Sub_counties.objects.get(sub_counties=subcounty_name)
        facility = None
        qi_project = None
        program_qi_project = None
        subcounty_qi_project = Subcounty_qi_projects.objects.get(id=pk, sub_county=subcounty)
        county_qi_project = None
        hub_qi_project = None
        program = None
    elif county_name:
        county = Counties.objects.get(county_name=county_name)
        facility = None
        qi_project = None
        program_qi_project = None
        subcounty_qi_project = None
        county_qi_project = County_qi_projects.objects.get(id=pk, county=county)
        hub_qi_project = None
        program = None
    elif hub_name:
        hub = Hub.objects.get(hub=hub_name)
        facility = None
        qi_project = None
        program_qi_project = None
        subcounty_qi_project = None
        county_qi_project = None
        hub_qi_project = Hub_qi_projects.objects.get(id=pk, hub=hub)
        program = None

    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        form = RootCauseImagesForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.facility = facility
            post.program = program
            post.qi_project = qi_project
            post.program_qi_project = program_qi_project
            post.subcounty_qi_project = subcounty_qi_project
            post.county_qi_project = county_qi_project
            post.hub_qi_project = hub_qi_project
            post.save()
            # return HttpResponseRedirect(request.session['page_from'])
            return redirect(request.session['page_from'])
    else:
        form = RootCauseImagesForm()
    context = {"form": form,
               "title": "Add Root Cause Images",
               "facility_name": facility_name,
               "program_name": program_name,
               "subcounty_name": subcounty_name,
               "county_name": county_name,
               "hub_name": hub_name,
               }
    return render(request, 'project/baseline_images.html', context)

@login_required(login_url='login')
def action_plans_for_responsible_person(request, pk):
    if not request.user.first_name:
        return redirect("profile")
    responsible_person = Qi_team_members.objects.filter(user_id=pk).first()
    action_plans = ActionPlan.objects.filter(responsible__user_id=pk)

    context = {
        'responsible_person': responsible_person,
        'action_plans': action_plans,
    }
    return render(request, 'project/qi_team_members.html', context)


@login_required(login_url='login')
def qiteam_member_filter_project(request, pk):
    if not request.user.first_name:
        return redirect("profile")
    # get all the Qi_team_members where the user is a member
    qi_team_members = Qi_team_members.objects.filter(user_id=pk)
    qi_team_members = Qi_team_members.objects.filter(user_id=pk)

    # get all the QI_Projects where the Qi_team_member is associated with
    projects = QI_Projects.objects.filter(qi_team_members__in=qi_team_members)
    # for i in qi_team_members:
    first_name = qi_team_members.values_list('user__username', flat=True)[0]
    last_name = qi_team_members.values_list('user__last_name', flat=True)[0]
    facility_name = first_name + " " + last_name
    context = {}
    #
    #
    pro_perfomance_trial = {}
    projects_tracked = []
    # projects = QI_Projects.objects.filter(facility=pk).order_by("-date_updated")
    pk = str(pk).lower()
    projects = QI_Projects.objects.filter(qi_team_members__in=qi_team_members)
    subcounty_projects = Subcounty_qi_projects.objects.filter(qi_team_members__in=qi_team_members)
    county_projects = County_qi_projects.objects.filter(qi_team_members__in=qi_team_members)
    hub_projects = Hub_qi_projects.objects.filter(qi_team_members__in=qi_team_members)
    program_projects = Program_qi_projects.objects.filter(qi_team_members__in=qi_team_members)
    all_projects = list(chain(projects, subcounty_projects, hub_projects, county_projects, program_projects))
    # facility_name = pk
    number_of_projects_created = len(all_projects)
    try:
        qi_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.project_id,
             'tested of change': x.tested_change,

             'facility': x.project.facility_name,
             'cqi': x.project.project_title,
             'department': x.project.departments.department,
             } for x in TestedChange.objects.filter(project__qi_team_members__in=qi_team_members)
        ]
        fac_qi_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.project_id,
             'tested of change': x.tested_change,

             'facility': x.project.hub,
             'cqi': x.project.project_title,
             'department': x.project.departments.department,
             } for x in TestedChange.objects.filter(program_project__qi_team_members__in=qi_team_members)
        ]
        program_qi_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.program_project_id,
             'tested of change': x.tested_change,

             'facility': x.program_project.program.program,
             'cqi': x.program_project.project_title,
             'department': x.program_project.departments.department,
             } for x in TestedChange.objects.filter(program_project__qi_team_members__in=qi_team_members)
        ]
        subcounty_qi_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.subcounty_project_id,
             'tested of change': x.tested_change,

             'facility': x.subcounty_project.sub_county.sub_counties,
             'cqi': x.subcounty_project.project_title,
             'department': x.subcounty_project.departments.department,
             } for x in TestedChange.objects.filter(subcounty_project__qi_team_members__in=qi_team_members)
        ]
        county_qi_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.county_project_id,
             'tested of change': x.tested_change,

             'facility': x.county_project.county.county_name,
             'cqi': x.county_project.project_title,
             'department': x.county_project.departments.department,
             } for x in TestedChange.objects.filter(county_project__qi_team_members__in=qi_team_members)
        ]
        hub_qi_projects = [
            {'achievements': x.achievements,
             'month_year': x.month_year,
             'project_id': x.hub_project_id,
             'tested of change': x.tested_change,

             'facility': x.hub_project.hub.hub,
             'cqi': x.hub_project.project_title,
             'department': x.hub_project.departments.department,
             } for x in TestedChange.objects.filter(hub_project__qi_team_members__in=qi_team_members)
        ]
        # then concatenate the two lists to get a single list of dictionaries
        # Finally, you can create a dataframe from this list of dictionaries.
        qi_projects_df = pd.DataFrame(qi_projects)

        program_qi_projects_df = pd.DataFrame(program_qi_projects)
        subcounty_qi_projects_df = pd.DataFrame(subcounty_qi_projects)
        county_qi_projects_df = pd.DataFrame(county_qi_projects)
        fac_qi_projects_df = pd.DataFrame(fac_qi_projects)

        hub_qi_projects_df = pd.DataFrame(hub_qi_projects)

        list_of_projects = pd.concat([qi_projects_df,
                                      program_qi_projects_df,
                                      subcounty_qi_projects_df,
                                      county_qi_projects_df,
                                      hub_qi_projects_df,
                                      fac_qi_projects_df
                                      ])
        # list_of_projects = pd.DataFrame(test_changes)
        projects_tracked = list_of_projects['project_id'].unique()
        pro_perfomance_trial = prepare_viz(list_of_projects, pk, "facility")

        # facility_name = pk

        # difference
        number_of_projects_created = len(all_projects)
        number_of_projects_with_test_of_change = len(pro_perfomance_trial)
        difference = number_of_projects_created - number_of_projects_with_test_of_change
    except:
        number_of_projects_created = len(all_projects)
        number_of_projects_with_test_of_change = 0
        difference = number_of_projects_created - number_of_projects_with_test_of_change
        pro_perfomance_trial = None

    context = {"projects": all_projects,
               "facility_name": facility_name,
               "title": "Ongoing",
               "pro_perfomance_trial": pro_perfomance_trial,
               "difference": difference,
               "projects_tracked": projects_tracked,
               "number_of_projects_created": number_of_projects_created,

               }
    return render(request, "project/department_filter_projects.html", context)
