from django.urls import path

from apps.data_analysis.views import download_csv
from apps.labpulse.views import add_commodities, add_facility, choose_lab, choose_testing_lab, add_cd4_count, \
    instructions_lab, \
    update_cd4_results, show_results, \
    GeneratePDF, \
    add_testing_lab, update_reagent_stocks, update_testing_labs, lab_pulse_update_button_settings, \
    choose_testing_lab_manual

urlpatterns = [
    path('choose-testing-lab/', choose_testing_lab, name="choose_testing_lab"),
    path('choose-lab/', choose_lab, name="choose_lab"),
    path('choose-testing-lab-retrospective/', choose_testing_lab_manual, name="choose_testing_lab_manual"),
    path('add-testing-lab/', add_testing_lab, name="add_testing_lab"),
    path('add-facility/laboratory/', add_facility, name="add_facility"),
    path('add-cd4-count-results/<str:report_type>/<uuid:pk_lab>/', add_cd4_count, name="add_cd4_count"),
    path('add-commodities/<uuid:pk_lab>/', add_commodities, name="add_commodities"),
    path('update-results/<str:report_type>/<uuid:pk>/', update_cd4_results, name="update_cd4_results"),
    path('update-testing-labs/<uuid:pk>/', update_testing_labs, name="update_testing_labs"),
    path('update-reagent-stocks/<uuid:pk>/', update_reagent_stocks, name="update_reagent_stocks"),
    path('show-results/', show_results, name="show_results"),
    path('instructions-lab/<str:section>/', instructions_lab, name="instructions_lab"),
    path('download/<str:name>/<str:filename>', download_csv, name='download_csv'),
    path('generate-pdf/', GeneratePDF.as_view(), name='generate_cd4_report_pdf'),
    path('update-button-settings/', lab_pulse_update_button_settings, name='lab_pulse_update_button_settings'),

]
