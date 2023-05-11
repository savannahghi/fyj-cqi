from django.urls import path

from apps.data_analysis.views import pharmacy, download_csv, load_fyj_censused, tat, fmaps_reporting_rate, viral_load

urlpatterns = [
    path('pharmacy/', pharmacy, name="load_data_pharmacy"),
    path('download/<str:name>/<str:filename>', download_csv, name='download_csv'),
    path('load-fyj-censused-facilities', load_fyj_censused, name='load_fyj_censused'),
    path('fmaps-reporting-rate', fmaps_reporting_rate, name='fmaps_reporting_rate'),
    path('viral-load', viral_load, name='viral_load'),
    path('tat', tat, name='tat'),
]
