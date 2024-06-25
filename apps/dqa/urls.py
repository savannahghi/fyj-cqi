from django.conf import settings
from django.urls import include, path

from apps.dqa.views import GeneratePDF, add_audit_team, add_data_verification, add_period, add_system_verification, \
    choose_facilities_sqa, delete_data_verification, dqa_dashboard, dqa_summary, dqa_work_plan_create, \
    export_dqa_work_plan_csv, instructions, load_data, load_khis_data, load_system_data, show_audit_team, \
    show_data_verification, show_dqa_work_plan, sqa, sqa_table, system_assessment_table, update_audit_team, \
    update_button_settings, update_data_verification, update_dqa_workplan, update_sqa, update_system_assessment

urlpatterns = [
    path('add-data-verification/', add_data_verification, name="add_data_verification"),
    path('add-system-verification/', add_system_verification, name="add_system_verification"),
    path('add-audit-team/<uuid:pk>/<str:quarter_year>', add_audit_team, name="add_audit_team"),
    path('choose-period/', add_period, name="add_period"),
    path('show-data-verification/', show_data_verification, name="show_data_verification"),
    path('dqa/datim-load-data/', load_data, name='load_datim_data'),
    path('dqa/khis-load-data/', load_khis_data, name='load_khis_data'),
    path('dqa/load_system_data/', load_system_data, name='load_system_data'),
    path('dqa/update-button-settings/', update_button_settings, name='update_button_settings'),
    path('facility/dqa_summary', dqa_summary, name='facility_dqa_summary'),
    path('instructions', instructions, name='instructions'),
    path('system-assessment-table', system_assessment_table, name='system_assessment_table'),
    path('sqa-table', sqa_table, name='sqa_table'),
    # path('create-dqa-work-plan/<uuid:pk>', dqa_work_plan_create, name='dqa_work_plan_create'),
    path('create-dqa-work-plan/<uuid:pk>/<str:quarter_year>/', dqa_work_plan_create, name='dqa_work_plan_create'),

    path('dqa-plan/', show_dqa_work_plan, name='show_dqa_work_plan'),
    path('audit-team/', show_audit_team, name='show_audit_team'),
    path('dqa-dashboard/<str:dqa_type>', dqa_dashboard, name='dqa_dashboard'),

    path('update-data-verification/<uuid:pk>', update_data_verification, name="update_data_verification"),
    path('update-system-assessment/<uuid:pk>', update_system_assessment, name="update_system_assessment"),
    path('update/<str:model_name>/<uuid:pk>/', update_sqa, name='update_sqa'),
    path('update-audit-team/<uuid:pk>', update_audit_team, name="update_audit_team"),
    path('update-dqa-workplan/<uuid:pk>', update_dqa_workplan, name="update_dqa_workplan"),
    path('delete-data-verification/<uuid:pk>', delete_data_verification, name="delete_data_verification"),
    # path('dqa_summary_pdf/', generate_pdf, name='dqa_summary_pdf'),
    path('generate-pdf/', GeneratePDF.as_view(), name='generate-pdf'),
    path('download-dqa-workplan/<str:quarter_year>/<str:selected_level>/', export_dqa_work_plan_csv,
         name='download_dqa_workplan'),

    path('facility-sqa/', choose_facilities_sqa, name="choose_facilities_sqa"),
    path('sqa/<str:report_name>/<str:quarter>/<str:year>/<uuid:pk>', sqa, name="sqa"),

]
# Include debug toolbar URLs only in DEBUG mode
# if settings.DEBUG:
#     import debug_toolbar
#     urlpatterns += [
#         path('__debug__/', include(debug_toolbar.urls)),
#     ]
