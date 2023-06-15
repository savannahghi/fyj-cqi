from django.urls import path

from apps.data_analysis.views import download_csv
from apps.labpulse.views import choose_testing_lab, add_cd4_count, update_cd4_results, show_results, GeneratePDF, \
    add_testing_lab

urlpatterns = [
    path('choose-testing-lab/', choose_testing_lab, name="choose_testing_lab"),
    path('add-testing-lab/', add_testing_lab, name="add_testing_lab"),
    path('add-cd4-count-results/<uuid:pk_lab>/', add_cd4_count, name="add_cd4_count"),
    path('update-results/<uuid:pk>/', update_cd4_results, name="update_cd4_results"),
    path('show-results/', show_results, name="show_results"),
    path('download/<str:name>/<str:filename>', download_csv, name='download_csv'),
    path('generate-pdf/', GeneratePDF.as_view(), name='generate_cd4_report_pdf'),

]
