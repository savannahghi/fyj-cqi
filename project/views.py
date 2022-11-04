from django.shortcuts import render


# Create your views here.

def dashboard(request):
    return render(request, "project/dashboard.html")


def deep_dive_facilities(request):
    return render(request, "project/deep_dive_facilities.html")


def deep_dive_chmt(request):
    return render(request, "project/deep_dive_chmt.html")
    # return render(request, "project/calendar.html")


def qi_team_members(request):
    return render(request, "project/qi_team_members.html")


def qi_managers(request):
    return render(request, "project/qi_managers.html")


def archived(request):
    return render(request, "project/archived.html")


def audit_trail(request):
    return render(request, "project/audit_trail.html")


def comments(request):
    return render(request, "project/comments.html")


def resources(request):
    return render(request, "project/resources.html")

def single_project(request):
    return render(request, "project/individual_qi_project.html")
