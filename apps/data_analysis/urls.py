from django.urls import include, path

from apps.data_analysis.views import UploadRTKDataView, compare_opening_closing_bal_moh730b, pharmacy, download_csv, \
    load_fyj_censused, rtk_inventory_viz, \
    rtk_visualization, \
    tat, fmaps_reporting_rate, viral_load, viral_track

urlpatterns = [
    path('pharmacy/', pharmacy, name="load_data_pharmacy"),
    path('download/<str:name>/<str:filename>', download_csv, name='download_csv'),
    path('load-fyj-censused-facilities', load_fyj_censused, name='load_fyj_censused'),
    path('fmaps-reporting-rate', fmaps_reporting_rate, name='fmaps_reporting_rate'),
    path('opening-closing-bal-moh730b', compare_opening_closing_bal_moh730b, name='compare_opening_closing_bal_moh730b'),
    path('viral-load', viral_load, name='viral_load'),
    path('viratrack/', viral_track, name='viral_track'),
    path('tat', tat, name='tat'),
    path('upload-rtks-data/', UploadRTKDataView.as_view(), name='upload_rtk'),
    path('rtk-visualization/', rtk_visualization, name='rtk_visualization'),
    path('rtk-inventory-viz/', rtk_inventory_viz, name='rtk_inventory_viz'),
]
# urlpatterns += [path('silk/', include('silk.urls', namespace='silk'))]