from django.urls import path

from apps.pharmacy.views import add_pharmacy_records, add_inventory, dqa_dashboard,\
    show_work_plan, \
    choose_facilities_inventory, choose_facilities_pharmacy, show_inventory, update_inventory, show_commodity_records, \
    update_pharmacy_records, create_inventory_work_plans, create_commodity_work_plans, update_workplan, \
    add_audit_team_pharmacy, show_audit_team_pharmacy, update_audit_team_pharmacy

urlpatterns = [
    path('add-commodities/<str:register_name>/<str:quarter>/<str:year>/<uuid:pk>/<str:date>/', add_pharmacy_records,
         name="add_pharmacy_records"),
    path('facility-inventory/', choose_facilities_inventory, name="choose_facilities_inventory"),
    path('facility-pharmacy/', choose_facilities_pharmacy, name="choose_facilities_pharmacy"),
    path('inventory/<str:report_name>/<str:quarter>/<str:year>/<uuid:pk>/<str:date>/', add_inventory,
         name="add_inventory"),
    path('work-plan/', show_work_plan, name="pharmacy_show_work_plan"),
    path('create-inventory-work-plan/<uuid:pk>/<str:report_name>/', create_inventory_work_plans,
         name="create_work_plan"),
    path('create-commodity-work-plan/<uuid:pk>/', create_commodity_work_plans, name="create_commodity_work_plans"),
    path('inventory/', show_inventory, name="show_inventory"),
    path('commodity-records/', show_commodity_records, name="show_commodity_records"),
    path('update-inventory/<uuid:pk>/<str:model>/', update_inventory, name="update_inventory"),
    path('update-records/<uuid:pk>/<str:register_name>', update_pharmacy_records, name="update_pharmacy_records"),
    path('update-workplan/<uuid:pk>/', update_workplan, name="update_workplan"),
    path('add-audit-team/<uuid:pk>/<str:quarter_year>', add_audit_team_pharmacy, name="add_pharmacy_audit_team"),
    path('audit-team/', show_audit_team_pharmacy, name='show_audit_team_pharmacy'),
    path('update-audit-team/<uuid:pk>', update_audit_team_pharmacy, name="update_audit_team_pharmacy"),
    path('pharmacy-dqa-dashboard/<str:dqa_type>', dqa_dashboard, name='pharmacy_dqa_dashboard'),
    # path('pharmacy-dqa-dashboard/', dqa_dashboard, name='pharmacy_dqa_dashboard'),

    # path('get_filtered_facilities/', get_filtered_facilities, name='get_filtered_facilities'),
]
