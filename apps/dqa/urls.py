from django.urls import path

from apps.dqa.views import add_data_verification, add_period, show_data_verification, update_data_verification, \
    delete_data_verification, load_data, dqa_summary, dqa_work_plan_create, show_dqa_work_plan, load_system_data, \
    add_system_verification, system_assessment_table, instructions

urlpatterns = [
    path('add-data-verification/', add_data_verification,name="add_data_verification"),
    path('add-system-verification/', add_system_verification,name="add_system_verification"),
    path('choose-period/', add_period,name="add_period"),
    path('show-data-verification/', show_data_verification,name="show_data_verification"),
    path('dqa/datim-load-data/', load_data, name='load_datim_data'),
    path('dqa/load_system_data/', load_system_data, name='load_system_data'),
    path('dqa_summary', dqa_summary, name='dqa_summary'),
    path('instructions', instructions, name='instructions'),
    path('system-assessment-table', system_assessment_table, name='system_assessment_table'),
    # path('create-dqa-work-plan/<uuid:pk>', dqa_work_plan_create, name='dqa_work_plan_create'),
    path('create-dqa-work-plan/<uuid:pk>/<str:quarter_year>/', dqa_work_plan_create, name='dqa_work_plan_create'),

    path('dqa-plan/', show_dqa_work_plan, name='show_dqa_work_plan'),

    path('update-data-verification/<uuid:pk>', update_data_verification,name="update_data_verification"),
    path('delete-data-verification/<uuid:pk>', delete_data_verification,name="delete_data_verification"),

]