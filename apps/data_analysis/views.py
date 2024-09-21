import calendar
import hashlib
import re
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
# Create your views here.
from django.utils.datastructures import MultiValueDictKeyError
from django.views.generic import FormView
from plotly import io as pio
from plotly.offline import plot
from plotly.subplots import make_subplots

from apps.data_analysis.forms import DataFilterForm, DateFilterForm, EmrFileUploadForm, FileUploadForm, \
    MultipleUploadForm
from apps.data_analysis.models import FYJHealthFacility, RTKData
from .filters import RTKDataFilter, RTKInventoryFilter
from ..cqi.models import Facilities, Sub_counties
from ..cqi.views import bar_chart
from ..labpulse.models import Cd4traker


# from silk.profiling.profiler import silk_profile


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


def rename_khis_col(df1, fyj_facility_mfl_code):
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
    df1 = rename_khis_col(df1, fyj_facility_mfl_code)

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


def merge_dfs(df, other_adult_df, other_adult_df_columns):
    other_adult_df = other_adult_df.merge(df, left_on="organisationunitcode", right_on="MFL Code", how="left")
    county_subcounty_cols = ['County', 'Subcounty']
    other_adult_df = other_adult_df[county_subcounty_cols + other_adult_df_columns]
    return other_adult_df, county_subcounty_cols


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
    other_paeds_bottles_df_columns = list(other_paeds_bottles_df.columns)
    other_paeds_bottles_df, county_subcounty_cols = merge_dfs(df, other_paeds_bottles_df,
                                                              other_paeds_bottles_df_columns)
    other_paeds_bottles_df['Other (Pediatric) bottles'] = other_paeds_bottles_df[othercolumns].sum(
        axis=1)
    paeds_others_filename = f"{filename}_other_paediatric"
    request.session['paediatric_report'] = other_paeds_bottles_df.to_dict()
    other_paeds_bottles_df_file = other_paeds_bottles_df.copy()

    other_paeds_bottles_df = other_paeds_bottles_df.drop(othercolumns + county_subcounty_cols, axis=1)

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
    other_adult_df_columns = list(other_adult_df.columns)
    other_adult_df, county_subcounty_cols = merge_dfs(df, other_adult_df, other_adult_df_columns)
    other_adult_df['Other (Adult) bottles'] = other_adult_df[othercolumns].sum(axis=1)
    adult_others_filename = f"{filename}_other_adult"
    request.session['adult_report'] = other_adult_df.to_dict()
    other_adult_df_file = other_adult_df.copy()

    other_adult_df = other_adult_df.drop(othercolumns + county_subcounty_cols, axis=1)

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
    final_df = pmp_report = pd.DataFrame()
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
    month_names_str = ""
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
                                other_paeds_bottles_df_file, reporting_errors_df, reporting_error_filename = \
                                analyse_pharmacy_data(request, df, df1)
                            # Compile PMP report
                            pmp_report = compile_pmp_report(final_df, other_adult_df_file, other_paeds_bottles_df_file,
                                                            filename)
                            month_names = final_df['periodname'].unique()
                            month_names_str = "_".join(month_names) if len(month_names) > 1 else month_names[0]
                            if len(month_names) > 1:
                                month_names_str = month_names_str.rsplit("_", 1)[0] + "" + \
                                                  month_names_str.rsplit("_", 1)[1]
                    else:
                        message = f"Please generate and upload either the Total Quantity issued this month or End of " \
                                  f"Month " \
                                  f"Physical Stock Count CSV file from <a href='{url}'>KHIS's website</a>."
                        messages.success(request, message)
                else:
                    message = f"Please generate and upload either the Total Quantity issued this month or End " \
                              f"of Month Physical Stock Count CSV file from <a href='{url}'>KHIS's website</a>."
                    messages.success(request, message)
                    return redirect('load_data_pharmacy')
            else:
                message = f"Please generate and upload either the Total Quantity issued this month or End of Month " \
                          f"Physical Stock Count CSV file from <a href='{url}'>KHIS's website</a>."
                messages.success(request, message)
                return redirect('load_data_pharmacy')
        except MultiValueDictKeyError:
            context = {
                "final_df": final_df, "pmp_report": pmp_report,
                "pmp_report_filename": f"{filename}_pmp_report {month_names_str}",
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
    request.session['pmp_report'] = pmp_report.to_dict()
    # Convert dict_items into a list
    dictionary = get_key_from_session_names(request)
    context = {
        "final_df": final_df, "pmp_report": pmp_report,
        "pmp_report_filename": f"{filename}_pmp_report {month_names_str}",
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
    df[col_name] = df[col_name].dt.days
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
    facilities_collect_receipt_tat = facilities_collect_dispatch_tat = sub_counties_collect_receipt_tat = \
        sub_counties_collect_dispatch_tat = hubs_collect_receipt_tat = hubs_collect_dispatch_tat = \
        counties_collect_receipt_tat = counties_collect_dispatch_tat = program_collect_dispatch_tat = \
        program_collect_receipt_tat = pd.DataFrame()
    facility_c_r_filename = facility_c_d_filename = subcounty_c_r_filename = subcounty_c_d_filename = dictionary = \
        target_text = hub_c_r_filename = hub_c_d_filename = county_c_r_filename = county_c_d_filename = \
        program_c_d_filename = program_c_r_filename = hub_viz = fyj_viz = county_viz = sub_county_viz = None
    date_picker_form = DateFilterForm(request.POST or None)
    form = MultipleUploadForm(request.POST or None)

    if not request.user.first_name:
        return redirect("profile")
    # if request.method == 'POST' and "file" in request.FILES:
    if request.method == 'POST':
        try:
            if request.method == 'POST':
                form = MultipleUploadForm(request.POST, request.FILES)
                url = 'https://eiddash.nascop.org/reports/EID'
                if form.is_valid():
                    uploaded_files = request.FILES.getlist('files')
                    # Check if all uploaded files are CSV files
                    all_csv_files = all(file.name.endswith('.csv') for file in uploaded_files)
                    if all_csv_files:
                        dfs = []
                        for i in uploaded_files:
                            dfs.append(pd.read_csv(i))
                        df = pd.concat(dfs)
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
    nairobi_all_rate = nairobi_all.groupby(['month/year', 'date'])[
        'F-MAPS Revision 2019 Reporting rate (%)'].mean(numeric_only=True).reset_index().sort_values('date')
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
    overall_df = nairobi_730b.groupby(['month/year', 'date'])[
        rates_cols].mean(numeric_only=True).reset_index().sort_values('date')
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
    # df1 = df1[~df1['facility'].str.contains("adventist centre", case=False)]
    #
    # # Add Hope med C MFL CODE
    # df1.loc[df1['facility'] == "Hope Med C", 'organisationunitcode'] = 19278
    # # st francis
    # # df1.loc[df1['organisationunitcode'] == 13202, 'organisationunitcode'] = 17943
    # df1.loc[df1['facility'].str.contains("st francis comm", case=False), 'organisationunitcode'] = 17943
    #
    # # adventist
    # # df1.loc[df1['organisationunitcode'] == 23385, 'organisationunitcode'] = 18535
    # df1.loc[df1['facility'].str.contains("better living", case=False), 'organisationunitcode'] = 18535
    # df1.loc[df1['facility'].str.contains("better living",
    #                                      case=False),
    # 'facility'] = "Adventist Centre for Care and Support"
    #
    # # illasit
    # # df1.loc[df1['organisationunitcode'] == 20372, 'organisationunitcode'] = 14567
    # df1.loc[df1['facility'].str.contains("illasit h", case=False), 'organisationunitcode'] = 14567
    # # imara
    # # df1.loc[df1['organisationunitcode'] == 17685, 'organisationunitcode'] = 12981
    # df1.loc[df1['facility'].str.contains("imara health", case=False), 'organisationunitcode'] = 12981
    # # mary immaculate
    # df1.loc[
    #     df1['facility'].str.contains("mary immaculate sister", case=False), 'organisationunitcode'] = 13062
    #
    # # biafra lion
    # df1.loc[
    #     df1['facility'].str.contains("biafra lion", case=False), 'organisationunitcode'] = 12883

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
    no_fcdrr = no_fcdrr.groupby(['facility', 'MFL Code', 'month/year'])[
        'Facility - CDRR Revision 2019 Reporting rate (%)'].count().reset_index()

    no_fcdrr_df = no_fcdrr_copy.groupby(['month/year'])['facility'].count().reset_index()
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
    no_fmaps = no_fmaps.groupby(['facility', 'MFL Code', 'month/year'])[
        'F-MAPS Revision 2019 Reporting rate (%)'].count().reset_index()

    no_fmaps_df = no_fmaps_copy.groupby(['month/year'])['facility'].count().reset_index()
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
    data_rate = data.groupby(['month/year', 'date'])[col].mean(numeric_only=True).reset_index().sort_values('date')
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
    overall_df = all_data.groupby(['month/year', 'date'])[
        'F-MAPS Revision 2019 Reporting rate (%)'].mean(numeric_only=True).reset_index().sort_values('date')
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

    program_facilities_rate = program_facilities.groupby(['month/year', 'date'])[
        'F-MAPS Revision 2019 Reporting rate (%)'].mean(numeric_only=True).reset_index().sort_values('date')
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
        return '1-4..'
    elif x == 9:
        return '5-9..'
    elif x == 14:
        return '10-14..'
    elif x == 19:
        return '15-19'
    elif x == 24:
        return '20-24'
    elif x == 25:
        return '25+'


def make_crosstab_facility_age(df):
    """This function makes a crosstab"""
    # create a list with age bands, in the required order
    age = ['1-4.', '5-9.', '10-14.', '15-19', '20-24', '25-29', '30-34', '35-39', '40-44', '45-49', '50-54', '55-59',
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
        return '1-4.'
    elif x == 9:
        return '5-9.'
    elif x == 14:
        return '10-14.'
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
    age = ["Missing age", '1-4.', '5-9.', '10-14.', '15-19', '20-24', '25-29', '30-34', '35-39', '40-44', '45-49',
           '50-54',
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
    df['months since last VL'] = (df['months since last VL'].dt.days / 30.44).round()
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
    subcounty_vl = new_df.groupby(group_by_cols + ['Viral Load'])['V.L'].sum().reset_index()
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
        newdf_HVL.groupby(['Month', 'Month vl Tested', 'period', 'Year vl Tested'])[
            'V.L'].sum().reset_index().sort_values(['Year vl Tested', 'Month'])
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

    hvl_linelist_facility = hvl_linelist.groupby(["Facility Name"])[
        'V.L'].sum(numeric_only=True).reset_index().sort_values("V.L", ascending=False)
    hvl_linelist_facility['%'] = round(
        hvl_linelist_facility['V.L'] / sum(hvl_linelist_facility['V.L']) * 100, 1)
    hvl_linelist_facility = hvl_linelist_facility.rename(columns={"V.L": "STF"})

    newdf_HVL_age_sex = newdf_HVL.groupby(["Age", "Sex"])[
        'V.L'].sum(numeric_only=True).reset_index().sort_values("V.L", ascending=False)
    newdf_HVL_age_sex['%'] = round(
        newdf_HVL_age_sex['V.L'] / sum(newdf_HVL_age_sex['V.L']) * 100,
        1)
    newdf_HVL_age_sex = newdf_HVL_age_sex.rename(columns={"V.L": "HVL"})
    newdf_HVL_age_sex['HVL %'] = newdf_HVL_age_sex['HVL'].astype(str) + " (" + \
                                 newdf_HVL_age_sex[
                                     '%'].astype(str) + "%)"
    newdf_HVL_age_sex["Age"] = pd.Categorical(newdf_HVL_age_sex["Age"],
                                              categories=['1-4.', '5-9.', '10-14.', '15-19',
                                                          '20-24',
                                                          '25-29', '30-34', '35-39',
                                                          '40-44',
                                                          '45-49', '50-54',
                                                          '55-59', '60-64', '65+'],
                                              ordered=True)
    newdf_HVL_age_sex.sort_values('Age', inplace=True)
    return newdf_HVL_age_sex, hvl_linelist, hvl_linelist_facility


def calculate_overall_resuppression_rate(confirm_rx_failure, newdf_HVL, newdf_llv, df):
    # Ensure 'Patient CCC No' columns are of string type
    confirm_rx_failure["Patient CCC No"] = confirm_rx_failure["Patient CCC No"].astype(str)
    newdf_HVL["Patient CCC No"] = newdf_HVL["Patient CCC No"].astype(str)
    newdf_llv["Patient CCC No"] = newdf_llv["Patient CCC No"].astype(str)
    df["Patient CCC No"] = df["Patient CCC No"].astype(str)

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

    resuppression_rate_df = resuppression_status.groupby(["resuppression status"])['V.L'].sum().reset_index()
    resuppression_rate_df = resuppression_rate_df.sort_values("V.L", ascending=False)
    resuppression_rate_df['%'] = round(resuppression_rate_df['V.L'] / sum(resuppression_rate_df['V.L']) * 100,
                                       1).astype(str) + "%"
    return resuppression_rate_df, resuppression_status


def calculate_facility_resuppression_rate(resuppression_status):
    facility_resuppression_status = \
        resuppression_status.groupby(['Facility Name', 'Facility Code', "resuppression status"])[
            'V.L'].sum().reset_index()
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
                                                                 )['V.L'].sum().reset_index()

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


def prepare_data(main_df: pd.DataFrame, other_adult_df: pd.DataFrame,
                 other_paeds_df: pd.DataFrame, filename):
    """Prepare data for merging"""
    other_adult_df.columns = [
        'County', 'Subcounty', 'organisationunitname',
        'MFL Code', 'periodname', 'ABC) 300mg Tablets 60s',
        'ABC/3TC 600mg/300mg FDC Tablets 60s', 'ATV/r 300/100mg Tablets 30s',
        'DRV 600mg Tablets 60s', 'ETV 200mg Tablets 60s',
        '3TC 150mg Tablets 60s', 'RAL 400mg Tablets 60s',
        'RTV 100mg Tablets 60s', 'TDF/3TC FDC (300/300mg) Tablets 30s',
        'AZT 300mg Tablets 60s', 'AZT/3TC FDC (300/150mg) Tablets 30s',
        'LPV/r 200/50mg Tablets 120s', 'DTG 50mg tabs 30s',
        'Other (Adult) bottles'
    ]

    other_paeds_df.columns = [
        'County', 'Subcounty', 'organisationunitname',
        'MFL Code', 'periodname', 'ABC/3TC 120mg/60mg',
        'ABC/3TC 60mg/30mg FDC Tablets 60s', 'ATV 100mg Caps 60s',
        'DRV 150mg Tablets 240s', 'DRV 75mg Tablets 480s',
        'DRV susp 100mg/ml  (200ml Bottles) 200ml bottle',
        'ETV 100mg Tablets 60s', 'ETV 25mg Tablets 60s',
        '3TC liquid 10mg/ml (240ml Bottles) 240ml bottle',
        'RAL 25mg Tablets 60s',
        'Ritonavir liquid 80mg/ml (90ml Bottles) 90ml bottle',
        'AZT/3TC FDC (60/30mg) Tablets 60s', 'Other (Pediatric) bottles'
    ]
    # Convert MFL code to int
    main_df = main_df[main_df["County"] != ""]
    main_df['MFL Code'] = main_df['MFL Code'].astype(int)
    other_adult_df['MFL Code'] = other_adult_df['MFL Code'].astype(int)
    other_paeds_df['MFL Code'] = other_paeds_df['MFL Code'].astype(int)

    total_df = main_df[[
        'County', 'Health Subcounty', 'Subcounty',
        'organisationunitname', 'MFL Code', 'Hub(1,2,3 o 4)', 'periodname',
        'TLD 30s', 'TLD 90s', 'TLD 180s', 'TL_400 30', 'TLE_400 90s',
        'TLE_600 30s', 'LPV/r 40/10', 'LPV/r 100/25', 'DTG 10', 'NVP 200',
        'NVP (Pediatric) bottles', 'Other (Adult) bottles',
        'Other (Pediatric) bottles'
    ]]
    col_name = f"{filename.upper()} Bottles(Units)"
    total_df = total_df.melt(id_vars=[
        'County', 'Health Subcounty', 'Subcounty',
        'organisationunitname', 'MFL Code', 'Hub(1,2,3 o 4)', 'periodname'
    ],
        value_vars=[
            'TLD 30s', 'TLD 90s', 'TLD 180s', 'TL_400 30',
            'TLE_400 90s', 'TLE_600 30s', 'LPV/r 40/10',
            'LPV/r 100/25', 'DTG 10', 'NVP 200',
            'NVP (Pediatric) bottles',
            'Other (Adult) bottles',
            'Other (Pediatric) bottles'
        ], value_name=col_name)

    total_df = total_df.groupby("County")[col_name].sum().reset_index()
    # merge dfs together
    merged = main_df.merge(
        other_adult_df,
        on=["County", "MFL Code", "organisationunitname", "periodname"]).merge(
        other_paeds_df,
        on=["County", "MFL Code", "organisationunitname", "periodname"])

    return merged, total_df


def compile_pmp_report(main_df: pd.DataFrame, other_adult_df: pd.DataFrame,
                       other_paeds_df: pd.DataFrame, filename) -> pd.DataFrame:
    """Compile the PMP report"""
    prepared_data, total_df = prepare_data(main_df, other_adult_df, other_paeds_df, filename)
    pmp = prepared_data.groupby(['County'])[[
        'TLD 90s', 'DTG 10', 'DTG 50mg tabs 30s', 'ABC/3TC 120mg/60mg', 'CTX 240mg/5ml', '3HP 300/300',
    ]].sum().reset_index()
    pmp = total_df.merge(pmp, on="County", how="left")
    pmp.index += 1
    pmp.loc['Total'] = pmp.sum(numeric_only=True)
    pmp.loc['Total'] = pmp.loc['Total'].fillna("")
    for col in pmp.columns[1:]:
        pmp[col] = pmp[col].astype(int)
    return pmp


def prepare_to_send_via_sessions(llv_linelist):
    llv_linelist = llv_linelist.applymap(
        lambda x: x.strftime('%Y-%m-%d %H:%M:%S') if isinstance(x, pd.Timestamp) else x)
    # Handle NaT values by replacing them with None
    llv_linelist = llv_linelist.where(pd.notnull(llv_linelist), None)
    if "HVL" in llv_linelist.columns:
        del llv_linelist["V.L"]
    llv_linelist = llv_linelist.reset_index(drop=True)
    llv_linelist.index = range(1, len(llv_linelist) + 1)

    return llv_linelist


def box_plot_chart(df, y_values_list, title, labels=None):
    fig = px.box(df, y=y_values_list,
                 labels=labels,
                 title=title, height=450)
    return plot(fig, include_plotlyjs=False, output_type="div")


def show_period_hvl(df):
    df = df.copy()
    date_columns = [x for x in df.columns if "Date" in x]
    # Loop through each date column and convert to datetime format
    for column in date_columns:
        df[column] = pd.to_datetime(df[column], errors='coerce')

    # Replace this with the actual way you get the current date, e.g., pd.to_datetime('today') or pd.Timestamp.today()
    current_date = pd.to_datetime('today')
    string_date = current_date.strftime('%d-%b-%Y')
    # Calculate the difference in days between 'Date Collected' and the current date
    df[f'period with HVL (Collection - {string_date})'] = (current_date - df['Date Collected']).dt.days
    df[f'period with HVL (Dispatch - {string_date})'] = (current_date - df['Date Dispatched']).dt.days
    period_hvl_box_plot_fig = box_plot_chart(df, [f'period with HVL (Collection - {string_date})',
                                                  f'period with HVL (Dispatch - {string_date})'],
                                             title=f'Box Plot of Period with HVL N={df.shape[0]} ',
                                             labels={'value': 'Period with HVL (days)',
                                                     'variable': 'Category'})
    return period_hvl_box_plot_fig


@login_required(login_url='login')
def viral_load(request):
    all_results_df = subcounty_ = facility_less_1000_df = vl_done_df = subcounty_vl = facility_vl = hvl_linelist = \
        llv_linelist = hvl_linelist_facility = llv_linelist_facility = facility_resuppression_status = \
        confirm_rx_failure = pd.DataFrame()
    vs_text = facility_analyzed_text = subcounty_fig = monthly_trend_fig = weekly_trend_fig = monthly_hvl_trend_fig = \
        hvl_sex_age_fig = llv_sex_age_fig = monthly_llv_trend_fig = justification_fig = period_hvl_box_plot_fig = None
    filter_text = "All"

    # form = FileUploadForm(request.POST or None)
    form = MultipleUploadForm(request.POST or None)
    date_picker_form = DateFilterForm(request.POST or None)
    data_filter_form = DataFilterForm(request.POST or None)
    if not request.user.first_name:
        return redirect("profile")
    if request.method == 'POST':
        try:
            form = MultipleUploadForm(request.POST, request.FILES)
            message = "It seems that the dataset you uploaded is incorrect. To proceed with the analysis, " \
                      "kindly upload detailed Viral load CSV file. Please generate this file from the website link " \
                      "below and ensure it is in CSV format before uploading it. You can find detailed " \
                      "instructions on how to upload the file below. Thank you."
            if form.is_valid():
                # file = request.FILES['file']
                uploaded_files = request.FILES.getlist('files')
                # Check if all uploaded files are CSV files
                all_csv_files = all(file.name.endswith('.csv') for file in uploaded_files)
                if all_csv_files:
                    dfs = []
                    for i in uploaded_files:
                        dfs.append(pd.read_csv(i))
                    df = pd.concat(dfs)
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
                                df.groupby(['Month', 'Month vl Tested', 'period', 'Year vl Tested'])[
                                    'V.L'].sum().reset_index().sort_values(['Year vl Tested', 'Month'])
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
                            #####################
                            # PERIOD ON HVL
                            ####################
                            period_hvl_box_plot_fig = show_period_hvl(hvl_linelist)
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
                "justification_fig": justification_fig, "period_hvl_box_plot_fig": period_hvl_box_plot_fig,
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
        hvl_linelist[col] = pd.to_datetime(hvl_linelist[col], errors='coerce')
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
        "justification_fig": justification_fig, "period_hvl_box_plot_fig": period_hvl_box_plot_fig,
    }

    return render(request, 'data_analysis/vl.html', context)


def convert_month_year(month_year):
    month_name, year = month_year.split()
    month_abbr = calendar.month_abbr[list(
        calendar.month_name).index(month_name)]
    year = year[-2:]
    return f"{month_abbr}-{year}"


def read_uploaded_file(request, uploaded_files):
    expected_columns = [
        'County', 'Sub-County', 'MFL Code', 'Facility Name',
        'Commodity Name', 'Beginning Balance', 'Quantity Received',
        'Quantity Used', 'Quantity Requested', 'Tests Done', 'Losses',
        'Positive Adjustments', 'Negative Adjustments', 'Ending Balance',
        'Days Out of Stock', 'Quantity Expiring in 6 Months'
    ]
    dfs = []
    for file in uploaded_files:
        pattern = r'\((\w+ \d{4})\)'
        file_name = file.name.split('.')[0].title()
        month_year = re.findall(pattern, file_name)
        if file.name.endswith('.xlsx'):
            if month_year:
                month_year = convert_month_year(month_year[0])
                df = pd.read_excel(file)
                actual_columns = df.columns.tolist()
                if actual_columns == expected_columns:
                    df.insert(0, "month", f"{month_year}")
                    df['month_column'] = pd.to_datetime(df['month'], format='%b-%y') + pd.offsets.MonthEnd(0)
                    dfs.append(df)
                else:
                    messages.error(request, f"File: {file.name}, does not have the expected column names")
            else:
                messages.error(request, f"File: {file.name}, does not have the expected month name. "
                                        f"Check if the file name was changed ")
        else:
            messages.error(request, f"File: {file.name} is not an .xlsx file")
    if len(dfs) > 0:
        final_df = pd.concat(dfs)
    else:
        final_df = None
    return final_df


class UploadRTKDataView(LoginRequiredMixin, FormView):
    login_url = 'login'
    template_name = 'data_analysis/rtk.html'
    form_class = MultipleUploadForm
    success_url = reverse_lazy('upload_rtk')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dqa_type'] = 'upload_rtk'
        return context

    def form_valid(self, form):
        """
        Handle file upload and data import.

        :param form: The form containing the uploaded files.
        :return: A redirect to the RTK data upload page.
        """
        # Get the uploaded files from the form
        uploaded_files = self.request.FILES.getlist('files')

        # Read the uploaded data into a pandas DataFrame
        data = read_uploaded_file(self.request, uploaded_files)

        # Get the unique facility names, MFL codes, and commodity names from the data
        months = set(data['month'].unique())
        mfl_codes = set(data['MFL Code'].unique())
        commodities = set(data['Commodity Name'].unique())

        # Check if any of the data already exists in the database
        existing_facilities = RTKData.objects.filter(
            month__in=months,
            commodity_name__in=commodities,
            mfl_code__in=mfl_codes
        ).values_list('facility_name', 'month').distinct().order_by('facility_name')

        if existing_facilities:
            # Format an error message if any data already exists
            error_message = "The following data already exists:\n\n"
            for facility, month in existing_facilities:
                error_message += f"- {facility}: {month}\n"
            # If there is an error message, display it and redirect the user back to the upload page
            messages.error(self.request, error_message)
            return redirect('upload_rtk')

        # If there is no error message, save the data to the database using a transaction
        if data is not None:
            with transaction.atomic():
                for index, row in data.iterrows():
                    rtk_data = RTKData(
                        month=row['month'],
                        county=row['County'],
                        sub_county=row['Sub-County'],
                        mfl_code=row['MFL Code'],
                        facility_name=row['Facility Name'],
                        commodity_name=row['Commodity Name'],
                        beginning_balance=row['Beginning Balance'],
                        quantity_received=row['Quantity Received'],
                        quantity_used=row['Quantity Used'],
                        quantity_requested=row['Quantity Requested'],
                        tests_done=row['Tests Done'],
                        losses=row['Losses'],
                        positive_adjustments=row['Positive Adjustments'],
                        negative_adjustments=row['Negative Adjustments'],
                        ending_balance=row['Ending Balance'],
                        days_out_of_stock=row['Days Out of Stock'],
                        quantity_expiring_in_6_months=row['Quantity Expiring in 6 Months'],
                        month_column=row['month_column'],
                    )
                    rtk_data.save()
            messages.success(self.request, 'Data uploaded successfully!')

        # Return a redirect to the RTK data upload page
        return super().form_valid(form)


# @silk_profile(name='trend_variances')
def trend_variances(negative_variances_df, title, bar_grouping=False):
    if bar_grouping:
        # Define a color map for resistance levels
        color_map = {'Negative': '#e41a1c', 'Positive': '#4daf4a',

                     }
        fig = px.bar(negative_variances_df, x="month_num", y="Variance", color="variance type", text="Variance",
                     title=title, height=400, barmode="group", color_discrete_map=color_map)

        # Adjust the legend
        fig.update_layout(legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ))
        # Make text bigger and bold
        fig.update_traces(textfont=dict(size=16, color='black', family='Arial',
                                        #                                         weight='bold'
                                        ))

        # Ensure all month names are displayed on x-axis
        fig.update_xaxes(tickmode='array',
                         tickvals=negative_variances_df['month_num'],
                         ticktext=negative_variances_df['month_num'].dt.strftime('%b-%y'))

        # Adjust layout for better visibility of text annotations
        fig.update_layout(
            annotations=[dict(xref='paper', yref='paper', x=1, y=-0.15, showarrow=False, text="Source: HCMP")])
    else:
        fig = px.bar(negative_variances_df, x="month_num", y="Variance", text="Variance", title=title)

    return plot(fig, include_plotlyjs=False, output_type="div")


def get_variance_df(df):
    overall_variances_trend = df.groupby(["month", "month_num"])['Variance'].sum().reset_index().sort_values(
        "month_num")
    positive_variances_df = df[df['Variance'] > 0]

    positive_variances_df = positive_variances_df.groupby(["month", "month_num"])[
        'Variance'].sum().reset_index().sort_values("month_num")
    positive_variances_df['variance type'] = "Positive"
    negative_variances_df = df[df['Variance'] < 0]
    negative_variances_df = negative_variances_df.groupby(["month", "month_num"])[
        'Variance'].sum().reset_index().sort_values("month_num")
    negative_variances_df['Variance'] = negative_variances_df['Variance'].abs()
    negative_variances_df['variance type'] = "Negative"
    pos_neg_var = pd.concat([positive_variances_df, negative_variances_df]).sort_values("month_num")
    no_variances_df = df[df['Variance'] == 0]
    no_variances_df = no_variances_df.groupby(["month", "month_num"])[
        'Facility Name'].count().reset_index().sort_values("month_num")
    return no_variances_df, pos_neg_var, negative_variances_df, positive_variances_df, overall_variances_trend


def most_frequent_bars(most_frequent_sub_counties, county, x_axis, text, title, show_source=False, height=400,
                       y_axis_title="Frequency"):
    fig = px.bar(most_frequent_sub_counties, x=x_axis, y='count', text=text,
                 title=title,
                 height=height,
                 labels={'count': y_axis_title, 'Sub-County': 'Sub-County'},
                 color='count',  # You can use color to represent the frequency
                 color_continuous_scale='bluered',  # Choose a color scale
                 )

    fig.update_traces(textfont=dict(size=18, color='black', family='Arial',
                                    #                                         weight='bold'
                                    ))
    if show_source:
        fig.update_layout(
            annotations=[dict(xref='paper', yref='paper', x=1, y=-0.18, showarrow=False, text="Source: HCMP")])

    return plot(fig, include_plotlyjs=False, output_type="div")


def add_percentage_and_count_string(haart_class_df, col):
    # Calculate percentage and round to the nearest integer
    haart_class_df['%'] = round(haart_class_df[col] / haart_class_df[col].sum() * 100).astype(int)

    # Create a new column with count and percentage string
    haart_class_df['count (%)'] = haart_class_df[col].astype(str) + " (" + haart_class_df['%'].astype(str) + "%)"

    return haart_class_df


def get_monthly_frequency(variances, col):
    number_of_facilities = len(variances['Facility Name'].unique())
    variances_trend_df = variances.groupby(["month", "month_num"])[col].count().reset_index().sort_values(
        "month_num")
    variances_trend_df = variances_trend_df.rename(columns={col: "Frequency"})
    variances_trend_df = add_percentage_and_count_string(variances_trend_df, "Frequency")
    return variances_trend_df, number_of_facilities


def trend_variances_(negative_variances_df,
                     title,
                     y_axis,
                     x_axis,
                     text,
                     bar_grouping=False,
                     color=None):
    if bar_grouping:
        # Define a color map for resistance levels
        color_map = {'Negative': '#e41a1c', 'Positive': '#4daf4a'}
        fig = px.bar(negative_variances_df,
                     x=x_axis,
                     y=y_axis,
                     color=color,
                     text=text,
                     title=title,
                     height=400,
                     barmode="group",
                     color_discrete_map=color_map)
    else:
        fig = px.bar(negative_variances_df,
                     x=x_axis,
                     y=y_axis,
                     text=text,
                     title=title)
        # Adjust the legend
        fig.update_layout(legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        # Make text bigger and bold
        fig.update_traces(
            textfont=dict(size=16, color='black', family='Arial'))

        # Ensure all month names are displayed on x-axis
        fig.update_xaxes(
            tickmode='array',
            tickvals=negative_variances_df['month_num'],
            ticktext=negative_variances_df['month_num'].dt.strftime('%b-%y'))

        # Adjust layout for better visibility of text annotations
        fig.update_layout(annotations=[
            dict(xref='paper',
                 yref='paper',
                 x=1,
                 y=-0.15,
                 showarrow=False,
                 text="Source: HCMP")
        ])

    return plot(fig, include_plotlyjs=False, output_type="div")


def convert_to_df(rtk_qs):
    data = list(rtk_qs.values_list('month', 'county', 'sub_county', 'mfl_code', 'facility_name',
                                   'commodity_name', 'beginning_balance', 'quantity_received',
                                   'quantity_used', 'quantity_requested', 'tests_done', 'losses',
                                   'positive_adjustments', 'negative_adjustments', 'ending_balance',
                                   'days_out_of_stock', 'quantity_expiring_in_6_months'))

    df = pd.DataFrame(data, columns=[
        'month', 'County', 'Sub-County', 'MFL Code', 'Facility Name',
        'Commodity Name', 'Beginning Balance', 'Quantity Received',
        'Quantity Used', 'Quantity Requested', 'Tests Done', 'Losses',
        'Positive Adjustments', 'Negative Adjustments', 'Ending Balance',
        'Days Out of Stock', 'Quantity Expiring in 6 Months'
    ])
    return df


# @silk_profile(name='calculate_screening_variances_for_loop')
def calculate_screening_variances(bal):
    bal = bal.copy()  # Make a copy of the DataFrame to avoid modifying the original
    bal.loc[:, 'month_num'] = pd.to_datetime(bal['month'], format="%b-%y")
    bal.loc[:, 'month_year'] = bal['month']
    bal = bal.sort_values("month_num")
    bal.loc[:, 'Previous month Ending Balance'] = bal.groupby(['Facility Name', 'Commodity Name'])[
        'Ending Balance'].shift(1)
    bal = bal.fillna(0)
    bal.loc[:, 'Variance'] = bal['Beginning Balance'].astype(int) - bal['Previous month Ending Balance'].astype(int)
    bal = bal[bal['Previous month Ending Balance'] != 0]
    return bal


def calculate_variances_subcounties(df, variances, col):
    all_subcounty_reports = df[col].value_counts().sort_values(ascending=False).reset_index()

    all_subcounty_reports.columns = [col, 'All reports']
    most_frequent_sub_counties = variances[col].value_counts().sort_values(ascending=False).reset_index()
    most_frequent_sub_counties.columns = [col, 'count']

    most_frequent_sub_counties.columns = [col, 'variant reports']
    subcounty_variance = most_frequent_sub_counties.merge(all_subcounty_reports, on=col)
    subcounty_variance['%'] = round(subcounty_variance['variant reports'] / subcounty_variance['All reports'] * 100,
                                    1)

    subcounty_variance['variance %'] = subcounty_variance['variant reports'].astype(str) + " (" + \
                                       subcounty_variance['%'].astype(str) + "%)"
    subcounty_variance['Concordant report'] = subcounty_variance['All reports'] - subcounty_variance['variant reports']
    subcounty_variance['concor_%'] = round(
        subcounty_variance['Concordant report'] / subcounty_variance['All reports'] * 100,
        1)

    subcounty_variance['Concordant report %'] = subcounty_variance['Concordant report'].astype(str) + " (" + \
                                                subcounty_variance['concor_%'].astype(str) + "%)"
    return subcounty_variance


def show_subcounty_variances(subcounty_variance, county, min_date, max_date, x_axis):
    # Create a bar plot for "All reports"
    fig = px.bar(subcounty_variance, x=x_axis, y="Concordant report", text="Concordant report %", height=550,
                 title=f"{x_axis} Reports and Variances    County : {county}   Period: {min_date} - {max_date}",
                 color_discrete_sequence=['#4daf4a'], hover_data=["Concordant report", "All reports"])

    # Add a bar plot for "variance %" with a secondary y-axis
    fig.add_traces(px.bar(subcounty_variance, x=x_axis, y='%', text='variance %',
                          title="Percentage of Variant Reports",
                          color_discrete_sequence=['#e41a1c'], hover_name='variance %').data)

    # Set the range of the secondary y-axis
    fig.update_layout(yaxis2=dict(overlaying='y', side='right', range=[0, 100]))

    # Update the text font and size
    fig.update_traces(textfont=dict(size=15, color='black', family='Arial'))
    if x_axis == "Hub":
        x_axis = "Hubs"
    else:
        x_axis = "Sub-Counties"

    fig.update_layout(xaxis_title=x_axis, yaxis_title='Reports and Variances')

    fig.update_layout(
        annotations=[dict(xref='paper', yref='paper', x=1, y=-0.15, showarrow=False, text="Source: HCMP")])

    # Show the plot
    return plot(fig, include_plotlyjs=False, output_type="div")


def get_quarter(month: str) -> str:
    """
    This function takes a month string in the format 'Month-Year' and returns the corresponding quarter.

    Parameters:
    month (str): The month string in the format 'Month-Year'.

    Returns:
    str: The quarter string in the format 'QX-Year', where X is the quarter number (1-4).
    """
    # Extract the year from the month string
    year = int(month.split('-')[1])
    # Determine the quarter based on the month
    if 'Oct' in month or 'Nov' in month or 'Dec' in month:
        return f'Q1-{year + 1}'
    elif 'Jan' in month or 'Feb' in month or 'Mar' in month:
        return f'Q2-{year}'
    elif 'Apr' in month or 'May' in month or 'Jun' in month:
        return f'Q3-{year}'
    elif 'Jul' in month or 'Aug' in month or 'Sep' in month:
        return f'Q4-{year}'


def generate_quarter_map(quarters: list) -> dict:
    """
    This function takes a list of quarter strings and returns a dictionary mapping each quarter to the next quarter.

    Parameters:
    quarters (list): A list of quarter strings in the format 'QX-Year', where X is the quarter number (1-4).

    Returns:
    dict: A dictionary mapping each quarter to the next quarter.
    """
    quarter_map = {}
    for quarter in quarters:
        quarter, year = quarter.split('-')
        next_quarter = {'Q1': 'Q2', 'Q2': 'Q3', 'Q3': 'Q4', 'Q4': 'Q1'}[quarter]
        next_year = year if quarter != 'Q4' else str(int(year) + 1)
        quarter_map[quarter + '-' + year] = next_quarter + '-' + next_year
    return quarter_map


# Define a function to extract quarter and year
def extract_quarter_and_year(quarter_fy):
    quarter, year = quarter_fy.split('-')
    return (int(year), {'Q1': 1, 'Q2': 2, 'Q3': 3, 'Q4': 4}[quarter])


def sort_quarter_year(kaj):
    # Filter out NaN values and convert quarters_fy to datetime for sorting
    quarters_filtered = kaj['quarters_fy'].dropna()

    # Sort quarters chronologically
    quarters_sorted = sorted(quarters_filtered.unique(), key=extract_quarter_and_year)
    kaj = kaj.copy()
    kaj['quarters_fy'] = pd.Categorical(kaj['quarters_fy'], categories=quarters_sorted, ordered=True)
    # Sort the DataFrame by quarters_fy
    df_sorted = kaj.sort_values(by='quarters_fy')
    return df_sorted


def process_data(rtk_df, cols_to_use, groupby_period, get_facility_data=None):
    """
   This function processes the data in the given DataFrame.

   Parameters:
   rtk_df (pandas.DataFrame): The input DataFrame.
   cols_to_use (list): A list of column names to be used for summing.
   groupby_period (str): The period to group the data by (e.g. 'quarter', 'year').

   Returns:
   tuple: A tuple containing two DataFrames. The first DataFrame contains the processed data,
          and the second DataFrame contains the filtered data with the beginning balance.
   """
    rtk_df_filtered_ending_bal = pd.DataFrame()
    # Create a copy of the DataFrame
    rtks_df = rtk_df.copy()

    # Apply the get_quarter function to the 'month' column again (not sure why this is done twice)
    rtks_df[f'{groupby_period}'] = rtks_df.apply(lambda row: get_quarter(row['month']), axis=1)

    # Group the DataFrame by county, commodity_name, and quarters_fy, and sum the quantity_received, tests_done,
    # and days_out_of_stock columns
    if get_facility_data is None:
        result = rtks_df.groupby(['County', 'Commodity Name', f'{groupby_period}'])[cols_to_use].sum().reset_index()
    else:
        result = rtks_df.groupby(['County', 'Facility Name', 'Commodity Name', f'{groupby_period}'])[
            cols_to_use].sum().reset_index()

    # Filter the DataFrame to only include rows where the 'month' column contains 'Mar', 'Dec', 'Jun', or 'Sep'
    rtk_df_filtered = rtks_df[(rtks_df['month'].str.contains('Mar|Dec|Jun|Sep'))]

    # Group the filtered DataFrame by county, commodity_name, and quarters_fy, and sum the ending_balance column
    if get_facility_data is None:
        rtk_df_filtered = rtk_df_filtered.groupby(['County', 'Commodity Name', f'{groupby_period}'])[
            'Ending Balance'].sum().reset_index()
    else:
        rtk_df_filtered = rtk_df_filtered.groupby(['County', 'Facility Name', 'Commodity Name', f'{groupby_period}'])[
            'Ending Balance'].sum().reset_index()
        rtk_df_filtered_ending_bal = rtk_df_filtered.copy()

    # Get unique quarters from the filtered DataFrame
    unique_quarters = rtk_df_filtered[f'{groupby_period}'].unique()

    # Generate the quarter map
    quarter_map = generate_quarter_map(unique_quarters)

    # Apply the quarter map to the 'quarters_fy' column
    rtk_df_filtered[f'{groupby_period}'] = rtk_df_filtered[f'{groupby_period}'].map(quarter_map)
    rtk_df_filtered = sort_quarter_year(rtk_df_filtered)
    # Rename the 'ending_balance' column to 'beginning_balance'
    rtk_df_filtered = rtk_df_filtered.rename(columns={"Ending Balance": "Beginning Balance"})

    # Merge the result DataFrame with the filtered DataFrame
    if get_facility_data is None:
        commodity_result = result.merge(rtk_df_filtered, on=['County', 'Commodity Name', f'{groupby_period}'])
        # Rename the columns of the merged DataFrame
        commodity_result = commodity_result[
            ['County', 'Commodity Name', f'{groupby_period}', 'Beginning Balance'] + cols_to_use]
    else:
        commodity_result = result.merge(rtk_df_filtered,
                                        on=['County', 'Facility Name', 'Commodity Name', f'{groupby_period}'])
        if "Ending Balance" in commodity_result.columns:
            del commodity_result["Ending Balance"]

        commodity_result = commodity_result.merge(rtk_df_filtered_ending_bal,
                                                  on=['County', 'Facility Name', 'Commodity Name', 'quarters_fy'])
        commodity_result['Unattributable losses/gains'] = commodity_result["Ending Balance"] - (
                (commodity_result['Beginning Balance'] + commodity_result['Quantity Received'] +
                 commodity_result['Positive Adjustments']) - (
                        commodity_result['Quantity Used'] + commodity_result['Losses'] +
                        commodity_result['Negative Adjustments'])
        )
        # Rename the columns of the merged DataFrame
        commodity_result = commodity_result[
            ['County', 'Facility Name', 'Commodity Name', f'{groupby_period}', 'Beginning Balance'] + cols_to_use + [
                'Unattributable losses/gains']]

        # Final result
    return commodity_result, rtk_df_filtered.reset_index()


@login_required(login_url='login')
def rtk_visualization(request):
    """
    Show visualizations of RTK data.

    :param request: The request object.
    :return: A render object with the visualizations.
    """
    #####################################
    # Get chosen facility type
    #####################################
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
        # record_count = int(request.GET.get('record_count', 10))  # Get the selected record count (default: 10)
        selected_facility_type = request.GET.get('record_count', 'False')
    else:
        selected_facility_type = request.GET.get('record_count', 'True')

    most_frequent_hub_figs = most_frequent_sub_counties_figs = sub_counties_figs = most_frequent_facilities_figs = \
        sub_county_variances_list = None
    hub_variances_list = trend_variances_list = trend_monthly_variances_list = []

    def fetch_past_one_year_cd4_data(request):
        # Get the user's start_date input from the request GET parameters
        start_date_param = request.GET.get('start_date')
        end_date_param = request.GET.get('end_date')
        use_one_year_data = True
        days = 450
        # Use default logic for one year ago
        one_year_ago = datetime.now() - timedelta(days=days)
        one_year_ago = datetime(
            one_year_ago.year,
            one_year_ago.month,
            one_year_ago.day,
            23, 59, 59, 999999
        )

        if start_date_param:
            # Parse the user's input into a datetime object
            start_date = datetime.strptime(start_date_param, '%Y-%m-%d')

            # If the user's input is beyond one year ago, use it
            if start_date < datetime.now() - timedelta(days=days) and (
                    not end_date_param or start_date < datetime.strptime(end_date_param, '%Y-%m-%d')):
                one_year_ago = start_date
                use_one_year_data = False
        # Handle N+1 Query using prefetch_related /lab-pulse/download/{filter_type}
        rtk_query_set = RTKData.objects.filter(month_column__gte=one_year_ago).order_by('facility_name', 'month')

        return rtk_query_set, use_one_year_data

    rtk_qs, use_one_year_data = fetch_past_one_year_cd4_data(request)

    # Convert queryset to dataframe
    # rtk_qs = RTKData.objects.all().order_by('facility_name', 'month')
    rtk_qs_filters = RTKDataFilter(request.GET, queryset=rtk_qs)
    facility_type_options = [("False", "FYJ"), ("True", "All")]
    df = convert_to_df(rtk_qs_filters.qs)
    dqa_type = "rtk"

    # Generate a cache key based on relevant data
    data_hash = hashlib.sha256(
        f"{df.to_dict()}:{request.GET.get('start_date')}:{request.GET.get('end_date')}:"
        f"{request.GET.get('record_count')}:{request.GET.get('commodity_name')}:{request.GET.get('sub_county')}:"
        f"{request.GET.get('county')}:{request.GET.get('facility_name')}".encode()
    ).hexdigest()
    cache_key = f'rtk_visualization:{data_hash}'

    # Check if the view is cached
    cached_view = cache.get(cache_key)
    if cached_view is not None:
        return cached_view

    if df.shape[0] > 0:
        # Get all facilities
        if selected_facility_type == "True":
            all_facilities = True
        else:
            all_facilities = False

        if not all_facilities:
            type_of_facilities = "FYJ"
            # Get FYJ facilities
            facilities = Facilities.objects.all()
            # Filter data by FYJ facilities
            df = df[df['MFL Code'].isin([facility.mfl_code for facility in facilities])]
            # Extracting hub information from Sub_counties model
            sub_county_hub_mapping = Sub_counties.objects.values('facilities__mfl_code', 'hub__hub')
            facility_hub_df = pd.DataFrame(sub_county_hub_mapping)
            facility_hub_df.columns = ["MFL Code", "Hub"]
            df = df.merge(facility_hub_df, on='MFL Code', how="left")
            df = df[~df['Hub'].isnull()]
            bal = df[['month', 'County', 'Sub-County', "Hub", 'MFL Code', 'Facility Name',
                      'Commodity Name', 'Beginning Balance', 'Ending Balance']]
            bal = bal.drop_duplicates()


        else:
            type_of_facilities = "ALL"
            bal = df[['month', 'County', 'Sub-County', 'MFL Code', 'Facility Name',
                      'Commodity Name', 'Beginning Balance', 'Ending Balance']]
        df = calculate_screening_variances(bal)

        trend_variances_list = []
        for county in df['County'].unique():
            no_variances_df, pos_neg_var, negative_variances_df, positive_variances_df, overall_variances_trend = get_variance_df(
                df[df['County'] == county])
            trend_variances_list.append(trend_variances(pos_neg_var,
                                                        f"Monthly Trend of Variances (Positive and Negative)  {type_of_facilities} facilities : {county} County",
                                                        bar_grouping=True))

        variances = df[df['Variance'] != 0].reset_index(drop=True)
        max_date = variances["month_num"].max().date()
        min_date = variances["month_num"].min().date()
        try:
            max_date = max_date.strftime("%b-%Y")
            min_date = min_date.strftime("%b-%Y")
        except ValueError:
            max_date = ""
            min_date = ""
        if not all_facilities:
            variances = variances[
                ['month_year', 'month_num', 'month', 'County', 'Sub-County', "Hub", 'MFL Code', 'Facility Name',
                 'Commodity Name',
                 'Beginning Balance', 'Ending Balance',
                 'Previous month Ending Balance', 'Variance']]
        else:
            variances = variances[
                ['month_year', 'month_num', 'month', 'County', 'Sub-County', 'MFL Code', 'Facility Name',
                 'Commodity Name',
                 'Beginning Balance', 'Ending Balance',
                 'Previous month Ending Balance', 'Variance']]

        trend_monthly_variances_list = []
        for county in df['County'].unique():
            county_specific_df = variances[variances['County'] == county]
            variances_trend_df, number_of_facilities = get_monthly_frequency(county_specific_df, 'Facility Name')
            trend_monthly_variances_list.append(trend_variances_(variances_trend_df,
                                                                 f"Facility Monthly Variances       N= {len(variances['Facility Name'].unique())} {type_of_facilities}  Facilities   {county} County      Period: {min_date} - {max_date}",
                                                                 y_axis="Frequency",
                                                                 x_axis="month_num",
                                                                 text="count (%)"))

        most_frequent_sub_counties_figs = []
        for county in df['County'].unique():
            county_specific_df = variances[variances['County'] == county]
            most_frequent_sub_counties = county_specific_df['Sub-County'].value_counts().sort_values(
                ascending=False).reset_index()
            most_frequent_sub_counties.columns = ['Sub-County', 'count']
            most_frequent_sub_counties = add_percentage_and_count_string(most_frequent_sub_counties, "count")
            title = f"Most Frequent Sub-Counties Over Time   N= {most_frequent_sub_counties['count'].sum()}   Reports : {len(variances['Facility Name'].unique())} {type_of_facilities} Facilities   {county} County      Period: {min_date} - {max_date}"
            most_frequent_sub_counties_figs.append(
                most_frequent_bars(most_frequent_sub_counties, county, "Sub-County", "count (%)", title,
                                   show_source=True))

        if type_of_facilities == "FYJ":
            most_frequent_hub_figs = []
            for county in df['County'].unique():
                county_specific_df = variances[variances['County'] == county]
                most_frequent_hubs = county_specific_df['Hub'].value_counts().sort_values(
                    ascending=False).reset_index()
                most_frequent_hubs.columns = ['Hub', 'count']
                most_frequent_hubs = add_percentage_and_count_string(most_frequent_hubs, "count")
                title = f"Most Frequent Hub Over Time   N= {most_frequent_hubs['count'].sum()}   Reports : {len(variances['Facility Name'].unique())} {type_of_facilities} Facilities   {county} County      Period: {min_date} - {max_date}"
                most_frequent_hub_figs.append(
                    most_frequent_bars(most_frequent_hubs, county, "Hub", "count (%)", title, show_source=True))

        sub_counties_figs = []

        # Group the data by County and Sub-County
        grouped_df = variances.groupby(['County', 'Sub-County'])

        # Iterate through each group and create a figure
        for county, sub_county_df in grouped_df:
            # Get the name of the sub-county
            sub_county = sub_county_df['Sub-County'].unique()[0]
            county = sub_county_df['County'].unique()[0]

            # Get the monthly frequency data for the sub-county
            variances_trend_df, number_of_facilities = get_monthly_frequency(sub_county_df, "Facility Name")

            # Create a figure for the sub-county
            sub_counties_figs.append(trend_variances_(
                variances_trend_df,
                f"Monthly Variances per Sub-County : {sub_county}    County : {county}    N={variances_trend_df['Frequency'].sum()}   Reports : {number_of_facilities} {type_of_facilities} Facilities   Period: {min_date} - {max_date}",
                y_axis="Frequency",
                x_axis="month_num",
                text="count (%)"
            ))

        unique_facilities_df = variances.drop_duplicates(subset=["Facility Name", "month_num"])

        most_frequent_facilities_figs = []
        for county in df['County'].unique():
            county_specific_df = unique_facilities_df[unique_facilities_df['County'] == county]
            most_frequent_facilities = county_specific_df['Facility Name'].value_counts().sort_values(
                ascending=False).reset_index()
            most_frequent_facilities.columns = ['Facility Name', 'count']
            if most_frequent_facilities.shape[0] > 50:
                top_50 = most_frequent_facilities.head(50)
                top_50_text = "(Top 50 facilities)"
            else:
                top_50 = most_frequent_facilities
                top_50_text = f"{most_frequent_facilities.shape[0]} facilities"
            title = f'Most Frequent Facilities Over Time   {top_50_text}    {type_of_facilities} facilities    Period: {min_date} - {max_date}'
            most_frequent_facilities_figs.append(
                most_frequent_bars(top_50, county, "Facility Name", "count", title, show_source=False, height=600,
                                   y_axis_title="Variant reports in months"))

        sub_county_variances_list = []
        for county in df['County'].unique():
            county_specific = df[df['County'] == county]
            subcounty_variance = calculate_variances_subcounties(county_specific, variances, 'Sub-County')
            sub_county_variances_list.append(
                show_subcounty_variances(subcounty_variance, county, min_date, max_date, "Sub-County"))
        if type_of_facilities == "FYJ":
            hub_variances_list = []
            for county in df['County'].unique():
                county_specific = df[df['County'] == county]
                hub_variance = calculate_variances_subcounties(county_specific, variances, 'Hub')
                hub_variances_list.append(show_subcounty_variances(hub_variance, county, min_date, max_date, "Hub"))

    context = {
        "trend_variances_list": trend_variances_list, "trend_monthly_variances_list": trend_monthly_variances_list,
        "most_frequent_sub_counties_figs": most_frequent_sub_counties_figs, "sub_counties_figs": sub_counties_figs,
        "most_frequent_facilities_figs": most_frequent_facilities_figs,
        "sub_county_variances_list": sub_county_variances_list, "most_frequent_hub_figs": most_frequent_hub_figs,
        "hub_variances_list": hub_variances_list, "rtk_qs_filters": rtk_qs_filters,
        "facility_type_options": facility_type_options, "dqa_type": dqa_type,
    }

    # Cache the entire rendered view for 30 days
    rendered_view = render(request, 'data_analysis/rtk_viz.html', context)
    cache.set(cache_key, rendered_view, 30 * 24 * 60 * 60)

    return rendered_view
    # return render(request, 'data_analysis/rtk_viz.html', context)


def waterfall(df, beginning_balance, quantity_received, positive_adjustments, losses, negative_adjustments,
              ending_balance, last_week_tx_curr, start_quarters_fy, end_quarters_fy, commodity_name,
              type_of_facilities):
    expect_tx_curr = int(beginning_balance + quantity_received + positive_adjustments)
    total_accounted = int(negative_adjustments + ending_balance + losses)
    difference = last_week_tx_curr - expect_tx_curr - total_accounted
    if difference > 0:
        text_loss = "Unattributable Gain"
        text_loss = f"<b>{text_loss}</b>"
    elif difference < 0:
        text_loss = "Unattributable Loss"
        text_loss = f"<b>{text_loss}</b>"
    else:
        text_loss = "No Gain/Loss"

    last_week_txcurr_date = end_quarters_fy
    fig = go.Figure(go.Waterfall(
        name="20", orientation="v",
        measure=["relative", "relative", "relative", "total", "relative", "relative", "relative", "relative",
                 "total"],
        # x=[f"{start_quarters_fy} Opening Bal", "Quantity received", "+ve adjustments", "Available Stocks",
        #    "Quantity used", "Losses", "-ve adjustments", f"{text_loss}", f"{last_week_txcurr_date} Ending Bal"],
        x=[f"<b>{start_quarters_fy} Opening Bal</b>", "Quantity received", "+ve adjustments", "Available Stocks",
           "Quantity used", "Losses", "-ve adjustments", text_loss,
           f"<b>{last_week_txcurr_date} Ending Bal</b>"],

        textposition="outside",
        text=[beginning_balance, quantity_received, positive_adjustments, expect_tx_curr, ending_balance,
              losses, negative_adjustments, difference, last_week_tx_curr],
        y=[beginning_balance, quantity_received, positive_adjustments, expect_tx_curr, ending_balance, losses,
           negative_adjustments, difference, last_week_tx_curr],
        connector={"line": {"color": "rgb(63, 63, 63)"}},
    ))

    fig.update_layout(
        title=f"{type_of_facilities} Waterfall Analysis: {commodity_name.strip()} Inventory Transactions ({start_quarters_fy} to "
              f"{end_quarters_fy})",
        #         autosize=False,
        height=550,
        title_font={"size": 16},
        font={"size": 11},
        margin=dict(l=50, r=50, b=100, t=100, pad=4)
    )

    fig.update_yaxes(automargin=True)
    # remove grid lines
    fig.update_yaxes(showgrid=False)
    fig.update_xaxes(showgrid=False)
    # change connectors color
    fig.update_traces(connector_line_color="black")
    fig.update_traces(connector_line_dash="dashdot")
    return plot(fig, include_plotlyjs=False, output_type="div")


@login_required(login_url='login')
def rtk_inventory_viz(request):
    """
    Show visualizations of RTK data.

    :param request: The request object.
    :return: A render object with the visualizations.
    """
    #####################################
    # Get chosen facility type
    #####################################
    if request.method == "GET":
        request.session['page_from'] = request.META.get('HTTP_REFERER', '/')
        selected_facility_type = request.GET.get('record_count', 'False')
    else:
        selected_facility_type = request.GET.get('record_count', 'True')
    waterfall_chart = dictionary = None
    unattributable_df = commodity_result_df = pd.DataFrame()
    unattributable_filename = commodity_report_filename = ""

    def fetch_past_one_year_cd4_data(request):
        """
        Retrieves CD4 data from the past year based on user input or default logic.

        Args:
            request: A request object containing GET parameters.

        Returns:
            A tuple containing the query set and a flag indicating whether to use the default one-year data.
        """

        # Retrieve user input from request GET parameters
        start_date_param = request.GET.get('start_date')
        end_date_param = request.GET.get('end_date')

        # Set default values
        use_one_year_data = True
        days = 450

        # Calculate one year ago
        one_year_ago = datetime.now() - timedelta(days=days)
        one_year_ago = one_year_ago.replace(hour=23, minute=59, second=59, microsecond=999999)

        # Handle user input
        if start_date_param:
            start_date = datetime.strptime(start_date_param, '%Y-%m-%d')
            if start_date < datetime.now() - timedelta(days=days):
                if not end_date_param or start_date < datetime.strptime(end_date_param, '%Y-%m-%d'):
                    one_year_ago = start_date
                    use_one_year_data = False

        # Query the database
        rtk_query_set = RTKData.objects.filter(month_column__gte=one_year_ago).order_by('facility_name', 'month')

        return rtk_query_set, use_one_year_data

    rtk_qs, use_one_year_data = fetch_past_one_year_cd4_data(request)

    # Convert queryset to dataframe
    rtk_qs_filters = RTKInventoryFilter(request.GET, queryset=rtk_qs)
    facility_type_options = [("False", "FYJ"), ("True", "All")]
    df = convert_to_df(rtk_qs_filters.qs)
    facility_name_ = request.GET.get('facility_name')
    facility_type = request.GET.get('record_count')

    rtk_all = df.copy()
    # Apply the get_quarter function to the 'month' column to create a new 'quarters_fy' column
    rtk_all.loc[:, 'quarters_fy'] = rtk_all['month'].apply(get_quarter)
    dqa_type = "rtk_viz"

    # Generate a cache key based on relevant data
    data_hash = hashlib.sha256(
        f"{rtk_all.to_dict()}:{request.GET.get('start_date')}:{request.GET.get('end_date')}:"
        f"{request.GET.get('record_count')}:{request.GET.get('commodity_name')}:{request.GET.get('sub_county')}:"
        f"{request.GET.get('county')}:{request.GET.get('facility_name')}".encode()
    ).hexdigest()
    cache_key = f'rtk_inventory_viz:{data_hash}'

    # Check if the view is cached
    cached_view = cache.get(cache_key)
    if cached_view is not None:
        return cached_view

    if df.shape[0] > 0:
        # Get all facilities
        if selected_facility_type == "True":
            all_facilities = True
        else:
            all_facilities = False

        cols_to_use = ['Quantity Received', 'Quantity Used', 'Quantity Requested', 'Tests Done', 'Losses',
                       'Positive Adjustments', 'Negative Adjustments', 'Ending Balance', 'Days Out of Stock',
                       'Quantity Expiring in 6 Months']

        report_cols_to_use = ['Quantity Received', 'Tests Done', 'Days Out of Stock', 'Ending Balance']

        if not all_facilities:
            type_of_facilities = "FYJ Facilities"
            # Get FYJ facilities
            facilities = Facilities.objects.all()
            # Filter data by FYJ facilities
            rtk_all = rtk_all[rtk_all['MFL Code'].isin([facility.mfl_code for facility in facilities])]
            # Extracting hub information from Sub_counties model
            sub_county_hub_mapping = Sub_counties.objects.values('facilities__mfl_code', 'hub__hub')
            facility_hub_df = pd.DataFrame(sub_county_hub_mapping)
            facility_hub_df.columns = ["MFL Code", "Hub"]
            rtk_all = rtk_all.merge(facility_hub_df, on='MFL Code', how="left")
            rtk_all = rtk_all[~rtk_all['Hub'].isnull()]
            rtk_df = rtk_all[
                ['month', 'County', 'Sub-County', "Hub", 'MFL Code', 'Facility Name', 'Commodity Name'] + cols_to_use]
            rtk_df = rtk_df.drop_duplicates()
        else:
            type_of_facilities = "ALL Facilities"
            rtk_df = df[['month', 'County', 'Sub-County', 'MFL Code', 'Facility Name', 'Commodity Name'] + cols_to_use]
        if len(rtk_df['month'].unique()) > 1:
            if facility_name_ is not "" or facility_type == "False":
                get_facility_data = facility_name_

            else:
                get_facility_data = None
            kaj, rtk_df_filtered = process_data(rtk_df, cols_to_use, groupby_period="quarters_fy",
                                                get_facility_data=get_facility_data)

            # Sort the DataFrame by quarters_fy
            df = sort_quarter_year(kaj)

            df_sorted = df.sort_values(by='quarters_fy')
            df_sorted = df_sorted.copy().reset_index(drop=True)
            df_sorted.loc['Column_Total'] = df_sorted.sum(numeric_only=True, axis=0)
            # Fill NaN values with 0 before converting to integers
            # df_sorted.fillna(0, inplace=True)
            # Convert the columns to integers
            numeric_cols = df_sorted.select_dtypes(include=[np.number])
            df_sorted[numeric_cols.columns] = numeric_cols.apply(lambda x: x.astype(int), axis=0)

            start_quarters_fy = df_sorted.head(1)['quarters_fy'].unique()[0]
            end_quarters_fy = df_sorted.tail(2)['quarters_fy'].unique()[0]
            commodity_name = ', '.join(map(str, df_sorted['Commodity Name'].dropna().unique())).strip()

            if len(commodity_name.split(', ')) == 4:
                commodity_name = "All Commodities"

            rtk_df_filtered = rtk_df_filtered.groupby(['Commodity Name', 'quarters_fy']).sum().reset_index()

            if len(df_sorted["Commodity Name"].dropna().unique()) > 1:
                beginning_balance = df_sorted.tail(1)['Beginning Balance'].unique()[0]

                last_quarter = df_sorted["quarters_fy"].dropna().tail(1).unique()[0]
                last_quarter_df = df_sorted[df_sorted["quarters_fy"] == last_quarter]
                ending_balance = last_quarter_df['Ending Balance'].sum()
            else:
                beginning_balance = df_sorted.head(1)['Beginning Balance'].unique()[0]
                ending_balance = sort_quarter_year(rtk_df_filtered).tail(1)['Beginning Balance'].unique()[0]

            quantity_received = df_sorted.tail(1)['Quantity Received'].unique()[0]
            quantity_used = df_sorted.tail(1)['Quantity Used'].unique()[0] * -1
            losses = df_sorted.tail(1)['Losses'].unique()[0] * -1
            positive_adjustments = df_sorted.tail(1)['Positive Adjustments'].unique()[0]
            negative_adjustments = df_sorted.tail(1)['Negative Adjustments'].unique()[0] * -1

            waterfall_chart = waterfall(df, beginning_balance, quantity_received, positive_adjustments, losses,
                                        negative_adjustments, quantity_used, ending_balance, start_quarters_fy,
                                        end_quarters_fy,
                                        commodity_name, type_of_facilities)

            if 'Unattributable losses/gains' in df_sorted.columns:
                unattributable_df = df_sorted.copy()
                unattributable_filename = "Unattributable_gains_losses"
                request.session['unattributed_report'] = unattributable_df.to_dict()

            ##############################################################
            # Generate report
            ##############################################################
            commodity_result_df, beg_bal_filtered = process_data(rtk_df, report_cols_to_use,
                                                                 groupby_period="quarters_fy",
                                                                 )

            commodity_report_filename = "commodity_report"
            request.session['commodity_report'] = commodity_result_df.to_dict()
        dictionary = get_key_from_session_names(request)

    context = {
        "rtk_qs_filters": rtk_qs_filters, "facility_type_options": facility_type_options, "dqa_type": dqa_type,
        "waterfall_chart": waterfall_chart, "dictionary": dictionary, "unattributable_df": unattributable_df,
        "commodity_result_df": commodity_result_df, "unattributable_filename": unattributable_filename,
        "commodity_report_filename": commodity_report_filename,
    }

    # Cache the entire rendered view for 30 days
    rendered_view = render(request, 'data_analysis/rtk_viz.html', context)
    cache.set(cache_key, rendered_view, 30 * 24 * 60 * 60)

    return rendered_view
    # return render(request, 'data_analysis/rtk_viz.html', context)


def transform_nascop_data(df1, one_year_ago, facility_code):
    df1 = df1.drop_duplicates("Patient CCC No", keep="last")

    # df1.loc[:, 'Date Collected'] = pd.to_datetime(df1['Date Collected'], dayfirst=True)
    try:
        df1.loc[:, 'Date Collected'] = pd.to_datetime(df1['Date Collected'], dayfirst=True)
    except ValueError:
        df1['Date Collected'] = pd.to_datetime(df1['Date Collected'])
    # Filter the DataFrame to include only rows where 'Date Collected' more than 1 year ago
    df1 = df1[df1['Date Collected'] > one_year_ago]

    df1.loc[:, 'Date Collected'] = pd.to_datetime(df1['Date Collected'], dayfirst=True)

    # facility_code = \
    #     df1.groupby(['Facility Code']).count()['Facilty'].reset_index().sort_values("Facilty", ascending=False).head(1)[
    #         'Facility Code'].unique()[0]

    df1 = df1[df1['Facility Code'] == facility_code]
    df1['Date Collected'] = pd.to_datetime(df1['Date Collected'], errors='coerce')
    df1.loc[:, "Patient CCC No"] = df1["Patient CCC No"].astype(str)
    # df1['Patient CCC No'] = df1['Patient CCC No'].str.replace(".0", "")
    return df1


def age_buckets_pepfar(age):
    """Convert age to age ranges."""
    if age < 1:
        return '< 1'
    elif 1 <= age <= 4:
        return '1-4'
    elif 5 <= age <= 9:
        return '5-9'
    elif 10 <= age <= 14:
        return '10-14'
    elif 15 <= age <= 19:
        return '15-19'
    elif 20 <= age <= 24:
        return '20-24'
    elif 25 <= age <= 29:
        return '25-29'
    elif 30 <= age <= 34:
        return '30-34'
    elif 35 <= age <= 39:
        return '35-39'
    elif 40 <= age <= 44:
        return '40-44'
    elif 45 <= age <= 49:
        return '45-49'
    elif 50 <= age <= 54:
        return '50-54'
    elif 55 <= age <= 59:
        return '55-59'
    elif 60 <= age <= 64:
        return '60-64'

    else:
        return '65+'


def transform_emr_data(df):
    df = df[df['Age at reporting'].notna()]
    df.loc[:, "Last VL Result"] = df["Last VL Result"].replace("0", "LDL")
    df['Last VL Date'] = pd.to_datetime(df['Last VL Date'], dayfirst=True)
    df.loc[:, 'Art Start Date'] = pd.to_datetime(df['Art Start Date'], dayfirst=True)
    df.loc[:, 'DOB'] = pd.to_datetime(df['DOB'], dayfirst=True)
    df['age_band'] = df['Age at reporting'].apply(age_buckets_pepfar)
    df.loc[:, "CCC No"] = df["CCC No"].astype(str)
    # df['CCC No'] = df['CCC No'].str.replace(".0", "")
    return df


def rename_nascop_kenyaemr_cols(discordant_results):
    return discordant_results.rename(
        columns={'Last VL Result': 'Last VL Result (KenyaEMR)', 'Last VL Date': 'Last VL Date (KenyaEMR)',
                 'Date Collected': "Date Collected (NASCOP's)",
                 "Result": "Result (NASCOP's)"})


def separate_dfs(df, df1, current_date):
    merged_df_100 = pd.merge(df, df1, left_on=['CCC No', 'Last VL Date'], right_on=['Patient CCC No', 'Date Collected'])
    merged_df_100 = merged_df_100[
        ['CCC No', "Age at reporting", 'age_band', 'Sex', 'Last VL Date', 'Last VL Result', 'Date Collected', 'Result']]

    set2 = set(merged_df_100['CCC No'].unique())
    set1 = set(df['CCC No'].unique())

    missing = list(sorted(set1 - set2))

    not_merged = df[df['CCC No'].isin(missing)]

    merged_df_ccc_only = pd.merge(not_merged, df1, left_on='CCC No', right_on='Patient CCC No')[
        ['CCC No', "Age at reporting", 'age_band', 'Sex', 'Last VL Date', 'Last VL Result', 'Date Collected',
         'Result', ]]
    merged_df_ccc_only['date_difference'] = (
            merged_df_ccc_only['Date Collected'] - merged_df_ccc_only['Last VL Date']).dt.days
    merged_df_ccc_only_above0 = merged_df_ccc_only[merged_df_ccc_only['date_difference'] >= 0].sort_values(
        "date_difference", ascending=False)
    has_results_within_test_month_above0 = merged_df_ccc_only_above0[merged_df_ccc_only_above0['date_difference'] <= 30]

    missing_results_outside_test_month = merged_df_ccc_only_above0[merged_df_ccc_only_above0['date_difference'] > 30]
    merged_df_ccc_only_below0 = merged_df_ccc_only[
        ~merged_df_ccc_only['CCC No'].isin(merged_df_ccc_only_above0['CCC No'].unique())].sort_values("date_difference",
                                                                                                      ascending=False)

    has_results_within_test_month_below0 = merged_df_ccc_only_below0[
        merged_df_ccc_only_below0['date_difference'] >= -30]
    results_not_in_nascop = merged_df_ccc_only_below0[merged_df_ccc_only_below0['date_difference'] < -30]

    accountable_results_above0 = list(missing_results_outside_test_month['CCC No'].unique()) + list(
        has_results_within_test_month_above0['CCC No'].unique())
    missing_results_above0 = merged_df_ccc_only_above0[
        ~merged_df_ccc_only_above0['CCC No'].isin(accountable_results_above0)].sort_values("date_difference",
                                                                                           ascending=False)
    accountable_results_below0 = list(results_not_in_nascop['CCC No'].unique()) + list(
        has_results_within_test_month_below0['CCC No'].unique())

    missing_results_below0 = merged_df_ccc_only_below0[
        ~merged_df_ccc_only_below0['CCC No'].isin(accountable_results_below0)].sort_values("date_difference",
                                                                                           ascending=False)

    missing_results_ccc_only = pd.concat([missing_results_above0, missing_results_below0])

    accountable_result_only_ccc = accountable_results_above0 + accountable_results_below0 + list(
        missing_results_ccc_only['CCC No'].unique())

    not_merged1 = not_merged[~not_merged['CCC No'].isin(accountable_result_only_ccc)]

    # Calculate the date one year ago from the current date
    one_year_ago = current_date - pd.DateOffset(years=1)

    # Filter the DataFrame to include only rows where 'Date Collected' more than 1 year ago
    not_merged1_one_year_ago = not_merged1[not_merged1['Last VL Date'] < one_year_ago]
    return not_merged1_one_year_ago, not_merged1, has_results_within_test_month_above0, has_results_within_test_month_below0, merged_df_100, results_not_in_nascop, missing_results_outside_test_month, missing_results_below0


def categorize_vl(df):
    df = df.copy()
    ldl_df = df[df['Last VL Result'] == "LDL"]
    non_ldl_df = df[df['Last VL Result'] != "LDL"]
    non_vl = non_ldl_df[non_ldl_df['Last VL Result'].isnull()]
    non_vl = non_vl.copy()
    if not non_vl.empty:
        non_vl.loc[:, 'Last_VL_Category'] = "no vl"
    non_null_df = non_ldl_df[non_ldl_df['Last VL Result'].notnull()]
    non_null_df.loc[:, 'Last VL Result'] = non_null_df['Last VL Result'].astype(int)
    new_ldl = non_null_df[non_null_df['Last VL Result'] <= 50]
    hvl = non_null_df[non_null_df['Last VL Result'] > 50]
    hvl = hvl.copy()
    if not hvl.empty:
        hvl.loc[:, 'Last_VL_Category'] = "HVL"
    hvl_above_1000 = hvl[hvl['Last VL Result'] >= 1000]
    hvl_above_200 = hvl[hvl['Last VL Result'] >= 200]
    ldl_so_far = pd.concat([ldl_df, new_ldl])
    if not ldl_so_far.empty:
        ldl_so_far['Last_VL_Category'] = "LDL"
    df = pd.concat([ldl_so_far, hvl, non_vl])
    return df


def split_by_eligibility(possible_invalid):
    # Get the current date
    current_date = pd.to_datetime(datetime.now().date())
    possible_invalid['Art Start Date'] = pd.to_datetime(possible_invalid['Art Start Date'])
    # Calculate the difference in days between 'current_date' and 'Last VL Date'
    possible_invalid['days_since_last_vl'] = (current_date - possible_invalid['Last VL Date']).dt.days
    possible_invalid['days_since_started_art'] = (current_date - possible_invalid['Art Start Date']).dt.days

    last_6_months = possible_invalid[possible_invalid['days_since_started_art'] <= 180]
    above_6_months = possible_invalid[possible_invalid['days_since_started_art'] > 180]
    not_on_art = possible_invalid[possible_invalid['days_since_started_art'].isnull()]

    pregnant = above_6_months[(above_6_months['Active in PMTCT'] == "Yes")]
    non_pregnant = above_6_months[(above_6_months['Active in PMTCT'] != "Yes")]
    zero_24yrs = non_pregnant[non_pregnant['Age at reporting'] < 25]
    above_25yrs = non_pregnant[non_pregnant['Age at reporting'] >= 25]
    return last_6_months, above_6_months, not_on_art, pregnant, zero_24yrs, above_25yrs


def filter_hvl(above_25yrs):
    return above_25yrs[
        ~(above_25yrs["Last_VL_Category"].str.contains("ldl", case=False)) & (above_25yrs['days_since_last_vl'] >= 120)]


def filter_ldl_eligible(above_25yrs):
    return above_25yrs[
        (above_25yrs["Last_VL_Category"].str.contains("ldl", case=False)) & (above_25yrs['days_since_last_vl'] >= 180)]


def filter_missed_12__months_vl(pregnant):
    missed_6mons_pregnant = pregnant[
        (pregnant['days_since_last_vl'] > 365) & (pregnant["Last_VL_Category"].str.contains("ldl", case=False))]
    return missed_6mons_pregnant


def generate_duedates(above_25yrs, month_duedates, col):
    patient_due_list = []

    for i, (lower, upper) in enumerate(month_duedates, start=1):
        patients_due = above_25yrs[(above_25yrs[col] > lower) & (above_25yrs[col] <= upper)].copy()
        patients_due["Due in (n) months"] = i
        patient_due_list.append(patients_due)

    due_next_12_months_raw = pd.concat(patient_due_list)
    due_next_12_months = due_next_12_months_raw.groupby('Due in (n) months')['CCC No'].count().reset_index()
    due_next_12_months.columns = ["Due in (n) months", "Numbers"]
    return due_next_12_months, due_next_12_months_raw, patient_due_list


# def compute_month_year(n_months, current_date=None):
#     month_index = (current_date.month + n_months - 1) % 12 + 1
#     month_abbr = calendar.month_abbr[month_index]
#     year = current_date.year + (current_date.month + n_months - 1) // 12
#     return f"{month_abbr}-{year}"


def filter_missed_6__months_vl(pregnant):
    missed_6mons_pregnant = pregnant[
        (pregnant['days_since_last_vl'] > 180) & (pregnant["Last_VL_Category"].str.contains("ldl", case=False))]
    return missed_6mons_pregnant


# Calculate the date 4 months ago from today
def filter_tx_new_not_eligible(last_6_months):
    no_vl_last_6_months = last_6_months[
        (last_6_months['Last VL Date'].isnull()) & (last_6_months['days_since_last_vl'] < 120)]
    return no_vl_last_6_months


# Calculate the date 4 months ago from today
def filter_no_vl_lastn_months(last_6_months):
    no_vl_last_6_months = last_6_months[
        (last_6_months['Last VL Date'].isnull()) & (last_6_months['days_since_last_vl'] >= 120)]
    return no_vl_last_6_months


def categorize_eligible_patients(last_6_months, pregnant, zero_24yrs, above_25yrs):
    last_6_months_with_vl = last_6_months[
        (last_6_months['Last VL Date'].notnull()) & (last_6_months['days_since_last_vl'] >= 120)]

    no_vl_last_6_months = filter_no_vl_lastn_months(last_6_months)
    # pregnant

    no_vl_pregnant = filter_no_vl_lastn_months(pregnant)
    # 0-24
    no_vl_zero_24yrs = filter_no_vl_lastn_months(zero_24yrs)
    # 25+
    no_vl_above_25yrs = filter_no_vl_lastn_months(above_25yrs)
    no_vl_ever = pd.concat([no_vl_above_25yrs, no_vl_zero_24yrs, no_vl_pregnant, no_vl_last_6_months])
    no_vl_ever = no_vl_ever.copy()
    if not no_vl_ever.empty:
        no_vl_ever['eligibility criteria'] = "no vl ever"

    # TX NEW NOT ELIGIBLE
    tx_new_not_eligible = filter_tx_new_not_eligible(last_6_months)

    missed_6mons_zero_24yrs = filter_missed_6__months_vl(zero_24yrs)
    missed_6mons_zero_24yrs = missed_6mons_zero_24yrs.copy()
    if not missed_6mons_zero_24yrs.empty:
        missed_6mons_zero_24yrs['eligibility criteria'] = "missed 6 months vl (0-24yrs)"

    no_vl_so_far = pd.concat([missed_6mons_zero_24yrs, no_vl_ever])

    missed_6mons_pregnant = filter_missed_6__months_vl(pregnant)
    missed_6mons_pregnant = missed_6mons_pregnant.copy()
    if not missed_6mons_pregnant.empty:
        missed_6mons_pregnant['eligibility criteria'] = "missed 6 months vl (pg/bf)"

    missed_12mons_above_25yrs = filter_missed_12__months_vl(above_25yrs)
    missed_12mons_above_25yrs = missed_12mons_above_25yrs.copy()
    if not missed_12mons_above_25yrs.empty:
        missed_12mons_above_25yrs.loc[:, 'eligibility criteria'] = "missed 12 months vl (>25yrs)"

    no_vl_so_far = pd.concat([missed_6mons_zero_24yrs, no_vl_ever, missed_6mons_pregnant, missed_12mons_above_25yrs])

    hvl_last_6_months = filter_hvl(last_6_months_with_vl)
    hvl_last_6_months = hvl_last_6_months.copy()
    if not hvl_last_6_months.empty:
        hvl_last_6_months['eligibility criteria'] = "hvl within last 6 months"

    hvl_above_25yrs = filter_hvl(above_25yrs)
    hvl_above_25yrs = hvl_above_25yrs.copy()
    if not hvl_above_25yrs.empty:
        hvl_above_25yrs['eligibility criteria'] = "hvl (>25yrs)"

    hvl_zero_24yrs = filter_hvl(zero_24yrs)
    hvl_zero_24yrs = hvl_zero_24yrs.copy()
    if not hvl_zero_24yrs.empty:
        hvl_zero_24yrs['eligibility criteria'] = "hvl (0-24yrs)"

    hvl_pregnant = filter_hvl(pregnant)
    hvl_pregnant = hvl_pregnant.copy()
    if not hvl_pregnant.empty:
        hvl_pregnant['eligibility criteria'] = "hvl (pg/bf)"
    hvl_df = pd.concat([hvl_pregnant, hvl_above_25yrs, hvl_zero_24yrs])

    no_vl_so_far_ = pd.concat([no_vl_so_far, hvl_df])
    no_vl_so_far_ = no_vl_so_far_.drop_duplicates("CCC No", keep="last")
    return no_vl_so_far_, tx_new_not_eligible


def process_vl_backlog(not_merged1_one_year_ago):
    not_merged1_one_year_ago_ = categorize_vl(not_merged1_one_year_ago)
    last_6_months, above_6_months, not_on_art, pregnant, zero_24yrs, above_25yrs = split_by_eligibility(
        not_merged1_one_year_ago_)
    no_vl_so_far, tx_new_not_eligible = categorize_eligible_patients(
        last_6_months, pregnant, zero_24yrs, above_25yrs)
    return no_vl_so_far, tx_new_not_eligible


def generate_reports(no_vl_so_far, not_merged1, merged_df_100, has_results_within_test_month_above0,
                     has_results_within_test_month_below0, results_not_in_nascop,
                     missing_results_outside_test_month, missing_results_below0):
    no_vl_list = list(no_vl_so_far['CCC No'].unique())
    missing_list = not_merged1[~not_merged1['CCC No'].isin(no_vl_list)]
    no_vl_so_far_within_one_year, tx_new_not_eligible = process_vl_backlog(missing_list)
    no_vl_list_1 = list(no_vl_so_far_within_one_year['CCC No'].unique())
    with_results_no_ccc_merge = missing_list[~missing_list['CCC No'].isin(no_vl_list_1)]
    no_vl_ever = with_results_no_ccc_merge[with_results_no_ccc_merge['Last VL Date'].isnull()].copy()
    no_vl_ever.loc[:, 'eligibility criteria'] = "No VL ever"

    results_not_in_nascop1 = with_results_no_ccc_merge[with_results_no_ccc_merge['Last VL Date'].notnull()]
    # WITH RESULTS
    with_results_df = pd.concat(
        [merged_df_100, has_results_within_test_month_above0, has_results_within_test_month_below0])
    # BACK LOG
    backlog_df = pd.concat([no_vl_so_far_within_one_year, no_vl_so_far, no_vl_ever])

    # No results in NASCOP
    results_not_in_nascop1 = results_not_in_nascop1[
        ['CCC No', 'Age at reporting', 'age_band', 'Sex', 'Last VL Date', 'Last VL Result']]
    results_not_in_nascop_overall = pd.concat([results_not_in_nascop, results_not_in_nascop1]).copy()
    results_not_in_nascop_overall['reason'] = "Result not in NASCOP's website"

    # Missing Result in KenyaEMR
    missing_in_emr = pd.concat([missing_results_outside_test_month, missing_results_below0])
    missing_in_emr['reason'] = "Result Not in KenyaEMR"
    missing_in_emr = pd.concat([missing_in_emr, results_not_in_nascop]).reset_index(drop=True)
    missing_in_emr.index += 1
    del missing_in_emr['date_difference']

    missing_in_emr = rename_nascop_kenyaemr_cols(missing_in_emr)

    with_results_df.loc[:, 'Last VL Result'] = with_results_df['Last VL Result'].replace(0, "LDL")
    with_results_df.loc[:, 'Result'] = with_results_df['Result'].replace("< LDL copies/ml", "LDL")

    # results discordance
    discordant_results = with_results_df[with_results_df['Last VL Result'] != with_results_df['Result']]
    discordant_results = rename_nascop_kenyaemr_cols(discordant_results)
    del discordant_results['date_difference']
    return discordant_results, with_results_df, missing_in_emr, results_not_in_nascop_overall, backlog_df, no_vl_ever


def prep_categorical_columns(backlog_df, col):
    dist_backlog = backlog_df.groupby([col])['CCC No'].count().reset_index()
    dist_backlog.columns = [col, "TX_CURR (Eligible)"]
    dist_backlog['%'] = round(
        dist_backlog["TX_CURR (Eligible)"] / dist_backlog["TX_CURR (Eligible)"].sum() * 100, ).astype(int)
    dist_backlog['%'] = dist_backlog["TX_CURR (Eligible)"].astype(str) + " (" + dist_backlog['%'].astype(str) + "%)"
    return dist_backlog


def sort_custom_agebands(df, col):
    # Define the custom sorting order
    custom_order = ['<1', '1-4.', '5-9', '10-14.', '15-19', '20-24', '25-29', '30-34', '35-39', '40-44', '45-49',
                    '50-54', '55-59', '60-64', '65+']

    # Convert the specified column to Categorical with custom ordering
    df[col] = pd.Categorical(df[col], categories=custom_order, ordered=True)

    # Get the unique values present in the specified column
    available_age_bands = df[col].unique()

    # Sort the DataFrame by the specified column
    df = df.sort_values(col)

    # Return the sorted DataFrame and the available custom order
    return df, available_age_bands


def create_barchart_with_secondary_axis(vl_uptake_df, overall_vl_uptake, title, secondary_text):
    # Create subplots with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Add traces
    fig.add_trace(
        go.Bar(x=vl_uptake_df['Age band'], y=vl_uptake_df["TX_CURR (Eligible)"], name="TX_CURR (Eligible)",
               # marker_color='blue',
               marker={'color': 'blue'},
               text=vl_uptake_df["TX_CURR (Eligible)"],  # Add text labels
               texttemplate='<b><span style="color:blue">%{text:}</span></b>',
               textposition='outside'  # Position the text outside the bars
               ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Bar(x=vl_uptake_df['Age band'], y=vl_uptake_df['valid results'], name='Valid results',
               # marker_color='green',
               marker={'color': 'green'},
               text=vl_uptake_df['valid results'],  # Add text labels
               texttemplate='<b><span style="color:green">%{text:}</span></b>',
               textposition='outside'  # Position the text outside the bars
               ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(x=vl_uptake_df['Age band'], y=vl_uptake_df['vl_uptake'], name=secondary_text, mode='lines+text',
                   # marker_color='red',
                   marker={'color': 'red'},
                   text=vl_uptake_df['vl_uptake'],  # Add text labels
                   texttemplate='<b><span style="color:black">%{text:}%</span></b>',
                   # Format the text to be bold and red
                   textposition='top center'  # Position the text above the markers
                   ),
        secondary_y=True,
    )

    # Add figure title
    fig.update_layout(
        title_text=f"{title} {overall_vl_uptake}%",
        height=500,
        legend=dict(
            # title='Gender',  # Update legend title
            orientation='h',  # Set legend orientation to horizontal
            x=0,  # Set x to 0 for left-align, adjust as needed
            y=1.1  # Set y to 1.1 for top position, adjust as needed
        )
    )

    # Set x-axis title
    fig.update_xaxes(title_text="Age band")

    # Set y-axes titles
    fig.update_yaxes(title_text="TX_CURR and Valid results", secondary_y=False)
    fig.update_yaxes(title_text=f"{secondary_text} (%)", secondary_y=True, range=[0, 110])
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)
    return plot(fig, include_plotlyjs=False, output_type="div")


def to_session_dict(df):
    """Convert DataFrame to a dictionary of strings for session storage.

    This function converts all the elements of the DataFrame to strings to handle
    the TypeError "Object of type Timestamp is not JSON serializable".

    Args:
        df (pandas.DataFrame): The DataFrame to be converted.

    Returns:
        dict: The DataFrame converted to a dictionary with all elements as strings.
    """
    return df.astype(str).to_dict()


def set_session_data(request, data_dict):
    """Set multiple DataFrames in session after converting to dictionary of strings."""
    for key, df in data_dict.items():
        request.session[key] = to_session_dict(df)


def filter_backlog_df(backlog_df, criteria, col):
    """Filter backlog DataFrame based on given criteria."""
    return backlog_df[backlog_df[col] == criteria]


def prepare_df_cd4(list_of_projects):
    column_names = [
        "County", "Sub-county", "Testing Laboratory", "Facility", "MFL CODE", "CCC NO.", "Age", "Sex",
        "Collection Date", "Testing date", "Received date", "Date Dispatch", "Justification", "CD4 Count",
        "Serum CRAG date", "Serum Crag", "TB LAM date", "TB LAM", "Received status", "Rejection reason", "TAT",
        "age_unit",
    ]
    # convert data from database to a dataframe
    list_of_projects = pd.DataFrame(list_of_projects)
    list_of_projects.columns = column_names

    list_of_projects_fac = list_of_projects.copy()
    # convert to datetime with UTC
    date_columns = ['Testing date', 'Collection Date', 'Received date', 'Date Dispatch']
    list_of_projects_fac[date_columns] = list_of_projects_fac[date_columns].astype("datetime64[ns, UTC]")

    return list_of_projects_fac


def calculate_vl_uptake(last_one_year_df, cd4_results):
    """
    Calculate VL uptake for different age bands within the preprocessed data.

    Parameters:
    last_one_year_df (pd.DataFrame): The preprocessed DataFrame containing patient information.

    Returns:
    pd.DataFrame: A DataFrame with VL uptake calculations for different age bands.
    float: The overall VL uptake percentage.
    """

    # Calculate TX_CURR (Eligible)
    all_df = last_one_year_df.groupby("age_band")['CCC No'].count().reset_index()
    all_df.columns = ['Age band', 'TX_CURR (Eligible)']

    # Calculate valid results
    vl_results = cd4_results.groupby("age_band")['CCC No'].count().reset_index()
    vl_results.columns = ['Age band', 'valid results']

    # Merge and calculate VL uptake
    vl_uptake_df = all_df.merge(vl_results, on="Age band", how="left")
    vl_uptake_df['vl_uptake'] = round(vl_uptake_df['valid results'] / vl_uptake_df['TX_CURR (Eligible)'] * 100)

    # Define the age categories
    age_categories = ['< 1', '1-4', '5-9', '10-14', '15-19', '20-24', '25-29', '30-34', '35-39', '40-44',
                      '45-49', '50-54', '55-59', '60-64', '65+']

    # Convert 'Age band' to a categorical type with the specified order
    vl_uptake_df['Age band'] = pd.Categorical(vl_uptake_df['Age band'], categories=age_categories, ordered=True)

    # Sort the DataFrame by 'Age band'
    vl_uptake_df = vl_uptake_df.sort_values('Age band')
    vl_uptake_df['vl_uptake'] = vl_uptake_df['vl_uptake'].fillna(0).astype(int)

    # Calculate overall VL uptake
    overall_vl_uptake = round(vl_uptake_df['valid results'].sum() / vl_uptake_df['TX_CURR (Eligible)'].sum() * 100)

    return vl_uptake_df, overall_vl_uptake


def process_cd4_data(cd4_df, df, facility_mfl_code, one_year_ago):
    """
    Process CD4 data to find missing and discordant results between KenyaEMR and Labpulse data.

    Parameters:
    cd4_df (pd.DataFrame): The DataFrame containing CD4 count information.
    df (pd.DataFrame): The DataFrame containing patient information.
    facility_mfl_code (int): The MFL code of the facility.
    one_year_ago (datetime): A datetime object representing one year ago from the current date.

    Returns:
    tuple: A tuple containing DataFrames for missing in Labpulse, missing in EMR, and discordant results.
    """
    # Identify date columns
    date_cols = [col for col in cd4_df.columns if "date" in col.lower()]

    for col in date_cols:
        # Convert identified date columns to datetime format, ensuring they are in UTC
        cd4_df[col] = pd.to_datetime(cd4_df[col], utc=True, format='ISO8601')
        # Format datetime columns to 'YYYY-MM-DD' and ensure they are in datetime format
        cd4_df[col] = cd4_df[col].dt.strftime('%Y-%m-%d')
        # Convert back to datetime without time part
        cd4_df[col] = pd.to_datetime(cd4_df[col])

    # Sort and remove duplicates
    cd4_df = cd4_df.sort_values("Collection Date")
    cd4_df = cd4_df.drop_duplicates(subset=['CCC NO.'], keep="last")

    # Ensure relevant columns in `df` are in datetime format
    df['Latest CD4 Count Date '] = pd.to_datetime(df['Latest CD4 Count Date '])
    df["Art Start Date"] = pd.to_datetime(df["Art Start Date"])

    # Ensure CD4 counts are in string format
    df['Latest CD4 Count'] = df['Latest CD4 Count'].astype(str)
    cd4_df['CD4 Count'] = cd4_df['CD4 Count'].astype(str)

    # Merge DataFrames
    merged_cd4 = df.merge(cd4_df[cd4_df['MFL CODE'] == facility_mfl_code], left_on="CCC No", right_on="CCC NO.")
    merged_cd4 = merged_cd4[[
        'CCC No', 'Age at reporting', 'age_band', 'Sex_x', 'Art Start Date', 'Current Regimen',
        'Latest CD4 Count', 'Latest CD4 Count Date ',
        'Collection Date', 'Justification', 'CD4 Count', 'Serum CRAG date', 'Serum Crag', 'TB LAM date', 'TB LAM'
    ]]

    merged_cd4.columns = [
        'CCC No', 'Age at reporting', 'age_band', 'Sex', 'Art Start Date', 'Current Regimen',
        'Latest CD4 Count (KenyaEMR)',
        'Latest CD4 Count Date (KenyaEMR)', 'Collection Date (Labpulse)', 'Justification (Labpulse)',
        'CD4 Count (Labpulse)', 'Serum CRAG date (Labpulse)', 'Serum Crag (Labpulse)', 'TB LAM date (Labpulse)',
        'TB LAM (Labpulse)'
    ]

    # Convert CD4 counts to numeric
    merged_cd4.loc[:, 'CD4 Count (Labpulse)'] = pd.to_numeric(merged_cd4['CD4 Count (Labpulse)'], errors='coerce')
    merged_cd4.loc[:, 'Latest CD4 Count (KenyaEMR)'] = pd.to_numeric(merged_cd4['Latest CD4 Count (KenyaEMR)'],
                                                                     errors='coerce')

    # Find matching and possible missing records
    cd4_results = merged_cd4[merged_cd4['Latest CD4 Count (KenyaEMR)'] == merged_cd4['CD4 Count (Labpulse)']]
    possible_missing_in_emr = merged_cd4[
        merged_cd4['Latest CD4 Count (KenyaEMR)'] != merged_cd4['CD4 Count (Labpulse)']].copy()

    possible_missing_in_emr.loc[:, 'date_diff'] = (possible_missing_in_emr['Collection Date (Labpulse)'] -
                                                   possible_missing_in_emr[
                                                       'Latest CD4 Count Date (KenyaEMR)']).dt.days.copy()

    possible_missing_in_emr = possible_missing_in_emr.sort_values("date_diff")

    discordant_results_cd4 = possible_missing_in_emr[(possible_missing_in_emr["date_diff"] <= 35) &
                                                     (possible_missing_in_emr["date_diff"] > -35)]
    if "date_diff" in discordant_results_cd4.columns:
        del discordant_results_cd4['date_diff']

    missing_in_emr_1 = possible_missing_in_emr[
        possible_missing_in_emr['Latest CD4 Count Date (KenyaEMR)'].isnull()].sort_values("Collection Date (Labpulse)")
    missing_in_emr_2 = possible_missing_in_emr[(possible_missing_in_emr["date_diff"] > 35)].sort_values(
        "Collection Date (Labpulse)")
    missing_in_emr = pd.concat([missing_in_emr_1, missing_in_emr_2])
    missing_in_labpulse = possible_missing_in_emr[(possible_missing_in_emr["date_diff"] < -35)].sort_values("date_diff")
    if "date_diff" in missing_in_labpulse.columns:
        del missing_in_labpulse['date_diff']
    if "date_diff" in missing_in_emr.columns:
        del missing_in_emr['date_diff']
    if "date_diff" in discordant_results_cd4.columns:
        del discordant_results_cd4['date_diff']

    return missing_in_labpulse, missing_in_emr, discordant_results_cd4, merged_cd4


def filter_and_preprocess_cd4(df, missing_in_labpulse, current_date):
    """
    Filter data for the last year, exclude records missing in Labpulse, and prepare the data for further analysis.

    Parameters:
    df (pd.DataFrame): The DataFrame containing patient information.
    missing_in_labpulse (pd.DataFrame): The DataFrame containing records missing in Labpulse.
    current_date (datetime): The current date to calculate the days since ART start.

    Returns:
    pd.DataFrame: The filtered and preprocessed DataFrame.
    """
    # Calculate days since ART start
    df['days_since_start_ART'] = (current_date - df['Art Start Date']).dt.days

    # Filter data for the last year and exclude records missing in Labpulse
    last_one_year_df = df[df['days_since_start_ART'] <= 365].sort_values("Art Start Date")
    last_one_year_df = last_one_year_df[~last_one_year_df['CCC No'].isin(missing_in_labpulse['CCC No'].unique())]

    return last_one_year_df


def sort_month_year(df, col):
    """
    Sort the DataFrame by the specified month_year column chronologically.

    Parameters:
    df (pd.DataFrame): The DataFrame to be sorted.
    col (str): The column name containing month and year in 'MMM-YYYY' format.

    Returns:
    pd.DataFrame: The sorted DataFrame.
    """
    # Convert 'month_year' to datetime
    df.loc[:, 'month_year_datetime'] = pd.to_datetime(df[col], format='%b-%Y')
    # Sort the DataFrame by the new datetime column
    df = df.sort_values(by='month_year_datetime')
    # Drop the auxiliary datetime column if no longer needed
    df = df.drop(columns='month_year_datetime')
    # Reset index for clean DataFrame
    df = df.reset_index(drop=True)
    return df


def analyze_cd4_reflex_test_uptake(merged_cd4, one_year_ago):
    """
    Analyze CD4 testing data and generate a plot showing the relationship
    between CD4 count <200, Serum Crag, and TB LAM testing over time.

    Parameters:
    merged_cd4 (pd.DataFrame): The DataFrame containing the merged CD4 testing data.
    one_year_ago (datetime): The datetime object representing one year ago from the current date.

    Returns:
    plotly line chart
    """
    # Filter the DataFrame based on the conditions specified
    cd4_scrag = merged_cd4[(merged_cd4["Art Start Date"] > one_year_ago) &
                           ((merged_cd4["Latest CD4 Count (KenyaEMR)"] <= 200) |
                            (merged_cd4["CD4 Count (Labpulse)"] <= 200))].copy()

    # Add the month_year column
    cd4_scrag.loc[:, 'month_year'] = pd.to_datetime(cd4_scrag['Collection Date (Labpulse)']).dt.strftime('%b-%Y')

    # Group by month_year and count the relevant columns
    cd4_ = cd4_scrag.groupby("month_year")["CCC No"].count().reset_index()
    tb_lam_ = cd4_scrag.groupby("month_year")["TB LAM (Labpulse)"].count().reset_index()
    s_crag_ = cd4_scrag.groupby("month_year")["Serum Crag (Labpulse)"].count().reset_index()

    # Sort the DataFrames
    cd4_ = sort_month_year(cd4_, "month_year")
    tb_lam_ = sort_month_year(tb_lam_, "month_year")
    s_crag_ = sort_month_year(s_crag_, "month_year")

    # Merge the DataFrames
    cd4_cascade = cd4_.merge(s_crag_, on="month_year").merge(tb_lam_, on="month_year")
    cd4_cascade.columns = ['month_year', 'CD4 <200', 'Serum Crag', 'TB LAM']

    # Calculate totals and uptakes
    total_cd4_less_200 = cd4_cascade['CD4 <200'].sum()
    total_crag = cd4_cascade['Serum Crag'].sum()
    total_tb_lam = cd4_cascade['TB LAM'].sum()
    s_crag_uptake = round((total_crag / total_cd4_less_200 * 100), 1)
    tb_lam_uptake = round((total_tb_lam / total_cd4_less_200 * 100), 1)

    # Melt the DataFrame for plotting
    melted_df = pd.melt(cd4_cascade, id_vars=['month_year'], var_name='Test Type', value_name='Count')
    # filter missing reflex tests
    missing_tb_lam = cd4_scrag[(cd4_scrag['TB LAM (Labpulse)'].isnull())]
    if "month_year" in missing_tb_lam.columns:
        del missing_tb_lam['month_year']
    missing_scrag = cd4_scrag[(cd4_scrag['Serum Crag (Labpulse)'].isnull())]
    if "month_year" in missing_scrag.columns:
        del missing_scrag['month_year']
    return missing_tb_lam, missing_scrag, melted_df, s_crag_uptake, tb_lam_uptake


def compare_reflex_tests(melted_df, s_crag_uptake, tb_lam_uptake):
    # Create and show the plot
    fig = px.line(melted_df, x="month_year", y="Count", color="Test Type", text="Count",
                  title=f"Relationship Between CD4 Count <200, Serum Crag ({s_crag_uptake}%) and TB LAM Testing ({tb_lam_uptake}%)")
    fig.update_traces(textposition='top center')
    fig.update_layout(legend=dict(
        yanchor="top",
        y=0.99,
        xanchor="left",
        x=0.01
    ))
    return plot(fig, include_plotlyjs=False, output_type="div")


@login_required(login_url='login')
def viral_track(request):
    if not request.user.first_name:
        return redirect("profile")
    #####################################
    # Pull CD4 data
    #####################################
    cd4_df = pd.DataFrame()
    cd4_qs = Cd4traker.objects.all()
    if cd4_qs.exists():
        # Use select_related to fetch related objects in a single query
        queryset = cd4_qs.select_related('facility_name', 'testing_laboratory', 'sub_county',
                                         'county').order_by('-date_of_collection')

        # Retrieve data as a list of dictionaries
        data = list(queryset.values(
            'county__county_name', 'sub_county__sub_counties', 'testing_laboratory__testing_lab_name',
            'facility_name__name', 'facility_name__mfl_code', 'patient_unique_no', 'age', 'sex',
            'date_of_collection', 'date_of_testing', 'date_sample_received', 'date_dispatched', 'justification',
            'cd4_count_results', 'date_serum_crag_results_entered', 'serum_crag_results', 'date_tb_lam_results_entered',
            'tb_lam_results', 'received_status', 'reason_for_rejection', 'tat_days', 'age_unit'
        ))
        cd4_df = prepare_df_cd4(data)

    vl_backlog_fig = vl_uptake_fig = cd4_uptake_fig = vl_backlog_detailed_fig = cd4_scrag_tblam_fig = vl_cascade_fig \
        = facility_name = None
    df = df1 = discordant_results = missing_in_labpulse = cd4_missing_in_emr = discordant_results_cd4 = \
        cd4_scrag = results_not_in_nascop_overall = missing_tb_lam = missing_scrag = missing_in_emr = backlog_df = \
        no_vl_ever = pd.DataFrame()

    # Get the current date
    current_date = pd.to_datetime(datetime.now().date())
    # Calculate the date one year ago from the current date
    one_year_ago = current_date - pd.DateOffset(years=1)

    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        form_emr = EmrFileUploadForm(request.POST, request.FILES)
        # date_picker_form = DateFilterForm(request.POST)
        # data_filter_form = DataFilterForm(request.POST)
        if form.is_valid() and form_emr.is_valid():
            # and date_picker_form.is_valid() and data_filter_form.is_valid():
            # Check if the uploaded files are CSV
            if not form.cleaned_data['file'].name.endswith('.csv'):
                messages.error(request,
                               f"Please upload a CSV file. The file '{form.cleaned_data['file'].name}' is not a CSV file.")
                return redirect('viral_track')

            if not form_emr.cleaned_data['file1'].name.endswith('.csv'):
                messages.error(request,
                               f"Please upload a CSV file. The file '{form_emr.cleaned_data['file1'].name}' is not a CSV file.")
                return redirect('viral_track')

            # Read the first CSV file
            df1 = pd.read_csv(form.cleaned_data['file'])

            # Read the second CSV file
            df = pd.read_csv(form_emr.cleaned_data['file1'])

            # Check if df contains "NUPI" and "Baseline CD4"
            df_has_nupi = "NUPI" in df.columns and "Baseline CD4" in df.columns

            # Check if df1 contains "NUPI" and "Baseline CD4"
            df1_has_nupi = "NUPI" in df1.columns and "Baseline CD4" in df1.columns

            # Ensure df is the DataFrame with "NUPI" and "Baseline CD4"
            if not df_has_nupi and df1_has_nupi:
                df, df1 = df1, df

        if "NUPI" not in df.columns:
            messages.error(request, "Please Upload Update Active on ART Patients Linelist.csv from Kenya EMR")
            return redirect("viral_track")
        if "Batch" not in df1.columns:
            messages.error(request, "Please Upload the correct dataset from NASCOP website. (See instructions below)")
            return redirect("viral_track")

        # Get the current date
        current_date = pd.to_datetime(datetime.now().date())

        # Get facility mfl code
        facility_mfl_code = df['MFL Code'].unique()[0]

        # Calculate the date one year ago from the current date
        one_year_ago = current_date - pd.DateOffset(years=1)

        df1 = transform_nascop_data(df1, one_year_ago, facility_mfl_code)

        # Calculate the date three months ago from the current date
        three_months_ago = current_date - pd.DateOffset(months=3)
        df['Art Start Date'] = pd.to_datetime(df['Art Start Date'])
        df = df[df['Art Start Date'] < three_months_ago]

        df = transform_emr_data(df)

        if len(list(df1['Facilty'].unique())) == 1:
            facility_name = df1['Facilty'].unique()[0]
        else:
            facility_name = ""

        # current_month_abbr = calendar.month_abbr[current_date.month]
        #
        # vl_month_abbr = calendar.month_abbr[df1['Date Collected'].min().month]
        # Get the current date
        current_date = pd.to_datetime(datetime.now().date())

        # # Example variables for current month abbreviation and VL month abbreviation
        # current_month_abbr = current_date.strftime("%b")  # e.g., 'Jun' for June
        # vl_month_abbr = one_year_ago.strftime("%b")  # e.g., 'Jun' for June of the previous year

        not_merged1_one_year_ago, not_merged1, has_results_within_test_month_above0, \
            has_results_within_test_month_below0, merged_df_100, results_not_in_nascop, \
            missing_results_outside_test_month, missing_results_below0 = separate_dfs(
            df, df1, current_date)
        no_vl_so_far, tx_new_not_eligible = process_vl_backlog(not_merged1_one_year_ago)
        discordant_results, with_results_df, missing_in_emr, results_not_in_nascop_overall, backlog_df, \
            no_vl_ever = generate_reports(no_vl_so_far, not_merged1, merged_df_100,
                                          has_results_within_test_month_above0,
                                          has_results_within_test_month_below0, results_not_in_nascop,
                                          missing_results_outside_test_month, missing_results_below0)
        vl_cascade = pd.DataFrame(
            {
                "With a valid VL": with_results_df.shape[0],
                "VL backlog": backlog_df.shape[0],
                f"Results missing in KenyaEMR": missing_in_emr.shape[0],
                f"Results missing in NASCOP's website": results_not_in_nascop_overall.shape[0],
                f"NASCOP_EMR discordance": discordant_results.shape[0],
            }.items(), columns=['Variable', "TX_CURR (Eligible)"]
        )
        vl_cascade['%'] = round(vl_cascade["TX_CURR (Eligible)"] / vl_cascade["TX_CURR (Eligible)"].sum() * 100, )
        vl_cascade['%'] = vl_cascade["TX_CURR (Eligible)"].astype(str) + " (" + vl_cascade['%'].astype(str) + "%)"
        vl_cascade.index += 1
        tx_curr_df = pd.DataFrame(
            {"TX_CURR (Eligible)": df.shape[0],

             }.items(), columns=['Variable', "TX_CURR (Eligible)"]
        )
        tx_curr_df['%'] = tx_curr_df["TX_CURR (Eligible)"]

        vl_cascade = pd.concat([tx_curr_df, vl_cascade])
        vl_cascade.index += 1
        dist_backlog = prep_categorical_columns(backlog_df, "eligibility criteria")

        backlog_df_age_band = backlog_df.groupby(["age_band", "Sex"])['CCC No'].count().reset_index()

        result, custom_order = sort_custom_agebands(backlog_df_age_band, 'age_band')
        result.columns = ['Age band', 'Sex', "TX_CURR (Eligible)"]
        result['%'] = (result["TX_CURR (Eligible)"] / result["TX_CURR (Eligible)"].sum() * 100).round().astype(int)

        result['%'] = result["TX_CURR (Eligible)"].astype(str) + " (" + result['%'].astype(str) + "%)"
        vl_backlog_fig = bar_chart(result, "Age band", "TX_CURR (Eligible)",
                                   title=f"VL BACKLOG n={backlog_df.shape[0]}",
                                   height=350, color="Sex",
                                   background_shadow=False, xaxis_title="Age Bands",
                                   text="%",
                                   title_size=12, axis_text_size=10, yaxis_title=None, legend_title="Sex")

        vl_uptake_df, overall_vl_uptake = calculate_vl_uptake(df, with_results_df)
        vl_uptake_fig = create_barchart_with_secondary_axis(vl_uptake_df, overall_vl_uptake, "VIRAL LOAD UPTAKE",
                                                            "VL Uptake")

        vl_backlog_detailed_fig = bar_chart(dist_backlog, "eligibility criteria", "TX_CURR (Eligible)",
                                            title=f"VL BACKLOG n={backlog_df.shape[0]}",
                                            height=350, background_shadow=False,
                                            xaxis_title="Eligibility Criteria",
                                            text="%",
                                            title_size=12, axis_text_size=10, yaxis_title=None, legend_title=None)

        vl_cascade_fig = bar_chart(vl_cascade, "Variable", "TX_CURR (Eligible)", title=f"VL CASCADE", height=350,
                                   background_shadow=False,
                                   xaxis_title="Variable",
                                   text="%",
                                   title_size=12, axis_text_size=10, yaxis_title="TX CURR", legend_title=None)
        ##########################################
        # CD4 REPORT
        ##########################################
        missing_in_labpulse, cd4_missing_in_emr, discordant_results_cd4, merged_cd4 = process_cd4_data(cd4_df, df,
                                                                                                       facility_mfl_code,
                                                                                                       one_year_ago)
        last_one_year_df = filter_and_preprocess_cd4(df, missing_in_labpulse, current_date)
        # Filter data for valid CD4 results
        cd4_results = last_one_year_df[~last_one_year_df['Latest CD4 Count Date '].isnull()]
        cd4_uptake_df, overall_cd4_uptake = calculate_vl_uptake(last_one_year_df, cd4_results)
        cd4_uptake_fig = create_barchart_with_secondary_axis(cd4_uptake_df, overall_cd4_uptake,
                                                             "CD4 UPTAKE (TX_NEW past 12 months)",
                                                             "CD4 Uptake")
        missing_tb_lam, missing_scrag, melted_df, s_crag_uptake, tb_lam_uptake = analyze_cd4_reflex_test_uptake(
            merged_cd4, one_year_ago)
        cd4_scrag_tblam_fig = compare_reflex_tests(melted_df, s_crag_uptake, tb_lam_uptake)
    else:
        form = FileUploadForm()
        form_emr = EmrFileUploadForm()
        # date_picker_form = DateFilterForm()
        # data_filter_form = DataFilterForm()

    # Convert DataFrames to dictionaries and store in session
    session_data = {
        'backlog_df': backlog_df,
        'missing_in_emr': missing_in_emr,
        'results_not_in_nascop_overall': results_not_in_nascop_overall.drop(columns=['date_difference'],
                                                                            errors='ignore'),
        'discordant_results': discordant_results,
        'no_vl_ever': no_vl_ever,
        'discordant_results_cd4': discordant_results_cd4,
        'cd4_missing_in_emr': cd4_missing_in_emr,
        'missing_in_labpulse': missing_in_labpulse,
        'missing_tb_lam': missing_tb_lam, "missing_scrag": missing_scrag,
    }
    set_session_data(request, session_data)

    # Filter backlog DataFrame based on criteria
    criteria_filters = {
        'hvl_pregnant': "hvl (pg/bf)",
        'hvl_above_25yrs': "hvl (>25yrs)",
        'hvl_zero_24yrs': "hvl (0-24yrs)",
        'missed_6mons_zero_24yrs': "missed 6 months vl (0-24yrs)",
        'missed_6mons_pregnant': "missed 6 months vl (pg/bf)",
        'missed_12mons_above_25yrs': "missed 12 months vl (>25yrs)"
    }
    if backlog_df.empty:
        backlog_df['eligibility criteria'] = ""
    filtered_data = {key: filter_backlog_df(backlog_df, criteria, 'eligibility criteria') for key, criteria in
                     criteria_filters.items()}

    # Add hvl_df which contains all records with 'hvl' in 'eligibility criteria'
    filtered_data['hvl_df'] = backlog_df[backlog_df['eligibility criteria'].str.contains("hvl")]

    set_session_data(request, filtered_data)

    # Convert dict_items into a list
    dictionary = get_key_from_session_names(request)

    context = {
        "form": form, "form_emr": form_emr, "cd4_scrag_tblam_fig": cd4_scrag_tblam_fig,
        # "date_picker_form": date_picker_form, "data_filter_form": data_filter_form,
        "vl_backlog_fig": vl_backlog_fig, "vl_uptake_fig": vl_uptake_fig, "cd4_uptake_fig": cd4_uptake_fig,
        "vl_backlog_detailed_fig": vl_backlog_detailed_fig, "vl_cascade_fig": vl_cascade_fig,
        "dictionary": dictionary, "one_year_ago": one_year_ago.strftime('%d %B %Y'),
        "backlog_df": backlog_df, "no_vl_ever": no_vl_ever, "current_date": current_date.strftime('%d %B %Y'),
        "missed_6mons_zero_24yrs": filtered_data['missed_6mons_zero_24yrs'], "cd4_scrag": cd4_scrag,
        "missed_6mons_pregnant": filtered_data['missed_6mons_pregnant'],
        "missed_12mons_above_25yrs": filtered_data['missed_12mons_above_25yrs'],
        "missing_in_emr": missing_in_emr, "discordant_results_cd4": discordant_results_cd4,
        "hvl_pregnant": filtered_data['hvl_pregnant'], "missing_in_labpulse": missing_in_labpulse,
        "hvl_above_25yrs": filtered_data['hvl_above_25yrs'], "cd4_missing_in_emr": cd4_missing_in_emr,
        "hvl_zero_24yrs": filtered_data['hvl_zero_24yrs'],
        "hvl_df": filtered_data['hvl_df'], 'missing_tb_lam': missing_tb_lam, "missing_scrag": missing_scrag,
        "results_not_in_nascop_overall": results_not_in_nascop_overall,
        "facility_name_date": f"{facility_name} {current_date.strftime('%Y-%m-%d')}",
        "discordant_results": discordant_results, "dqa_type": "viral track",
    }

    return render(request, 'data_analysis/viral_tracker.html', context)


def convert_mfl_code_to_int(df):
    # drop the rows containing letters
    df = df[pd.to_numeric(df['organisationunitcode'], errors='coerce').notnull()]
    df['organisationunitcode'] = df['organisationunitcode'].astype(int)
    return df


def normalize_khis_facilities(df1, fyj_facility_mfl_code):
    df1 = df1[~df1['organisationunitcode'].isnull()]
    df1 = convert_mfl_code_to_int(df1)
    df1 = df1[df1['organisationunitcode'].isin(fyj_facility_mfl_code)]
    return df1


def clean_up_khis_moh730b_regimen(variances_df):
    variances_df['regimen'] = variances_df['regimen'].str.replace("MoH 730B Revision 2017", "")
    variances_df['regimen'] = variances_df['regimen'].str.replace("MoH 730B Revision 2019", "")
    variances_df['regimen'] = variances_df['regimen'].str.replace("Paediatric preparations", "")
    variances_df['regimen'] = variances_df['regimen'].str.replace("Medicines for OIs", "")
    variances_df['regimen'] = variances_df['regimen'].str.replace("Adult preparations", "")
    variances_df['regimen'] = variances_df['regimen'].str.replace("TB/ HIV DRUGS", "")

    # Strip white spaces from both ends of each entry
    variances_df['regimen'] = variances_df['regimen'].str.strip()

    return variances_df


def sort_variances(neg_disc, col):
    neg_disc = clean_up_khis_moh730b_regimen(neg_disc)
    neg_disc['variances'] = abs(neg_disc['variances'])
    neg_disc = neg_disc.groupby(['regimen'])[['variances']].sum().reset_index().sort_values(
        "variances", ascending=False)
    neg_disc.columns = ['regimen', col]
    return neg_disc


def create_variance_bars(df_fig, col, county):
    # Create horizontal bar chart for negative variances
    fig = px.bar(df_fig.head(10), x=col, y='regimen', text=col, height=450,
                 orientation='h', title=f'Top 10 Drugs with {col.title()}: {county}',
                 labels={col: f'{col.title()}', 'regimen': 'Drug Name'},
                 color=col, color_continuous_scale='PuRd')
    fig.update_layout(yaxis={'categoryorder': 'total ascending'})
    return plot(fig, include_plotlyjs=False, output_type="div")


def create_variances_heatmap(variance_regimen, county):
    # Create a new dataframe with absolute values of variances
    heatmap_df = variance_regimen[
        ['regimen', 'negative variances', 'positive variances']].copy()
    heatmap_df['negative variances'] = heatmap_df['negative variances'].abs()
    heatmap_df['overall variances'] = heatmap_df['negative variances'] + heatmap_df[
        'positive variances']

    # Sort the dataframe by overall variances in descending order
    heatmap_df = heatmap_df.sort_values('overall variances', ascending=False)

    # Create the heatmap
    fig = px.imshow(
        heatmap_df[['negative variances', 'positive variances', 'overall variances']],
        labels=dict(x="Variance Type", y="Drug Name", color="Variance"),
        y=heatmap_df['regimen'],
        x=['Negative Variances', 'Positive Variances', 'Overall Variances'],
        color_continuous_scale='PuRd',
        aspect="auto",
        text_auto=True,
        title=f"Heatmap of Drug Variances: {county}")
    if len(heatmap_df) > 10:
        height = len(heatmap_df) * 25
    else:
        height = len(heatmap_df) * 55

    # Update layout for better readability
    fig.update_layout(
        #     width=1000,  # Adjust width as needed
        height=height,  # Adjust height based on number of drugs
        xaxis_side="top",
        yaxis={'dtick': 1, 'tickmode': 'linear'},
        coloraxis_colorbar=dict(
            title="Variance",
            ticksuffix=" units",
            lenmode="pixels", len=300,
        )
    )

    return plot(fig, include_plotlyjs=False, output_type="div")


def create_variance_visualizations(variances_df, county="FYJ"):
    neg_disc = sort_variances(variances_df[variances_df['variances'] < 0],
                              'negative variances')
    negative_var_fig = create_variance_bars(neg_disc, 'negative variances', county)

    pos_disc = sort_variances(variances_df[variances_df['variances'] > 0],
                              'positive variances')
    positive_var_fig = create_variance_bars(pos_disc, 'positive variances', county)

    variance_regimen = neg_disc.merge(pos_disc, on="regimen", how="outer").fillna(0)
    variance_regimen.columns = ['regimen', 'negative variances', 'positive variances']
    variance_regimen = variance_regimen.sort_values(
        by=['negative variances', 'positive variances'],
        ascending=False)
    overall_var_fig = create_variances_heatmap(variance_regimen, county)
    return negative_var_fig, positive_var_fig, overall_var_fig


def create_county_status_chart(county_status, level):
    # Sort the data by total ART sites in descending order
    county_status_sorted = county_status.sort_values('ART sites', ascending=False)

    county_names = county_status_sorted[level].tolist()
    facilities_without_variances = (county_status_sorted['ART sites'] - county_status_sorted[
        '# Facility with variances']).tolist()
    facilities_with_variances = county_status_sorted['# Facility with variances'].tolist()
    total_facilities = county_status_sorted['ART sites'].tolist()

    total_all_facilities = sum(total_facilities)

    fig = go.Figure(data=[
        go.Bar(name='Facilities without Variances', x=county_names,
               y=facilities_without_variances, marker_color='#0A255C',
               text=[f"{y} ({y / t * 100:.1f}%)" for y, t in
                     zip(facilities_without_variances, total_facilities)],
               textposition='inside'),
        go.Bar(name='Facilities with Variances', x=county_names, y=facilities_with_variances,
               marker_color='#B10023',
               text=[f"{y} ({y / t * 100:.1f}%)" for y, t in
                     zip(facilities_with_variances, total_facilities)],
               textposition='inside')
    ])

    for i, total in enumerate(total_facilities):
        fig.add_annotation(
            x=county_names[i],
            y=total,
            text=f"Total: {total}",
            showarrow=False,
            yshift=10,
            font=dict(color="black", size=10)
        )
    if level == "County":
        level = "Counties"
    elif level == "Subcounty":
        level = "Subcounties"

    fig.update_layout(
        title=f'Concordant Reports (MOH 730B) Across {level} (Total Facilities: {total_all_facilities})',
        barmode='stack',
        xaxis_title=level,
        yaxis_title='Number of ART Facilities',
        legend_title='Facility Status',
        height=500,
    )

    fig.update_traces(textfont=dict(size=10, color="white"))
    fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
    fig.update_layout(legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    ))

    return pio.to_html(fig, full_html=False)


def compile_concordance_report(variances_df, df1, level):
    county_variances = variances_df.groupby(level)['Facility_Name'].nunique().reset_index()

    # art_sites = pd.DataFrame(county_art_sites.items(), columns=[level, 'ART sites'])
    art_sites = \
        df1[df1['Care & Treatment(Yes/No)'].str.contains("yes", case=False)].groupby(
            [level])[
            'facility'].nunique().reset_index()
    art_sites.columns = [level, 'ART sites']
    county_status = art_sites.merge(county_variances, on=level, how="outer").fillna(0)
    county_status = county_status.rename(
        columns={"Facility_Name": "# Facility with variances"})
    county_status['Facility concordance %'] = round(
        100 - county_status['# Facility with variances'] / county_status['ART sites'] * 100, 1)

    # Usage:
    county_status_chart = create_county_status_chart(county_status, level)
    return county_status_chart


def pre_process_moh730b(df, df1):
    fyj_facility_mfl_code = df1['MFL Code'].unique()
    common_col = ['organisationunitid', 'organisationunitname', 'organisationunitcode',
                  'organisationunitdescription', 'periodid', 'periodname', 'month_year',
                  'periodcode',
                  'perioddescription']
    beginning_bal = [x for x in df.columns if "Beginning Balance" in x]

    ending_bal = [x for x in df.columns if "End of Month Physical Stock Count" in x]
    beginning_bal_df = df[common_col + beginning_bal]

    beginning_bal_df['report_type'] = "beginning balance"
    ending_bal_df = df[common_col + ending_bal]

    beginning_bal_df = beginning_bal_df.melt(id_vars=common_col, value_vars=beginning_bal,
                                             var_name='regimen', value_name='beginning_values')

    beginning_bal_df['report_type'] = "beginning balance"
    beginning_bal_df = beginning_bal_df.sort_values("month_year")

    beginning_bal_df = beginning_bal_df[
        beginning_bal_df['month_year'] == beginning_bal_df['month_year'].unique()[1]]
    beginning_bal_df['regimen'] = beginning_bal_df['regimen'].str.replace(" Beginning Balance", '')
    ending_bal_df = ending_bal_df.melt(id_vars=common_col,
                                       value_vars=ending_bal_df,
                                       var_name='regimen',
                                       value_name='ending_values')

    ending_bal_df['report_type'] = "ending balance"
    ending_bal_df = ending_bal_df.sort_values("month_year")
    ending_bal_df = ending_bal_df[ending_bal_df['month_year'] ==
                                  ending_bal_df['month_year'].unique()[0]]

    ending_bal_df['regimen'] = ending_bal_df['regimen'].str.replace(
        " End of Month Physical Stock Count", '')
    merged_df = ending_bal_df.merge(beginning_bal_df,
                                    on=[
                                        'organisationunitid',
                                        'organisationunitname',
                                        'organisationunitcode', 'regimen'
                                    ])
    merged_df = merged_df[[
        'organisationunitname', 'organisationunitcode', 'periodname_x', 'regimen',
        'ending_values', 'report_type_x', 'periodname_y', 'beginning_values',
        'report_type_y'
    ]]
    merged_df = merged_df.rename(
        columns={"periodname_x": "previous_month", "periodname_y": "month"})
    merged_df['variances'] = merged_df['ending_values'] - merged_df['beginning_values']

    merged_df = normalize_khis_facilities(merged_df, fyj_facility_mfl_code)
    merged_df = merged_df.merge(df1, left_on="organisationunitcode", right_on="MFL Code")
    merged_df = merged_df[['County', 'Subcounty', 'Hub',
                           'organisationunitname', 'organisationunitcode', 'previous_month',
                           'regimen',
                           'ending_values', 'report_type_x', 'month', 'beginning_values',
                           'report_type_y', 'variances'
                           ]]

    # convert all float columns to int
    m = merged_df.select_dtypes(np.number)
    merged_df[m.columns] = m.round().astype('Int64')
    merged_df = merged_df.rename(columns={"organisationunitname": "Facility_Name",
                                          "organisationunitcode": "MFL_Code"})
    prev_mon = merged_df['previous_month'].unique()[0]
    mon_name = merged_df['month'].unique()[0]

    # Get the current date and time
    current_time = datetime.now()

    # Format the current date and time as a string
    time_str = current_time.strftime("%Y-%m-%d %H-%M-%S")

    # Use the formatted time string in the file name
    filename = f"MOH 730B {mon_name} beginning bal vs {prev_mon} ending bal {time_str}"
    variances_df = merged_df[merged_df['variances'] != 0].sort_values("variances", ascending=False)

    variances_df = clean_up_khis_moh730b_regimen(variances_df)

    # Apply the decoding to the 'regimen' column
    variances_df['regimen'] = variances_df['regimen'].str.replace("/", "_")

    negative_var_fig_fyj, positive_var_fig_fyj, overall_var_fig_fyj = create_variance_visualizations(
        variances_df)
    visualize_variance = []
    for county in variances_df['County'].unique():
        county_df = variances_df[variances_df['County'] == county]
        negative_var_fig, positive_var_fig, overall_var_fig = create_variance_visualizations(
            county_df, county=county)
        visualize_variance.append(overall_var_fig)
        visualize_variance.append(positive_var_fig)
        visualize_variance.append(negative_var_fig)
    county_status_chart = compile_concordance_report(variances_df, df1, 'County')
    subcounty_status_chart = compile_concordance_report(variances_df, df1, 'Subcounty')
    return variances_df, visualize_variance, county_status_chart, subcounty_status_chart, filename, \
        negative_var_fig_fyj, positive_var_fig_fyj, overall_var_fig_fyj


@login_required(login_url='login')
def compare_opening_closing_bal_moh730b(request):
    final_df = pd.DataFrame()
    filename = None
    negative_var_fig_fyj = None
    positive_var_fig_fyj = None
    overall_var_fig_fyj = None
    visualize_variance = None
    county_status_chart = None
    subcounty_status_chart = None
    dictionary = None
    form = FileUploadForm(request.POST or None)
    report_name = "MOH 730B CONCORDANCE"
    variances_df = pd.DataFrame()
    datasets = [
        "MOH 730B Beginning balance",
        "MOH 730B Ending balance",
    ]

    if not request.user.first_name:
        return redirect("profile")
    if request.method == 'POST':
        try:
            form = FileUploadForm(request.POST, request.FILES)
            message = "It seems that the dataset you uploaded is incorrect. To proceed with the analysis, " \
                      "kindly upload the MoH 730B beginning balance and closing balance in one file. Please generate " \
                      "these files and ensure they are in CSV format before uploading them. You can find detailed " \
                      "instructions on how to upload the files below. Thank you. "
            if form.is_valid():
                file = request.FILES['file']
                if "csv" in file.name:
                    df = pd.read_csv(file).fillna(0)
                    df['month_year'] = pd.to_datetime(df['periodname'])
                else:
                    messages.success(request, message)
                    return redirect('compare_opening_closing_bal_moh730b')
                # Check if required columns exist in the DataFrame
                if len(df.columns) >= 140:
                    # Read data from FYJHealthFacility model into a pandas DataFrame
                    qs = FYJHealthFacility.objects.all()
                    df1 = pd.DataFrame.from_records(qs.values())

                    df1 = df1.rename(columns={
                        "mfl_code": "MFL Code", "county": "County", 'health_subcounty': 'Health Subcounty',
                        'subcounty': 'Subcounty', 'hub': 'Hub', 'm_and_e_mentor': 'M&E Mentor/SI associate',
                        'm_and_e_assistant': 'M&E Assistant', 'care_and_treatment': 'Care & Treatment(Yes/No)',
                        'hts': 'HTS(Yes/No)', 'vmmc': 'VMMC(Yes/No)', 'key_pop': 'Key Pop(Yes/No)',
                        'facility_type': 'Faclity Type', 'category': 'Category (HVF/MVF/LVF)', 'emr': 'EMR'
                    })
                    df1['MFL Code'] = df1['MFL Code'].astype(int)

                    if df.shape[0] > 0 and df1.shape[0] > 0:
                        variances_df, visualize_variance, county_status_chart, subcounty_status_chart, filename, negative_var_fig_fyj, positive_var_fig_fyj, overall_var_fig_fyj = pre_process_moh730b(
                            df, df1)
                else:
                    messages.success(request, message)
                    return redirect('compare_opening_closing_bal_moh730b')
            else:
                messages.success(request, message)
                return redirect('compare_opening_closing_bal_moh730b')
        except MultiValueDictKeyError:
            context = {
                "variances_df": variances_df, "negative_var_fig_fyj": negative_var_fig_fyj,
                "dictionary": dictionary, "positive_var_fig_fyj": positive_var_fig_fyj,
                "filename": filename, "overall_var_fig_fyj": overall_var_fig_fyj, "datasets": datasets,
                "county_status_chart": county_status_chart, "subcounty_status_chart": subcounty_status_chart,
                "visualize_variance": visualize_variance, "form": form, "report_name": report_name,
            }

            return render(request, 'data_analysis/upload.html', context)
    # start index at 1 for Pandas DataFrame
    variances_df.index = range(1, len(variances_df) + 1)
    # Drop date from dfs
    dfs = [variances_df]
    for df in dfs:
        if "date" in df.columns:
            df.drop('date', axis=1, inplace=True)
    request.session['variances_df'] = variances_df.to_dict()
    # Convert dict_items into a list
    dictionary = get_key_from_session_names(request)
    context = {
        "variances_df": variances_df, "filename": filename, "final_df": final_df,
        "dictionary": dictionary, "positive_var_fig_fyj": positive_var_fig_fyj, "datasets": datasets,
        "negative_var_fig_fyj": negative_var_fig_fyj, "visualize_variance": visualize_variance,
        "overall_var_fig_fyj": overall_var_fig_fyj, "county_status_chart": county_status_chart,
        "subcounty_status_chart": subcounty_status_chart, "form": form, "report_name": report_name,
    }

    return render(request, 'data_analysis/moh730B beginning vs closing.html', context)
