import pandas as pd
import numpy as np
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Count
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect

from account.forms import NewUserForm, UpdateUserForm
from .models import QI_Projects
# from .forms import QI_ProjectsForm, Close_projectForm, CreateUserForm, AccountForm
from .forms import QI_ProjectsForm, Close_projectForm, TestedChangeForm
from .filters import *

import plotly.express as px
import plotly.graph_objects as go
from plotly.offline import plot
import plotly.offline as opy


# Create your views here.
@login_required(login_url='login')
def dashboard(request):
    form = QI_ProjectsForm()
    context = {"form": form}
    return render(request, "project/dashboard.html", context)


@login_required(login_url='login')
def add_project(request):
    # check the page user is from
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    if request.method == "POST":
        form = QI_ProjectsForm(request.POST)
        if form.is_valid():
            form.save()
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
            form.save()
            # form.created_by = request.user
            # form.modified_by = request.user
            # form.save()
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
    #     print(num_post)
    #     context = {"qi_list": qi_list, "num_post": num_post, "projects": projects,
    #
    #                }
    #     return render(request, "project/facility_landing_page.html", context)

    projects = QI_Projects.objects.count()
    my_filters = QiprojectFilter(request.GET, queryset=qi_list)
    qi_list = my_filters.qs

    context = {"qi_list": qi_list, "num_post": num_post, "projects": projects,
               "my_filters": my_filters,
               }
    return render(request, "project/facility_landing_page.html", context)


@login_required(login_url='login')
def facility_project(request, pk):
    projects = QI_Projects.objects.filter(facility=pk).order_by("-date_updated")
    # print(projects)
    # print(projects[1])
    facility_name = pk
    # for user in NewUser.objects.annotate(post_count=Count('username')):
    #     print(user,user.post_count)
    #     print(user[0].post_count)
    #     print(user[1].post_count)
    # print(user[2].post_count)
    # print(projects.created_by)

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
    #     print(num_post)
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
    return render(request, "project/facility_projects.html", context)


@login_required(login_url='login')
def department_project(request, pk):
    projects = QI_Projects.objects.filter(department=pk)
    # print(projects)
    # print(projects[1])
    facility_name = pk
    # for user in NewUser.objects.annotate(post_count=Count('username')):
    #     print(user,user.post_count)
    #     print(user[0].post_count)
    #     print(user[1].post_count)
    # print(user[2].post_count)
    # print(projects.created_by)

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
    #     print(num_post)
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
    return render(request, "project/department_projects.html", context)


@login_required(login_url='login')
def qi_creator(request, pk):
    print(pk)
    projects = QI_Projects.objects.filter(created_by__username=pk)
    print(projects)
    # print(projects[1])
    facility_name = pk
    # for user in NewUser.objects.annotate(post_count=Count('username')):
    #     print(user,user.post_count)
    #     print(user[0].post_count)
    #     print(user[1].post_count)
    # print(user[2].post_count)
    # print(projects.created_by)

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
    #     print(num_post)
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
        "form": form
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
    print(team)
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
    return render(request, "project/comments.html")


@login_required(login_url='login')
def resources(request):
    return render(request, "project/resources.html")


def line_chart(df, x_axis, y_axis, title):
    fig = px.line(df, x=x_axis, y=y_axis, text=y_axis,
                  title=title, hover_name=x_axis, hover_data={
            "tested of change": True,
            "achievements": True, })
    fig.update_traces(textposition='top center')
    # fig.add_trace(go.Line(x=df[x_axis], y=df[y_axis], mode='markers'))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)
    fig.add_hline(y=90, line_width=1, line_dash="dash", line_color="green")
    fig.add_hline(y=75, line_width=1, line_dash="dash", line_color="red")
    fig.update_layout({
        'plot_bgcolor': 'rgba(0, 0, 0, 0)',
        'paper_bgcolor': 'rgba(0, 0, 0, 0)',
    })
    # fig.update_traces(texttemplate='%{text:.s}')

    return fig.to_html()


def bar_chart(df, x_axis, y_axis, title):
    fig = px.bar(df, x=x_axis, y=y_axis, text=y_axis,
                 title=title,
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


def prepare_trends(df):
    df['achievements'] = df['achievements'].astype(int)
    df = df.sort_values("month_year")
    df['month_year'] = df['month_year'].astype(str) + "."
    project_performance = line_chart(df, "month_year", "achievements", "Project performance")
    return project_performance


@login_required(login_url='login')
def single_project(request, pk):
    facility_project = QI_Projects.objects.get(id=pk)
    # get other facility projects
    other_projects = QI_Projects.objects.filter(facility=facility_project.facility)
    # Hit db once
    test_of_change_qs = TestedChange.objects.all()

    other_facility_projects_lst = []
    for proj in other_projects:
        # use manager
        changes_others = test_of_change_qs.filter(project_id=proj.id).order_by('-month_year')
        try:
            changes_others = [
                {'month_year': x.month_year,
                 'tested of change': x.tested_change,
                 'achievements': x.achievements,
                 'facility': x.project,
                 'project': x.project.project_title,
                 } for x in changes_others
            ]
            # print("changes_others...")
            # print(changes_others)
            # convert data from database to a dataframe
            df_changes_others = pd.DataFrame(changes_others)
            # print(df_changes_others)

            other_facility_projects_lst.append(prepare_trends(df_changes_others))
        except:
            changes_others = [
                {'month_year': 0,
                 'tested of change': 0,
                 'achievements': 0,
                 }
            ]
            other_facility_projects_lst.append(changes_others[0])

    pro_perfomance_ = dict(zip(["pro_perfomance_" + str(count) for count, i in enumerate(other_facility_projects_lst)],
                               other_facility_projects_lst))
    # print(list(pro_perfomance_.values())[-3])
    # print(list(pro_perfomance_.values())[0])

    # print(proj)
    # assign it to a dataframe using list comprehension
    other_projects = [
        {'department(s)': x.department,
         'project category': x.project_category,
         'id': x.id,
         } for x in other_projects
    ]
    # convert data from database to a dataframe
    df_other_projects = pd.DataFrame(other_projects)
    df_other_projects['total projects'] = 1
    # print(df_other_projects)

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
        # print("pro_perfomance_....")
        # print(pro_perfomance_)
        df_other_projects = df_other_projects.groupby('department(s)').sum()['total projects']
        df_other_projects = df_other_projects.reset_index().sort_values('total projects', ascending=False)

        project_performance = prepare_trends(df)

        facility_proj_performance = bar_chart(df_other_projects, "department(s)", "total projects", "facility projects")
        context = {"facility_project": facility_project, "test_of_change": changes,
                   "project_performance": project_performance, "facility_proj_performance": facility_proj_performance,
                   "pro_perfomance_": pro_perfomance_}
    else:
        context = {"facility_project": facility_project, "test_of_change": changes, "pro_perfomance_": pro_perfomance_}
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
