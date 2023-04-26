import datetime
from datetime import date, datetime
import pandas as pd
import plotly.express as px
from plotly.offline import plot
from django.contrib import messages
from django.db import transaction, IntegrityError
from django.http import HttpResponse
from django.shortcuts import render, redirect

# Create your views here.
from django.utils.datastructures import MultiValueDictKeyError

from apps.data_analysis.forms import DateFilterForm, FileUploadForm
from apps.data_analysis.models import FYJHealthFacility


def load_fyj_censused(request):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == 'POST':
        file = request.FILES['file']
        # Read the data from the Excel file into a pandas DataFrame
        keyword = "census"
        xls_file = pd.ExcelFile(file)
        sheet_names = [sheet for sheet in xls_file.sheet_names if
                       keyword.upper() in sheet.upper()]
        if sheet_names:
            dfs = pd.read_excel(file, sheet_name=sheet_names)
            df = pd.concat([df.assign(sheet_name=name) for name, df in dfs.items()])
            try:
                with transaction.atomic():
                    if len(df.columns) <= 18:
                        df.fillna("", inplace=True)
                        # Iterate over each row in the DataFrame
                        for index, row in df.iterrows():
                            defaults = {
                                'county': row['County'],
                                'health_subcounty': row['Health Subcounty'],
                                'subcounty': row['Subcounty'],
                                'ward': row['Ward'],
                                'facility': row['Facility'],
                                'datim_mfl': row['DATIM MFL'],
                                'm_and_e_mentor': row['M&E Mentor/SI associate'],
                                'm_and_e_assistant': row['M&E Assistant'],
                                'care_and_treatment': row['Care & Treatment(Yes/No)'],
                                'hts': row['HTS(Yes/No)'],
                                'vmmc': row['VMMC(Yes/No)'],
                                'key_pop': row['Key Pop(Yes/No)'],
                                'hub': row['Hub(1,2,3 o 4)'],
                                'facility_type': row['Faclity Type'],
                                'category': row['Category (HVF/MVF/LVF)'],
                                'emr': row['EMR']
                            }
                            FYJHealthFacility.objects.update_or_create(mfl_code=row['MFL Code'], defaults=defaults)

                        messages.error(request, f'Data successfully saved in the database!')
                        return redirect(request.path_info)
                    else:
                        # Notify the user that the data is not correct
                        messages.error(request, f'Kindly confirm if {file} has all data columns.The file has'
                                                f'{len(df.columns)} columns')
                        redirect('load_data')
            except IntegrityError:
                facility_list = ', '.join(str(month) for month in df['Facility'].unique())
                error_msg = f"{facility_list.title()} data is already exists. Possible duplicates in the dataset you " \
                            f"are uploading "
                messages.error(request, error_msg)
        else:
            messages.error(request, f"Uploaded file does not have a sheet named 'census'.")
            redirect(request.path_info)
    return render(request, 'data_analysis/load_data.html')


def download_csv(request, name, filename):
    session_items = []
    for key, value in request.session.items():
        session_items.append(key)

    df = request.session[f'{name}']
    df = pd.DataFrame(df)

    response = HttpResponse(df.to_csv(), content_type='text/csv')

    response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'

    return response


def get_key_from_session_names(request):
    # convert dict to a lidt
    data_in_sessions = list(request.session.items())
    keys = []
    values = []
    #
    for count, i in enumerate(data_in_sessions):
        keys.append(data_in_sessions[count][0])
        values.append(data_in_sessions[count][0])
    # make a dictionary from two lists with the same key and value
    dictionary = dict(zip(keys, values))
    return dictionary


def prepare_sc_curr_arvdisp_df(df1, fyj_facility_mfl_code, default_cols):
    # df1 = pd.read_csv(path1)
    # st francis
    df1.loc[df1['organisationunitcode'] == 13202, 'organisationunitcode'] = 17943
    # adventist
    df1.loc[df1['organisationunitcode'] == 23385, 'organisationunitcode'] = 18535
    # illasit
    df1.loc[df1['organisationunitcode'] == 20372, 'organisationunitcode'] = 14567
    # imara
    df1.loc[df1['organisationunitcode'] == 17685, 'organisationunitcode'] = 12981
    df1 = df1[~df1['organisationunitcode'].isnull()]
    df1 = df1[df1['organisationunitcode'].isin(fyj_facility_mfl_code)]

    df1["organisationunitcode"] = df1["organisationunitcode"].astype(int)
    dispensed_cols = [col for col in df1.columns if "Total Quantity issued this month" in col]
    end_of_months_cols = [col for col in df1.columns if "End of Month Physical Stock Count" in col]

    if len(dispensed_cols) > 0:
        # get the last 6 months data
        # divide the period into 2
        first_3_months = sorted(list(df1['periodid'].unique()))[:3]
        last_3_months = sorted(list(df1['periodid'].unique()))[3:]

        ###########################################################
        # UNCOMMENT BELOW TO GET DATA FOR THE FIRST THREE MONTHS  #
        ###########################################################
        #         print(f"FIRST THREE MONTHS: {first_3_months}")
        #         df1=df1[df1['periodid'].isin(first_3_months)]

        ###########################################################
        # UNCOMMENT BELOW TO GET DATA FOR THE LAST THREE MONTHS  #
        ###########################################################

        #         print(f"LAST THREE MONTHS: {last_3_months}")
        #         df1=df1[df1['periodid'].isin(last_3_months)]
        ###################################################################
        # TO GET DATA FOR THE LAST 2 QUARTERS, COMMENT ABOVE TWO FILTERS  #
        ###################################################################

        # display(df1.head(6))
        dispensed_df = df1[default_cols + dispensed_cols]
        # display(dispensed_df.head(2))
        filename = "sc_arvdisp"
    else:
        # get the last month data
        last_month = df1['periodid'].unique().max()
        df1 = df1[df1['periodid'] == last_month]

        dispensed_df = df1[default_cols + end_of_months_cols]
        filename = "sc_curr"
    return dispensed_df, df1, dispensed_cols, end_of_months_cols, filename


def make_dfs(df1, dtg_cols, regimen, default_cols):
    dtg_df = df1[default_cols + dtg_cols].fillna(0)
    dtg_df_original = dtg_df.copy()
    if "periodname" not in default_cols:
        for i in dtg_df.columns[2:]:
            dtg_df[i] = dtg_df[i].astype(int)
    else:
        for i in dtg_df.columns[3:]:
            dtg_df[i] = dtg_df[i].astype(int)

    tld_cols = [col for col in dtg_df.columns if regimen in col]
    tld_df = dtg_df[default_cols + tld_cols].fillna(0)

    non_tld_cols = [col for col in dtg_df.columns if regimen not in col]
    non_tld_in_dtg_df = dtg_df[non_tld_cols].fillna(0)

    return dtg_df, tld_df, non_tld_in_dtg_df


def analyse_pharmacy_data(request, df, df1):
    df['MFL Code'] = df['MFL Code'].astype(int)
    fyj_facility_mfl_code = list(df['MFL Code'].unique())
    default_cols = ['organisationunitname', 'organisationunitcode', "periodname"]
    dispensed_df, df1, dispensed_cols, end_of_months_cols, filename = prepare_sc_curr_arvdisp_df(df1,
                                                                                                 fyj_facility_mfl_code,
                                                                                                 default_cols)
    dtg_cols = [col for col in dispensed_df.columns if "dtg" in col.lower()]
    efv_cols = [col for col in dispensed_df.columns if "efv" in col.lower()]
    lpvr_cols = [col for col in dispensed_df.columns if "lpv/" in col.lower()]
    nvp_cols = [col for col in dispensed_df.columns if "nvp" in col.lower()]
    abc_3tc_cols = [col for col in dispensed_df.columns if "(ABC/3TC) 120" in col]
    ctx_cols = [col for col in dispensed_df.columns if "Cotrimoxazole" in col]
    rifapentine_cols = [col for col in dispensed_df.columns if "Rifapentine" in col]
    dtg_df, tld_df, non_tld_in_dtg_df = make_dfs(df1, dtg_cols, "(TDF/3TC/DTG)", default_cols)
    tld_180s_cols = [col for col in tld_df.columns if "180s" in col]

    if len(dispensed_cols) > 0:
        if len(tld_180s_cols) != 0:
            tld_180s_df = tld_df[default_cols + tld_180s_cols].fillna(0)
        else:
            tld_180s_df = tld_df[default_cols].fillna(0)
            tld_180s_df[
                "MoH 730B Revision 2019 Tenofovir/Lamivudine/Dolutegravir (TDF/3TC/DTG) FDC (300/300/50mg) " \
                "FDC Tablets 180s Total Quantity issued this month"] = 0
    else:
        if len(tld_180s_cols) != 0:
            tld_180s_df = tld_df[default_cols + tld_180s_cols].fillna(0)
        else:
            tld_180s_df = tld_df[default_cols].fillna(0)
            tld_180s_df[
                "MoH 730B Revision 2019 Tenofovir/Lamivudine/Dolutegravir (TDF/3TC/DTG) FDC (300/300/50mg) " \
                "FDC Tablets 180s End of Month Physical Stock Count"] = 0
    if "periodname" in default_cols:
        tld_df = tld_df.merge(tld_180s_df,
                              on=["organisationunitname", "organisationunitcode", "periodname"])
    else:
        tld_df = tld_df.merge(tld_180s_df, on=["organisationunitname", "organisationunitcode"])

    ctx, ctx_df, non_abc_3tc_in_abc_3tc_df = make_dfs(df1, ctx_cols, "Cotrimoxazole", default_cols)

    ctx_df = ctx_df[default_cols + ctx_cols]
    if "periodname" in default_cols:
        tld_df = tld_df.merge(ctx_df, on=["organisationunitname", "organisationunitcode", "periodname"])
    else:
        tld_df = tld_df.merge(ctx_df, on=["organisationunitname", "organisationunitcode"])
    efv_df, tle_df, non_tle_in_efv_df = make_dfs(df1, efv_cols, "(TDF/3TC/EFV)", default_cols)
    if "periodname" in default_cols:
        tld_tle_df = tld_df.merge(tle_df,
                                  on=["organisationunitname", "organisationunitcode", "periodname"])
    else:
        tld_tle_df = tld_df.merge(tle_df, on=["organisationunitname", "organisationunitcode"])

    lpvr_df, kaletra_df, non_kaletra_in_lpv_df = make_dfs(df1, lpvr_cols, "LPV/", default_cols)

    if "periodname" in default_cols:
        tld_tle_lpv_df = tld_tle_df.merge(kaletra_df,
                                          on=["organisationunitname", "organisationunitcode",
                                              "periodname"])
    else:
        tld_tle_lpv_df = tld_tle_df.merge(kaletra_df,
                                          on=["organisationunitname", "organisationunitcode"])

    if "periodname" in default_cols:
        tld_tle_lpv_dtg10_df = tld_tle_lpv_df.merge(non_tld_in_dtg_df,
                                                    on=["organisationunitname", "organisationunitcode",
                                                        "periodname"])
    else:
        tld_tle_lpv_dtg10_df = tld_tle_lpv_df.merge(non_tld_in_dtg_df,
                                                    on=["organisationunitname", "organisationunitcode"])
    abc_3tc_df, abc_3tc__df, non_abc_3tc_in_abc_3tc_df = make_dfs(df1, abc_3tc_cols, "(ABC/3TC) 120",
                                                                  default_cols)
    if "periodname" in default_cols:
        tld_tle_lpv_dtg10_df = tld_tle_lpv_dtg10_df.merge(abc_3tc_df,
                                                          on=["organisationunitname",
                                                              "organisationunitcode",
                                                              "periodname"])
    else:
        tld_tle_lpv_dtg10_df = tld_tle_lpv_dtg10_df.merge(abc_3tc_df,
                                                          on=["organisationunitname",
                                                              "organisationunitcode"])
    nvp_df, nevirapine_df, non_nevirapine_in_nvp_df = make_dfs(df1, nvp_cols, "NVP", default_cols)
    adult_nvp_cols = [col for col in nevirapine_df.columns if 'Adult' in col and "/NVP)" in col]
    adult_nvp200_cols = [col for col in nevirapine_df.columns if 'Adult' in col and "(NVP)" in col]
    paeds_nvp_cols = [col for col in nevirapine_df.columns if
                      '(NVP)' in col and "Paediatric" in col or "Susp" in col]
    paeds_azt3tcnvp_cols = [col for col in nevirapine_df.columns if
                            "/NVP)" in col and "Paediatric" in col]

    paeds_nvp = nevirapine_df[default_cols + paeds_nvp_cols]
    othercolumns = paeds_nvp.columns[2:]
    paeds_nvp['NVP (Pediatric) bottles'] = paeds_nvp[othercolumns].sum(axis=1)

    adult_nvp = nevirapine_df[default_cols + adult_nvp_cols]
    if "periodname" in default_cols:
        nvp_ = adult_nvp.merge(paeds_nvp,
                               on=["organisationunitname", "organisationunitcode", "periodname"])
    else:
        nvp_ = adult_nvp.merge(paeds_nvp, on=["organisationunitname", "organisationunitcode"])
    paeds_azt3tcnvp = nevirapine_df[default_cols + paeds_azt3tcnvp_cols]

    if "periodname" in default_cols:
        nvp_ = nvp_.merge(paeds_azt3tcnvp,
                          on=["organisationunitname", "organisationunitcode", "periodname"])
    else:
        nvp_ = nvp_.merge(paeds_azt3tcnvp, on=["organisationunitname", "organisationunitcode"])
    adult_nvp_200 = nevirapine_df[default_cols + adult_nvp200_cols]

    if "periodname" in default_cols:
        nvp_ = nvp_.merge(adult_nvp_200,
                          on=["organisationunitname", "organisationunitcode", "periodname"])
    else:
        nvp_ = nvp_.merge(adult_nvp_200, on=["organisationunitname", "organisationunitcode"])
    if "periodname" in default_cols:
        tld_tle_lpv_dtg10_nvp_df = tld_tle_lpv_dtg10_df.merge(nvp_, on=["organisationunitname",
                                                                        "organisationunitcode",
                                                                        "periodname"])
    else:
        tld_tle_lpv_dtg10_nvp_df = tld_tle_lpv_dtg10_df.merge(nvp_, on=["organisationunitname",
                                                                        "organisationunitcode"])
    rifapentine_df, rifapentine_df, non_rifapentine_in_rifapentine_df = make_dfs(df1, rifapentine_cols,
                                                                                 "Rifapentine",
                                                                                 default_cols)
    if "periodname" in default_cols:
        tld_tle_lpv_dtg10_nvp_df = tld_tle_lpv_dtg10_nvp_df.merge(rifapentine_df,
                                                                  on=["organisationunitname",
                                                                      "organisationunitcode",
                                                                      "periodname"])
    else:
        tld_tle_lpv_dtg10_nvp_df = tld_tle_lpv_dtg10_nvp_df.merge(rifapentine_df,
                                                                  on=["organisationunitname",
                                                                      "organisationunitcode"])

    # other Adult bottles
    adult_bottles = [col for col in dispensed_df.columns if "adult" in col.lower()]
    paediatric_bottles = [col for col in dispensed_df.columns if "paediatric" in col.lower()]

    set1 = set(paediatric_bottles)
    set2 = set(list(tld_tle_lpv_dtg10_nvp_df.columns))

    missing = list(sorted(set1 - set2))

    other_paeds_bottles_df = dispensed_df[default_cols + missing].fillna(0)

    if "periodname" not in default_cols:
        for i in other_paeds_bottles_df.columns[1:]:
            other_paeds_bottles_df[i] = other_paeds_bottles_df[i].astype(int)
        other_paeds_bottles_df = other_paeds_bottles_df.groupby(
            ["organisationunitname", "organisationunitcode"]).sum(numeric_only=True).reset_index()
    else:
        for i in other_paeds_bottles_df.columns[3:]:
            other_paeds_bottles_df[i] = other_paeds_bottles_df[i].astype(int)
        other_paeds_bottles_df = other_paeds_bottles_df.groupby(
            ["organisationunitname", "organisationunitcode", "periodname"]).sum(
            numeric_only=True).reset_index()
    othercolumns = list(other_paeds_bottles_df.columns[3:])
    othercolumns = [col for col in othercolumns if "(AZT)" not in col]

    other_paeds_bottles_df = other_paeds_bottles_df[default_cols + othercolumns]

    other_paeds_bottles_df['Other (Pediatric) bottles'] = other_paeds_bottles_df[othercolumns].sum(
        axis=1)
    paeds_others_filename = f"{filename}_other_paediatric"
    request.session['paediatric_report'] = other_paeds_bottles_df.to_dict()
    other_paeds_bottles_df_file = other_paeds_bottles_df.copy()

    other_paeds_bottles_df = other_paeds_bottles_df.drop(othercolumns, axis=1)

    set1 = set(adult_bottles)
    set2 = set(list(tld_tle_lpv_dtg10_nvp_df.columns))

    missing = list(sorted(set1 - set2))

    other_adult_df = dispensed_df[default_cols + missing].fillna(0)

    if "periodname" not in default_cols:
        for i in other_adult_df.columns[1:]:
            other_adult_df[i] = other_adult_df[i].astype(int)
        other_adult_df = other_adult_df.groupby(["organisationunitname", "organisationunitcode"]).sum(
            numeric_only=True).reset_index()
        othercolumns = list(other_adult_df.columns[2:])
    else:
        for i in other_adult_df.columns[3:]:
            other_adult_df[i] = other_adult_df[i].astype(int)
        other_adult_df = other_adult_df.groupby(
            ["organisationunitname", "organisationunitcode", "periodname"]).sum(
            numeric_only=True).reset_index()
        othercolumns = list(other_adult_df.columns[3:])

    other_adult_df = other_adult_df[default_cols + othercolumns]
    other_adult_df['Other (Adult) bottles'] = other_adult_df[othercolumns].sum(axis=1)
    adult_others_filename = f"{filename}_other_adult"
    request.session['adult_report'] = other_adult_df.to_dict()
    other_adult_df_file = other_adult_df.copy()

    other_adult_df = other_adult_df.drop(othercolumns, axis=1)

    if "periodname" in default_cols:
        tld_tle_lpv_dtg10_nvp_adultothers_df = tld_tle_lpv_dtg10_nvp_df.merge(other_adult_df,
                                                                              on=[
                                                                                  "organisationunitname",
                                                                                  "organisationunitcode",
                                                                                  "periodname"])
    else:
        tld_tle_lpv_dtg10_nvp_adultothers_df = tld_tle_lpv_dtg10_nvp_df.merge(other_adult_df,
                                                                              on=[
                                                                                  "organisationunitname",
                                                                                  "organisationunitcode"])
    if "periodname" in default_cols:
        tld_tle_lpv_dtg10_nvp_others_df = tld_tle_lpv_dtg10_nvp_adultothers_df.merge(
            other_paeds_bottles_df,
            on=["organisationunitname",
                "organisationunitcode",
                "periodname"])
    else:
        tld_tle_lpv_dtg10_nvp_others_df = tld_tle_lpv_dtg10_nvp_adultothers_df.merge(
            other_paeds_bottles_df,
            on=["organisationunitname",
                "organisationunitcode"])
    if len(dispensed_cols) > 0:
        tld_tle_lpv_dtg10_nvp_others_df = tld_tle_lpv_dtg10_nvp_others_df.rename(columns={
            "MoH 730B Revision 2017 Adult preparations Zidovudine/Lamivudine/Nevirapine (AZT/3TC/NVP) FDC ("
            "300/150/200mg) Tablets 60s Total Quantity issued this month": "AZT/3TC/NVP (Adult) bottles",
            "MoH 730B Revision 2017 Paediatric preparations Zidovudine/Lamivudine/Nevirapine (AZT/3TC/NVP) "
            "FDC (60/30/50mg) Tablets 60s Total Quantity issued this month": "AZT/3TC/NVP (Pediatric) bottles",
            "MoH 730B Revision 2019Dolutegravir(DTG) 10mg Dispersible.Scored 30s Total Quantity issued this "
            "month": "DTG 10",
            "MoH 730B Revision 2017 Adult preparations Dolutegravir(DTG) 50mg tabs 30s Total Quantity issued "
            "this month": "DTG 50",
            "MoH 730B Revision 2019Lopinavir/ritonavir (LPV/r) 40/10mg Caps(Pellets) 120s Total Quantity "
            "issued this month": "LPV/r 40/10",
            "MoH 730B Revision 2017 Paediatric preparations Lopinavir/ritonavir (LPV/r) 100/25mg Tabs 60s "
            "Total Quantity issued this month": "LPV/r 100/25",
            "MoH 730B Revision 2017 Adult preparations Tenofovir/Lamivudine/Efavirenz (TDF/3TC/EFV) FDC ("
            "300/300/400mg) FDC Tablets 30s Total Quantity issued this month": "TL_400 30",
            "MoH 730B Revision 2017 Adult preparations Tenofovir/Lamivudine/Efavirenz (TDF/3TC/EFV) FDC ("
            "300/300/600mg) FDC Tablets 30s Total Quantity issued this month": "TLE_600 30s",
            "MoH 730B Revision 2019Tenofovir/Lamivudine/Efavirenz (TDF/3TC/EFV) FDC (300/300/400mg) FDC "
            "Tablets  90s Total Quantity issued this month": "TLE_400 90s",
            "MoH 730B Revision 2017 Adult preparations Tenofovir/Lamivudine/Dolutegravir (TDF/3TC/DTG) FDC ("
            "300/300/50mg) FDC Tablets 30s Total Quantity issued this month": "TLD 30s",
            "MoH 730B Revision 2019Tenofovir/Lamivudine/Dolutegravir (TDF/3TC/DTG) FDC (300/300/50mg) FDC "
            "Tablets 90s Total Quantity issued this month": "TLD 90s",
            "MoH 730B Revision 2019 Tenofovir/Lamivudine/Dolutegravir (TDF/3TC/DTG) FDC (300/300/50mg) FDC "
            "Tablets 180s Total Quantity issued this month": "TLD 180s",
            "MoH 730B Revision 2019Rifapentine (P) 150mg tab 24s Total Quantity issued this month":
                "Rifapentine 150mg",
            "MoH 730B Revision 2019Rifapentine/Isoniazid  (P) 300mg/300mg tabs 30s Total Quantity issued this "
            "month": "3HP 300/300",
            "MoH 730B Revision 2017 Paediatric preparations Abacavir/Lamivudine (ABC/3TC) 120mg/60mg FDC "
            "Tablets 30s Total Quantity issued this month": "(ABC/3TC) 120mg/60mg",
            "MoH 730B Revision 2017 Adult preparations Nevirapine (NVP) 200mg Tablets 60s Total Quantity "
            "issued this month": "NVP 200",
            "MoH 730B Revision 2017 Medicines for OIs Cotrimoxazole suspension 240mg/5ml  100ml bottle Total "
            "Quantity issued this month": "CTX 240mg/5ml",
            "MoH 730B Revision 2017 Medicines for OIs Cotrimoxazole 960mg Tablets 100s Total Quantity issued "
            "this month": "CTX 960",

        })

    elif len(end_of_months_cols) > 0:
        tld_tle_lpv_dtg10_nvp_others_df = tld_tle_lpv_dtg10_nvp_others_df.rename(columns={
            "MoH 730B Revision 2017 Adult preparations Zidovudine/Lamivudine/Nevirapine (AZT/3TC/NVP) FDC ("
            "300/150/200mg) Tablets 60s End of Month Physical Stock Count": "AZT/3TC/NVP (Adult) bottles",
            "MoH 730B Revision 2017 Paediatric preparations Zidovudine/Lamivudine/Nevirapine (AZT/3TC/NVP) "
            "FDC (60/30/50mg) Tablets 60s End of Month Physical Stock Count": "AZT/3TC/NVP (Pediatric) "
                                                                              "bottles",
            "MoH 730B Revision 2019Dolutegravir(DTG) 10mg Dispersible.Scored 30s End of Month Physical Stock "
            "Count": "DTG 10",
            "MoH 730B Revision 2017 Adult preparations Dolutegravir(DTG) 50mg tabs 30s End of Month Physical "
            "Stock Count": "DTG 50",
            "MoH 730B Revision 2019Lopinavir/ritonavir (LPV/r) 40/10mg Caps(Pellets) 120s End of Month "
            "Physical Stock Count": "LPV/r 40/10",
            "MoH 730B Revision 2017 Paediatric preparations Lopinavir/ritonavir (LPV/r) 100/25mg Tabs 60s End "
            "of Month Physical Stock Count": "LPV/r 100/25",
            "MoH 730B Revision 2017 Adult preparations Tenofovir/Lamivudine/Efavirenz (TDF/3TC/EFV) FDC ("
            "300/300/400mg) FDC Tablets 30s End of Month Physical Stock Count": "TL_400 30",
            "MoH 730B Revision 2017 Adult preparations Tenofovir/Lamivudine/Efavirenz (TDF/3TC/EFV) FDC ("
            "300/300/600mg) FDC Tablets 30s End of Month Physical Stock Count": "TLE_600 30s",
            "MoH 730B Revision 2019Tenofovir/Lamivudine/Efavirenz (TDF/3TC/EFV) FDC (300/300/400mg) FDC "
            "Tablets  90s End of Month Physical Stock Count": "TLE_400 90s",
            "MoH 730B Revision 2017 Adult preparations Tenofovir/Lamivudine/Dolutegravir (TDF/3TC/DTG) FDC ("
            "300/300/50mg) FDC Tablets 30s End of Month Physical Stock Count": "TLD 30s",
            "MoH 730B Revision 2019Tenofovir/Lamivudine/Dolutegravir (TDF/3TC/DTG) FDC (300/300/50mg) FDC "
            "Tablets 90s End of Month Physical Stock Count": "TLD 90s",
            "MoH 730B Revision 2019 Tenofovir/Lamivudine/Dolutegravir (TDF/3TC/DTG) FDC (300/300/50mg) FDC "
            "Tablets 180s End of Month Physical Stock Counth": "TLD 180s",
            "MoH 730B Revision 2019 Tenofovir/Lamivudine/Dolutegravir (TDF/3TC/DTG) FDC (300/300/50mg) FDC "
            "Tablets 180s End of Month Physical Stock Count": "TLD 180s",
            "MoH 730B Revision 2019Rifapentine (P) 150mg tab 24s End of Month Physical Stock Count":
                "Rifapentine 150mg",
            "MoH 730B Revision 2019Rifapentine/Isoniazid  (P) 300mg/300mg tabs 30s End of Month Physical "
            "Stock Count": "3HP 300/300",
            "MoH 730B Revision 2017 Paediatric preparations Abacavir/Lamivudine (ABC/3TC) 120mg/60mg FDC "
            "Tablets 30s End of Month Physical Stock Count": "(ABC/3TC) 120mg/60mg",
            "MoH 730B Revision 2017 Adult preparations Nevirapine (NVP) 200mg Tablets 60s End of Month "
            "Physical Stock Count": "NVP 200",
            "MoH 730B Revision 2017 Medicines for OIs Cotrimoxazole suspension 240mg/5ml  100ml bottle End of "
            "Month Physical Stock Count": "CTX 240mg/5ml",
            "MoH 730B Revision 2017 Medicines for OIs Cotrimoxazole 960mg Tablets 100s End of Month Physical "
            "Stock Count": "CTX 960",
        })
    cols_to_drop = [col for col in tld_tle_lpv_dtg10_nvp_others_df.columns if
                    "moh 730b revision" in col.lower()]
    tld_tle_lpv_dtg10_nvp_others_df = tld_tle_lpv_dtg10_nvp_others_df.drop(cols_to_drop, axis=1)
    numeric_cols = ['TLD 30s', 'TLD 90s',
                    'TLD 180s', "CTX 960", "CTX 240mg/5ml", 'TL_400 30', 'TLE_600 30s',
                    'TLE_400 90s', "LPV/r 100/25",
                    "LPV/r 40/10", "DTG 50", 'DTG 10', 'AZT/3TC/NVP (Adult) bottles', 'NVP 200',
                    'NVP (Pediatric) bottles', '(ABC/3TC) 120mg/60mg',
                    '3HP 300/300', 'Other (Adult) bottles', 'Other (Pediatric) bottles']

    if "periodname" in default_cols:
        final_df = tld_tle_lpv_dtg10_nvp_others_df.merge(df, left_on="organisationunitcode",
                                                         right_on="MFL Code", how="left")
    else:
        final_df = tld_tle_lpv_dtg10_nvp_others_df.merge(df, left_on="organisationunitcode",
                                                         right_on="MFL Code")
    final_df['MFL Code'] = final_df['MFL Code'].astype(str)
    final_df.loc['Total'] = final_df.sum(numeric_only=True)
    final_df.loc['Total'] = final_df.loc['Total'].fillna("")
    final_df[numeric_cols] = final_df[numeric_cols].astype(int)
    if "periodname" in default_cols:
        try:
            final_df = final_df[
                ['County', 'Health Subcounty', 'Subcounty', 'organisationunitname', 'MFL Code',
                 'Hub(1,2,3 o 4)', "periodname", 'TLD 30s', 'TLD 90s',
                 'TLD 180s', "CTX 960", "CTX 240mg/5ml", 'TL_400 30', 'TLE_600 30s',
                 'TLE_400 90s', "LPV/r 100/25",
                 "LPV/r 40/10", "DTG 50", 'DTG 10', 'AZT/3TC/NVP (Adult) bottles', 'NVP 200',
                 'NVP (Pediatric) bottles', '(ABC/3TC) 120mg/60mg',
                 '3HP 300/300', 'Other (Adult) bottles', 'Other (Pediatric) bottles',
                 'M&E Mentor/SI associate',
                 'M&E Assistant', 'Care & Treatment(Yes/No)', 'HTS(Yes/No)',
                 'VMMC(Yes/No)', 'Key Pop(Yes/No)', 'Faclity Type',
                 'Category (HVF/MVF/LVF)', 'EMR']]
        except KeyError as e:
            missing_columns = [col.replace("'", "") for col in
                               str(e).split("[")[1].split("]")[0].split(",")]
            # print(f"Columns {', '.join(missing_columns)} not found. "
            #       f"Adding missing columns with default value 0.")
            for col in missing_columns:
                final_df[col] = 0
            final_df = final_df[
                ['County', 'Health Subcounty', 'Subcounty', 'organisationunitname', 'MFL Code',
                 'Hub(1,2,3 o 4)', "periodname", 'TLD 30s', 'TLD 90s',
                 'TLD 180s', "CTX 960", "CTX 240mg/5ml", 'TL_400 30', 'TLE_600 30s',
                 'TLE_400 90s', "LPV/r 100/25", "LPV/r 40/10", "DTG 50", 'DTG 10',
                 'AZT/3TC/NVP (Adult) bottles', 'NVP 200', 'NVP (Pediatric) bottles',
                 '(ABC/3TC) 120mg/60mg', 'M&E Mentor/SI associate',
                 'M&E Assistant', 'Care & Treatment(Yes/No)', 'HTS(Yes/No)',
                 'VMMC(Yes/No)', 'Key Pop(Yes/No)', 'Faclity Type',
                 'Category (HVF/MVF/LVF)', 'EMR']]
    else:
        try:
            final_df = final_df[
                ['County', 'Health Subcounty', 'Subcounty', 'organisationunitname', 'MFL Code',
                 'Hub(1,2,3 o 4)',
                 'TLD 30s', 'TLD 90s',
                 'TLD 180s', "CTX 960", "CTX 240mg/5ml", 'TL_400 30', 'TLE_600 30s',
                 'TLE_400 90s', "LPV/r 100/25",
                 "LPV/r 40/10", "DTG 50", 'DTG 10', 'AZT/3TC/NVP (Adult) bottles', 'NVP 200',
                 'NVP (Pediatric) bottles', '(ABC/3TC) 120mg/60mg',
                 '3HP 300/300', 'Other (Adult) bottles', 'Other (Pediatric) bottles',
                 'M&E Mentor/SI associate', 'M&E Assistant',
                 'Care & Treatment(Yes/No)', 'HTS(Yes/No)', 'VMMC(Yes/No)', 'Key Pop(Yes/No)',
                 'Faclity Type', 'Category (HVF/MVF/LVF)'
                    , 'EMR']]
        except KeyError as e:
            missing_columns = [col.replace("'", "") for col in
                               str(e).split("[")[1].split("]")[0].split(",")]
            # print(f"Columns {', '.join(missing_columns)} not found. "
            #       f"Adding missing columns with default value 0.")
            for col in missing_columns:
                final_df[col] = 0
            final_df = final_df[
                ['County', 'Health Subcounty', 'Subcounty', 'organisationunitname', 'MFL Code',
                 'Hub(1,2,3 o 4)',
                 'TLD 30s', 'TLD 90s',
                 'TLD 180s', "CTX 960", "CTX 240mg/5ml", 'TL_400 30', 'TLE_600 30s',
                 'TLE_400 90s', "LPV/r 100/25",
                 "LPV/r 40/10", "DTG 50", 'DTG 10', 'AZT/3TC/NVP (Adult) bottles', 'NVP 200',
                 'NVP (Pediatric) bottles', '(ABC/3TC) 120mg/60mg',
                 '3HP 300/300', 'Other (Adult) bottles', 'Other (Pediatric) bottles',
                 'M&E Mentor/SI associate',
                 'M&E Assistant', 'Care & Treatment(Yes/No)', 'HTS(Yes/No)',
                 'VMMC(Yes/No)', 'Key Pop(Yes/No)', 'Faclity Type',
                 'Category (HVF/MVF/LVF)', 'EMR']]

    return final_df, filename, other_adult_df_file, adult_others_filename, paeds_others_filename, other_paeds_bottles_df_file


def pharmacy(request):
    final_df = pd.DataFrame()
    filename = None
    other_adult_df_file = pd.DataFrame()
    adult_others_filename = None
    paeds_others_filename = None
    dictionary = None
    other_paeds_bottles_df_file = pd.DataFrame()
    form = FileUploadForm(request.POST or None)
    if not request.user.first_name:
        return redirect("profile")
    if request.method == 'POST':
        try:
            form = FileUploadForm(request.POST, request.FILES)
            url = 'https://hiskenya.org/dhis-web-data-visualizer/index.html#/'
            if form.is_valid():
                # try:
                file = request.FILES['file']
                if "csv" in file.name:
                    df1 = pd.read_csv(file)
                else:
                    message = f"Upload either the Total Quantity issued this month or End of " \
                              f"Month Physical Stock Count CSV file from <a href='{url}'>KHIS's website</a>."
                    messages.success(request, message)
                    return redirect('load_data_pharmacy')
                # Check if required columns exist in the DataFrame
                if all(col_name in df1.columns for col_name in
                       ['organisationunitname', 'organisationunitcode', "periodname"]):
                    # Read data from FYJHealthFacility model into a pandas DataFrame
                    qs = FYJHealthFacility.objects.all()
                    df = pd.DataFrame.from_records(qs.values())

                    df = df.rename(columns={
                        "mfl_code": "MFL Code", "county": "County", 'health_subcounty': 'Health Subcounty',
                        'subcounty': 'Subcounty', 'hub': 'Hub(1,2,3 o 4)', 'm_and_e_mentor': 'M&E Mentor/SI associate',
                        'm_and_e_assistant': 'M&E Assistant', 'care_and_treatment': 'Care & Treatment(Yes/No)',
                        'hts': 'HTS(Yes/No)', 'vmmc': 'VMMC(Yes/No)', 'key_pop': 'Key Pop(Yes/No)',
                        'facility_type': 'Faclity Type', 'category': 'Category (HVF/MVF/LVF)', 'emr': 'EMR'
                    })
                    if df.shape[0] > 0 and df1.shape[0] > 0:
                        final_df, filename, other_adult_df_file, adult_others_filename, paeds_others_filename, \
                        other_paeds_bottles_df_file = analyse_pharmacy_data(request, df, df1)
                else:
                    message = f"Please generate upload either the Total Quantity issued this month or End of Month " \
                              f"Physical Stock Count CSV file from <a href='{url}'>KHIS's website</a>."
                    messages.success(request, message)
                    return redirect('load_data_pharmacy')
            else:
                message = f"Please generate upload either the Total Quantity issued this month or End of Month " \
                          f"Physical Stock Count CSV file from <a href='{url}'>KHIS's website</a>."
                messages.success(request, message)
                return redirect('load_data_pharmacy')
        except MultiValueDictKeyError:
            context = {
                "final_df": final_df,
                "dictionary": dictionary,
                "filename": filename,
                "other_adult_df_file": other_adult_df_file,
                "adult_others_filename": adult_others_filename,
                "paeds_others_filename": paeds_others_filename,
                "other_paeds_bottles_df_file": other_paeds_bottles_df_file,
                "form":form,
            }

            return render(request, 'data_analysis/upload.html', context)

    request.session['report'] = final_df.to_dict()
    # Convert dict_items into a list
    dictionary = get_key_from_session_names(request)
    context = {
        "final_df": final_df,
        "dictionary": dictionary,
        "filename": filename,
        "other_adult_df_file": other_adult_df_file,
        "adult_others_filename": adult_others_filename,
        "paeds_others_filename": paeds_others_filename,
        "other_paeds_bottles_df_file": other_paeds_bottles_df_file,
        "form": form,
    }

    return render(request, 'data_analysis/upload.html', context)


######################################################################################
# LABORATORY SECTION
######################################################################################

# Define a function to convert the column names into datetime objects
def to_datetime(col):
    import datetime
    try:
        return datetime.datetime.strptime(col, '%b-%Y')
    except ValueError:
        return datetime.datetime.min


def generate_tat_report(df, groupby, starting_date, last_date, col_name):
    # Check if last_date is less than starting_date and assign starting_date to last_date in such cases

    # define a function to check and assign values
    def check_and_assign_dates(row):
        if row[last_date] < row[starting_date]:
            row[last_date] = row[starting_date]
        return row

    # apply the function to the DataFrame
    df = df.apply(check_and_assign_dates, axis=1)

    # add TAT column
    df[col_name] = df[last_date] - df[starting_date]

    # Remove days in TAT column
    df[col_name] = df[col_name].astype('timedelta64[D]')
    if groupby == "Facilty":
        filter_by = 'Facility Code'
    else:
        filter_by = groupby

    if "Sample ID" in df.columns:
        text = "Sample ID"
    else:
        text = "Patient CCC No"

    unit_dfs = []
    for mfl_code in df[filter_by].unique():
        max_length = 0
        max_patient_number = 0
        std_sample_tat = 0
        unit_df = df[df[filter_by] == mfl_code]
        samples_above_mean_df = unit_df[unit_df[col_name] > unit_df[col_name].mean()]
        # Calculate the first and third quartiles and the interquartile range (IQR)
        Q1 = unit_df[col_name].quantile(0.25)
        Q3 = unit_df[col_name].quantile(0.75)
        IQR = Q3 - Q1

        # Identify outliers as data points that are more than 1.5 times the IQR below Q1 or above Q3
        outliers = unit_df[(unit_df[col_name] > Q3 + 1.5 * IQR)]
        #         display(outliers.shape[0])

        try:
            min_sample_tat = int(unit_df[col_name].min())
        except ValueError:
            min_sample_tat = 0
        try:
            max_sample_tat = int(unit_df[col_name].max())
        except ValueError:
            max_sample_tat = 0

        try:
            std_sample_tat = unit_df[col_name].std()
        except ValueError:
            std_sample_tat = 0

        max_df = unit_df[unit_df[col_name] == max_sample_tat]
        #         display(max_df)
        max_length = len(list(max_df[text].unique()))
        max_patient_number = sorted(list(max_df[text].unique()))
        #         max_patient_number = ', '.join(sorted(list(max_df['Patient CCC No'].unique())))

        min_df = unit_df[unit_df[col_name] == min_sample_tat]
        min_patient_number = ', '.join(sorted(list(min_df[text].astype(str).unique())))
        outliers_patient_number = ', '.join(sorted(list(outliers[text].astype(str).unique())))
        if groupby == "Facilty":
            col_to_use = "mfl_code"
        else:
            col_to_use = groupby
        unit_dfs.append({f'{col_to_use}': mfl_code, f'{col_name} max_sample_tat (days)': max_sample_tat,
                         f'{col_name} min_sample_tat (days)': min_sample_tat,
                         "# of samples analyzed": unit_df.shape[0],
                         "# of samples with TAT above mean": samples_above_mean_df.shape[0],
                         "# of samples with Maximum TAT": max_length,
                         "unique number(s) with Maximum TAT": max_patient_number,
                         "# of outlier samples": outliers.shape[0],
                         "outliers unique number(s)": outliers_patient_number,
                         f'{col_name} (Standard deviation TAT days)': std_sample_tat,
                         }
                        )

    df_result = pd.DataFrame(unit_dfs).fillna(0)
    for col in df_result.columns[1:3]:
        df_result[col] = df_result[col].astype(int)
    df_result[df_result.columns[-1]] = round(df_result[df_result.columns[-1]]).astype(int)

    # find the average of TAT grouped by area of interest
    if groupby == "Facilty":
        turn_around_time = round(df.groupby([groupby, 'month_year', filter_by]).mean(numeric_only=True)[col_name])
    else:
        turn_around_time = round(df.groupby([groupby, 'month_year']).mean(numeric_only=True)[col_name])

    # convert results into a dataframe and sort TAT column Z-A
    tat = pd.DataFrame(turn_around_time).sort_values(col_name, ascending=False).reset_index()
    #     display(tat)

    if groupby == "Facilty":
        facility_monthly_collect_receipt_tat = pd.pivot_table(tat, values=col_name, index=[groupby, filter_by],
                                                              columns=['month_year']).reset_index()
    else:
        facility_monthly_collect_receipt_tat = pd.pivot_table(tat, values=col_name, index=[groupby],
                                                              columns=['month_year']).reset_index()
    cols = list(facility_monthly_collect_receipt_tat.columns)
    # Sort the list of column names based on their datetime values
    sorted_cols = sorted(cols, key=to_datetime)

    # Print the sorted list of column names
    facility_monthly_collect_receipt_tat = facility_monthly_collect_receipt_tat[sorted_cols].fillna(0)
    for i in facility_monthly_collect_receipt_tat.columns[1:]:
        facility_monthly_collect_receipt_tat[i] = facility_monthly_collect_receipt_tat[i].astype(int)

    # Set the name of the columns to None
    facility_monthly_collect_receipt_tat.columns.name = None

    # Convert mean, median, standard deviation maximum and minimum TAT
    col_list = list(facility_monthly_collect_receipt_tat.columns[2:])
    facility_monthly_collect_receipt_tat[f'{col_name} (Mean TAT days)'] = facility_monthly_collect_receipt_tat[
        col_list].mean(axis=1)
    facility_monthly_collect_receipt_tat[f'{col_name} (Median TAT days)'] = facility_monthly_collect_receipt_tat[
        col_list].median(axis=1)
    facility_monthly_collect_receipt_tat[f'{col_name} (Mean TAT days)'] = round(
        facility_monthly_collect_receipt_tat[f'{col_name} (Mean TAT days)'], )
    facility_monthly_collect_receipt_tat[f'{col_name} (Median TAT days)'] = round(
        facility_monthly_collect_receipt_tat[f'{col_name} (Median TAT days)'], )

    if groupby == "Facilty":
        facility_monthly_collect_receipt_tat = facility_monthly_collect_receipt_tat.merge(df_result,
                                                                                          left_on="Facility Code",
                                                                                          right_on="mfl_code")
        del facility_monthly_collect_receipt_tat['mfl_code']

    else:
        facility_monthly_collect_receipt_tat = facility_monthly_collect_receipt_tat.merge(df_result, on=groupby)

    cols_to_include = [col for col in facility_monthly_collect_receipt_tat.columns if col != "Facility Code"]
    facility_monthly_collect_receipt_tat.loc['Mean', cols_to_include] = round(
        facility_monthly_collect_receipt_tat.loc[:, cols_to_include].mean(numeric_only=True))
    facility_monthly_collect_receipt_tat.loc['Median', cols_to_include] = round(
        facility_monthly_collect_receipt_tat.loc[:, cols_to_include].median(numeric_only=True))
    facility_monthly_collect_receipt_tat.loc['Std', cols_to_include] = round(
        facility_monthly_collect_receipt_tat.loc[:, cols_to_include].std(numeric_only=True))
    facility_monthly_collect_receipt_tat.loc['Min', cols_to_include] = round(
        facility_monthly_collect_receipt_tat.loc[:, cols_to_include].min(numeric_only=True))
    facility_monthly_collect_receipt_tat.loc['Max', cols_to_include] = round(
        facility_monthly_collect_receipt_tat.loc[:, cols_to_include].max(numeric_only=True))

    facility_monthly_collect_receipt_tat = facility_monthly_collect_receipt_tat.fillna("")
    return facility_monthly_collect_receipt_tat, df_result


def prepare_collect_dispatch_df(hubs_collect_dispatch_tat, report_type):
    if "Facility Code" in hubs_collect_dispatch_tat.columns:
        del hubs_collect_dispatch_tat['Facility Code']
    hubs_collect_dispatch_tat = hubs_collect_dispatch_tat[
        hubs_collect_dispatch_tat[report_type] != ""]
    hubs_collect_dispatch_tat = hubs_collect_dispatch_tat[
        list(hubs_collect_dispatch_tat.columns[0:7])]
    hubs_collect_dispatch_tat['TAT type'] = "collection to dispatch"

    return hubs_collect_dispatch_tat


def prepare_collect_receipt_df(hub_monthly_collect_receipt_tat, report_type):
    if "Facility Code" in hub_monthly_collect_receipt_tat.columns:
        del hub_monthly_collect_receipt_tat['Facility Code']
    hub_monthly_collect_receipt_tat = hub_monthly_collect_receipt_tat[
        hub_monthly_collect_receipt_tat[report_type] != ""]
    hub_monthly_collect_receipt_tat = hub_monthly_collect_receipt_tat[
        list(hub_monthly_collect_receipt_tat.columns[0:7])]
    hub_monthly_collect_receipt_tat['TAT type'] = "collection to receipt"
    return hub_monthly_collect_receipt_tat


def visualize_tat_type(hub_df, viz_name, target_text):
    hub_df = pd.melt(hub_df, id_vars=[viz_name, 'TAT type'], value_vars=list(hub_df.columns[1:7]),
                     var_name='Month_Year', value_name='TAT (mean)')
    hub_df = hub_df[hub_df['Month_Year'] != "Facility Code"]
    a = hub_df.groupby([viz_name, 'Month_Year', 'TAT type']).sum(numeric_only=True).reset_index()

    # Order dfs based on TAT mean of collection to dispatch
    ordered_dfs = []
    for hub in hub_df[viz_name].unique():
        hub_specific_df = a[(a[viz_name] == hub) & (~a["Month_Year"].str.contains("tat", case=False))]
        #         display(hub_specific_df)

        hub_specific_df['month_year'] = pd.to_datetime(hub_specific_df['Month_Year'], format='%b-%Y')
        hub_specific_df = hub_specific_df.sort_values('month_year')

        hub_specific_df = hub_specific_df[hub_specific_df['TAT type'] == 'collection to dispatch']
        ordered_dfs.append(hub_specific_df.tail(1))
    #         break
    ordered_tat_dfs = pd.concat(ordered_dfs).sort_values("TAT (mean)", ascending=False)
    viz_dicts = {}
    # use Ordered dfs to display charts
    for hub in ordered_tat_dfs[viz_name]:
        hub_specific_df = a[(a[viz_name] == hub) & (~a["Month_Year"].str.contains("tat", case=False))]
        hub_specific_df['month_year'] = pd.to_datetime(hub_specific_df['Month_Year'], format='%b-%Y')
        hub_specific_df = hub_specific_df.sort_values('month_year')
        #         display(hub_specific_df)
        #         break

        title = f"Mean {target_text} TAT Trend {hub.title()} {viz_name}" if "hub" not in hub.lower() else f"Mean {target_text} TAT Trend {hub.title()}"
        fig = px.line(hub_specific_df, x='month_year', y="TAT (mean)", text='TAT (mean)', color="TAT type", title=title,
                      height=450)
        fig.update_traces(textposition='top center')
        if target_text == "VL":
            y = 14
        else:
            y = 10
        fig.add_shape(type='line', x0=hub_specific_df['month_year'].min(), y0=y, x1=hub_specific_df['month_year'].max(),
                      y1=y,
                      line=dict(color='red', width=2, dash='dot'))

        fig.add_annotation(x=hub_specific_df['month_year'].max(), y=y,
                           text=f"FYJ {target_text} TAT Target (<={y})",
                           showarrow=True, arrowhead=1,
                           font=dict(size=14, color='red'))
        fig.update_layout(legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ))
        viz_dicts[hub] = plot(fig, include_plotlyjs=False, output_type="div")
    return viz_dicts


#         break
def transform_data(df, df1, date_picker_form):
    df['Facility Code'] = df['Facility Code'].astype(int)
    df['V.L'] = 1
    df1['MFL Code'] = df1['MFL Code'].astype(int)
    #
    df = df.merge(df1, left_on='Facility Code', right_on="MFL Code", how='left')
    df = df.rename(columns={"Hub(1,2,3 o 4)": "Hub"})
    df = df.rename(columns={"County_x": "County"})
    if "Sample ID" in df.columns:
        target_text = "EID"
    else:
        target_text = "VL"
    date_cols = [col for col in df.columns if "date" in col.lower()]
    # Convert cols to datetime
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')

    from_date = date_picker_form.cleaned_data['from_date']
    to_date = date_picker_form.cleaned_data['to_date']
    df = df.loc[(df['Date Collected'].dt.date >= from_date) &
                (df['Date Collected'].dt.date <= to_date)]

    df['month_year'] = pd.to_datetime(df['Date Collected']).dt.strftime('%b-%Y')
    ########################################
    # Collection and Receipt
    ########################################
    facilities_collect_receipt_tat, df_result = generate_tat_report(
        df, "Facilty", "Date Collected", "Date Received",
        "Collected to Received")
    facility_c_r_filename = f"facilities_collect_receipt_tat_{target_text}"

    sub_counties_collect_receipt_tat, df_result = generate_tat_report(
        df, 'Sub-County', "Date Collected", "Date Received",
        "Collected to Received (TAT "
        "days)")
    subcounty_c_r_filename = f"sub_counties_collect_receipt_tat_{target_text}"
    hubs_collect_receipt_tat, df_result = generate_tat_report(
        df, 'Hub', "Date Collected", "Date Received",
        "Collected to Received (TAT days)")
    hub_c_r_filename = f"hubs_collect_receipt_tat_{target_text}"
    counties_collect_receipt_tat, df_result = generate_tat_report(
        df, 'County', "Date Collected", "Date Received",
        "Collected to Received")
    county_c_r_filename = f"counties_collect_receipt_tat_{target_text}"
    ########################################
    # Collection and Dispatch
    ########################################
    facilities_collect_dispatch_tat, df_result = generate_tat_report(
        df, "Facilty", "Date Collected", "Date Dispatched",
        "Collection to Dispatch")
    facility_c_d_filename = f"facilities_collect_dispatch_tat_{target_text}"

    sub_counties_collect_dispatch_tat, df_result = generate_tat_report(
        df, "Sub-County", "Date Collected", "Date Dispatched",
        "Collection to Dispatch")
    subcounty_c_d_filename = f"sub_counties_collect_dispatch_tat_{target_text}"
    hubs_collect_dispatch_tat, df_result = generate_tat_report(
        df, "Hub", "Date Collected", "Date Dispatched",
        "Collection to Dispatch (TAT days)")
    hub_c_d_filename = f"hubs_collect_dispatch_tat_{target_text}"
    counties_collect_dispatch_tat, df_result = generate_tat_report(
        df, "County", "Date Collected", "Date Dispatched",
        "Collection to Dispatch (TAT days)")
    county_c_d_filename = f"counties_collect_dispatch_tat_{target_text}"
    ########################################
    # Merge Collect to receipt and Collection to Dispatch
    ########################################

    hubs_collect_receipt_tat_trend = prepare_collect_receipt_df(
        hubs_collect_receipt_tat, "Hub")
    hubs_collect_dispatch_tat_trend = prepare_collect_dispatch_df(
        hubs_collect_dispatch_tat, "Hub")
    hub_df = pd.concat([hubs_collect_receipt_tat_trend,
                        hubs_collect_dispatch_tat_trend])

    hub_viz = visualize_tat_type(hub_df, "Hub", target_text)

    counties_collect_receipt_tat_trend = prepare_collect_receipt_df(
        counties_collect_receipt_tat, "County")

    counties_collect_dispatch_tat_trend = prepare_collect_dispatch_df(
        counties_collect_dispatch_tat, "County")

    counties_df = pd.concat(
        [counties_collect_receipt_tat_trend,
         counties_collect_dispatch_tat_trend])

    county_viz = visualize_tat_type(counties_df, "County", target_text)

    sub_counties_collect_receipt_tat_trend = prepare_collect_receipt_df(
        sub_counties_collect_receipt_tat, "Sub-County")
    sub_counties_collect_dispatch_tat_trend = prepare_collect_dispatch_df(
        sub_counties_collect_dispatch_tat, "Sub-County")
    sub_counties_df = pd.concat([sub_counties_collect_receipt_tat_trend,
                                 sub_counties_collect_dispatch_tat_trend])

    sub_county_viz = visualize_tat_type(sub_counties_df, "Sub-County",
                                        target_text)
    return facilities_collect_receipt_tat, facility_c_r_filename, \
           sub_counties_collect_receipt_tat, subcounty_c_r_filename, \
           hubs_collect_receipt_tat, hub_c_r_filename, \
           counties_collect_receipt_tat, county_c_r_filename, \
           facilities_collect_dispatch_tat, facility_c_d_filename, \
           sub_counties_collect_dispatch_tat, subcounty_c_d_filename, \
           hubs_collect_dispatch_tat, hub_c_d_filename, \
           counties_collect_dispatch_tat, county_c_d_filename, hub_viz, \
           county_viz, sub_county_viz,target_text


def tat(request):
    facilities_collect_receipt_tat = pd.DataFrame()
    facilities_collect_dispatch_tat = pd.DataFrame()
    sub_counties_collect_receipt_tat = pd.DataFrame()
    sub_counties_collect_dispatch_tat = pd.DataFrame()
    hubs_collect_receipt_tat = pd.DataFrame()
    hubs_collect_dispatch_tat = pd.DataFrame()
    counties_collect_receipt_tat = pd.DataFrame()
    counties_collect_dispatch_tat = pd.DataFrame()
    facility_c_r_filename = None
    facility_c_d_filename = None
    subcounty_c_r_filename = None
    subcounty_c_d_filename = None
    dictionary = None
    target_text = None
    hub_c_r_filename = None
    hub_c_d_filename = None
    county_c_r_filename = None
    county_c_d_filename = None
    date_picker_form = DateFilterForm(request.POST or None)
    form = FileUploadForm(request.POST or None)
    hub_viz = None
    county_viz = None
    sub_county_viz = None
    if not request.user.first_name:
        return redirect("profile")
    if request.method == 'POST' and "file" in request.FILES:
        try:
            if request.method == 'POST':
                form = FileUploadForm(request.POST, request.FILES)
                url = 'https://eiddash.nascop.org/reports/EID'
                if form.is_valid():
                    # try:
                    file = request.FILES['file']
                    if "csv" in file.name:
                        df = pd.read_csv(file)
                    else:
                        message = f"Please generate overall 'All Outcomes (+/-) for EID' or 'Detailed for VL' and " \
                                  f"upload the CSV from <a href='{url}'>NASCOP's website</a>."
                        messages.success(request, message)
                        return redirect('tat')
                    # Check if required columns exist in the DataFrame
                    if all(col_name in df.columns for col_name in
                           ['Date Collected', 'Date Received', 'Date Tested', 'Date Dispatched']):
                        # Read data from FYJHealthFacility model into a pandas DataFrame
                        qs = FYJHealthFacility.objects.all()
                        df1 = pd.DataFrame.from_records(qs.values())

                        df1 = df1.rename(columns={
                            "mfl_code": "MFL Code", "county": "County", 'health_subcounty': 'Health Subcounty',
                            'subcounty': 'Subcounty', 'hub': 'Hub(1,2,3 o 4)',
                            'm_and_e_mentor': 'M&E Mentor/SI associate',
                            'm_and_e_assistant': 'M&E Assistant', 'care_and_treatment': 'Care & Treatment(Yes/No)',
                            'hts': 'HTS(Yes/No)', 'vmmc': 'VMMC(Yes/No)', 'key_pop': 'Key Pop(Yes/No)',
                            'facility_type': 'Faclity Type', 'category': 'Category (HVF/MVF/LVF)', 'emr': 'EMR'
                        })
                        if df.shape[0] > 0 and df1.shape[0] > 0:
                            if request.method == 'POST':
                                date_picker_form = DateFilterForm(request.POST)
                                if date_picker_form.is_valid():
                                    facilities_collect_receipt_tat, facility_c_r_filename, \
                                    sub_counties_collect_receipt_tat, subcounty_c_r_filename, \
                                    hubs_collect_receipt_tat, hub_c_r_filename, \
                                    counties_collect_receipt_tat, county_c_r_filename, \
                                    facilities_collect_dispatch_tat, facility_c_d_filename, \
                                    sub_counties_collect_dispatch_tat, subcounty_c_d_filename, \
                                    hubs_collect_dispatch_tat, hub_c_d_filename, \
                                    counties_collect_dispatch_tat, county_c_d_filename, hub_viz, \
                                    county_viz, sub_county_viz, target_text = transform_data(df, df1, date_picker_form)
                    else:
                        message = f"Please generate overall 'All Outcomes (+/-) for EID' or 'Detailed for VL' and " \
                                  f"upload the CSV from <a href='{url}'>NASCOP's website</a>."
                        messages.success(request, message)
                        return redirect('tat')

        except MultiValueDictKeyError:
            context = {
                "date_picker_form": date_picker_form,
                "facilities_collect_receipt_tat": facilities_collect_receipt_tat,
                "facilities_collect_dispatch_tat": facilities_collect_dispatch_tat,
                "sub_counties_collect_receipt_tat": sub_counties_collect_receipt_tat,
                "sub_counties_collect_dispatch_tat": sub_counties_collect_dispatch_tat,
                "hubs_collect_receipt_tat": hubs_collect_receipt_tat,
                "hubs_collect_dispatch_tat": hubs_collect_dispatch_tat,
                "counties_collect_receipt_tat": counties_collect_receipt_tat,
                "counties_collect_dispatch_tat": counties_collect_dispatch_tat,
                "dictionary": dictionary,
                "facility_c_r_filename": facility_c_r_filename,
                "facility_c_d_filename": facility_c_d_filename,
                "subcounty_c_r_filename": subcounty_c_r_filename,
                "subcounty_c_d_filename": subcounty_c_d_filename,
                "form": form,
                "target_text": target_text,
                "hub_c_r_filename": hub_c_r_filename,
                "hub_c_d_filename": hub_c_d_filename,
                "county_c_r_filename": county_c_r_filename,
                "county_c_d_filename": county_c_d_filename,
                "hub_viz": hub_viz,
                "county_viz": county_viz,
                "sub_county_viz": sub_county_viz,

            }

            return render(request, 'data_analysis/upload.html', context)

    request.session['facilities_collect_receipt_tat'] = facilities_collect_receipt_tat.to_dict()
    request.session['facilities_collect_dispatch_tat'] = facilities_collect_dispatch_tat.to_dict()
    request.session['sub_counties_collect_receipt_tat'] = sub_counties_collect_receipt_tat.to_dict()
    request.session['sub_counties_collect_dispatch_tat'] = sub_counties_collect_dispatch_tat.to_dict()
    request.session['hubs_collect_receipt_tat'] = hubs_collect_receipt_tat.to_dict()
    request.session['hubs_collect_dispatch_tat'] = hubs_collect_dispatch_tat.to_dict()
    request.session['counties_collect_receipt_tat'] = counties_collect_receipt_tat.to_dict()
    request.session['counties_collect_dispatch_tat'] = counties_collect_dispatch_tat.to_dict()

    # Convert dict_items into a list
    dictionary = get_key_from_session_names(request)
    context = {
        "date_picker_form": date_picker_form,
        "facilities_collect_receipt_tat": facilities_collect_receipt_tat,
        "facilities_collect_dispatch_tat": facilities_collect_dispatch_tat,
        "sub_counties_collect_receipt_tat": sub_counties_collect_receipt_tat,
        "sub_counties_collect_dispatch_tat": sub_counties_collect_dispatch_tat,
        "hubs_collect_receipt_tat": hubs_collect_receipt_tat,
        "hubs_collect_dispatch_tat": hubs_collect_dispatch_tat,
        "counties_collect_receipt_tat": counties_collect_receipt_tat,
        "counties_collect_dispatch_tat": counties_collect_dispatch_tat,
        "dictionary": dictionary,
        "facility_c_r_filename": facility_c_r_filename,
        "facility_c_d_filename": facility_c_d_filename,
        "subcounty_c_r_filename": subcounty_c_r_filename,
        "subcounty_c_d_filename": subcounty_c_d_filename,
        "form": form,
        "target_text": target_text,
        "hub_c_r_filename": hub_c_r_filename,
        "hub_c_d_filename": hub_c_d_filename,
        "county_c_r_filename": county_c_r_filename,
        "county_c_d_filename": county_c_d_filename,
        "hub_viz": hub_viz,
        "county_viz": county_viz,
        "sub_county_viz": sub_county_viz,
    }

    return render(request, 'data_analysis/tat.html', context)