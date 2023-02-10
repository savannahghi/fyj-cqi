from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect

# Create your views here.
from dqa.form import DataVerificationForm, PeriodForm, QuarterSelectionForm, YearSelectionForm, FacilitySelectionForm
from dqa.models import DataVerification
from project.models import Facilities


def add_period(request):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    if request.method == 'POST':
        period_form = PeriodForm(request.POST)
        if period_form.is_valid():
            period_form.save()
            return HttpResponseRedirect(request.session['page_from'])
    else:
        period_form = PeriodForm()
    context = {
        "period_form": period_form,
    }
    return render(request, 'dqa/add_period.html', context)


def add_data_verification(request):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')


    if request.method == 'POST':
        form = DataVerificationForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.created_by = request.user
            post.save()
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = DataVerificationForm()
    quarters = {
        # "Qtr1":['Oct',' Nov','Dec','Total'],
        # "Qtr2": ['Jan', 'Feb', 'Mar', 'Total'],
        "Qtr3": ['Apr', 'May', 'Jun'],
        # "Qtr4":['Jul','Aug','Sep','Total'],

    }
    form = list(form)
    context = {
        "form": form,
        "quarters": quarters
    }
    return render(request, 'dqa/add_data_verification.html', context)


def show_data_verification(request):
    form = QuarterSelectionForm(request.POST or None)
    year_form = YearSelectionForm(request.POST or None)
    facility_form = FacilitySelectionForm(request.POST or None)

    selected_quarter = "Qtr1"
    selected_year = "2021"
    year_suffix = "21"
    selected_facility=None

    if form.is_valid() and year_form.is_valid() and facility_form.is_valid():
        selected_quarter = form.cleaned_data['quarter']
        selected_year = year_form.cleaned_data['year']
        selected_facility = facility_form.cleaned_data['facilities']
        year_suffix = selected_year[-2:]
        quarters = {
            selected_quarter: [
                f'Oct-{year_suffix}', f'Nov-{year_suffix}', f'Dec-{year_suffix}', 'Total'
            ] if selected_quarter == 'Qtr1' else [
                f'Jan-{year_suffix}', f'Feb-{year_suffix}', f'Mar-{year_suffix}', 'Total'
            ] if selected_quarter == 'Qtr2' else [
                f'Apr-{year_suffix}', f'May-{year_suffix}', f'Jun-{year_suffix}', 'Total'
            ] if selected_quarter == 'Qtr3' else [
                f'Jul-{year_suffix}', f'Aug-{year_suffix}', f'Sep-{year_suffix}', 'Total'
            ]
        }
    else:
        quarters = {}
    data_verification = DataVerification.objects.filter(quarter_year__quarter=selected_quarter,
                                                        quarter_year__year=selected_year,
                                                        facility_name=selected_facility,
                                                        )

    if not data_verification:
        messages.error(request, f"No DQA data found for {selected_facility} {selected_quarter}-FY{year_suffix}. "
                                f"Please add data for the facility.")
        # return redirect('show_data_verification', pk=pk)

    print(quarters)
    context = {
        'form': form,
        "year_form":year_form,
        "facility_form":facility_form,
        "quarters": quarters,
        "selected_year":year_suffix,
        'data_verification': data_verification
    }
    return render(request, 'dqa/show data verification.html', context)


@login_required(login_url='login')
def update_data_verification(request, pk):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
    item = DataVerification.objects.get(id=pk)
    if request.method == "POST":
        form = DataVerificationForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(request.session['page_from'])
    else:
        form = DataVerificationForm(instance=item)
    context = {
        "form": form,
        "title": "Update DQA data",
    }
    return render(request, 'dqa/add_data_verification.html', context)


@login_required(login_url='login')
def delete_data_verification(request, pk):
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')

    item = DataVerification.objects.get(id=pk)
    if request.method == "POST":
        item.delete()

        return HttpResponseRedirect(request.session['page_from'])
    context = {
        "test_of_changes": item
    }
    return render(request, 'project/delete_test_of_change.html', context)