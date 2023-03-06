from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect

# Create your views here.
from apps.account.forms import CustomUserForm, UpdateUserForm


# from user.forms import CreateUserForm

@login_required(login_url='login')
def register(request):
    form = CustomUserForm()
    # form = CreateUserForm()
    if request.method == "POST":
        form = CustomUserForm(request.POST)
        # form = CreateUserForm(request.POST)
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
    # form = CustomUserForm()
    # form = UserCreationForm()
    if request.method == "POST":
        form = UpdateUserForm(request.POST,instance=request.user)
        # form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            user = form.cleaned_data.get("username")
            messages.success(request, f"Account was successfully update")
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = UpdateUserForm(instance=request.user)

    return render(request, "project/add_milestones.html", {"form": form,"profile":"profile"})


def login_page(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:

            login(request, user)
            redirect("facilities_landing_page", project_type="facility")

    return render(request, "account/login_page.html", {})


def logout_page(request):
    logout(request)
    return redirect("login")

