import re

import numpy as np
import pandas as pd
import plotly.express as px
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render
# Create your views here.
from django.utils.datastructures import MultiValueDictKeyError
from plotly.offline import plot

from apps.data_analysis.forms import DataFilterForm, DateFilterForm, FileUploadForm
from apps.data_analysis.models import FYJHealthFacility


@login_required(login_url='login')
def load_fyj_censused(request):
    if not request.user.first_name:
        return redirect("profile")
    if request.method == 'POST' and "file" in request.FILES:
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

@login_required(login_url='login')
def download_csv(request, name, filename):
    session_items = []
    for key, value in request.session.items():
        session_items.append(key)

    df = request.session[f'{name}']
    df = pd.DataFrame(df)

    response = HttpResponse(df.to_csv(), content_type='text/csv')

    response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'

    return response


def convert_mfl_code_to_int(df):
    # drop the rows containing letters
    df = df[pd.to_numeric(df['organisationunitcode'], errors='coerce').notnull()]
    df['organisationunitcode'] = df['organisationunitcode'].astype(int)
    return df


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


# def prepare_sc_curr_arvdisp_df(df1, fyj_facility_mfl_code, default_cols):
#     df1 = df1[~df1['organisationunitname'].str.contains("adventist centre", case=False)]
#     # df1 = pd.read_csv(path1)
#     # Add Hope med C MFL CODE
#     df1.loc[df1['organisationunitname'] == "Hope Med C", 'organisationunitcode'] = 19278
#     # st francis
#     # df1.loc[df1['organisationunitcode'] == 13202, 'organisationunitcode'] = 17943
#     df1.loc[df1['organisationunitname'].str.contains("st francis comm", case=False), 'organisationunitcode'] = 17943
#
#     # adventist
#     # df1.loc[df1['organisationunitcode'] == 23385, 'organisationunitcode'] = 18535
#     df1.loc[df1['organisationunitname'].str.contains("better living", case=False), 'organisationunitcode'] = 18535
#     df1.loc[df1['organisationunitname'].str.contains("better living",
#                                                      case=False),
#     'organisationunitname'] = "Adventist Centre for Care and Support"
#
#     # illasit
#     # df1.loc[df1['organisationunitcode'] == 20372, 'organisationunitcode'] = 14567
#     df1.loc[df1['organisationunitname'].str.contains("illasit h", case=False), 'organisationunitcode'] = 14567
#     # imara
#     # df1.loc[df1['organisationunitcode'] == 17685, 'organisationunitcode'] = 12981
#     df1.loc[df1['organisationunitname'].str.contains("imara health", case=False), 'organisationunitcode'] = 12981
#     # mary immaculate
#     df1.loc[
#         df1['organisationunitname'].str.contains("mary immaculate sister", case=False), 'organisationunitcode'] = 13062
#
#     # biafra lion
#     df1.loc[
#         df1['organisationunitname'].str.contains("biafra lion", case=False), 'organisationunitcode'] = 12883
#
#     # for i in df1['organisationunitcode'].unique():
#     #     if "18535" in i.lower():
#     #         print(i)
#     #     print("Not found")
#     df1 = df1[~df1['organisationunitcode'].isnull()]
#     df1 = convert_mfl_code_to_int(df1)
#     df1 = df1[df1['organisationunitcode'].isin(fyj_facility_mfl_code)]
#
#     # df1["organisationunitcode"] = df1["organisationunitcode"].astype(int)
#     dispensed_cols = [col for col in df1.columns if "Total Quantity issued this month" in col]
#     end_of_months_cols = [col for col in df1.columns if "End of Month Physical Stock Count" in col]
#
#     if len(dispensed_cols) > 0:
#         # get the last 6 months data
#         # divide the period into 2
#         first_3_months = sorted(list(df1['periodid'].unique()))[:3]
#         last_3_months = sorted(list(df1['periodid'].unique()))[3:]
#
#         ###########################################################
#         # UNCOMMENT BELOW TO GET DATA FOR THE FIRST THREE MONTHS  #
#         ###########################################################
#         #         print(f"FIRST THREE MONTHS: {first_3_months}")
#         #         df1=df1[df1['periodid'].isin(first_3_months)]
#
#         ###########################################################
#         # UNCOMMENT BELOW TO GET DATA FOR THE LAST THREE MONTHS  #
#         ###########################################################
#
#         #         print(f"LAST THREE MONTHS: {last_3_months}")
#         #         df1=df1[df1['periodid'].isin(last_3_months)]
#         ###################################################################
#         # TO GET DATA FOR THE LAST 2 QUARTERS, COMMENT ABOVE TWO FILTERS  #
#         ###################################################################
#         dispensed_df = df1[default_cols + dispensed_cols]
#         filename = "sc_arvdisp"
#     else:
#         # get the last month data
#         last_month = df1['periodid'].unique().max()
#         df1 = df1[df1['periodid'] == last_month]
#
#         dispensed_df = df1[default_cols + end_of_months_cols]
#         filename = "sc_curr"
#     return dispensed_df, df1, dispensed_cols, end_of_months_cols, filename


def rename_khis_col(df1,fyj_facility_mfl_code):
    df1 = df1[~df1['organisationunitname'].str.contains("adventist centre", case=False)]
    # df1 = pd.read_csv(path1)
    # Add Hope med C MFL CODE
    df1.loc[df1['organisationunitname'] == "Hope Med C", 'organisationunitcode'] = 19278
    # st francis
    # df1.loc[df1['organisationunitcode'] == 13202, 'organisationunitcode'] = 17943
    # df1.loc[df1['organisationunitname'].str.contains("st francis comm", case=False), 'organisationunitcode'] = 17943

    # adventist
    # df1.loc[df1['organisationunitcode'] == 23385, 'organisationunitcode'] = 18535
    # df1.loc[df1['organisationunitname'].str.contains("better living", case=False), 'organisationunitcode'] = 18535
    # df1.loc[df1['organisationunitname'].str.contains("better living",
    #                                                  case=False),
    # 'organisationunitname'] = "Adventist Centre for Care and Support"

    # illasit
    # df1.loc[df1['organisationunitcode'] == 20372, 'organisationunitcode'] = 14567
    # df1.loc[df1['organisationunitname'].str.contains("illasit h", case=False), 'organisationunitcode'] = 14567
    # imara
    # df1.loc[df1['organisationunitcode'] == 17685, 'organisationunitcode'] = 12981
    # df1.loc[df1['organisationunitname'].str.contains("imara health", case=False), 'organisationunitcode'] = 12981
    # mary immaculate
    # df1.loc[
    #     df1['organisationunitname'].str.contains("mary immaculate sister", case=False), 'organisationunitcode'] = 13072

    # biafra lion
    # df1.loc[
    #     df1['organisationunitname'].str.contains("biafra lion", case=False), 'organisationunitcode'] = 12883

    # for i in df1['organisationunitcode'].unique():
    #     if "18535" in i.lower():
    #         print(i)
    #     print("Not found")
    df1 = df1[~df1['organisationunitcode'].isnull()]
    df1 = convert_mfl_code_to_int(df1)
    df1 = df1[df1['organisationunitcode'].isin(fyj_facility_mfl_code)]
    return df1
def prepare_sc_curr_arvdisp_df(df1, fyj_facility_mfl_code, default_cols):
    df1=rename_khis_col(df1, fyj_facility_mfl_code)

    # df1["organisationunitcode"] = df1["organisationunitcode"].astype(int)
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
        dispensed_df = df1[default_cols + dispensed_cols]
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


def process_reporting_errors(dispensed_df, tld_180s_df, default_cols, dispensed_cols, end_of_months_cols,
                             sc_arvdisp_cols, sc_curr_cols):
    """
    Process and identify reporting errors in a DataFrame.

    Args:
    dispensed_df (DataFrame): DataFrame containing dispensed data.
    tld_180s_df (DataFrame): DataFrame with tld_180s data.
    default_cols (list): List of default columns.
    dispensed_cols (list): List of columns specific to dispensed data.
    end_of_months_cols (list): List of columns specific to end_of_month data.
    sc_arvdisp_cols (dict): Dictionary for renaming columns related to sc_arvdisp data.
    sc_curr_cols (dict): Dictionary for renaming columns related to sc_curr data.

    Returns:
    DataFrame: Processed DataFrame with reporting errors identified and processed.
    """
    # Create lists of specific column names
    tle_400_90s = [x for x in dispensed_df.columns if "(TDF/3TC/EFV) FDC (300/300/400mg)" in x and "90s" in x]
    tle_600_30s = [x for x in dispensed_df.columns if "(TDF/3TC/EFV) FDC (300/300/600mg)" in x]
    lpv_r_pellets = [x for x in dispensed_df.columns if "40/10mg" in x]
    azt_3tc_nvp = [x for x in dispensed_df.columns if "AZT/3TC/NVP" in x]
    nvp_tabs = [x for x in dispensed_df.columns if "(NVP) 200mg" in x]

    # Create a subset DataFrame with selected columns
    reporting_errors_df = dispensed_df[
        default_cols + tle_400_90s + tle_600_30s + lpv_r_pellets + azt_3tc_nvp + nvp_tabs]

    # Merge tld_180s data and fill NaN values with 0
    if "periodname" in default_cols:
        reporting_errors_df = reporting_errors_df.merge(tld_180s_df,
                                                        on=["organisationunitname", "organisationunitcode",
                                                            "periodname"]).fillna(0)
    else:
        reporting_errors_df = reporting_errors_df.merge(tld_180s_df,
                                                        on=["organisationunitname", "organisationunitcode"]).fillna(0)

    # Rename columns based on the source of data (dispensed or end_of_month)
    if len(dispensed_cols) > 0:
        reporting_errors_df = reporting_errors_df.rename(columns=sc_arvdisp_cols)
    elif len(end_of_months_cols) > 0:
        reporting_errors_df = reporting_errors_df.rename(columns=sc_curr_cols)

    # Filter columns based on values > 0
    reporting_errors_df = reporting_errors_df[
        (reporting_errors_df.iloc[:, 3:] != 0).any(axis=1)
    ]

    # Convert a specific column to string and reset index
    reporting_errors_df['organisationunitcode'] = reporting_errors_df['organisationunitcode'].astype(str)
    reporting_errors_df.reset_index(drop=True, inplace=True)
    # Compute and add the 'Total' row
    reporting_errors_df.loc['Total'] = reporting_errors_df.sum(numeric_only=True)
    reporting_errors_df.loc['Total'] = reporting_errors_df.loc['Total'].fillna("")
    # Convert relevant columns to integers
    reporting_errors_df.iloc[:, 3:] = reporting_errors_df.iloc[:, 3:].astype(int)

    return reporting_errors_df


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
    lpvr_cols_200_50 = [col for col in dispensed_df.columns if "200/50mg" in col]
    dtg_50_cols = [col for col in dispensed_df.columns if "50mg tabs 30s" in col]

    nvp_cols = [col for col in dispensed_df.columns if "nvp" in col.lower()]
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
    #########################################
    # MERGE TLD 180S
    #########################################
    if "periodname" in default_cols:
        tld_df = tld_df.merge(tld_180s_df,
                              on=["organisationunitname", "organisationunitcode", "periodname"])
    else:
        tld_df = tld_df.merge(tld_180s_df, on=["organisationunitname", "organisationunitcode"])
    #########################################
    # MERGE CTX
    #########################################
    ctx, ctx_df, non_abc_3tc_in_abc_3tc_df = make_dfs(df1, ctx_cols, "Cotrimoxazole", default_cols)

    ctx_df = ctx_df[default_cols + ctx_cols]
    if "periodname" in default_cols:
        tld_df = tld_df.merge(ctx_df, on=["organisationunitname", "organisationunitcode", "periodname"])
    else:
        tld_df = tld_df.merge(ctx_df, on=["organisationunitname", "organisationunitcode"])
    #########################################
    # MERGE TLE
    #########################################
    efv_df, tle_df, non_tle_in_efv_df = make_dfs(df1, efv_cols, "(TDF/3TC/EFV)", default_cols)
    if "periodname" in default_cols:
        tld_tle_df = tld_df.merge(tle_df,
                                  on=["organisationunitname", "organisationunitcode", "periodname"])
    else:
        tld_tle_df = tld_df.merge(tle_df, on=["organisationunitname", "organisationunitcode"])
    #########################################
    # MERGE KALETRA
    #########################################

    lpvr_df, kaletra_df, non_kaletra_in_lpv_df = make_dfs(df1, lpvr_cols, "LPV/", default_cols)

    cols_to_use_lpvr_200_50 = ["organisationunitname", "organisationunitcode", "periodname"] + lpvr_cols_200_50
    lpvr_cols_200_50_df = kaletra_df[cols_to_use_lpvr_200_50]

    if "periodname" in default_cols:
        tld_tle_lpv_df = tld_tle_df.merge(kaletra_df,
                                          on=["organisationunitname", "organisationunitcode",
                                              "periodname"])
    else:
        tld_tle_lpv_df = tld_tle_df.merge(kaletra_df,
                                          on=["organisationunitname", "organisationunitcode"])
    #########################################
    # MERGE NON IN TLD
    #########################################

    if "periodname" in default_cols:
        tld_tle_lpv_dtg10_df = tld_tle_lpv_df.merge(non_tld_in_dtg_df,
                                                    on=["organisationunitname", "organisationunitcode",
                                                        "periodname"])
    else:
        tld_tle_lpv_dtg10_df = tld_tle_lpv_df.merge(non_tld_in_dtg_df,
                                                    on=["organisationunitname", "organisationunitcode"])

    nvp_df, nevirapine_df, non_nevirapine_in_nvp_df = make_dfs(df1, nvp_cols, "NVP", default_cols)
    adult_nvp_cols = [col for col in nevirapine_df.columns if 'Adult' in col and "/NVP)" in col]
    adult_nvp200_cols = [col for col in nevirapine_df.columns if 'Adult' in col and "(NVP)" in col]

    paeds_nvp_cols = [col for col in nevirapine_df.columns if "paediatric" in col.lower() and "10mg/ml" not in col]
    paeds_azt3tcnvp_cols = [col for col in nevirapine_df.columns if
                            "/NVP)" in col and "Paediatric" in col]

    paeds_nvp = nevirapine_df[default_cols + paeds_nvp_cols]
    othercolumns = paeds_nvp.columns[3:]
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
    missing = [x for x in missing if "NVP" not in x and "(EFV)" not in x]

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
    missing = [x for x in missing if "(EFV)" not in x and "(TDF)" not in x]

    other_adult_df = dispensed_df[default_cols + missing].fillna(0)

    other_adult_df = other_adult_df.merge(lpvr_cols_200_50_df, on=[
        "organisationunitname",
        "organisationunitcode",
        "periodname"])

    cols_to_use_dtg_50 = ["organisationunitname", "organisationunitcode", "periodname"] + dtg_50_cols
    cols_to_use_dtg_50_df = dtg_df[cols_to_use_dtg_50]

    other_adult_df = other_adult_df.merge(cols_to_use_dtg_50_df, on=[
        "organisationunitname",
        "organisationunitcode",
        "periodname"])

    # Drop columns containing the substring 'FTC' and '3TC/3TC
    substring_to_drop = 'FTC'
    filtered_df = other_adult_df.filter(like=substring_to_drop, axis=1)
    columns_to_drop = filtered_df.columns
    other_adult_df.drop(columns=columns_to_drop, inplace=True)

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
    sc_arvdisp_cols = {"MoH 730B Revision 2017 Adult preparations Zidovudine/Lamivudine/Nevirapine (AZT/3TC/NVP) FDC ("
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
                       "MoH 730B Revision 2017 Adult preparations Lopinavir/ritonavir (LPV/r) 200/50mg Tablets 120s "
                       "Total Quantity issued this month": "LPV/r 200/50",
                       "MoH 730B Revision 2017 Paediatric preparations Lopinavir/ritonavir (LPV/r) 40/10mg Caps 120s "
                       "Total Quantity issued this month": "LPV/r 40/10 Caps 120s"
                       }
    sc_curr_cols = {
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
        "MoH 730B Revision 2017 Adult preparations Lopinavir/ritonavir (LPV/r) 200/50mg Tablets 120s End of "
        "Month Physical Stock Count": "LPV/r 200/50",
        "MoH 730B Revision 2017 Paediatric preparations Lopinavir/ritonavir (LPV/r) 40/10mg Caps 120s "
        "End of Month Physical Stock Count": "LPV/r 40/10 Caps 120s"
    }
    if len(dispensed_cols) > 0:
        tld_tle_lpv_dtg10_nvp_others_df = tld_tle_lpv_dtg10_nvp_others_df.rename(columns=sc_arvdisp_cols)

    elif len(end_of_months_cols) > 0:
        tld_tle_lpv_dtg10_nvp_others_df = tld_tle_lpv_dtg10_nvp_others_df.rename(columns=sc_curr_cols)
    # drop DTG 10MGS
    tld_tle_lpv_dtg10_nvp_others_df = tld_tle_lpv_dtg10_nvp_others_df.drop(["DTG 50"], axis=1)
    cols_to_drop = [col for col in tld_tle_lpv_dtg10_nvp_others_df.columns if
                    "moh 730b revision" in col.lower()]
    tld_tle_lpv_dtg10_nvp_others_df = tld_tle_lpv_dtg10_nvp_others_df.drop(cols_to_drop, axis=1)

    if "periodname" in default_cols:
        final_df = tld_tle_lpv_dtg10_nvp_others_df.merge(df, left_on="organisationunitcode",
                                                         right_on="MFL Code", how="left")
    else:
        final_df = tld_tle_lpv_dtg10_nvp_others_df.merge(df, left_on="organisationunitcode",
                                                         right_on="MFL Code")
    final_df['MFL Code'] = final_df['MFL Code'].astype(str)
    final_df.loc['Total'] = final_df.sum(numeric_only=True)
    final_df.loc['Total'] = final_df.loc['Total'].fillna("")

    #####################################################
    # REPORTING ERRORS
    #####################################################
    reporting_errors_df = process_reporting_errors(dispensed_df, tld_180s_df, default_cols, dispensed_cols,
                                                   end_of_months_cols, sc_arvdisp_cols, sc_curr_cols)

    reporting_error_filename = f"{filename}_reporting_errors"
    request.session['reporting_errors'] = reporting_errors_df.to_dict()

    if "periodname" in default_cols:
        try:
            final_df = final_df[
                ['County', 'Health Subcounty', 'Subcounty', 'organisationunitname', 'MFL Code',
                 'Hub(1,2,3 o 4)', "periodname",
                 'TLD 30s', 'TLD 90s', 'TLD 180s',
                 'TL_400 30', 'TLE_400 90s', 'TLE_600 30s',
                 "LPV/r 40/10", "LPV/r 100/25", 'DTG 10', 'NVP 200', 'NVP (Pediatric) bottles',
                 'Other (Adult) bottles', 'Other (Pediatric) bottles', "CTX 960", "CTX 240mg/5ml",
                 'AZT/3TC/NVP (Adult) bottles', '3HP 300/300',
                 'M&E Mentor/SI associate',
                 'M&E Assistant', 'Care & Treatment(Yes/No)', 'HTS(Yes/No)',
                 'VMMC(Yes/No)', 'Key Pop(Yes/No)', 'Faclity Type',
                 'Category (HVF/MVF/LVF)', 'EMR']]

        except KeyError as e:
            missing_columns = [col.replace("'", "") for col in
                               str(e).split("[")[1].split("]")[0].split(",")]
            # Remove white spaces from column names
            missing_columns = [col.strip() for col in missing_columns]
            for col in missing_columns:
                final_df[col] = 0
            final_df = final_df[
                ['County', 'Health Subcounty', 'Subcounty', 'organisationunitname', 'MFL Code',
                 'Hub(1,2,3 o 4)', "periodname",
                 'TLD 30s', 'TLD 90s', 'TLD 180s',
                 'TL_400 30', 'TLE_400 90s', 'TLE_600 30s',
                 "LPV/r 40/10", "LPV/r 100/25", 'DTG 10', 'NVP 200', 'NVP (Pediatric) bottles',
                 'Other (Adult) bottles', 'Other (Pediatric) bottles', "CTX 960", "CTX 240mg/5ml",
                 'AZT/3TC/NVP (Adult) bottles', '3HP 300/300',
                 'M&E Mentor/SI associate',
                 'M&E Assistant', 'Care & Treatment(Yes/No)', 'HTS(Yes/No)',
                 'VMMC(Yes/No)', 'Key Pop(Yes/No)', 'Faclity Type',
                 'Category (HVF/MVF/LVF)', 'EMR']]
    else:
        try:
            final_df = final_df[
                ['County', 'Health Subcounty', 'Subcounty', 'organisationunitname', 'MFL Code',
                 'Hub(1,2,3 o 4)',
                 'TLD 30s', 'TLD 90s', 'TLD 180s',
                 'TL_400 30', 'TLE_400 90s', 'TLE_600 30s',
                 "LPV/r 40/10", "LPV/r 100/25", 'DTG 10', 'NVP 200', 'NVP (Pediatric) bottles',
                 'Other (Adult) bottles', 'Other (Pediatric) bottles', "CTX 960", "CTX 240mg/5ml",
                 'AZT/3TC/NVP (Adult) bottles', '3HP 300/300',
                 'M&E Mentor/SI associate', 'M&E Assistant',
                 'Care & Treatment(Yes/No)', 'HTS(Yes/No)', 'VMMC(Yes/No)', 'Key Pop(Yes/No)',
                 'Faclity Type', 'Category (HVF/MVF/LVF)'
                    , 'EMR']]
        except KeyError as e:
            missing_columns = [col.replace("'", "") for col in
                               str(e).split("[")[1].split("]")[0].split(",")]
            # Remove white spaces from column names
            missing_columns = [col.strip() for col in missing_columns]
            for col in missing_columns:
                final_df[col] = 0
            final_df = final_df[
                ['County', 'Health Subcounty', 'Subcounty', 'organisationunitname', 'MFL Code',
                 'Hub(1,2,3 o 4)',
                 'TLD 30s', 'TLD 90s', 'TLD 180s',
                 'TL_400 30', 'TLE_400 90s', 'TLE_600 30s',
                 "LPV/r 40/10", "LPV/r 100/25", 'DTG 10', 'NVP 200', 'NVP (Pediatric) bottles',
                 'Other (Adult) bottles', 'Other (Pediatric) bottles', "CTX 960", "CTX 240mg/5ml",
                 'AZT/3TC/NVP (Adult) bottles', '3HP 300/300',
                 'M&E Assistant', 'Care & Treatment(Yes/No)', 'HTS(Yes/No)',
                 'VMMC(Yes/No)', 'Key Pop(Yes/No)', 'Faclity Type',
                 'Category (HVF/MVF/LVF)', 'EMR']]

    return final_df, filename, other_adult_df_file, adult_others_filename, paeds_others_filename, \
        other_paeds_bottles_df_file, reporting_errors_df, reporting_error_filename


@login_required(login_url='login')
def pharmacy(request):
    final_df = pd.DataFrame()
    filename = None
    other_adult_df_file = pd.DataFrame()
    adult_others_filename = None
    paeds_others_filename = None
    reporting_error_filename = None
    dictionary = None
    other_paeds_bottles_df_file = pd.DataFrame()
    reporting_errors_df = pd.DataFrame()
    form = FileUploadForm(request.POST or None)
    datasets = ["Total Quantity issued this month <strong>or</strong>", "End of Month Physical Stock Count"]
    dqa_type = "sc_curr_arvdisp"
    report_name = "ARV Dispensing and Stock Availability Analysis for FYJ-Supported Facilities"
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
                    expected_cols = [col for col in df1.columns if "total quantity issued this month" in col.lower() or
                                     "end of month physical stock count" in col.lower()]
                    if len(expected_cols) >= 1:
                        # Read data from FYJHealthFacility model into a pandas DataFrame
                        qs = FYJHealthFacility.objects.all()
                        df = pd.DataFrame.from_records(qs.values())

                        df = df.rename(columns={
                            "mfl_code": "MFL Code", "county": "County", 'health_subcounty': 'Health Subcounty',
                            'subcounty': 'Subcounty', 'hub': 'Hub(1,2,3 o 4)',
                            'm_and_e_mentor': 'M&E Mentor/SI associate',
                            'm_and_e_assistant': 'M&E Assistant', 'care_and_treatment': 'Care & Treatment(Yes/No)',
                            'hts': 'HTS(Yes/No)', 'vmmc': 'VMMC(Yes/No)', 'key_pop': 'Key Pop(Yes/No)',
                            'facility_type': 'Faclity Type', 'category': 'Category (HVF/MVF/LVF)', 'emr': 'EMR'
                        })
                        if df.shape[0] > 0 and df1.shape[0] > 0:
                            final_df, filename, other_adult_df_file, adult_others_filename, paeds_others_filename, \
                                other_paeds_bottles_df_file, reporting_errors_df, reporting_error_filename = analyse_pharmacy_data(
                                request, df,
                                df1)
                    else:
                        message = f"Please generate and upload either the Total Quantity issued this month or End of Month " \
                                  f"Physical Stock Count CSV file from <a href='{url}'>KHIS's website</a>."
                        messages.success(request, message)
                else:
                    message = f"Please generate and upload either the Total Quantity issued this month or End of Month " \
                              f"Physical Stock Count CSV file from <a href='{url}'>KHIS's website</a>."
                    messages.success(request, message)
                    return redirect('load_data_pharmacy')
            else:
                message = f"Please generate and upload either the Total Quantity issued this month or End of Month " \
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
                "paeds_others_filename": paeds_others_filename, "reporting_error_filename": reporting_error_filename,
                "other_paeds_bottles_df_file": other_paeds_bottles_df_file,
                "reporting_errors_df": reporting_errors_df,
                "form": form, "datasets": datasets, "dqa_type": dqa_type, "report_name": report_name
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
        "paeds_others_filename": paeds_others_filename, "reporting_error_filename": reporting_error_filename,
        "other_paeds_bottles_df_file": other_paeds_bottles_df_file,
        "reporting_errors_df": reporting_errors_df,
        "form": form, "datasets": datasets, "dqa_type": dqa_type, "report_name": report_name
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


# def time_taken(start_time, title):
#     print(f"{title}, it took (hh:mm:ss.ms) {datetime.now() - start_time}")


def generate_tat_report(df, groupby, starting_date, last_date, col_name):
    # Check if last_date is less than starting_date and assign starting_date to last_date in such cases
    df[last_date] = df[[last_date, starting_date]].max(axis=1)

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
        max_length = len(list(max_df[text].unique()))
        max_patient_number = sorted(list(max_df[text].unique()))
        #         max_patient_number = ', '.join(sorted(list(max_df['Patient CCC No'].unique())))

        min_df = unit_df[unit_df[col_name] == min_sample_tat]
        min_patient_number = ', '.join(sorted(list(min_df[text].unique())))
        outliers_patient_number = ', '.join(sorted(list(outliers[text].unique())))
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
        hubs_collect_dispatch_tat.drop(columns=["Facility Code"], inplace=True)

    hubs_collect_dispatch_tat = hubs_collect_dispatch_tat.loc[
        hubs_collect_dispatch_tat[report_type] != ""]

    expected_columns = [col for col in hubs_collect_dispatch_tat.columns if re.match(r'[A-Za-z]{3}-\d{4}', col)]
    hubs_collect_dispatch_tat = hubs_collect_dispatch_tat[
        [hubs_collect_dispatch_tat.columns[0]] + expected_columns].copy()

    hubs_collect_dispatch_tat['TAT type'] = "collection to dispatch"
    return hubs_collect_dispatch_tat


def prepare_collect_receipt_df(hub_monthly_collect_receipt_tat, report_type):
    if "Facility Code" in hub_monthly_collect_receipt_tat.columns:
        hub_monthly_collect_receipt_tat.drop(columns=["Facility Code"], inplace=True)

    hub_monthly_collect_receipt_tat = hub_monthly_collect_receipt_tat.loc[
        hub_monthly_collect_receipt_tat[report_type] != ""]

    expected_columns = [col for col in hub_monthly_collect_receipt_tat.columns if re.match(r'[A-Za-z]{3}-\d{4}', col)]
    hub_monthly_collect_receipt_tat = hub_monthly_collect_receipt_tat[
        [hub_monthly_collect_receipt_tat.columns[0]] + expected_columns].copy()

    hub_monthly_collect_receipt_tat['TAT type'] = "collection to receipt"
    return hub_monthly_collect_receipt_tat


def visualize_tat_type(hub_df, viz_name, target_text):
    expected_columns = [col for col in hub_df.columns if re.match(r'[A-Za-z]{3}-\d{4}', col)]
    hub_df = pd.melt(hub_df, id_vars=[viz_name, 'TAT type'], value_vars=expected_columns,
                     var_name='Month_Year', value_name='TAT (mean)')
    hub_df = hub_df[hub_df['Month_Year'] != "Facility Code"]
    a = hub_df.groupby([viz_name, 'Month_Year', 'TAT type']).sum(numeric_only=True).reset_index()

    # Order dfs based on TAT mean of collection to dispatch
    ordered_dfs = []
    for hub in hub_df[viz_name].unique():
        hub_specific_df = a[(a[viz_name] == hub) & (~a["Month_Year"].str.contains("tat", case=False))]

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
        hub_specific_df['year'] = hub_specific_df['month_year'].dt.year
        hub_specific_df = hub_specific_df.sort_values('month_year')
        # pivot the data to get separate columns for each TAT type
        pivoted_df = hub_specific_df.pivot(index='month_year', columns='TAT type', values='TAT (mean)').reset_index()
        earliest_year = min(hub_specific_df['year'])
        fy_split = pd.to_datetime(f"{earliest_year}-10-01", format='%Y-%m-%d')

        earliest_year = int(str(earliest_year)[-2:])
        following_year = max(hub_specific_df['year'])
        following_year = int(str(following_year)[-2:])

        fy23_corr = pivoted_df[pivoted_df['month_year'] >= fy_split]
        fy22_corr = pivoted_df[pivoted_df['month_year'] < fy_split]

        # calculate the correlation coefficient
        # correlation = round(pivoted_df['collection to dispatch'].corr(pivoted_df['collection to receipt']), 1)
        fy23_correlation = round(fy23_corr["collection to dispatch"].corr(fy23_corr["collection to receipt"]), 1)
        fy22_correlation = round(fy22_corr["collection to dispatch"].corr(fy22_corr["collection to receipt"]), 1)
        max_value = max(pivoted_df['collection to dispatch'])
        min_value = min(pivoted_df['collection to receipt'])
        # corr_text = f"Correlation between C-R and C-D: {correlation}"

        fy23_corr_text = f"FY{following_year} correlation between C-R and C-D : {fy23_correlation}"
        fy22_corr_text = f"FY{earliest_year} correlation between C-R and C-D : {fy22_correlation}"

        fy23 = hub_specific_df[
            (hub_specific_df['month_year'] >= fy_split) & (hub_specific_df['TAT type'] == "collection to dispatch")]
        fy22 = hub_specific_df[
            (hub_specific_df['month_year'] < fy_split) & (hub_specific_df['TAT type'] == "collection to dispatch")]
        try:
            mean_sample_tested_fy23 = round(sum(fy23["TAT (mean)"]) / len(fy23["TAT (mean)"]), 1)
            median_sample_tested_fy23 = round(fy23["TAT (mean)"].median(), 1)
        except ZeroDivisionError:
            mean_sample_tested_fy23 = 0
            median_sample_tested_fy23 = 0
        try:
            mean_sample_tested_fy22 = round(sum(fy22["TAT (mean)"]) / len(fy22["TAT (mean)"]), 1)
            median_sample_tested_fy22 = round(fy22["TAT (mean)"].median(), 1)
        except ZeroDivisionError:
            mean_sample_tested_fy22 = 0
            median_sample_tested_fy22 = 0

        # try:
        #     mean_sample_tested = int(sum(hub_specific_df["TAT (mean)"]) / len(hub_specific_df["TAT (mean)"]))
        #     median_sample_tested = int(hub_specific_df["TAT (mean)"].median())
        # except ZeroDivisionError:
        #     mean_sample_tested = 0
        #     median_sample_tested = 0
        if target_text == "VL":
            y = 14
        else:
            y = 10

        title = f"Mean {target_text} TAT Trend {hub.title()} {viz_name}" if "hub" not in hub.lower() else f"Mean {target_text} TAT Trend {hub.title()}"
        fig = px.line(hub_specific_df, x='month_year', y="TAT (mean)", text='TAT (mean)', color="TAT type",
                      title=title + f"  Target : <={y}",
                      height=450)
        fig.update_traces(textposition='top center')

        # fig.add_shape(type='line', x0=hub_specific_df['month_year'].min(), y0=y, x1=hub_specific_df['month_year'].max(),
        #               y1=y,
        #               line=dict(color='grey', width=2, dash='solid'))
        #
        # fig.add_annotation(x=hub_specific_df['month_year'].max(), y=y,
        #                    text=f"FYJ {target_text} TAT Target (<={y})",
        #                    showarrow=True, arrowhead=1,
        #                    font=dict(size=8, color='grey'))
        if fy23.shape[0] > 0:
            fig.add_shape(type='line', x0=fy23['month_year'].max(), y0=mean_sample_tested_fy23,
                          x1=fy23['month_year'].min(),
                          y1=mean_sample_tested_fy23,
                          line=dict(color='red', width=2, dash='dot'))

            fig.add_annotation(x=fy23['month_year'].max(), y=mean_sample_tested_fy23,
                               text=f"FY{following_year} Mean monthly TAT (C-D) {mean_sample_tested_fy23}",
                               showarrow=True, arrowhead=1,
                               font=dict(size=8, color='red'))
            fig.add_shape(type='line', x0=fy23['month_year'].min(), y0=median_sample_tested_fy23,
                          x1=fy23['month_year'].max(),
                          y1=median_sample_tested_fy23,
                          line=dict(color='black', width=2, dash='dot'))

            fig.add_annotation(x=fy23['month_year'].min(), y=median_sample_tested_fy23,
                               text=f"FY{following_year} Median monthly TAT (C-D) {median_sample_tested_fy23}",
                               showarrow=True, arrowhead=1,
                               font=dict(size=8, color='black'))
            fig.add_annotation(x=fy23['month_year'].max(), y=max_value,
                               text=fy23_corr_text,
                               showarrow=False,
                               font=dict(size=8, color='black'))
        if fy22.shape[0] > 0:
            fig.add_shape(type='line', x0=fy22['month_year'].max(), y0=mean_sample_tested_fy22,
                          x1=fy22['month_year'].min(),
                          y1=mean_sample_tested_fy22,
                          line=dict(color='red', width=2, dash='dot'))

            fig.add_annotation(x=fy22['month_year'].max(), y=mean_sample_tested_fy22,
                               text=f"FY{earliest_year} Mean monthly TAT (C-D) {mean_sample_tested_fy22}",
                               showarrow=True, arrowhead=1,
                               font=dict(size=8, color='red'))
            fig.add_shape(type='line', x0=fy22['month_year'].min(), y0=median_sample_tested_fy22,
                          x1=fy22['month_year'].max(),
                          y1=median_sample_tested_fy22,
                          line=dict(color='black', width=2, dash='dot'))

            fig.add_annotation(x=fy22['month_year'].min(), y=median_sample_tested_fy22,
                               text=f"FY{earliest_year} Median monthly TAT (C-D) {median_sample_tested_fy22}",
                               showarrow=True, arrowhead=1,
                               font=dict(size=8, color='black'))
            fig.add_annotation(x=fy22['month_year'].min(), y=min_value,
                               text=fy22_corr_text,
                               showarrow=False,
                               font=dict(size=8, color='black'))
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
def transform_data(df, df1, from_date, to_date):
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

    df = df.loc[(df['Date Collected'].dt.date >= from_date) &
                (df['Date Collected'].dt.date <= to_date)]

    df['month_year'] = pd.to_datetime(df['Date Collected']).dt.strftime('%b-%Y')
    df.insert(0, "Program", "FYJ")
    ########################################
    # Collection and Receipt
    ########################################
    if "Sample ID" in df.columns:
        text = "Sample ID"
    else:
        text = "Patient CCC No"
    df[text] = df[text].astype(str)

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

    program_collect_receipt_tat, df_result = generate_tat_report(
        df, 'Program', "Date Collected", "Date Received",
        "Collected to Received")
    program_c_r_filename = f"program_collect_receipt_tat_{target_text}"
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

    program_collect_dispatch_tat, df_result = generate_tat_report(
        df, "Program", "Date Collected", "Date Dispatched",
        "Collection to Dispatch (TAT days)")
    program_c_d_filename = f"program_collect_dispatch_tat_{target_text}"
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
    ################################################
    # Program
    ################################################
    program_collect_receipt_tat_trend = prepare_collect_receipt_df(
        program_collect_receipt_tat, "Program")

    program_collect_dispatch_tat_trend = prepare_collect_dispatch_df(
        program_collect_dispatch_tat, "Program")
    program_df = pd.concat(
        [program_collect_receipt_tat_trend,
         program_collect_dispatch_tat_trend])

    if "County" in program_df.columns:
        del program_df['County']

    program_viz_df = program_df.groupby(['Program', 'TAT type']).sum(numeric_only=True).reset_index()
    fyj_viz = visualize_tat_type(program_viz_df, "Program", target_text)

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
        county_viz, sub_county_viz, target_text, fyj_viz, program_c_d_filename, program_c_r_filename, \
        program_collect_dispatch_tat, program_collect_receipt_tat


@login_required(login_url='login')
def tat(request):
    facilities_collect_receipt_tat = pd.DataFrame()
    facilities_collect_dispatch_tat = pd.DataFrame()
    sub_counties_collect_receipt_tat = pd.DataFrame()
    sub_counties_collect_dispatch_tat = pd.DataFrame()
    hubs_collect_receipt_tat = pd.DataFrame()
    hubs_collect_dispatch_tat = pd.DataFrame()
    counties_collect_receipt_tat = pd.DataFrame()
    counties_collect_dispatch_tat = pd.DataFrame()
    program_collect_dispatch_tat = pd.DataFrame()
    program_collect_receipt_tat = pd.DataFrame()
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
    program_c_d_filename = None
    program_c_r_filename = None
    date_picker_form = DateFilterForm(request.POST or None)
    form = FileUploadForm(request.POST or None)
    hub_viz = None
    fyj_viz = None
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
                                    from_date = date_picker_form.cleaned_data['from_date']
                                    to_date = date_picker_form.cleaned_data['to_date']
                                    if to_date <= from_date:
                                        messages.error(request,
                                                       f"The selected end date ({to_date}) should be later than the start date "
                                                       f"({from_date}). Please choose valid dates.")
                                        return redirect('viral_load')
                                    else:

                                        facilities_collect_receipt_tat, facility_c_r_filename, \
                                            sub_counties_collect_receipt_tat, subcounty_c_r_filename, \
                                            hubs_collect_receipt_tat, hub_c_r_filename, \
                                            counties_collect_receipt_tat, county_c_r_filename, \
                                            facilities_collect_dispatch_tat, facility_c_d_filename, \
                                            sub_counties_collect_dispatch_tat, subcounty_c_d_filename, \
                                            hubs_collect_dispatch_tat, hub_c_d_filename, \
                                            counties_collect_dispatch_tat, county_c_d_filename, hub_viz, \
                                            county_viz, sub_county_viz, target_text, fyj_viz, program_c_d_filename, \
                                            program_c_r_filename, program_collect_dispatch_tat, \
                                            program_collect_receipt_tat = transform_data(df, df1, from_date, to_date)
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
                "program_c_d_filename": program_c_d_filename,
                "program_c_r_filename": program_c_r_filename,
                "hub_viz": hub_viz,
                "county_viz": county_viz, "fyj_viz": fyj_viz,
                "sub_county_viz": sub_county_viz, "dqa_type": "tat",

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
    request.session['program_collect_receipt_tat'] = program_collect_receipt_tat.to_dict()
    request.session['program_collect_dispatch_tat'] = program_collect_dispatch_tat.to_dict()

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
        "program_c_d_filename": program_c_d_filename,
        "program_c_r_filename": program_c_r_filename,
        "hub_viz": hub_viz,
        "county_viz": county_viz, "fyj_viz": fyj_viz,
        "sub_county_viz": sub_county_viz, "dqa_type": "tat",
    }
    return render(request, 'data_analysis/tat.html', context)


def fmarp_trend(reporting_rates, x_axis, y_axis, title=None, color=None):
    fig = px.bar(reporting_rates, x=x_axis, y=y_axis, text=y_axis, height=450,
                 barmode="group", color=color,
                 title=title
                 )
    fig.update_traces(textposition='outside')
    fig.update_layout(legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    ))
    fig.update_layout(
        xaxis=dict(
            tickfont=dict(
                size=8
            ),
            title_font=dict(
                size=10
            )
        ),
        yaxis=dict(
            title_font=dict(
                size=8
            )
        ),
        legend=dict(
            font=dict(
                size=10
            )
        ),
        title=dict(
            font=dict(
                size=14
            )
        )
    )
    if "missing" not in title.lower():
        fig.update_yaxes(range=[0, 110])
    else:
        fig.update_yaxes(range=[0, reporting_rates[y_axis].max() + 3])
    return plot(fig, include_plotlyjs=False, output_type="div")


def hvl_trend(reporting_rates, x_axis, y_axis, title=None, color=None):
    fig = px.bar(reporting_rates, x=x_axis, y=y_axis, text=y_axis, height=480,
                 color=color,
                 title=title
                 )
    fig.update_traces(textposition='outside')
    fig.update_layout(legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    ))
    fig.update_layout(
        xaxis=dict(
            tickfont=dict(
                size=8
            ),
            title_font=dict(
                size=10
            )
        ),
        yaxis=dict(
            title_font=dict(
                size=8
            )
        ),
        legend=dict(
            font=dict(
                size=10
            )
        ),
        title=dict(
            font=dict(
                size=14
            )
        )
    )
    # if "missing" not in title.lower():
    #     fig.update_yaxes(range=[0, 110])
    # else:
    #     fig.update_yaxes(range=[0, reporting_rates[y_axis].max() + 3])
    return plot(fig, include_plotlyjs=False, output_type="div")


def merge_county_program_df(df, df1):
    df = df.merge(df1, left_on="organisationunitcode", right_on="MFL Code", how="left")
    df = df[['County',
             'Subcounty', 'organisationunitname', 'MFL Code',
             'periodid', 'periodname',
             'F-MAPS Revision 2019 Reporting rate (%)']]
    df = df.rename(columns={"organisationunitname": "facility"})
    df = df.rename(columns={"periodname": "month/year"})
    return df


def make_region_specific_df(nairobi_all, name):
    nairobi_all = nairobi_all.rename(columns={"periodname": "month/year"})
    nairobi_all['date'] = pd.to_datetime(nairobi_all['month/year'])
    nairobi_all_rate = nairobi_all.groupby(['month/year', 'date']).mean(numeric_only=True)[
        'F-MAPS Revision 2019 Reporting rate (%)'].reset_index().sort_values('date')
    nairobi_all_rate['F-MAPS Revision 2019 Reporting rate (%)'] = round(
        nairobi_all_rate['F-MAPS Revision 2019 Reporting rate (%)'], 1)
    nairobi_all_rate.insert(0, "region", name)
    average_reporting_rate = round(nairobi_all_rate['F-MAPS Revision 2019 Reporting rate (%)'].mean(), 1)

    return nairobi_all_rate, average_reporting_rate


def make_county_specific_charts(df, nairobi_facitities_mfl_code, county):
    nairobi_all = df[df['orgunitlevel2'] == f'{county} County']
    nairobi_all_rate, nairobi_average_reporting_rate = make_region_specific_df(nairobi_all, county)
    fyj_nairobi_facilities = nairobi_all[nairobi_all['organisationunitcode'].isin(nairobi_facitities_mfl_code)]
    fyj_nairobi_facilities_rate, fyj_nrb_average_reporting_rate = make_region_specific_df(fyj_nairobi_facilities,
                                                                                          "FYJ")
    reporting_rates = pd.concat([fyj_nairobi_facilities_rate, nairobi_all_rate])
    fig = fmarp_trend(reporting_rates, "month/year", "F-MAPS Revision 2019 Reporting rate (%)",
                      title=f'F-MAPS reporting rate trends. FYJ {county} Average reporting rate {fyj_nrb_average_reporting_rate}%  '
                            f'{county} county Average reporting rate {nairobi_average_reporting_rate}%',
                      color="region")
    return fig


def fmarp_line_trend(reporting_rates, x_axis, y_axis, title=None, color=None):
    fig = px.line(reporting_rates, x=x_axis, y=y_axis, text=y_axis, height=500,
                  #              barmode="group",
                  color=color,
                  title=title
                  )
    #     fig.update_traces(textposition='outside')
    fig.update_layout(legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    ))
    #     fig.update_yaxes(rangemode="tozero")
    #     fig.update_yaxes(range=[70, 100])
    fig.update_layout(
        xaxis=dict(
            tickfont=dict(
                size=8
            ),
            title_font=dict(
                size=10
            )
        ),
        yaxis=dict(
            title_font=dict(
                size=8
            )
        ),
        legend=dict(
            font=dict(
                size=10
            )
        ),
        title=dict(
            font=dict(
                size=14
            )
        )
    )

    fig.update_traces(textposition='top center')
    return plot(fig, include_plotlyjs=False, output_type="div")


def make_charts(nairobi_730b, title):
    nairobi_730b.columns = nairobi_730b.columns.str.replace("'", "_")
    rates_cols = list(nairobi_730b.columns[-3:-1])
    overall_df = nairobi_730b.groupby(['month/year', 'date']).mean(numeric_only=True)[
        rates_cols].reset_index().sort_values('date')
    overall_df[rates_cols[0]] = round(overall_df[rates_cols[0]], 1)
    overall_df[rates_cols[1]] = round(overall_df[rates_cols[1]], 1)

    overall_df.insert(0, "region", f"{nairobi_730b['orgunitlevel2'].unique()[0]}")
    overall_df.reset_index(drop=True, inplace=True)
    a = pd.melt(overall_df, id_vars=['region', 'month/year', 'date'],
                value_vars=rates_cols,
                var_name='report', value_name='%')
    fig = fmarp_line_trend(a, "month/year", "%",
                           title=f'{title} Reporting rate vs Reporting rate on time',
                           color='report')
    return fig, overall_df


def transform_make_charts(all_facilities, cols_730b, name, fyj_facility_mfl_code):
    default_cols = ["orgunitlevel2", 'facility', 'organisationunitcode', "month/year"]
    all_facilities_730b = all_facilities[default_cols + cols_730b]
    all_facilities_730b['date'] = pd.to_datetime(all_facilities_730b['month/year'])
    all_facilities_730b.columns = all_facilities_730b.columns.str.replace("'", "_")
    rates_cols = list(all_facilities_730b.columns[-3:-1])
    nairobi_730b = all_facilities_730b[all_facilities_730b['orgunitlevel2'] == "Nairobi County"]
    kajiado_730b = all_facilities_730b[all_facilities_730b['orgunitlevel2'] == "Kajiado County"]
    nairobi_730b_fig, nairobi_730b_overall = make_charts(nairobi_730b, "Nairobi county")
    kajiado_730b_fig, kajiado_730b_overall = make_charts(kajiado_730b, "Kajiado county")

    all_facilities_730b = convert_mfl_code_to_int(all_facilities_730b)
    program_facilities = all_facilities_730b[all_facilities_730b['organisationunitcode'].isin(fyj_facility_mfl_code)]
    nairobi_program_facilities_730b = program_facilities[program_facilities['orgunitlevel2'] == "Nairobi County"]
    kajiado_program_facilities_730b = program_facilities[program_facilities['orgunitlevel2'] == "Kajiado County"]
    nairobi_program_facilities_730b_fig, fyj_nairobi_730 = make_charts(nairobi_program_facilities_730b, "FYJ Nairobi")
    kajiado_program_facilities_730b_fig, fyj_kajiado_730 = make_charts(kajiado_program_facilities_730b, "FYJ Kajiado")
    program_facilities_730b_fig, fyj_730b = make_charts(program_facilities, "FYJ")
    return nairobi_730b_fig, kajiado_730b_fig, nairobi_program_facilities_730b_fig, kajiado_program_facilities_730b_fig, \
        nairobi_730b_overall, kajiado_730b_overall, fyj_nairobi_730, fyj_kajiado_730, program_facilities_730b_fig, fyj_730b


def prepare_program_facilities_df(df1, fyj_facility_mfl_code):
    df1 = df1[~df1['facility'].str.contains("adventist centre", case=False)]

    # Add Hope med C MFL CODE
    df1.loc[df1['facility'] == "Hope Med C", 'organisationunitcode'] = 19278
    # st francis
    # df1.loc[df1['organisationunitcode'] == 13202, 'organisationunitcode'] = 17943
    df1.loc[df1['facility'].str.contains("st francis comm", case=False), 'organisationunitcode'] = 17943

    # adventist
    # df1.loc[df1['organisationunitcode'] == 23385, 'organisationunitcode'] = 18535
    df1.loc[df1['facility'].str.contains("better living", case=False), 'organisationunitcode'] = 18535
    df1.loc[df1['facility'].str.contains("better living",
                                         case=False),
    'facility'] = "Adventist Centre for Care and Support"

    # illasit
    # df1.loc[df1['organisationunitcode'] == 20372, 'organisationunitcode'] = 14567
    df1.loc[df1['facility'].str.contains("illasit h", case=False), 'organisationunitcode'] = 14567
    # imara
    # df1.loc[df1['organisationunitcode'] == 17685, 'organisationunitcode'] = 12981
    df1.loc[df1['facility'].str.contains("imara health", case=False), 'organisationunitcode'] = 12981
    # mary immaculate
    df1.loc[
        df1['facility'].str.contains("mary immaculate sister", case=False), 'organisationunitcode'] = 13062

    # biafra lion
    df1.loc[
        df1['facility'].str.contains("biafra lion", case=False), 'organisationunitcode'] = 12883

    df1 = df1[~df1['organisationunitcode'].isnull()]
    df1 = convert_mfl_code_to_int(df1)
    df1 = df1[df1['organisationunitcode'].isin(fyj_facility_mfl_code)]
    reporting_rates_cols = [col for col in df1.columns if "Reporting rate" in col]
    default_cols = ["orgunitlevel2", 'facility', 'organisationunitcode', "month/year"]
    df = df1[default_cols + reporting_rates_cols]
    return df


def missing_fcdrr(program_facilities, total_fmaps):
    no_fcdrr = program_facilities[
        (program_facilities['Facility - CDRR Revision 2019 Reporting rate (%)'].isnull())
        | (program_facilities['Facility - CDRR Revision 2019 Reporting rate (%)'] == 0)]
    no_fcdrr_copy = no_fcdrr.copy()
    no_fcdrr = no_fcdrr.groupby(['facility', 'MFL Code', 'month/year']).count()[
        'Facility - CDRR Revision 2019 Reporting rate (%)'].reset_index()

    no_fcdrr_df = no_fcdrr_copy.groupby(['month/year']).count()['facility'].reset_index()
    no_fcdrr_df = no_fcdrr_df.rename(columns={"facility": "facilities"})
    # convert 'month/year' column to datetime format
    no_fcdrr_df['Month/Year'] = pd.to_datetime(no_fcdrr_df['month/year'], format='%B %Y')
    total_fcdrr = sum(no_fcdrr_df['facilities'])

    total = total_fcdrr + total_fmaps
    # sort the DataFrame by 'month/year' column
    no_fcdrr_df = no_fcdrr_df.sort_values(by='Month/Year')
    no_fcdrr_df['report'] = "F-CDRR"
    return no_fcdrr_df, total_fcdrr, no_fcdrr, total


def missing_fmaps(program_facilities):
    no_fmaps = program_facilities[(program_facilities['F-MAPS Revision 2019 Reporting rate (%)'].isnull())
                                  | (program_facilities['F-MAPS Revision 2019 Reporting rate (%)'] == 0)]
    no_fmaps_copy = no_fmaps.copy()
    no_fmaps = no_fmaps.groupby(['facility', 'MFL Code', 'month/year']).count()[
        'F-MAPS Revision 2019 Reporting rate (%)'].reset_index()

    no_fmaps_df = no_fmaps_copy.groupby(['month/year']).count()['facility'].reset_index()
    no_fmaps_df = no_fmaps_df.rename(columns={"facility": "facilities"})
    # convert 'month/year' column to datetime format
    no_fmaps_df['Month/Year'] = pd.to_datetime(no_fmaps_df['month/year'], format='%B %Y')
    total_fmaps = sum(no_fmaps_df['facilities'])
    # sort the DataFrame by 'month/year' column
    no_fmaps_df = no_fmaps_df.sort_values(by='Month/Year')
    no_fmaps_df['report'] = "F-MAPS"
    return no_fmaps_df, no_fmaps, total_fmaps


def convert_and_sort_datetime(df):
    # Convert the "month/year" column to datetime
    df['month/year'] = pd.to_datetime(df['month/year'], format='%B %Y')

    # Sort the DataFrame by the "month/year" column
    df = df.sort_values('month/year')
    return df


def process_facility_data(data, region, col):
    """
    Process facility data for a specific region.

    Args:
        data (pandas.DataFrame): Facility data including the 'month/year' and 'col' columns.
        region (str): The region's name.
        col (str): The name of the column to compute the average.

    Returns:
        Tuple[float, pandas.DataFrame]: A tuple containing the average reporting rate for the region and the processed data.

    The function processes the facility data for the specified region by calculating the average reporting rate and formatting the data.

    Example:
        fyj_kajiado_facilities = pd.DataFrame(...)
        region = "Kajiado"
        col = "your_column_name"
        average_rate, processed_data = process_facility_data(fyj_kajiado_facilities, region, col)
    """
    data['date'] = pd.to_datetime(data['month/year'])
    data_rate = data.groupby(['month/year', 'date']).mean(numeric_only=True)[col].reset_index().sort_values('date')
    data_rate[col] = round(data_rate[col], 1)
    data_rate.insert(0, "region", region)
    average_reporting_rate = round(data_rate[col].mean(), 1)
    return average_reporting_rate, data_rate


def create_counties_reporting_rate(fyj_kajiado_facilities, fyj_nairobi_facilities, col):
    """
    Create a report with average reporting rates for Kajiado and Nairobi counties.

    Args:
        fyj_kajiado_facilities (pandas.DataFrame): Facility data for Kajiado county.
        fyj_nairobi_facilities (pandas.DataFrame): Facility data for Nairobi county.
        col (str): The name of the column to compute the average reporting rate.

    Returns:
        Tuple[float, float, pandas.DataFrame, pandas.DataFrame]:
        A tuple containing the average reporting rates for Nairobi and Kajiado, and the processed data for both counties.

    This function processes facility data for Kajiado and Nairobi counties, calculating the average reporting rates and
    returning the processed data.

    Example:
        fyj_kajiado_facilities = pd.DataFrame(...)
        fyj_nairobi_facilities = pd.DataFrame(...)
        col = "your_column_name"
        nairobi_rate, kajiado_rate, nairobi_data, kajiado_data = create_counties_reporting_rate(
            fyj_kajiado_facilities, fyj_nairobi_facilities, col)
    """
    kajiado_average_reporting_rate, fyj_kajiado_facilities_rate = process_facility_data(fyj_kajiado_facilities,
                                                                                        "Kajiado", col)
    nairobi_average_reporting_rate, fyj_nairobi_facilities_rate = process_facility_data(fyj_nairobi_facilities,
                                                                                        "Nairobi", col)
    return nairobi_average_reporting_rate, kajiado_average_reporting_rate, fyj_nairobi_facilities_rate, fyj_kajiado_facilities_rate


def analyse_fmaps_fcdrr(df, df1):
    all_facilities = df.copy()
    all_facilities = all_facilities.rename(columns={"organisationunitname": "facility"})
    all_facilities = all_facilities.rename(columns={"periodname": "month/year"})

    df1['MFL Code'] = df1['MFL Code'].astype(int)
    df1 = df1[df1['Care & Treatment(Yes/No)'] == "Yes"]
    nairobi_facitities_df = df1[df1['County'] == "Nairobi"]

    kajiado_facitities_df = df1[df1['County'] == 'Kajiado']

    fyj_facility_mfl_code = list(df1['MFL Code'].unique())
    nairobi_facitities_mfl_code = list(nairobi_facitities_df['MFL Code'].unique())
    kajiado_facitities_mfl_code = list(kajiado_facitities_df['MFL Code'].unique())

    df = df.rename(columns={
        "MoH 729B Facility - F'MAPS Revision 2019 - Reporting rate": "F-MAPS Revision 2019 Reporting rate (%)",
        "MoH 730B Facility - CDRR Revision 2019 - Reporting rate": "Facility - CDRR Revision 2019 Reporting rate (%)"})

    df = df[['organisationunitid', 'organisationunitname', 'organisationunitcode', 'orgunitlevel2',
             'organisationunitdescription', 'periodid', 'periodname', 'periodcode',
             'F-MAPS Revision 2019 Reporting rate (%)', "Facility - CDRR Revision 2019 Reporting rate (%)"]]
    # drop the rows containing letters and convert to int
    df = convert_mfl_code_to_int(df)

    all_data = merge_county_program_df(df, df1)
    all_data['date'] = pd.to_datetime(all_data['month/year'])
    # overall
    overall_df = all_data.groupby(['month/year', 'date']).mean(numeric_only=True)[
        'F-MAPS Revision 2019 Reporting rate (%)'].reset_index().sort_values('date')
    overall_df['F-MAPS Revision 2019 Reporting rate (%)'] = round(overall_df['F-MAPS Revision 2019 Reporting rate (%)'],
                                                                  1)
    overall_df.insert(0, "region", "Nairobi/Kajiado counties")
    average_reporting_rate_all = round(overall_df['F-MAPS Revision 2019 Reporting rate (%)'].mean(), 1)
    program_facilities = all_data[all_data['MFL Code'].isin(fyj_facility_mfl_code)]

    fyj_df = prepare_program_facilities_df(all_facilities, fyj_facility_mfl_code)
    cols_730b = sorted([col for col in fyj_df.columns if "730b" in col.lower()])
    cols_729b = sorted([col for col in fyj_df.columns if "729b" in col.lower()])

    nairobi_730b_fig, kajiado_730b_fig, nairobi_program_facilities_730b_fig, kajiado_program_facilities_730b_fig, \
        nairobi_730b_overall, kajiado_730b_overall, fyj_nairobi_730, fyj_kajiado_730, program_facilities_730b_fig, \
        fyj_730b = transform_make_charts(all_facilities, cols_730b, "730b", fyj_facility_mfl_code)
    nairobi_729b_fig, kajiado_729b_fig, nairobi_program_facilities_729b_fig, kajiado_program_facilities_729b_fig, \
        nairobi_729b_overall, kajiado_729b_overall, fyj_nairobi_729b, fyj_kajiado_729b, program_facilities_729b_fig, \
        fyj_729b = transform_make_charts(all_facilities, cols_729b, "729b", fyj_facility_mfl_code)

    program_facilities_rate = program_facilities.groupby(['month/year', 'date']).mean(numeric_only=True)[
        'F-MAPS Revision 2019 Reporting rate (%)'].reset_index().sort_values('date')
    program_facilities_rate['F-MAPS Revision 2019 Reporting rate (%)'] = round(
        program_facilities_rate['F-MAPS Revision 2019 Reporting rate (%)'], 1)
    program_facilities_rate.insert(0, "region", "FYJ")
    average_reporting_rate = round(program_facilities_rate['F-MAPS Revision 2019 Reporting rate (%)'].mean(), 1)

    reporting_rates = pd.concat([overall_df, program_facilities_rate])

    overall_fig = fmarp_trend(reporting_rates, "month/year", "F-MAPS Revision 2019 Reporting rate (%)",
                              title=f'F-MAPS reporting rate trends. FYJ Average reporting rate {average_reporting_rate}% '
                                    f' Overall Average reporting rate {average_reporting_rate_all}%',
                              color='region')
    #######################################
    # Nairobi reporting rate
    #######################################
    county = "Nairobi"
    nairobi_reporting_rate_fig = make_county_specific_charts(df, nairobi_facitities_mfl_code, county)

    #######################################
    # Kajiado reporting rate
    #######################################
    county = "Kajiado"
    kajiado_reporting_rate_fig = make_county_specific_charts(df, kajiado_facitities_mfl_code, county)
    ########################
    # No F-MAPS REPORTING
    ########################
    no_fmaps_df_all, no_fmaps_all, total_fmaps_all = missing_fmaps(all_data)
    no_fmaps_df, no_fmaps, total_fmaps = missing_fmaps(program_facilities)
    #######################################
    # Reporting rate on time FYJ Nairobi and Kajiado
    #######################################
    all_on_time = df.copy()
    all_on_time = all_on_time.rename(columns={"organisationunitname": "facility"})
    all_on_time = all_on_time.rename(columns={"periodname": "month/year"})
    all_on_time = all_on_time.rename(columns={"organisationunitcode": "MFL Code"})
    all_on_time = all_on_time.rename(columns={
        "MoH 730B Facility - CDRR Revision 2019 - Reporting rate on time":
            "Facility - CDRR Revision 2019 Reporting rate (%)"})
    program_facilities = all_on_time[all_on_time['MFL Code'].isin(fyj_facility_mfl_code)]
    # Nairobi vs FYJ
    fyj_nairobi_facilities = program_facilities[program_facilities['MFL Code'].isin(nairobi_facitities_mfl_code)]
    # Kajiado vs FYJ
    fyj_kajiado_facilities = program_facilities[program_facilities['MFL Code'].isin(kajiado_facitities_mfl_code)]
    ################################
    # FYJ F-CDRR TREND
    ################################
    nairobi_average_reporting_rate, kajiado_average_reporting_rate, fyj_nairobi_facilities_rate, \
        fyj_kajiado_facilities_rate = create_counties_reporting_rate(fyj_kajiado_facilities, fyj_nairobi_facilities,
                                                                     'Facility - CDRR Revision 2019 Reporting rate (%)')
    reporting_rates = pd.concat([fyj_nairobi_facilities_rate, fyj_kajiado_facilities_rate])
    fcdrr_fig = fmarp_trend(reporting_rates, "month/year", 'Facility - CDRR Revision 2019 Reporting rate (%)',
                            title=f'F-CDRR reporting rate on time trends. FYJ Kajiado mean :  {kajiado_average_reporting_rate}%   '
                                  f'FYJ Nairobi mean :  {nairobi_average_reporting_rate}%',
                            color="region")
    ################################
    # FYJ F-MAPS TREND
    ################################
    nairobi_average_reporting_rate, kajiado_average_reporting_rate, fyj_nairobi_facilities_rate, \
        fyj_kajiado_facilities_rate = create_counties_reporting_rate(fyj_kajiado_facilities, fyj_nairobi_facilities,
                                                                     'F-MAPS Revision 2019 Reporting rate (%)')
    reporting_rates = pd.concat([fyj_nairobi_facilities_rate, fyj_kajiado_facilities_rate])
    fmaps_fig = fmarp_trend(reporting_rates, "month/year", 'F-MAPS Revision 2019 Reporting rate (%)',
                            title=f'F-MAPS reporting rate on time trends. FYJ Kajiado mean :  {kajiado_average_reporting_rate}%   '
                                  f'FYJ Nairobi mean :  {nairobi_average_reporting_rate}%',
                            color="region")

    ########################
    # No F-CDRR REPORTING
    ########################
    no_fcdrr_df_all, total_fcdrr_all, no_fcdrr_all, total_all = missing_fcdrr(all_on_time, total_fmaps_all)
    no_fcdrr_df, total_fcdrr, no_fcdrr, total = missing_fcdrr(program_facilities, total_fmaps)

    no_reports = pd.concat([no_fcdrr_df, no_fmaps_df])
    no_reports_all = pd.concat([no_fcdrr_df_all, no_fmaps_df_all])

    no_reports = convert_and_sort_datetime(no_reports)
    no_reports_all = convert_and_sort_datetime(no_reports_all)

    try:
        fyj_contribution = round(total / total_all * 100, 1)
    except ZeroDivisionError:
        fyj_contribution = 0

    no_fcdrr_fmaps_fig = fmarp_trend(no_reports, "month/year", 'facilities',
                                     title=f"Monthly Distribution of FYJ Facilities with Missing Reports"
                                           f" N= {total} ({fyj_contribution}% of the missed reports) (FCDRR = {total_fcdrr}, FMAPS = {total_fmaps})",
                                     color='report')
    no_fcdrr_fmaps_fig_all = fmarp_trend(no_reports_all, "month/year", 'facilities',
                                         title=f"Monthly Distribution of All Facilities with Missing Reports"
                                               f" N= {total_all}  (FCDRR = {total_fcdrr_all}, FMAPS = {total_fmaps_all})",
                                         color='report')
    return fcdrr_fig, kajiado_reporting_rate_fig, nairobi_reporting_rate_fig, no_fmaps, no_fcdrr, overall_fig, \
        no_fcdrr_fmaps_fig, nairobi_730b_fig, kajiado_730b_fig, nairobi_program_facilities_730b_fig, \
        kajiado_program_facilities_730b_fig, nairobi_729b_fig, kajiado_729b_fig, nairobi_program_facilities_729b_fig, \
        kajiado_program_facilities_729b_fig, nairobi_730b_overall, kajiado_730b_overall, fyj_nairobi_730, fyj_kajiado_730, \
        nairobi_729b_overall, kajiado_729b_overall, fyj_nairobi_729b, fyj_kajiado_729b, no_fcdrr_fmaps_fig_all, \
        no_fcdrr_all, no_fmaps_all, program_facilities_730b_fig, fyj_730b, program_facilities_729b_fig, fyj_729b, fmaps_fig


@login_required(login_url='login')
def fmaps_reporting_rate(request):
    final_df = pd.DataFrame()
    other_adult_df_file = pd.DataFrame()
    nairobi_reporting_rate_fig = None
    kajiado_reporting_rate_fig = None
    overall_fig = None
    fcdrr_fig = None
    fmaps_fig = None
    no_fcdrr_fmaps_fig = None
    no_fcdrr_fmaps_fig_all = None
    dictionary = None
    no_fmaps = pd.DataFrame()
    no_fmaps_all = pd.DataFrame()
    no_fcdrr = pd.DataFrame()
    no_fcdrr_all = pd.DataFrame()
    other_paeds_bottles_df_file = pd.DataFrame()
    reporting_errors_df = pd.DataFrame()
    form = FileUploadForm(request.POST or None)
    datasets = ["MoH 729B Facility - F'MAPS Revision 2019 - Reporting rate <strong>and</strong>",
                "MoH 729B Facility - F'MAPS Revision 2019 - Reporting rate on time data <strong>and</strong>",
                "MoH 730B Facility - CDRR Revision 2019 - Reporting rate <strong>and</strong>",
                "MoH 730B Facility - CDRR Revision 2019 - Reporting rate on time",
                ]
    dqa_type = "reporting_rate_fmaps_fcdrr"
    report_name = "Facility Reporting Metrics for ARVs: F-MAPS and F-CDRR"
    nairobi_730b_fig = None
    kajiado_730b_fig = None
    nairobi_program_facilities_730b_fig = None
    kajiado_program_facilities_730b_fig = None
    program_facilities_730b_fig = None
    nairobi_729b_fig = None
    kajiado_729b_fig = None
    nairobi_program_facilities_729b_fig = None
    kajiado_program_facilities_729b_fig = None
    program_facilities_729b_fig = None
    nairobi_730b_overall = pd.DataFrame()
    kajiado_730b_overall = pd.DataFrame()
    fyj_nairobi_730 = pd.DataFrame()
    fyj_kajiado_730 = pd.DataFrame()
    nairobi_729b_overall = pd.DataFrame()
    kajiado_729b_overall = pd.DataFrame()
    fyj_nairobi_729b = pd.DataFrame()
    fyj_kajiado_729b = pd.DataFrame()
    fyj_730b = pd.DataFrame()
    fyj_729b = pd.DataFrame()

    if not request.user.first_name:
        return redirect("profile")
    if request.method == 'POST':
        try:
            form = FileUploadForm(request.POST, request.FILES)
            message = "It seems that the dataset you uploaded is incorrect. To proceed with the analysis, " \
                      "kindly upload the MoH 730B Facility - CDRR Revision 2019 - Reporting rate and reporting on " \
                      "time data, as well as the MoH 729B Facility - F'MAPS Revision 2019 - Reporting rate and " \
                      "reporting rate on time data. Please generate these files and ensure they are in CSV format " \
                      "before uploading them. You can find detailed instructions on how to upload the files below. " \
                      "Thank you. "
            if form.is_valid():
                file = request.FILES['file']
                if "csv" in file.name:
                    df = pd.read_csv(file)
                else:
                    messages.success(request, message)
                    return redirect('fmaps_reporting_rate')
                # Check if required columns exist in the DataFrame
                if all(col_name in df.columns for col_name in
                       ["organisationunitname", "orgunitlevel2", "organisationunitcode", "periodname",
                        "MoH 729B Facility - F'MAPS Revision 2019 - Reporting rate",
                        "MoH 729B Facility - F'MAPS Revision 2019 - Reporting rate on time",
                        "MoH 730B Facility - CDRR Revision 2019 - Reporting rate",
                        "MoH 730B Facility - CDRR Revision 2019 - Reporting rate on time",
                        ]):
                    # Read data from FYJHealthFacility model into a pandas DataFrame
                    qs = FYJHealthFacility.objects.all()
                    df1 = pd.DataFrame.from_records(qs.values())

                    df1 = df1.rename(columns={
                        "mfl_code": "MFL Code", "county": "County", 'health_subcounty': 'Health Subcounty',
                        'subcounty': 'Subcounty', 'hub': 'Hub(1,2,3 o 4)', 'm_and_e_mentor': 'M&E Mentor/SI associate',
                        'm_and_e_assistant': 'M&E Assistant', 'care_and_treatment': 'Care & Treatment(Yes/No)',
                        'hts': 'HTS(Yes/No)', 'vmmc': 'VMMC(Yes/No)', 'key_pop': 'Key Pop(Yes/No)',
                        'facility_type': 'Faclity Type', 'category': 'Category (HVF/MVF/LVF)', 'emr': 'EMR'
                    })
                    if df.shape[0] > 0 and df1.shape[0] > 0:
                        fcdrr_fig, kajiado_reporting_rate_fig, nairobi_reporting_rate_fig, no_fmaps, no_fcdrr, \
                            overall_fig, no_fcdrr_fmaps_fig, nairobi_730b_fig, kajiado_730b_fig, \
                            nairobi_program_facilities_730b_fig, kajiado_program_facilities_730b_fig, nairobi_729b_fig, \
                            kajiado_729b_fig, nairobi_program_facilities_729b_fig, kajiado_program_facilities_729b_fig, \
                            nairobi_730b_overall, kajiado_730b_overall, fyj_nairobi_730, fyj_kajiado_730, \
                            nairobi_729b_overall, kajiado_729b_overall, fyj_nairobi_729b, fyj_kajiado_729b, \
                            no_fcdrr_fmaps_fig_all, no_fcdrr_all, no_fmaps_all, program_facilities_730b_fig, fyj_730b, \
                            program_facilities_729b_fig, fyj_729b, fmaps_fig = analyse_fmaps_fcdrr(df, df1)
                else:
                    messages.success(request, message)
                    return redirect('fmaps_reporting_rate')
            else:
                messages.success(request, message)
                return redirect('fmaps_reporting_rate')
        except MultiValueDictKeyError:
            context = {
                "final_df": final_df,
                "dictionary": dictionary,
                # "filename": filename,
                "other_adult_df_file": other_adult_df_file, "reporting_errors_df": reporting_errors_df,
                "other_paeds_bottles_df_file": other_paeds_bottles_df_file, "report_name": report_name,
                "form": form, "fcdrr_fig": fcdrr_fig, "kajiado_reporting_rate_fig": kajiado_reporting_rate_fig,
                "nairobi_reporting_rate_fig": nairobi_reporting_rate_fig, "datasets": datasets, "dqa_type": dqa_type,
                # "no_fmaps": no_fmaps, "no_fcdrr": no_fcdrr,
                "overall_fig": overall_fig, "fmaps_fig": fmaps_fig,
                "no_fcdrr_fmaps_fig": no_fcdrr_fmaps_fig,
                "no_fcdrr_fmaps_fig_all": no_fcdrr_fmaps_fig_all,
                "nairobi_730b_fig": nairobi_730b_fig, "kajiado_730b_fig": kajiado_730b_fig,
                "nairobi_program_facilities_730b_fig": nairobi_program_facilities_730b_fig,
                "kajiado_program_facilities_730b_fig": kajiado_program_facilities_730b_fig,
                "program_facilities_730b_fig": program_facilities_730b_fig,
                "nairobi_729b_fig": nairobi_729b_fig, "kajiado_729b_fig": kajiado_729b_fig,
                "nairobi_program_facilities_729b_fig": nairobi_program_facilities_729b_fig,
                "kajiado_program_facilities_729b_fig": kajiado_program_facilities_729b_fig,
                "program_facilities_729b_fig": program_facilities_729b_fig

            }

            return render(request, 'data_analysis/upload.html', context)
    # start index at 1 for Pandas DataFrame
    no_fmaps.index = range(1, len(no_fmaps) + 1)
    no_fcdrr.index = range(1, len(no_fcdrr) + 1)
    no_fcdrr_all.index = range(1, len(no_fcdrr_all) + 1)
    no_fmaps_all.index = range(1, len(no_fmaps_all) + 1)
    # Drop date from dfs
    dfs = [nairobi_730b_overall, kajiado_730b_overall, fyj_nairobi_730, fyj_kajiado_730, nairobi_729b_overall,
           kajiado_729b_overall, fyj_nairobi_729b, fyj_kajiado_729b, fyj_730b, fyj_729b]
    for df in dfs:
        if "date" in df.columns:
            df.drop('date', axis=1, inplace=True)

    request.session['no_fmaps'] = no_fmaps.to_dict()
    request.session['no_fcdrr'] = no_fcdrr.to_dict()
    request.session['no_fcdrr_all'] = no_fcdrr_all.to_dict()
    request.session['no_fmaps_all'] = no_fmaps_all.to_dict()

    request.session['nairobi_730b_overall'] = nairobi_730b_overall.to_dict()
    request.session['kajiado_730b_overall'] = kajiado_730b_overall.to_dict()
    request.session['fyj_nairobi_730'] = fyj_nairobi_730.to_dict()
    request.session['fyj_kajiado_730'] = fyj_kajiado_730.to_dict()
    request.session['fyj_730b'] = fyj_730b.to_dict()
    request.session['nairobi_729b_overall'] = nairobi_729b_overall.to_dict()
    request.session['kajiado_729b_overall'] = kajiado_729b_overall.to_dict()
    request.session['fyj_nairobi_729b'] = fyj_nairobi_729b.to_dict()
    request.session['fyj_kajiado_729b'] = fyj_kajiado_729b.to_dict()
    request.session['fyj_729b'] = fyj_729b.to_dict()
    # Convert dict_items into a list
    dictionary = get_key_from_session_names(request)
    context = {
        "final_df": final_df,
        "dictionary": dictionary,
        "other_adult_df_file": other_adult_df_file, "reporting_errors_df": reporting_errors_df,
        "other_paeds_bottles_df_file": other_paeds_bottles_df_file, "report_name": report_name,
        "form": form, "fcdrr_fig": fcdrr_fig, "kajiado_reporting_rate_fig": kajiado_reporting_rate_fig,
        "nairobi_reporting_rate_fig": nairobi_reporting_rate_fig, "datasets": datasets, "dqa_type": dqa_type,
        # "no_fmaps": no_fmaps, "no_fcdrr": no_fcdrr,
        "overall_fig": overall_fig, "fmaps_fig": fmaps_fig,
        "no_fcdrr_fmaps_fig": no_fcdrr_fmaps_fig,
        "no_fcdrr_fmaps_fig_all": no_fcdrr_fmaps_fig_all,
        "nairobi_730b_fig": nairobi_730b_fig, "kajiado_730b_fig": kajiado_730b_fig,
        "nairobi_program_facilities_730b_fig": nairobi_program_facilities_730b_fig,
        "kajiado_program_facilities_730b_fig": kajiado_program_facilities_730b_fig,
        "program_facilities_730b_fig": program_facilities_730b_fig,
        "nairobi_729b_fig": nairobi_729b_fig, "kajiado_729b_fig": kajiado_729b_fig,
        "nairobi_program_facilities_729b_fig": nairobi_program_facilities_729b_fig,
        "kajiado_program_facilities_729b_fig": kajiado_program_facilities_729b_fig,
        "program_facilities_729b_fig": program_facilities_729b_fig
    }

    return render(request, 'data_analysis/upload.html', context)


def age_buckets3(x):
    """convert age to age ranges"""
    if x == 9:
        return '0-9.'
    elif x == 19:
        return '10-19.'
    elif x == 20:
        return '20+'


def age_buckets2(x):
    """convert age to age ranges"""
    if x == 1:
        return '<1'
    elif x == 4:
        return '1-4.'
    elif x == 9:
        return '5-9.'
    elif x == 14:
        return '10-14.'
    elif x == 19:
        return '15-19'
    elif x == 24:
        return '20-24'
    elif x == 25:
        return '25+'


def make_crosstab_facility_age(df):
    """This function makes a crosstab"""
    # create a list with age bands, in the required order
    age = ['1-4', '5-9', '10-14', '15-19', '20-24', '25-29', '30-34', '35-39', '40-44', '45-49', '50-54', '55-59',
           '60-64', '65+', 'All']
    # Generate crosstab
    try:
        df = pd.crosstab([df['Facilty'], df['Gender']], [df['Age']], margins=True)
    except:
        df = pd.crosstab([df['Facility Name'], df['Sex']], [df['Age']], margins=True)

    available_ages_bands = []
    for i in age:
        # convert column names to a list
        if i in list(df.columns):
            # append available age band to the list
            available_ages_bands.append(i)

            # Change order of columns produced by crosstab
    df = df[available_ages_bands]

    return df


def age_buckets(x):
    """convert age to age ranges"""
    if x == 1:
        return '< 1'
    elif x == 4:
        return '1-4'
    elif x == 9:
        return '5-9'
    elif x == 14:
        return '10-14'
    elif x == 19:
        return '15-19'
    elif x == 24:
        return '20-24'
    elif x == 29:
        return '25-29'
    elif x == 34:
        return '30-34'
    elif x == 39:
        return '35-39'
    elif x == 44:
        return '40-44'
    elif x == 49:
        return '45-49'
    elif x == 54:
        return '50-54'
    elif x == 59:
        return '55-59'
    elif x == 64:
        return '60-64'
    elif x == 69:
        return '65+'


def age_buckets1(x):
    """convert age to age ranges"""
    if x == 2:
        return '<2'
    elif x == 9:
        return '2-9'
    elif x == 19:
        return '10-19'
    elif x == 24:
        return '20-24'
    elif x == 25:
        return '25+'


def use_availble_columns(df):
    age = ["Missing age", '1-4', '5-9', '10-14', '15-19', '20-24', '25-29', '30-34', '35-39', '40-44', '45-49', '50-54',
           '55-59',
           '60-64', '65+', 'All']

    available_ages_bands = []
    for i in age:
        # convert column names to a list
        if i in list(df.columns):
            # append available age band to the list
            available_ages_bands.append(i)

    # Change order of columns produced by crosstab
    df = df[available_ages_bands]
    return df


def convert_pivot_to_dataframe(subcounties):
    """convert pivot table to dataframe"""
    subcounties = subcounties.reset_index()  # index to columns
    return subcounties


def customize_age_bands(df):
    df['Current age'] = df['Age'].astype(float)
    # customize agebands
    # df.loc[df['Current age'] <1, 'Current age'] = 1
    df.loc[(df['Current age'] >= 0) & (df['Current age'] < 1), 'Current age'] = 1
    df.loc[(df['Current age'] >= 1) & (df['Current age'] < 5), 'Current age'] = 4
    df.loc[(df['Current age'] >= 5) & (df['Current age'] < 10), 'Current age'] = 9
    df.loc[(df['Current age'] >= 10) & (df['Current age'] < 15), 'Current age'] = 14
    df.loc[(df['Current age'] >= 15) & (df['Current age'] < 20), 'Current age'] = 19
    df.loc[(df['Current age'] >= 20) & (df['Current age'] < 25), 'Current age'] = 24
    df.loc[(df['Current age'] >= 25) & (df['Current age'] < 30), 'Current age'] = 29
    df.loc[(df['Current age'] >= 30) & (df['Current age'] < 35), 'Current age'] = 34
    df.loc[(df['Current age'] >= 35) & (df['Current age'] < 40), 'Current age'] = 39
    df.loc[(df['Current age'] >= 40) & (df['Current age'] < 45), 'Current age'] = 44
    df.loc[(df['Current age'] >= 45) & (df['Current age'] < 50), 'Current age'] = 49
    df.loc[(df['Current age'] >= 50) & (df['Current age'] < 55), 'Current age'] = 54
    df.loc[(df['Current age'] >= 55) & (df['Current age'] < 60), 'Current age'] = 59
    df.loc[(df['Current age'] >= 60) & (df['Current age'] < 65), 'Current age'] = 64
    df.loc[df['Current age'] >= 65, 'Current age'] = 69

    df['Current age1'] = df['Age'].astype(float)

    # customize agebands
    df.loc[df['Current age1'] < 2, 'Current age1'] = 2
    df.loc[(df['Current age1'] >= 2) & (df['Current age1'] < 10), 'Current age1'] = 9

    df.loc[(df['Current age1'] >= 10) & (df['Current age1'] < 20), 'Current age1'] = 19
    df.loc[(df['Current age1'] >= 20) & (df['Current age1'] < 25), 'Current age1'] = 24

    df.loc[df['Current age1'] >= 25, 'Current age1'] = 25

    df['Current age2'] = df['Age'].astype(float)

    # customize agebands
    df.loc[df['Current age2'] < 1, 'Current age2'] = 1
    df.loc[(df['Current age2'] >= 1) & (df['Current age2'] < 5), 'Current age2'] = 4
    df.loc[(df['Current age2'] >= 5) & (df['Current age2'] < 10), 'Current age2'] = 9

    df.loc[(df['Current age2'] >= 10) & (df['Current age2'] < 15), 'Current age2'] = 14
    df.loc[(df['Current age2'] >= 15) & (df['Current age2'] < 20), 'Current age2'] = 19
    df.loc[(df['Current age2'] >= 20) & (df['Current age2'] < 25), 'Current age2'] = 24

    df.loc[df['Current age2'] >= 25, 'Current age2'] = 25

    df['Current age3'] = df['Age'].astype(float)

    # customize agebands
    df.loc[df['Current age3'] < 10, 'Current age3'] = 9
    df.loc[(df['Current age3'] >= 10) & (df['Current age3'] < 20), 'Current age3'] = 19
    df.loc[df['Current age3'] >= 20, 'Current age3'] = 20

    # Change age column to fit DATIM requirement
    df['Age'] = df['Current age'].apply(age_buckets)
    df['Age1'] = df['Current age1'].apply(age_buckets1)
    df['Age2'] = df['Current age2'].apply(age_buckets2)
    df['Age3'] = df['Current age3'].apply(age_buckets3)
    return df


def transform_vl_dataframe(df):
    """
    Takes a pandas dataframe of viral load data and transforms it by adding columns for
    the number of months since the last viral load test, the month and year of the test,
    and a combined period column. The month column is converted to a datetime object and sorted.
    """
    df['months since last VL'] = pd.Timestamp.now().normalize() - pd.to_datetime(df['Date Tested'])
    df['months since last VL'] = df['months since last VL'].astype('timedelta64[M]')
    df = df[~df['Date Tested'].isnull()]
    df['Month vl Tested'] = pd.to_datetime(df['Date Tested']).dt.strftime('%b')
    df['Year vl Tested'] = pd.to_datetime(df['Date Tested']).dt.strftime('%Y')
    df['period'] = df[['Month vl Tested', 'Year vl Tested']].agg('-'.join, axis=1)
    df['Month'] = df['Month vl Tested'].str.capitalize()
    df['Month'] = pd.to_datetime(df['Month'], format='%b', errors='coerce').dt.month
    df = df.sort_values(by='Month')
    return df


def preprocess_viral_load_data(df):
    """
    This function preprocesses viral load data by sorting the input DataFrame into several DataFrames,
    customizing the Viral Load column, and concatenating the resulting DataFrames into new ones.

    Args:
    df (DataFrame): input DataFrame containing viral load data

    Returns:
    df_ldl (DataFrame): DataFrame containing viral load data for LDL only
    df_below_400 (DataFrame): DataFrame containing viral load data below 400
    df_llv (DataFrame): DataFrame containing viral load data for LLV
    df_hvl (DataFrame): DataFrame containing viral load data for HVL
    df_no_vl (DataFrame): DataFrame containing viral load data for samples with no VL done
    df_collect_new_sample (DataFrame): DataFrame containing viral load data for samples requiring new collection
    df_invalid (DataFrame): DataFrame containing viral load data for samples marked as invalid
    """
    # copy facility df
    df = df.copy()

    df_LDL = df[df['Viral Load'] == '< LDL copies/ml']
    df_others = df[df['Viral Load'] != '< LDL copies/ml']

    #############################
    # Sort df into several dfs #
    #############################

    # # copy df others
    df_others = df_others.copy()

    df_collect_new_sample = df_others[df_others['Viral Load'] == 'Collect New Sample']
    df_others = df_others[df_others['Viral Load'] != 'Collect New Sample']
    no_vl_done = df_others[pd.isnull(df_others['Viral Load'])]

    # replace all blanks with no vl done
    no_vl_done['Result'] = "NO VL DONE"

    # filter nonblanks
    df_notblanks = df_others[pd.notnull(df_others['Viral Load'])]

    df_notblanks_invalid = df_notblanks[df_notblanks['Viral Load'] == "Invalid"]
    df_notblanks = df_notblanks[df_notblanks['Viral Load'] != "Invalid"]

    # convert nonblank values to numbers
    df_notblanks['Viral Load'] = pd.to_numeric(df_notblanks['Viral Load'].str.replace('[^0-9.]', ''), errors='coerce')

    # filter LLV
    newdf_LDL = df_notblanks[df_notblanks['Viral Load'] < 1000]
    # filter <400
    newdf_below_4001 = df_notblanks[df_notblanks['Viral Load'] < 200]

    ###############################
    # customize Viral load column #
    ###############################

    # replace all < LDL copies/ml with LDL
    df_LDL.loc[df_LDL['Viral Load'] == '< LDL copies/ml', 'Viral Load'] = "LDL"

    # # replace all blanks with no vl done
    df_collect_new_sample['Viral Load'] = "Collect new sample"
    df_collect_new_sample['Viral Load'].unique()

    # # replace all LLV with LDL
    newdf_LDL.loc[newdf_LDL['Viral Load'] < 1000, 'Viral Load'] = "LDL"

    # filter VL >1000
    newdf_HVL = df_notblanks[df_notblanks['Viral Load'] >= 1000]
    # newdf_HVL['Viral Load'].unique()
    newdf_llv = df_notblanks[(df_notblanks['Viral Load'] >= 200) & (df_notblanks['Viral Load'] < 1000)]

    newdf_llv.loc[newdf_llv['Viral Load'] < 1000, 'Viral Load'] = "LLV"

    newdf_below_4001.loc[newdf_below_4001['Viral Load'] < 200, 'Viral Load'] = "LDL"

    # # replace all >1000 with HVL
    newdf_HVL.loc[newdf_HVL['Viral Load'] >= 1000, 'Viral Load'] = "STF"
    newdf_HVL['Viral Load'].unique()

    # join LDL + LLV + HVL+ NO VL DONE + collect new sample
    new_df = pd.concat([df_LDL, newdf_LDL, newdf_HVL, no_vl_done, df_collect_new_sample])

    new_df1 = pd.concat([df_LDL, newdf_below_4001, newdf_llv, newdf_HVL])

    new_df2 = pd.concat([df_LDL, newdf_below_4001, newdf_llv, newdf_HVL, df_collect_new_sample, df_notblanks_invalid])

    # join LDL + LLV
    ldl = pd.concat([df_LDL, newdf_LDL])

    # join no vl V.L
    repeat_viral_load = pd.concat([df_collect_new_sample, no_vl_done, df_notblanks_invalid])
    return ldl, repeat_viral_load, new_df, new_df2, newdf_HVL, df_collect_new_sample, newdf_llv


def handle_facility_and_subcounty(new_df, group_by_cols):
    # Replace None values with "Missing"
    new_df['Viral Load'] = np.where(new_df['Viral Load'].isna(), "Missing results", new_df['Viral Load'])
    # Sub county Viral suppression
    subcounty_vl = new_df.groupby(group_by_cols + ['Viral Load']).sum()['V.L'].reset_index()
    subcounty_vl = subcounty_vl.pivot_table(values='V.L', index=subcounty_vl[group_by_cols], columns='Viral Load',
                                            aggfunc='first')
    subcounty_vl = subcounty_vl.fillna(0)

    if 'STF' in subcounty_vl.columns and 'LDL' in subcounty_vl.columns:
        subcounty_vl['Viral Suppression %'] = round(
            (subcounty_vl['LDL'] / (subcounty_vl['STF'] + subcounty_vl['LDL'])) * 100)
    elif 'STF' not in subcounty_vl.columns and 'LDL' in subcounty_vl.columns:
        subcounty_vl['Viral Suppression %'] = 100
    elif 'STF' in subcounty_vl.columns and 'LDL' not in subcounty_vl.columns:
        subcounty_vl['Viral Suppression %'] = 0
    else:
        # Both 'STF' and 'LDL' columns are missing
        subcounty_vl['Viral Suppression %'] = 0

    # subcounty_vl['Viral Suppression %'] = round(
    #     (subcounty_vl['LDL'] / (subcounty_vl['STF'] + subcounty_vl['LDL'])) * 100)
    subcounty_vl = subcounty_vl.sort_values('Viral Suppression %', ascending=False).astype(int)
    subcounty_vl['Viral Suppression %'] = subcounty_vl['Viral Suppression %'].astype(str) + "%"
    return subcounty_vl


def monthly_trend(monthly_vl_trend, title, y_axis_text):
    month_list = monthly_vl_trend['period'].unique()
    try:
        mean_sample_tested = sum(monthly_vl_trend['V.L']) / len(monthly_vl_trend['V.L'])
        median_sample_tested = monthly_vl_trend['V.L'].median()
    except ZeroDivisionError:
        mean_sample_tested = 0
        median_sample_tested = 0

    fig = px.bar(monthly_vl_trend, x='period', y='V.L', height=450,
                 title=f"{title} {monthly_vl_trend['V.L'].sum()}",
                 text='V.L',
                 )
    # Set x-axis title
    fig.update_xaxes(title_text="Period (in months)")
    # Set y-axes titles
    fig.update_yaxes(title_text=f"{y_axis_text}", secondary_y=False)
    fig.update_layout(legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    ))
    y = int(mean_sample_tested)
    x = int(median_sample_tested)
    fig.add_shape(type='line', x0=month_list[0], y0=y,
                  x1=month_list[-1],
                  y1=y,
                  line=dict(color='red', width=2, dash='dot'))

    fig.add_annotation(x=month_list[-1], y=y,
                       text=f"Mean monthly VL uptake {y}",
                       showarrow=True, arrowhead=1,
                       font=dict(size=8, color='red'))
    fig.add_shape(type='line', x0=month_list[0], y0=x,
                  x1=month_list[-1],
                  y1=x,
                  line=dict(color='black', width=2, dash='dot'))

    fig.add_annotation(x=month_list[0], y=x,
                       text=f"Median monthly VL uptake {x}",
                       showarrow=True, arrowhead=1,
                       font=dict(size=8, color='black'))
    fig.update_layout(
        xaxis=dict(
            tickfont=dict(
                size=8
            ),
            title_font=dict(
                size=10
            )
        ),
        yaxis=dict(
            title_font=dict(
                size=8
            )
        ),
        legend=dict(
            font=dict(
                size=10
            )
        ),
        title=dict(
            font=dict(
                size=14
            )
        )
    )
    monthly_trend_fig = plot(fig, include_plotlyjs=False, output_type="div")
    return monthly_trend_fig


def plot_monthly_trend(newdf_HVL, title, y_axis_text):
    monthly_hvl_trend = \
        newdf_HVL.groupby(['Month', 'Month vl Tested', 'period', 'Year vl Tested']).sum()[
            'V.L'].reset_index().sort_values(['Year vl Tested', 'Month'])
    monthly_hvl_trend_fig = monthly_trend(monthly_hvl_trend,
                                          title,
                                          y_axis_text)
    return monthly_hvl_trend_fig


def prepare_age_sex_df(df, newdf_HVL):
    hvl_ccc_nos = list(newdf_HVL['Patient CCC No'].unique())
    hvl_linelist = df[df['Patient CCC No'].isin(hvl_ccc_nos)]
    if "Time Result SMS SENT" in hvl_linelist.columns:
        del hvl_linelist['Time Result SMS SENT']
    # convert nonblank values to numbers
    hvl_linelist['Viral Load'] = pd.to_numeric(
        hvl_linelist['Viral Load'].str.replace('[^0-9.]', ''), errors='coerce')
    hvl_linelist = hvl_linelist[list(hvl_linelist.columns[:28])].sort_values("Viral Load",
                                                                             ascending=False)

    hvl_linelist_facility = hvl_linelist.groupby(["Facility Name"]).sum(numeric_only=True)[
        'V.L'].reset_index().sort_values("V.L", ascending=False)
    hvl_linelist_facility['%'] = round(
        hvl_linelist_facility['V.L'] / sum(hvl_linelist_facility['V.L']) * 100, 1)
    hvl_linelist_facility = hvl_linelist_facility.rename(columns={"V.L": "STF"})

    newdf_HVL_age_sex = newdf_HVL.groupby(["Age", "Sex"]).sum(numeric_only=True)[
        'V.L'].reset_index().sort_values("V.L", ascending=False)
    newdf_HVL_age_sex['%'] = round(
        newdf_HVL_age_sex['V.L'] / sum(newdf_HVL_age_sex['V.L']) * 100,
        1)
    newdf_HVL_age_sex = newdf_HVL_age_sex.rename(columns={"V.L": "HVL"})
    newdf_HVL_age_sex['HVL %'] = newdf_HVL_age_sex['HVL'].astype(str) + " (" + \
                                 newdf_HVL_age_sex[
                                     '%'].astype(str) + "%)"
    newdf_HVL_age_sex["Age"] = pd.Categorical(newdf_HVL_age_sex["Age"],
                                              categories=['1-4', '5-9', '10-14', '15-19',
                                                          '20-24',
                                                          '25-29', '30-34', '35-39',
                                                          '40-44',
                                                          '45-49', '50-54',
                                                          '55-59', '60-64', '65+'],
                                              ordered=True)
    newdf_HVL_age_sex.sort_values('Age', inplace=True)
    return newdf_HVL_age_sex, hvl_linelist, hvl_linelist_facility


def calculate_overall_resuppression_rate(confirm_rx_failure, newdf_HVL, newdf_llv, df):
    confirm_rx_failure_list = list(confirm_rx_failure["Patient CCC No"].unique())
    hvl_list = list(newdf_HVL["Patient CCC No"].unique())
    llv_list = list(newdf_llv["Patient CCC No"].unique())
    exclusion_list = llv_list + hvl_list
    set1 = set(confirm_rx_failure_list)
    set2 = set(exclusion_list)
    missing = list(sorted(set1 - set2))

    resuppressed_df = df[df["Patient CCC No"].isin(missing)].sort_values("Viral Load")
    resuppressed_df['resuppression status'] = "re-suppressed"
    newdf_llv['resuppression status'] = "LLV"
    newdf_HVL['resuppression status'] = "STF (HVL)"
    resuppression_status = pd.concat([resuppressed_df, newdf_HVL, newdf_llv])

    resuppression_rate_df = resuppression_status.groupby(["resuppression status"]).sum()['V.L'].reset_index()
    resuppression_rate_df = resuppression_rate_df.sort_values("V.L", ascending=False)
    resuppression_rate_df['%'] = round(resuppression_rate_df['V.L'] / sum(resuppression_rate_df['V.L']) * 100,
                                       1).astype(str) + "%"
    return resuppression_rate_df, resuppression_status


def calculate_facility_resuppression_rate(resuppression_status):
    facility_resuppression_status = \
        resuppression_status.groupby(['Facility Name', 'Facility Code', "resuppression status"]).sum()[
            'V.L'].reset_index()
    facility_resuppression_status = facility_resuppression_status.sort_values("V.L", ascending=False)
    facility_resuppression_status['%'] = round(
        facility_resuppression_status['V.L'] / sum(facility_resuppression_status['V.L']) * 100, 1).astype(str) + "%"
    facility_resuppression_status = facility_resuppression_status.pivot_table(index=['Facility Name', 'Facility Code'],
                                                                              columns='resuppression'
                                                                                      ' status', values='V.L')
    facility_resuppression_status = facility_resuppression_status.fillna(0)
    # facility_resuppression_status['Total repeat VL tests'] = facility_resuppression_status['LLV'] + \
    #                                                          facility_resuppression_status['STF (HVL)'] + \
    #                                                          facility_resuppression_status['re-suppressed']
    facility_resuppression_status['Total repeat VL tests'] = facility_resuppression_status.get('LLV', 0) + \
                                                             facility_resuppression_status.get('STF (HVL)', 0) + \
                                                             facility_resuppression_status.get('re-suppressed', 0)

    try:
        facility_resuppression_status["Resuppression rate %"] = round(
            facility_resuppression_status['re-suppressed'] / facility_resuppression_status[
                'Total repeat VL tests'] * 100,
            1)
    except KeyError:
        facility_resuppression_status["Resuppression rate %"] = 0
    facility_resuppression_status = facility_resuppression_status.sort_values("Resuppression rate %", ascending=False)
    facility_resuppression_status.reset_index(inplace=True)
    facility_resuppression_status.reset_index(drop=True)
    facility_resuppression_status = facility_resuppression_status.reset_index(drop=True)
    return facility_resuppression_status


def calculate_justification_resuppression_rate(resuppression_status):
    facility_resuppression_status = resuppression_status.groupby(['Justification',
                                                                  "resuppression status"]
                                                                 ).sum()['V.L'].reset_index()

    facility_resuppression_status = facility_resuppression_status.pivot_table(index=['Justification'],
                                                                              columns='resuppression status',
                                                                              values='V.L')
    facility_resuppression_status = facility_resuppression_status.reset_index()
    facility_resuppression_status = facility_resuppression_status.fillna(0)
    # facility_resuppression_status['Total repeat VL tests'] = facility_resuppression_status['LLV'] + \
    #                                                          facility_resuppression_status['STF (HVL)'] + \
    #                                                          facility_resuppression_status['re-suppressed']
    facility_resuppression_status['Total repeat VL tests'] = facility_resuppression_status.get('LLV', 0) + \
                                                             facility_resuppression_status.get('STF (HVL)', 0) + \
                                                             facility_resuppression_status.get('re-suppressed', 0)
    try:
        facility_resuppression_status["Resuppression rate %"] = round(
            facility_resuppression_status['re-suppressed'] / facility_resuppression_status[
                'Total repeat VL tests'] * 100,
            1)
    except KeyError:
        facility_resuppression_status["Resuppression rate %"] = 0
    facility_resuppression_status = facility_resuppression_status.sort_values("Resuppression rate %", ascending=False)

    return facility_resuppression_status


def prepare_to_send_via_sessions(llv_linelist):
    llv_linelist = llv_linelist.applymap(
        lambda x: x.strftime('%Y-%m-%d %H:%M:%S') if isinstance(x, pd.Timestamp) else x)
    if "HVL" in llv_linelist.columns:
        del llv_linelist["V.L"]
    llv_linelist = llv_linelist.reset_index(drop=True)
    llv_linelist.index = range(1, len(llv_linelist) + 1)

    return llv_linelist


@login_required(login_url='login')
def viral_load(request):
    all_results_df = pd.DataFrame()
    subcounty_ = pd.DataFrame()
    facility_less_1000_df = pd.DataFrame()
    vl_done_df = pd.DataFrame()
    subcounty_vl = pd.DataFrame()
    facility_vl = pd.DataFrame()
    hvl_linelist = pd.DataFrame()
    llv_linelist = pd.DataFrame()
    hvl_linelist_facility = pd.DataFrame()
    llv_linelist_facility = pd.DataFrame()
    facility_resuppression_status = pd.DataFrame()
    confirm_rx_failure = pd.DataFrame()
    vs_text = None
    facility_analyzed_text = None
    subcounty_fig = None
    monthly_trend_fig = None
    weekly_trend_fig = None
    monthly_hvl_trend_fig = None
    hvl_sex_age_fig = None
    llv_sex_age_fig = None
    monthly_llv_trend_fig = None
    justification_fig = None
    filter_text = "All"

    form = FileUploadForm(request.POST or None)
    date_picker_form = DateFilterForm(request.POST or None)
    data_filter_form = DataFilterForm(request.POST or None)
    if not request.user.first_name:
        return redirect("profile")
    if request.method == 'POST':
        try:
            form = FileUploadForm(request.POST, request.FILES)
            message = "It seems that the dataset you uploaded is incorrect. To proceed with the analysis, " \
                      "kindly upload detailed Viral load CSV file. Please generate this file from the website link " \
                      "below and ensure it is in CSV format before uploading it. You can find detailed " \
                      "instructions on how to upload the file below. Thank you."
            if form.is_valid():
                file = request.FILES['file']
                if "csv" in file.name:
                    df = pd.read_csv(file)
                else:
                    messages.success(request, message)
                    return redirect('viral_load')
                if data_filter_form.is_valid():
                    selected_option = data_filter_form.cleaned_data['filter_option']
                    if selected_option == "PMTCT":
                        df = df[df['PMTCT'].str.contains("breast feeding|pregnant", case=False, na=False)]
                        filter_text = "PMTCT"
                expected_columns = ['System ID', 'Batch', 'Patient CCC No', 'Lab Tested In', 'County',
                                    'Sub County', 'Partner', 'Facility Name', 'Facility Code', 'Sex', 'DOB',
                                    'Age', 'Sample Type', 'Date Collected', 'Justification',
                                    'Date Received', 'Date Tested', 'Date Dispatched',
                                    'ART Initiation Date', 'Received Status', 'Reasons for Repeat',
                                    'Rejected Reason', 'Regimen', 'Regimen Line', 'PMTCT', 'Viral Load',
                                    'Entry']
                if request.method == 'POST':
                    date_picker_form = DateFilterForm(request.POST)
                    if date_picker_form.is_valid():
                        df = df.rename(
                            columns={"Collection Date": "Date Collected", "Gender": "Sex", "Facilty": "Facility Name",
                                     "Result": "Viral Load", "Sub-County": "Sub County",
                                     "Date of Testing": "Date Tested"})
                        # Check if required columns exist in the DataFrame
                        if all(col_name in df.columns for col_name in expected_columns):
                            df['V.L'] = 1
                            date_cols = [col for col in df.columns if "date" in col.lower()]
                            # Convert cols to datetime
                            for col in date_cols:
                                df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')

                            from_date = date_picker_form.cleaned_data['from_date']
                            to_date = date_picker_form.cleaned_data['to_date']
                            if to_date <= from_date:
                                messages.error(request,
                                               f"The selected end date ({to_date}) should be later than the start date "
                                               f"({from_date}). Please choose valid dates.")
                                return redirect('viral_load')

                            df = df.loc[(df['Date Collected'].dt.date >= from_date) &
                                        (df['Date Collected'].dt.date <= to_date)]
                            df = df[(df['Justification'] != 'Recency Testing') & (df['Justification'] != 'Baseline')]
                            # Drop dulicates and keep last
                            df = df.sort_values('Date Collected').drop_duplicates(['Patient CCC No'], keep='last')

                            df = customize_age_bands(df)
                            try:
                                df = transform_vl_dataframe(df)
                            except ValueError:
                                messages.success(request,
                                                 f"No VL samples were collected between {from_date} and {to_date}.")
                                return redirect('viral_load')
                            # Replace None values with "Missing"
                            df['Age'] = np.where(df['Age'].isna(), "Missing age", df['Age'])
                            all_results = pd.crosstab(df['Sex'], [df['Age']], margins=True)
                            all_results_df = use_availble_columns(all_results).fillna(0)
                            dfsss = pd.crosstab(df['Sub County'], [df['Age']], margins=True)
                            dfsss = use_availble_columns(dfsss)
                            subcounty_ = dfsss.sort_values('All').reset_index()
                            ldl, repeat_viral_load, new_df, new_df2, newdf_HVL, df_collect_new_sample, newdf_llv = \
                                preprocess_viral_load_data(df)

                            newdf_HVL_age_sex, hvl_linelist, hvl_linelist_facility = prepare_age_sex_df(df, newdf_HVL)
                            hvl_linelist = hvl_linelist.fillna(0)
                            newdf_llv_age_sex, llv_linelist, llv_linelist_facility = prepare_age_sex_df(df, newdf_llv)
                            llv_linelist = llv_linelist.fillna(0)
                            newdf_llv_age_sex = newdf_llv_age_sex.rename(columns={"HVL": "LLV"})
                            llv_linelist_facility = llv_linelist_facility.rename(
                                columns={"STF": "# of LLV (200-999 cp/ml)"})

                            facility_vl_uptake = make_crosstab_facility_age(ldl)

                            ################################################################################
                            # DSD: TX _PVLS (NUMERATOR)
                            # Number of adults and pediatrics patients on ART with suppressed viral load
                            # V.L (<1,000 copies/ml) documentation in the medical records and/or supporting
                            # laboratory V.L within the past 12 months #
                            ################################################################################

                            facility_less_1000_df = convert_pivot_to_dataframe(facility_vl_uptake).fillna(0)
                            ################################################################################
                            # DSD: TX _PVLS (DENOMINATOR)
                            # Number of adults and pediatrics ART patients with a viral load V.L documented
                            # in the patient medical records and/or laboratory records in the past 12 months.
                            ################################################################################

                            vl_done = new_df.loc[(new_df['months since last VL'] <= 12)]
                            vl_done_df = convert_pivot_to_dataframe(make_crosstab_facility_age(vl_done)).fillna(0)
                            ######################
                            # Viral suppression  #
                            ######################
                            vs_rate = round((len(ldl) / (len(newdf_HVL) + len(ldl) + len(repeat_viral_load))) * 100, 1)

                            vs_text = f"Viral Load Suppression: {vs_rate}% overall, with {len(newdf_HVL)} cases " \
                                      f"of suspected treatment failure (STF) and {len(df_collect_new_sample)} requiring new " \
                                      f"samples collection."

                            facility_analyzed_text = f"Analyzed a dataset containing {df.shape[0]} rows (after removing " \
                                                     f"duplicates) from {len(list(df['Facility Name'].unique()))} facilities across " \
                                                     f"{len(list(df['Sub County'].unique()))} sub-counties."

                            # Replace None values with "Missing"
                            new_df['Viral Load'] = np.where(new_df['Viral Load'].isna(), "Missing results",
                                                            new_df['Viral Load'])
                            #################################
                            # Sub county Viral suppression  #
                            #################################
                            subcounty_vl = handle_facility_and_subcounty(new_df, ['County', "Sub County"])
                            subcounty_vl = subcounty_vl.reset_index().fillna(0)

                            ###############################
                            # Facility Viral suppression  #
                            ###############################
                            facility_vl = handle_facility_and_subcounty(new_df, ["Facility Name"])
                            facility_vl = facility_vl.reset_index().fillna(0)

                            # summarize data by groupby
                            monthly_vl_trend = \
                                df.groupby(['Month', 'Month vl Tested', 'period', 'Year vl Tested']).sum()[
                                    'V.L'].reset_index().sort_values(['Year vl Tested', 'Month'])
                            monthly_trend_fig = monthly_trend(monthly_vl_trend,
                                                              "Monthly VL uptake trend.      Total sample collected and "
                                                              "processed ", "VL sample taken")
                            subcounty_fig = subcounty_[subcounty_['Sub County'] != "All"].fillna(0)
                            subcounty_fig = hvl_trend(subcounty_fig, "Sub County", "All",
                                                      title=f"Viral load samples done per Sub County N = "
                                                            f"{sum(subcounty_fig['All'])}",
                                                      )
                            hvl_sex_age_fig = hvl_trend(newdf_HVL_age_sex, "Age", "HVL",
                                                        title=f"Distribution of HVL (>= 1000 cp/ml) by sex and age "
                                                              f"N = {sum(newdf_HVL_age_sex['HVL'])}",
                                                        color="Sex")
                            llv_sex_age_fig = hvl_trend(newdf_llv_age_sex, "Age", "LLV",
                                                        title=f"Distribution of LLV (200 -999 cp/ml) by sex and age "
                                                              f"N = {sum(newdf_llv_age_sex['LLV'])}",
                                                        color="Sex")

                            #################
                            # HVL
                            #################
                            monthly_hvl_trend_fig = plot_monthly_trend(newdf_HVL, "Monthly distribution of PLHIV with "
                                                                                  "Suspected Treatment Failure (STF)  "
                                                                                  "N = ", "# with Suspected Treatment "
                                                                                          "Failure (STF)")
                            #################
                            # LLV
                            #################
                            monthly_llv_trend_fig = plot_monthly_trend(newdf_llv, "Monthly distribution of PLHIV with "
                                                                                  "LLV N = ",
                                                                       "# with LLV (200-999 cp/ml)")

                            df['# sample collected'] = 1
                            df['Date Tested'] = pd.to_datetime(df['Date Tested'], errors='coerce')
                            df1 = df.groupby(pd.Grouper(freq='W', key='Date Tested'))[
                                '# sample collected'].sum().reset_index()
                            total_vl = df1['# sample collected'].sum()
                            mean_sample_tested = sum(df1['# sample collected']) / len(df1['# sample collected'])
                            median_sample_tested = df1['# sample collected'].median()
                            weekly_trend = df1['# sample collected'].sum()
                            fig = px.line(df1, x='Date Tested', y='# sample collected', text='# sample collected',
                                          height=450,
                                          title=f"Weekly Trend of Viral Load Testing Samples Collected N={weekly_trend}"
                                                f"      Maximum VLs : {max(df1['# sample collected'])}")
                            y = int(mean_sample_tested)
                            x = int(median_sample_tested)
                            fig.update_traces(textposition='top center')
                            fig.add_shape(type='line', x0=df1['Date Tested'].min(), y0=y,
                                          x1=df1['Date Tested'].max(),
                                          y1=y,
                                          line=dict(color='red', width=2, dash='dot'))

                            fig.add_annotation(x=df1['Date Tested'].max(), y=y,
                                               text=f"Mean weekly VL uptake {y}",
                                               showarrow=True, arrowhead=1,
                                               font=dict(size=8, color='red'))
                            fig.add_shape(type='line', x0=df1['Date Tested'].min(), y0=x,
                                          x1=df1['Date Tested'].max(),
                                          y1=x,
                                          line=dict(color='black', width=2, dash='dot'))

                            fig.add_annotation(x=df1['Date Tested'].min(), y=x,
                                               text=f"Median weekly VL uptake {x}",
                                               showarrow=True, arrowhead=1,
                                               font=dict(size=8, color='black'))
                            weekly_trend_fig = plot(fig, include_plotlyjs=False, output_type="div")
                            ###############################
                            # RESUPPRESSION
                            ###############################
                            confirm_rx_failure = df[
                                (df['Justification'] == 'Confirmation of Treatment Failure (Repeat VL)') |
                                (df['Justification'] == 'Confirmation of Treatment Failure (Repeat VL)') |
                                (df['Justification'] == 'Clinical Failure')]

                            ldl, repeat_viral_load, new_df, new_df2, newdf_HVL, df_collect_new_sample, newdf_llv = preprocess_viral_load_data(
                                confirm_rx_failure)
                            resuppression_rate_df, resuppression_status = calculate_overall_resuppression_rate(
                                confirm_rx_failure, newdf_HVL,
                                newdf_llv, df)
                            re_suppressed_df = resuppression_rate_df[
                                resuppression_rate_df['resuppression status'] == "re-suppressed"]

                            if not re_suppressed_df.empty:
                                resuppression_rate = re_suppressed_df.iloc[0, 2]
                                re_suppressed = re_suppressed_df.iloc[0, 1]
                            else:
                                # Handle the case when there are no rows matching the condition
                                resuppression_rate = "0 %"
                                re_suppressed = 0

                            # resuppression_rate = resuppression_rate_df[
                            #     resuppression_rate_df['resuppression status'] == "re-suppressed"].iloc[0, 2]
                            # re_suppressed = resuppression_rate_df[
                            #     resuppression_rate_df['resuppression status'] == "re-suppressed"].iloc[0, 1]
                            total_test_done = sum(resuppression_rate_df['V.L'])
                            facility_resuppression_status = calculate_facility_resuppression_rate(resuppression_status)
                            justification_r_r = calculate_justification_resuppression_rate(resuppression_status)
                            columns_to_melt = ['Total repeat VL tests', 'STF (HVL)', 're-suppressed', 'LLV',
                                               'Resuppression rate %']
                            justification_r_r = justification_r_r.melt(id_vars=['Justification'],
                                                                       value_vars=[col for col in columns_to_melt if
                                                                                   col in justification_r_r.columns],
                                                                       )
                            fig = px.bar(justification_r_r, x="Justification", y='value', text="value",
                                         barmode="group", color="resuppression status", height=450,
                                         title=f"Resuppression status and Resuppression rate = {resuppression_rate}  ({re_suppressed}/{total_test_done})")
                            fig.update_layout(legend=dict(
                                orientation="h",
                                yanchor="bottom",
                                y=1.02,
                                xanchor="right",
                                x=1
                            ))
                            justification_fig = plot(fig, include_plotlyjs=False, output_type="div")

                        else:
                            messages.success(request, message)
                            return redirect('viral_load')

            else:
                messages.success(request, message)
                return redirect('viral_load')
        except MultiValueDictKeyError:
            context = {
                "form": form,
                "all_results_df": all_results_df,
                "subcounty_": subcounty_,
                "facility_less_1000_df": facility_less_1000_df,
                "vl_done_df": vl_done_df,
                "vs_text": vs_text,
                "facility_analyzed_text": facility_analyzed_text,
                "subcounty_vl": subcounty_vl,
                "facility_vl": facility_vl,
                "monthly_trend_fig": monthly_trend_fig,
                "weekly_trend_fig": weekly_trend_fig,
                "subcounty_fig": subcounty_fig,
                "hvl_sex_age_fig": hvl_sex_age_fig,
                "llv_sex_age_fig": llv_sex_age_fig,
                "monthly_hvl_trend_fig": monthly_hvl_trend_fig,
                "monthly_llv_trend_fig": monthly_llv_trend_fig,
                "date_picker_form": date_picker_form,
                "data_filter_form": data_filter_form,
                "dqa_type": "viral_load",
                "hvl_linelist": hvl_linelist,
                "hvl_linelist_facility": hvl_linelist_facility,
                "llv_linelist_facility": llv_linelist_facility,
                "llv_linelist_facility_shape": llv_linelist_facility.shape[0],
                "facility_resuppression_status": facility_resuppression_status,
                "justification_fig": justification_fig,
            }

            return render(request, 'data_analysis/tat.html', context)
    request.session['all_results_df'] = all_results_df.to_dict()
    request.session['subcounty_'] = subcounty_.to_dict()
    request.session['facility_less_1000_df'] = facility_less_1000_df.to_dict()
    request.session['vl_done_df'] = vl_done_df.to_dict()
    request.session['facility_vl'] = facility_vl.to_dict()
    request.session['subcounty_vl'] = subcounty_vl.to_dict()
    hvl_linelist = hvl_linelist.applymap(
        lambda x: x.strftime('%Y-%m-%d %H:%M:%S') if isinstance(x, pd.Timestamp) else x)
    if "HVL" in hvl_linelist.columns:
        del hvl_linelist["V.L"]
    hvl_linelist = hvl_linelist.reset_index(drop=True)
    hvl_linelist.index = range(1, len(hvl_linelist) + 1)
    hvl_linelist_facility.index = range(1, len(hvl_linelist_facility) + 1)
    request.session['hvl_linelist'] = hvl_linelist.to_dict()

    llv_linelist = prepare_to_send_via_sessions(llv_linelist)
    request.session['llv_linelist'] = llv_linelist.to_dict()

    facility_resuppression_status = prepare_to_send_via_sessions(facility_resuppression_status)
    request.session['facility_resuppression_status'] = facility_resuppression_status.to_dict()
    confirm_rx_failure = prepare_to_send_via_sessions(confirm_rx_failure)
    confirm_rx_failure = confirm_rx_failure[list(confirm_rx_failure.columns[0:27])]
    request.session['confirm_rx_failure'] = confirm_rx_failure.to_dict()

    date_cols = [col for col in llv_linelist_facility.columns if "date" in col.lower()]
    for col in date_cols:
        llv_linelist_facility[col] = pd.to_datetime(llv_linelist_facility[col])
        llv_linelist_facility[col] = llv_linelist_facility[col].dt.date
    llv_linelist_facility.index = range(1, len(llv_linelist_facility) + 1)
    request.session['llv_linelist_facility'] = llv_linelist_facility.to_dict()

    date_cols = [col for col in hvl_linelist.columns if "date" in col.lower()]
    for col in date_cols:
        hvl_linelist[col] = pd.to_datetime(hvl_linelist[col])
        hvl_linelist[col] = hvl_linelist[col].dt.date
    request.session['hvl_linelist_facility'] = hvl_linelist_facility.to_dict()

    dfs_vl_uptake = {f"{filter_text} VL Results by sex and age": all_results_df,
                     f"{filter_text} VL Results by sub county": subcounty_,
                     "DSD: TX _PVLS (NUMERATOR)": facility_less_1000_df, "DSD: TX _PVLS (DENOMINATOR)": vl_done_df}
    dfs_vl_supp = {
        "Sub counties viral suppression": subcounty_vl, "Facilities viral suppression": facility_vl,
        "Suspected Treatment Failure (STF) line list": hvl_linelist,
        "Suspected Treatment Failure (STF) per facility (>=1000 cp/ml)": hvl_linelist_facility,
        "LLV line list (200 -999 cp/ml)": llv_linelist,
        "LLV per facility (200 -999 cp/ml)": llv_linelist_facility,
    }
    facility_resuppression_status = facility_resuppression_status.reset_index(drop=True)
    facility_resuppression_status.index = range(1, len(facility_resuppression_status) + 1)

    confirm_rx_failure = confirm_rx_failure.reset_index(drop=True)
    confirm_rx_failure.index = range(1, len(confirm_rx_failure) + 1)
    re_supp_dict = {
        "Facilities Resuppression Status": facility_resuppression_status,
        "Resuppression Linelist": confirm_rx_failure,
    }
    # Convert dict_items into a list
    dictionary = get_key_from_session_names(request)
    context = {
        "form": form,
        "dictionary": dictionary,
        "vs_text": vs_text,
        "facility_analyzed_text": facility_analyzed_text,
        "dfs_vl_uptake": dfs_vl_uptake,
        "dfs_vl_supp": dfs_vl_supp,
        "monthly_trend_fig": monthly_trend_fig,
        "weekly_trend_fig": weekly_trend_fig,
        "hvl_sex_age_fig": hvl_sex_age_fig,
        "llv_sex_age_fig": llv_sex_age_fig,
        "subcounty_fig": subcounty_fig,
        "monthly_hvl_trend_fig": monthly_hvl_trend_fig,
        "monthly_llv_trend_fig": monthly_llv_trend_fig,
        "date_picker_form": date_picker_form,
        "data_filter_form": data_filter_form,
        "dqa_type": "viral_load",
        "hvl_linelist": hvl_linelist,
        "llv_linelist": llv_linelist,
        "hvl_linelist_facility": hvl_linelist_facility,
        "llv_linelist_facility": llv_linelist_facility,
        "llv_linelist_facility_shape": llv_linelist_facility.shape[0],
        "re_supp_dict": re_supp_dict,
        "justification_fig": justification_fig,
    }

    return render(request, 'data_analysis/vl.html', context)
