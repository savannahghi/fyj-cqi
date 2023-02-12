import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect

# Create your views here.


from dqa.form import DataVerificationForm, PeriodForm, QuarterSelectionForm, YearSelectionForm, FacilitySelectionForm
from dqa.models import DataVerification, Period, Indicators, FyjPerformance
from project.models import Facilities


def load_data(request):
    if request.method == 'POST':
        file = request.FILES['file']
        # Read the data from the excel file into a pandas DataFrame
        keyword = "perf"
        xls_file = pd.ExcelFile(file)
        sheet_names = [sheet for sheet in xls_file.sheet_names if keyword.upper() in sheet.upper()]
        if sheet_names:
            dfs = pd.read_excel(file, sheet_name=sheet_names)
            df = pd.concat([df.assign(sheet_name=name) for name, df in dfs.items()])
            df = df[list(df.columns[:35])]
            # except:
            #     df = pd.read_excel(file)
            # except:
            #     df = pd.read_csv(file)

            if len(df.columns) == 35:
                df.fillna(0, inplace=True)
                process_cols = [col for col in df.columns if col not in [df.columns[1], df.columns[2]]]
                for col in process_cols:
                    df[col] = df[col].astype(int)
                df[df.columns[1]] = df[df.columns[1]].astype(str)
                df[df.columns[2]] = df[df.columns[2]].astype(str)

                # Iterate over each row in the DataFrame
                for index, row in df.iterrows():
                    performance = FyjPerformance()
                    performance.mfl_code = row[df.columns[0]]
                    performance.facility = row[df.columns[1]]
                    performance.month = row[df.columns[2]]
                    performance.tst_p = row[df.columns[3]]
                    performance.tst_a = row[df.columns[4]]
                    performance.tst_t = row[df.columns[5]]
                    performance.tst_pos_p = row[df.columns[6]]
                    performance.tst_pos_a = row[df.columns[7]]
                    performance.tst_pos_t = row[df.columns[8]]
                    performance.tx_new_p = row[df.columns[9]]
                    performance.tx_new_a = row[df.columns[10]]
                    performance.tx_new_t = row[df.columns[11]]
                    performance.tx_curr_p = row[df.columns[12]]
                    performance.tx_curr_a = row[df.columns[13]]
                    performance.tx_curr_t = row[df.columns[14]]
                    performance.pmtct_stat_d = row[df.columns[15]]
                    performance.pmtct_stat_n = row[df.columns[16]]
                    performance.pmtct_pos = row[df.columns[17]]
                    performance.pmtct_arv = row[df.columns[18]]
                    performance.pmtct_inf_arv = row[df.columns[19]]
                    performance.pmtct_eid = row[df.columns[20]]
                    performance.hei_pos = row[df.columns[21]]
                    performance.hei_pos_art = row[df.columns[22]]
                    performance.prep_new = row[df.columns[23]]
                    performance.gbv_sexual = row[df.columns[24]]
                    performance.gbv_emotional_physical = row[df.columns[25]]
                    performance.kp_anc = row[df.columns[26]]
                    performance.new_pos_anc = row[df.columns[27]]
                    performance.on_haart_anc = row[df.columns[28]]
                    performance.new_on_haart_anc = row[df.columns[29]]
                    performance.pos_l_d = row[df.columns[30]]
                    performance.pos_pnc = row[df.columns[31]]
                    performance.cx_ca = row[df.columns[32]]
                    performance.tb_stat_d = row[df.columns[33]]
                    performance.ipt = row[df.columns[34]]
                    performance.save()
                messages.error(request, f'Data successfully saved in the database!')
                return redirect('show_data_verification')
            else:
                # Notify the user that the data is incorrect
                messages.error(request, f'Kindly confirm if {file} has all data columns.The file has'
                                        f'{len(df.columns)} columns')
                print(df.columns)
                redirect('load_data')
        else:
            # Notify the user that the data already exists
            messages.error(request, f"Uploaded file does not have a sheet name performance.")
            redirect('load_data')

        # return redirect('show_data_verification')
    return render(request, 'dqa/upload.html')


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

    quarter_form = QuarterSelectionForm(request.POST or None)
    year_form = YearSelectionForm(request.POST or None)
    form = DataVerificationForm()

    selected_quarter = "Qtr1"
    selected_year = "2021"
    year_suffix = selected_year[-2:]

    if quarter_form.is_valid() and year_form.is_valid():
        selected_quarter = quarter_form.cleaned_data['quarter']
        request.session['selected_quarter'] = selected_quarter

        selected_year = year_form.cleaned_data['year']
        request.session['selected_year'] = selected_year
        year_suffix = selected_year[-2:]
        quarters = {
            selected_quarter: [
                f'Oct-{year_suffix}', f'Nov-{year_suffix}', f'Dec-{year_suffix}'
            ] if selected_quarter == 'Qtr1' else [
                f'Jan-{year_suffix}', f'Feb-{year_suffix}', f'Mar-{year_suffix}'
            ] if selected_quarter == 'Qtr2' else [
                f'Apr-{year_suffix}', f'May-{year_suffix}', f'Jun-{year_suffix}'
            ] if selected_quarter == 'Qtr3' else [
                f'Jul-{year_suffix}', f'Aug-{year_suffix}', f'Sep-{year_suffix}'
            ]
        }
    else:
        quarters = {
            "Qtr2": [f'January-{year_suffix}', f'Feb-{year_suffix}', f'Mar-{year_suffix}']
        }

    # if request.method == "POST":

    # Check if the request method is POST and the submit_data button was pressed
    if 'submit_data' in request.POST:
        # Create an instance of the DataVerificationForm with the submitted data
        form = DataVerificationForm(request.POST)

        # Check if the form data is valid
        if form.is_valid():
            # Get the selected indicator and facility name from the form data
            selected_indicator = form.cleaned_data['indicator']
            # print("selected_indicator:::::::::::::::::::::::::::::::")
            # print(selected_indicator)
            selected_facility = form.cleaned_data['facility_name']

            # Try to save the form data
            try:
                # Get the instance of the form data but don't commit it yet
                post = form.save(commit=False)

                # Set the user who created the data
                post.created_by = request.user

                # Get or create the period instance
                period, created = Period.objects.get_or_create(quarter=request.session['selected_quarter'],
                                                               year=request.session['selected_year'])

                # Set the quarter_year field of the form data
                post.quarter_year = period

                # Save the form data
                post.save()
                # Get the saved data for the selected quarter, year, and facility name
                data_verification = DataVerification.objects.filter(
                                                            quarter_year__quarter=request.session['selected_quarter'],
                                                            quarter_year__year=request.session['selected_year'],
                                                            facility_name=selected_facility,
                                                            )
                if data_verification:
                    # Check if the 'Number tested Positive aged 15+ years' and 'Number tested Positive aged <15
                    # years' are saved in the database
                    positive_15_plus = data_verification.filter(indicator='Number tested Positive aged 15+ years')
                    positive_less_15 = data_verification.filter(indicator='Number tested Positive aged <15 years')

                    # If both values are saved in the database, calculate the sum
                    if positive_15_plus and positive_less_15:

                        field_1 = 0
                        field_2 = 0
                        field_3 = 0
                        total_source = 0
                        field_5 = 0
                        field_6 = 0
                        field_7 = 0
                        total_731moh = 0
                        field_9 = 0
                        field_10 = 0
                        field_11 = 0
                        total_khis = 0

                        #  returns a new queryset containing all the elements from both querysets.
                        combined_queryset = positive_less_15 | positive_15_plus

                        for data in combined_queryset:
                            field_1 += int(data.field_1)
                            field_2 += int(data.field_2)
                            field_3 += int(data.field_3)
                            total_source += int(data.total_source)
                            field_5 += int(data.field_5)
                            field_6 += int(data.field_6)
                            field_7 += int(data.field_7)
                            total_731moh += int(data.total_731moh)
                            field_9 += int(data.field_9)
                            field_10 += int(data.field_10)
                            field_11 += int(data.field_11)
                            total_khis += int(data.total_khis)

                        try:
                            DataVerification.objects.create(indicator='Number tested Positive _Total',
                                                        field_1=field_1,
                                                        field_2=field_2,
                                                        field_3=field_3,
                                                        total_source=total_source,
                                                        field_5=field_5,
                                                        field_6=field_6,
                                                        field_7=field_7,
                                                        total_731moh=total_731moh,
                                                        field_9=field_9,
                                                        field_10=field_10,
                                                        field_11=field_11,
                                                        total_khis=total_khis,
                                                        created_by=request.user,
                                                        quarter_year=period,
                                                        facility_name=selected_facility)
                        except IntegrityError:
                            # handle the scenario where a duplicate instance is trying to be created
                            # for example, return an error message to the user
                            pass

                    # Check if the 'Number tested Positive aged 15+ years' and 'Number tested Positive aged <15
                    # years' are saved in the database
                    infant_anc = data_verification.filter(indicator='Infant ARV Prophyl_ANC')
                    infant_ld = data_verification.filter(indicator='Infant ARV Prophyl_L&D')
                    infant_pnc = data_verification.filter(indicator='Infant ARV Prophyl_PNC<= 6 weeks')

                    # # If both values are saved in the database, calculate the sum
                    if infant_anc and infant_ld and infant_pnc:

                        field_1 = 0
                        field_2 = 0
                        field_3 = 0
                        total_source = 0
                        field_5 = 0
                        field_6 = 0
                        field_7 = 0
                        total_731moh = 0
                        field_9 = 0
                        field_10 = 0
                        field_11 = 0
                        total_khis = 0
                        #  returns a new queryset containing all the elements from both querysets.
                        combined_queryset = infant_anc | infant_ld | infant_pnc

                        for data in combined_queryset:
                            field_1 += int(data.field_1)
                            field_2 += int(data.field_2)
                            field_3 += int(data.field_3)
                            total_source += int(data.total_source)
                            field_5 += int(data.field_5)
                            field_6 += int(data.field_6)
                            field_7 += int(data.field_7)
                            total_731moh += int(data.total_731moh)
                            field_9 += int(data.field_9)
                            field_10 += int(data.field_10)
                            field_11 += int(data.field_11)
                            total_khis += int(data.total_khis)

                        try:
                            DataVerification.objects.create(indicator='Total Infant prophylaxis',
                                                            field_1=field_1,
                                                            field_2=field_2,
                                                            field_3=field_3,
                                                            total_source=total_source,
                                                            field_5=field_5,
                                                            field_6=field_6,
                                                            field_7=field_7,
                                                            total_731moh=total_731moh,
                                                            field_9=field_9,
                                                            field_10=field_10,
                                                            field_11=field_11,
                                                            total_khis=total_khis,
                                                            created_by=request.user,
                                                            quarter_year=period,
                                                            facility_name=selected_facility)
                        except IntegrityError:
                            # handle the scenario where a duplicate instance is trying to be created
                            # for example, return an error message to the user
                            pass

                    # Check if the 'Number tested Positive aged 15+ years' and 'Number tested Positive aged <15
                    # years' are saved in the database
                    kp_anc = data_verification.filter(indicator='On HAART at 1st ANC')
                    new_art_anc = data_verification.filter(indicator='Start HAART ANC')
                    new_art_ld = data_verification.filter(indicator='Start HAART_L&D')
                    new_art_pnc = data_verification.filter(indicator='Start HAART_PNC<= 6 weeks')

                    # # If both values are saved in the database, calculate the sum
                    if kp_anc and new_art_anc and new_art_ld and new_art_pnc:

                        field_1 = 0
                        field_2 = 0
                        field_3 = 0
                        total_source = 0
                        field_5 = 0
                        field_6 = 0
                        field_7 = 0
                        total_731moh = 0
                        field_9 = 0
                        field_10 = 0
                        field_11 = 0
                        total_khis = 0

                        #  returns a new queryset containing all the elements from both querysets.
                        combined_queryset = kp_anc | new_art_anc | new_art_ld | new_art_pnc

                        for data in combined_queryset:
                            field_1 += int(data.field_1)
                            field_2 += int(data.field_2)
                            field_3 += int(data.field_3)
                            total_source += int(data.total_source)
                            field_5 += int(data.field_5)
                            field_6 += int(data.field_6)
                            field_7 += int(data.field_7)
                            total_731moh += int(data.total_731moh)
                            field_9 += int(data.field_9)
                            field_10 += int(data.field_10)
                            field_11 += int(data.field_11)
                            total_khis += int(data.total_khis)
                        try:
                            DataVerification.objects.create(indicator='Maternal HAART Total ',
                                                            field_1=field_1,
                                                            field_2=field_2,
                                                            field_3=field_3,
                                                            total_source=total_source,
                                                            field_5=field_5,
                                                            field_6=field_6,
                                                            field_7=field_7,
                                                            total_731moh=total_731moh,
                                                            field_9=field_9,
                                                            field_10=field_10,
                                                            field_11=field_11,
                                                            total_khis=total_khis,
                                                            created_by=request.user,
                                                            quarter_year=period,
                                                            facility_name=selected_facility)
                        except IntegrityError:
                            # handle the scenario where a duplicate instance is trying to be created
                            # for example, return an error message to the user
                            pass

                    # Check if the 'Number tested Positive aged 15+ years' and 'Number tested Positive aged <15
                    # years' are saved in the database
                    tx_new_less_15 = data_verification.filter(
                                                            indicator='Under 15yrs Starting on ART')
                    tx_new_above_15 = data_verification.filter(
                                                                indicator='Above 15yrs Starting on ART ')

                    # If both values are saved in the database, calculate the sum
                    if tx_new_above_15 and tx_new_less_15:

                        field_1 = 0
                        field_2 = 0
                        field_3 = 0
                        total_source = 0
                        field_5 = 0
                        field_6 = 0
                        field_7 = 0
                        total_731moh = 0
                        field_9 = 0
                        field_10 = 0
                        field_11 = 0
                        total_khis = 0

                        #  returns a new queryset containing all the elements from both querysets.
                        combined_queryset = tx_new_less_15 | tx_new_above_15

                        for data in combined_queryset:
                            field_1 += int(data.field_1)
                            field_2 += int(data.field_2)
                            field_3 += int(data.field_3)
                            total_source += int(data.total_source)
                            field_5 += int(data.field_5)
                            field_6 += int(data.field_6)
                            field_7 += int(data.field_7)
                            total_731moh += int(data.total_731moh)
                            field_9 += int(data.field_9)
                            field_10 += int(data.field_10)
                            field_11 += int(data.field_11)
                            total_khis += int(data.total_khis)

                        try:
                            DataVerification.objects.create(indicator='Number of adults and children starting ART',
                                                            field_1=field_1,
                                                            field_2=field_2,
                                                            field_3=field_3,
                                                            total_source=total_source,
                                                            field_5=field_5,
                                                            field_6=field_6,
                                                            field_7=field_7,
                                                            total_731moh=total_731moh,
                                                            field_9=field_9,
                                                            field_10=field_10,
                                                            field_11=field_11,
                                                            total_khis=total_khis,
                                                            created_by=request.user,
                                                            quarter_year=period,
                                                            facility_name=selected_facility)
                        except IntegrityError:
                            # handle the scenario where a duplicate instance is trying to be created
                            # for example, return an error message to the user
                            pass

                    # Check if the 'Number tested Positive aged 15+ years' and 'Number tested Positive aged <15
                    # years' are saved in the database
                    tx_curr_less_15 = data_verification.filter(
                        indicator='Currently on ART <15Years')
                    tx_curr_above_15 = data_verification.filter(
                        indicator='Currently on ART 15+ years')

                    # If both values are saved in the database, calculate the sum
                    if tx_curr_above_15 and tx_curr_less_15:

                        field_1 = 0
                        field_2 = 0
                        field_3 = 0
                        total_source = 0
                        field_5 = 0
                        field_6 = 0
                        field_7 = 0
                        total_731moh = 0
                        field_9 = 0
                        field_10 = 0
                        field_11 = 0
                        total_khis = 0

                        #  returns a new queryset containing all the elements from both querysets.
                        combined_queryset = tx_curr_less_15 | tx_curr_above_15

                        for data in combined_queryset:
                            field_1 += int(data.field_1)
                            field_2 += int(data.field_2)
                            field_3 += int(data.field_3)
                            total_source += int(data.total_source)
                            field_5 += int(data.field_5)
                            field_6 += int(data.field_6)
                            field_7 += int(data.field_7)
                            total_731moh += int(data.total_731moh)
                            field_9 += int(data.field_9)
                            field_10 += int(data.field_10)
                            field_11 += int(data.field_11)
                            total_khis += int(data.total_khis)

                        try:
                            DataVerification.objects.create(
                                indicator='Number of adults and children Currently on ART',
                                field_1=field_1,
                                field_2=field_2,
                                field_3=field_3,
                                total_source=total_source,
                                field_5=field_5,
                                field_6=field_6,
                                field_7=field_7,
                                total_731moh=total_731moh,
                                field_9=field_9,
                                field_10=field_10,
                                field_11=field_11,
                                total_khis=total_khis,
                                created_by=request.user,
                                quarter_year=period,
                                facility_name=selected_facility)
                        except IntegrityError:
                            # handle the scenario where a duplicate instance is trying to be created
                            # for example, return an error message to the user
                            pass

                # Redirect the user to the show_data_verification view
                return redirect("show_data_verification")

            # Handle the IntegrityError exception
            except IntegrityError as e:
                # Notify the user that the data already exists
                messages.error(request, f'Data for {selected_facility}, {request.session["selected_quarter"]}, '
                                        f'{selected_indicator} '
                                        f'already exists.')
        # If the form data is not valid
        else:
            # Create a new instance of the DataVerificationForm with the invalid data
            form = DataVerificationForm(request.POST)
    # If the request method is not POST or the submit_data button was not pressed
    else:
        # Create an empty instance of the DataVerificationForm
        form = DataVerificationForm()

    # convert a form into a list to allow slicing
    form = list(form)
    # Create the context for the template
    context = {
        "form": form,
        "quarters": quarters,
        "quarter_form": quarter_form,
        "year_form": year_form,
        "year_suffix": year_suffix
    }

    # Render the template with the context
    return render(request, 'dqa/add_data_verification.html', context)


# def add_data_verification(request):
#     if request.method == "GET":
#         request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
#
#     if request.method == 'POST':
#         form = DataVerificationForm(request.POST)
#         if form.is_valid():
#             post = form.save(commit=False)
#             post.created_by = request.user
#             post.save()
#             return HttpResponseRedirect(request.session['page_from'])
#     else:
#         form = DataVerificationForm()
#     quarters = {
#         # "Qtr1":['Oct',' Nov','Dec','Total'],
#         # "Qtr2": ['Jan', 'Feb', 'Mar', 'Total'],
#         "Qtr3": ['Apr', 'May', 'Jun'],
#         # "Qtr4":['Jul','Aug','Sep','Total'],
#
#     }
#     form = list(form)
#     context = {
#         "form": form,
#         "quarters": quarters
#     }
#     return render(request, 'dqa/add_data_verification.html', context)


def show_data_verification(request):
    form = QuarterSelectionForm(request.POST or None)
    year_form = YearSelectionForm(request.POST or None)
    facility_form = FacilitySelectionForm(request.POST or None)

    selected_quarter = "Qtr1"
    selected_year = "2021"
    year_suffix = "21"
    selected_facility = None

    if form.is_valid() and year_form.is_valid() and facility_form.is_valid():
        selected_quarter = form.cleaned_data['quarter']
        selected_year = year_form.cleaned_data['year']
        selected_facility = facility_form.cleaned_data['facilities']
        print("selected_facility.mfl_code:::::::::::::::")
        print(selected_facility.mfl_code)
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

    quarter_year = f"{selected_quarter}-{year_suffix}"
    print(selected_quarter)
    print(selected_year)
    print(selected_facility)
    data_verification = DataVerification.objects.filter(quarter_year__quarter=selected_quarter,
                                                        quarter_year__year=selected_year,
                                                        facility_name=selected_facility,
                                                        )
    # Get the Indicator choices in the order specified in the list
    indicator_choices = [choice[0] for choice in Indicators.INDICATOR_CHOICES]
    available_indicators = [i.indicator for i in data_verification]

    prevention = ['PrEP_New', 'Starting_TPT', 'GBV_Sexual violence', 'GBV_Emotional and /Physical Violence',
                  'Cervical Cancer Screening (Women on ART)']
    hts = ['Total tested ', 'Number tested Positive aged <15 years', 'Number tested Positive aged 15+ years',
           'Number tested Positive _Total']
    pmtct = ['Known Positive at 1st ANC', 'Positive Results_ANC', 'On HAART at 1st ANC', 'Start HAART ANC',
             'Infant ARV Prophyl_ANC', 'Positive Results_L&D', 'Start HAART_L&D', 'Infant ARV Prophyl_L&D',
             'Positive Results_PNC<=6 weeks', 'Start HAART_PNC<= 6 weeks', 'Infant ARV Prophyl_PNC<= 6 weeks',
             'Total Positive (PMTCT)', 'Maternal HAART Total ', 'Total Infant prophylaxis']
    care_rx = ['Under 15yrs Starting on ART', 'Above 15yrs Starting on ART ',
               'Number of adults and children starting ART', 'New & Relapse TB_Cases', 'Currently on ART <15Years',
               'Currently on ART 15+ years', 'Number of adults and children Currently on ART']

    program_accessed = []
    for indy in available_indicators:
        if indy in prevention:
            if "Prevention" not in program_accessed:
                program_accessed.append("Prevention")
        elif indy in hts:
            if "HTS" not in program_accessed:
                program_accessed.append("HTS")
        elif indy in pmtct:
            if "PMTCT" not in program_accessed:
                program_accessed.append("PMTCT")
        elif indy in care_rx:
            if "CARE & RX" not in program_accessed:
                program_accessed.append("CARE & RX")
    # Sort the data_verification objects based on the order of the indicator choices
    sorted_data_verification = sorted(data_verification, key=lambda x: indicator_choices.index(x.indicator))

    if not data_verification:
        if selected_facility:
            messages.error(request, f"No DQA data found for {selected_facility} {selected_quarter}-FY{year_suffix}. "
                                    f"Please add data for the facility.")

    try:
        fyj_performance = FyjPerformance.objects.filter(mfl_code=selected_facility.mfl_code,
                                                        quarter_year=quarter_year
                                                        )
    except:
        fyj_performance = None
    context = {
        'form': form,
        "year_form": year_form,
        "facility_form": facility_form,
        "quarters": quarters,
        "selected_year": year_suffix,
        'data_verification': sorted_data_verification,
        "program_accessed": program_accessed,
        "fyj_performance": fyj_performance,
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
        quarter_year = item.quarter_year.quarter_year
        print("item::::::::::::::::::::")
        print(quarter_year)
        year_suffix = quarter_year[-2:]
        selected_quarter = quarter_year[:4]
        print(selected_quarter)
        print(year_suffix)
        quarters = {
            selected_quarter: [
                f'Oct-{year_suffix}', f'Nov-{year_suffix}', f'Dec-{year_suffix}'
            ] if selected_quarter == 'Qtr1' else [
                f'Jan-{year_suffix}', f'Feb-{year_suffix}', f'Mar-{year_suffix}'
            ] if selected_quarter == 'Qtr2' else [
                f'Apr-{year_suffix}', f'May-{year_suffix}', f'Jun-{year_suffix}'
            ] if selected_quarter == 'Qtr3' else [
                f'Jul-{year_suffix}', f'Aug-{year_suffix}', f'Sep-{year_suffix}'
            ]
        }
        form = DataVerificationForm(instance=item)
    context = {
        "form": form,
        "title": "Update DQA data",
        "quarters": quarters,
    }
    return render(request, 'dqa/update_data_verification.html', context)


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
