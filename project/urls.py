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
    path('comments-no-response/', comments_no_response, name="comments_no_response"),
    path('comments-with-response/', comments_with_response, name="comments_with_response"),
    path('single-project-comments/<int:pk>/', single_project_comments, name="single_project_comments"),
    path('update-comments/<int:pk>/', update_comments, name="update_comments"),
    path('comments-response/<int:pk>/', comments_response, name="comments_response"),
    path('update-response/<int:pk>/', update_response, name="update_response"),
    path('resources/', resources, name="resources"),
    path('single-project/<int:pk>', single_project, name="single_project"),
    path('facility-projects/<str:pk>', facility_project, name="facility_project"),
    path('department-projects/<str:pk>', department_project, name="department_project"),
    path('department-all-projects/<str:pk>', department_filter_project, name="department_filter_project"),
    path('facility-all-projects/<str:pk>', facility_filter_project, name="facility_filter_project"),
    path('qicreator-all-projects/<str:pk>', qicreator_filter_project, name="qicreator_filter_project"),
    path('qi-creator/<str:pk>', qi_creator, name="qi_creators"),
    path('canceled-projects/<str:pk>', canceled_projects, name="canceled_projects"),
    path('not-started/<str:pk>', not_started, name="not_started"),
    path('completed-closed/<str:pk>', completed_closed, name="completed_closed"),
    path('ongoing-projects/<str:pk>', ongoing, name="ongoing"),
    path('measurement-frequency/<str:pk>', measurement_frequency, name="measurement_frequency"),
    path('postponed/<str:pk>', postponed, name="postponed"),
    path('add-project/', add_project, name="add_project"),
    path('facilities-landing-page/', facilities_landing_page, name="facilities_landing_page"),
    path('update-project/<int:pk>/', update_project, name="update_project"),
    path('tested-change/<int:pk>/', tested_change, name="tested_change"),
    path('update-test-of-change/<int:pk>/', update_test_of_change, name="update_test_of_change"),
    path('delete-test-of-change/<int:pk>/', delete_test_of_change, name="delete_test_of_change"),
    path('delete-project/<int:pk>', delete_project, name="delete_project"),
    path('delete-commment/<int:pk>/', delete_comment, name="delete_comment"),
    path('delete-response/<int:pk>/', delete_response, name="delete_response"),
]
