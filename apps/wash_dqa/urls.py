from django.urls import path

from apps.wash_dqa.views import GeneratePDF, add_audit_team, add_data_concordance, add_documentation, \
    export_wash_dqa_work_plan_csv, load_county_sub_county_ward_data, \
    load_jphes_data, show_audit_team, show_data_concordance, show_wash_dqa, show_wash_dqa_work_plan, update_audit_team, \
    update_data_concordance, \
    update_wash_dqa, update_wash_dqa_workplan, wash_dqa_dashboard, wash_dqa_summary, wash_dqa_work_plan_create

urlpatterns = [
    path('add-data-concordance/', add_data_concordance,name="add_data_concordance"),
    path('data-entry/<str:report_type>', add_documentation,name="add_documentation"),
    path('add-audit-team/<uuid:pk>/<str:quarter_year>', add_audit_team,name="add_audit_team_wash"),
    # path('choose-period/', add_period,name="add_period"),
    path('show-data-concordance/', show_data_concordance,name="show_data_concordance"),
    # path('dqa/datim-load-data/', load_data, name='load_datim_data'),
    path('load_jphes_data/', load_jphes_data, name='load_jphes_data'),
    path('county-subcounty-ward-data/', load_county_sub_county_ward_data, name='load_county_sub_county_ward_data'),
    # path('dqa/load_system_data/', load_system_data, name='load_system_data'),
    # path('dqa/update-button-settings/', update_button_settings, name='update_button_settings'),
    path('summary', wash_dqa_summary, name='wash_dqa_summary'),
    # path('instructions', instructions, name='instructions'),
    path('summary/<str:report_type>', show_wash_dqa, name='show_wash_dqa'),
    # path('system-assessment-table', system_assessment_table, name='system_assessment_table'),
    path('create-dqa-work-plan/<uuid:pk>/<str:quarter_year>/', wash_dqa_work_plan_create, name='wash_dqa_work_plan_create'),
    #
    path('work-plan/', show_wash_dqa_work_plan, name='show_wash_dqa_work_plan'),
    path('audit-team/', show_audit_team, name='show_wash_audit_team'),
    path('dqa-dashboard/<str:dqa_type>', wash_dqa_dashboard, name='wash_dqa_dashboard'),
    #
    path('update-data-concordance/<uuid:pk>', update_data_concordance,name="update_data_concordance"),
    path('update/<str:report_type>/<uuid:pk>', update_wash_dqa,name="update_wash_dqa"),
    path('update-audit-team/<uuid:pk>', update_audit_team,name="update_audit_team_wash"),
    path('update-workplan/<uuid:pk>', update_wash_dqa_workplan,name="update_wash_dqa_workplan"),
    # path('delete-data-verification/<uuid:pk>', delete_data_verification,name="delete_data_verification"),
    # # path('dqa_summary_pdf/', generate_pdf, name='dqa_summary_pdf'),
    path('generate-pdf/', GeneratePDF.as_view(), name='generate_wash_pdf'),
    path('download-wash-dqa-workplan/<str:quarter_year>/<str:selected_level>/<str:name>/', export_wash_dqa_work_plan_csv, name='export_wash_dqa_work_plan_csv'),

]