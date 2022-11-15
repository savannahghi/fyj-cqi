from django.urls import path
from project.views import *

urlpatterns = [
    path('', dashboard, name="dashboard"),
    path('deep-dive-facilities/', deep_dive_facilities, name="deep_dive_facilities"),
    # path('login/', login_page, name="login_page"),
    # path('register/', register_page, name="register"),
    # path('update-profile/<int:pk>', update_profile, name="update_profile"),
    path('update-profile/', update_profile, name="update_profile"),
    path('deep-dive-chmt/', deep_dive_chmt, name="deep_dive_chmt"),
    path('qi-team-members/', qi_team_members, name="qi_team_members"),
    path('qi-managers/', qi_managers, name="qi_managers"),
    path('archived/', archived, name="archived"),
    path('audit-trail/', audit_trail, name="audit_trail"),
    path('comments/', comments, name="comments"),
    path('resources/', resources, name="resources"),
    path('single-project/<int:pk>', single_project, name="single_project"),
    path('facility-projects/<str:pk>', facility_project, name="facility_project"),
    path('department-projects/<str:pk>', department_project, name="department_project"),
    path('qi-creator/<str:pk>', qi_creator, name="qi_creators"),
    path('add-project/', add_project, name="add_project"),
    path('facilities-landing-page/', facilities_landing_page, name="facilities_landing_page"),
    path('update-project/<int:pk>/', update_project, name="update_project"),
    path('tested-change/<int:pk>/', tested_change, name="tested_change"),
    path('update-test-of-change/<int:pk>/', update_test_of_change, name="update_test_of_change"),
    path('delete-test-of-change/<int:pk>/', delete_test_of_change, name="delete_test_of_change"),
    path('delete-project/<int:pk>', delete_project, name="delete_project"),
]
