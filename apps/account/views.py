from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect

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
        username = request.POST.get("username")
        password = request.POST.get("password")
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
            elif user.groups.filter(name__in=['subcounty_staffs_labpulse','laboratory_staffs_labpulse',
                                              'facility_staffs_labpulse',
                                              'referring_laboratory_staffs_labpulse']).exists():
                return redirect("show_results")
            else:
                # Redirect to CQI app
                return redirect("facilities_landing_page", project_type="facility")
    return render(request, "account/login_page.html", {})


def logout_page(request):
    logout(request)
    return redirect("login")
