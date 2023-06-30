from django.urls import path

from apps.fyj_mentorship.views import choose_facilities_mentorship, add_fyj_staff_details, add_carders, update_carder, \
    add_facility_carders, update_facility_carder, add_facility_staff_details, update_facility_staff_details, \
    add_program_area, update_program_area, add_fyj_mentorship, update_mentorship_checklist, \
    create_mentorship_work_plans, show_mentorship, show_program_area, update_fyj_staff_details, \
    show_mentorship_work_plan

urlpatterns = [
    path('facilities-mentorship/', choose_facilities_mentorship, name="choose_facilities_mentorship"),

    path('fyj-mentorship/<str:report_name>/<str:quarter>/<str:year>/<uuid:pk>/<str:date>/<uuid:program_area>/', add_fyj_mentorship,
         name="add_fyj_mentorship"),
    path('add-carder/', add_carders, name="add_carders"),
    path('add-facility-carders/', add_facility_carders, name="add_facility_carders"),
    path('add-facility-staff-details/', add_facility_staff_details, name="add_facility_staff_details"),
    path('add-program-area/', add_program_area, name="add_program_area"),
    path('add-fyj-staff-details/', add_fyj_staff_details, name="add_fyj_staff_details"),
    path('create-mentorship-work-plan/<uuid:pk>/<str:report_name>/', create_mentorship_work_plans,
         name="create_mentorship_work_plans"),

    path('update-checklist/<uuid:pk>/<str:model>/', update_mentorship_checklist, name="update_mentorship_checklist"),
    path('update-carder/<uuid:pk>', update_carder, name="update_carder"),
    path('update-facility-carder/<uuid:pk>', update_facility_carder, name="update_facility_carder"),
    path('update-facility-staff-details/<uuid:pk>', update_facility_staff_details,
         name="update_facility_staff_details"),
    path('update-fyj-staff-details/<uuid:pk>', update_fyj_staff_details,
         name="update_fyj_staff_details"),
    path('update-program-area/<uuid:pk>', update_program_area, name="update_program_area"),

    path('show-mentorship/', show_mentorship, name="show_mentorship"),
    path('show-mentorship-workplan/', show_mentorship_work_plan, name="show_mentorship_work_plan"),
    path('program-areas/', show_program_area, name="show_program_area"),

]
