from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.sessions.models import Session
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.utils import timezone

# Create your views here.
from apps.account.forms import CustomUserForm, UpdateUserForm


@login_required(login_url='login')
def register(request):
    form = CustomUserForm()
    if request.method == "POST":
        form = CustomUserForm(request.POST)
        if form.is_valid():
            form.save()
            user = form.cleaned_data.get("username")
            email = form.cleaned_data.get("email")
            password = form.cleaned_data.get("password2")
            messages.success(request, f"Account was created for {user} Successfully. Your email is {email} and "
                                      f"password is {password}")
            return redirect("login")

    return render(request, "account/registration.html", {"form": form})


@login_required(login_url='login')
def update_profile(request):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    if request.method == "POST":
        form = UpdateUserForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f"Your profile details were successfully updated")
            return HttpResponseRedirect(request.session['page_from'])
        else:
            messages.error(request, "There was an error updating your profile. Please check the form and try again.")
    else:
        form = UpdateUserForm(instance=request.user)
        messages.error(request, "Please complete your profile information to continue. Note that if you change "
                                "your username, you will use the new username for your next login.")

    return render(request, "project/add_milestones.html", {"form": form, "profile": "profile"})


# def login_page(request):
#     if request.method == "POST":
#         username = request.POST.get("username")
#         password = request.POST.get("password")
#         user = authenticate(request, username=username, password=password)
#         if user is not None:
#             login(request, user)
#             return redirect("facilities_landing_page", project_type="facility")
#
#     return render(request, "account/login_page.html", {})

def login_page(request):
    if request.method == "POST":
        username = request.POST.get("username").strip()
        password = request.POST.get("password").strip()
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Check for specific permissions and redirect accordingly
            # ################################
            # # Redirect CQI facility staffs #
            # ################################
            # if user.groups.filter(name='facility_staffs_cqi').exists():
            #     print("Triggered facilities_landing_page:::::::::::::::::::::::::::::::::::::::::::::::")
            #     return redirect("facilities_landing_page", project_type="facility")
            ##############################
            # Redirect labpulse Laboratory staffs #
            ##############################
            if user.groups.filter(name='laboratory_staffs_labpulse').exists():
                return redirect("choose_testing_lab")
            ##########################################################################################
            # Redirect labpulse facility, Program and Sub-county staffs, Referring Laboratory Staffs #
            ##########################################################################################
            elif user.groups.filter(name__in=['laboratory_staffs_labpulse',
                                              'facility_staffs_labpulse',
                                              'referring_laboratory_staffs_labpulse']).exists():
                return redirect("show_results")
            ##############################
            # Redirect UNITID lab staffs #
            ##############################
            elif user.groups.filter(name='unitid_staffs_labpulse').exists():
                return redirect("load_biochemistry_results")
            ##############################
            # Redirect Repo viewer       #
            ##############################
            elif user.groups.filter(name='repository_readers').exists():
                return redirect("manuscript_list")
            elif user.groups.filter(name='subcounty_staffs_labpulse').exists():
                return redirect("facilities_landing_page", project_type="facility")
            else:
                # Redirect to CQI app
                return redirect("facilities_landing_page", project_type="facility")
    return render(request, "account/login_page.html", {})

# Identify and delete sessions that are expired
def delete_expired_sessions():
    # Get the current time
    now = timezone.now()

    # Identify expired sessions
    expired_sessions = Session.objects.filter(expire_date__lt=now)

    # Delete expired sessions
    expired_sessions.delete()

def logout_page(request):
    # Clear the session
    request.session.clear()

    # Call the function to delete expired sessions
    delete_expired_sessions()

    logout(request)
    return redirect("login")
