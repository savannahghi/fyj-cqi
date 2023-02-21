from django.urls import path


from apps.account.views import update_profile
from apps.cqi.views import dashboard, deep_dive_facilities, load_data, monthly_data_review, deep_dive_chmt, \
    qi_team_members_view, qi_managers_view, archived, audit_trail, show_all_comments, comments_no_response, \
    comments_with_response, single_project_comments, update_comments, comments_response, update_response, \
    untracked_projects, resources, sub_counties_list, single_project, single_project_program, facility_project, \
    department_project, department_filter_project, qi_managers_filter_project, facility_filter_project, \
    qicreator_filter_project, county_filter_project, sub_county_filter_project, qi_creator, qi_managers_projects, \
    canceled_projects, not_started, completed_closed, add_lesson_learnt, lesson_learnt, show_project_comments, \
    like_dislike, show_sustainmentPlan, toggle_archive_project, ongoing, measurement_frequency, postponed, \
    add_stake_holders, add_qi_manager, add_department, add_category, add_subcounty, add_facility, add_hub, add_county, \
    add_resources, add_project, choose_project_level, add_project_facility, add_project_subcounty, add_project_county, \
    add_project_hub, add_project_program, add_qi_team_member, add_project_milestone, add_corrective_action, \
    add_sustainmentplan, add_baseline_image, add_images, create_comment, add_program, qi_team_involved, \
    facilities_landing_page, program_landing_page, update_project, tested_change, update_test_of_change, \
    update_resource, update_qi_managers, update_qi_team_member, update_milestone, update_sub_counties, update_hub, \
    update_action_plan, update_lesson_learnt, update_baseline, update_fields, update_sustainable_plan, \
    delete_test_of_change, delete_project, delete_comment, delete_response, delete_resource, delete_qi_team_member, \
    delete_milestone, delete_action_plan, delete_lesson_learnt, delete_comments, delete_sustainable_plan, \
    download_lessons, download_pdf, add_trigger

urlpatterns = [
    path('', dashboard, name="dashboard"),
    path('deep-dive-facilities/', deep_dive_facilities, name="deep_dive_facilities"),
    path('cqi/load-data/', load_data, name='load_data'),
    path('monthly-data-reviews/', monthly_data_review, name='monthly_data_review'),
    # path('login/', login_page, name="login_page"),
    # path('register/', register_page, name="register"),
    # path('update-profile/<int:pk>', update_profile, name="update_profile"),
    path('update-profile/', update_profile, name="update_profile"),
    path('deep-dive-chmt/', deep_dive_chmt, name="deep_dive_chmt"),
    # path('qi-team-members/', qi_team_members, name="qi_team_members"),
    path('qi-team-members/', qi_team_members_view, name="qi_team_members"),
    # path('qi-managers/', qi_managers, name="qi_managers"),
    path('qi-managers/', qi_managers_view, name="qi_managers"),
    path('archived/', archived, name="archived"),
    path('audit-trail/', audit_trail, name="audit_trail"),
    # path('comments/', comments, name="comments"),
    path('show_all_comments/', show_all_comments, name="comments"),
    path('comments-no-response/', comments_no_response, name="comments_no_response"),
    path('comments-with-response/', comments_with_response, name="comments_with_response"),
    path('single-cqi-comments/<int:pk>/', single_project_comments, name="single_project_comments"),
    path('update-comments/<int:pk>/', update_comments, name="update_comments"),
    path('comments-response/<int:pk>/', comments_response, name="comments_response"),
    path('update-response/<int:pk>/', update_response, name="update_response"),
    path('untracked-projects/', untracked_projects, name="untracked_projects"),
    path('resources/', resources, name="resources"),
    path('sub-counties-list/', sub_counties_list, name="sub_counties_list"),
    path('single-cqi/<int:pk>', single_project, name="single_project"),
    path('single-cqi-program/<int:pk>', single_project_program, name="single_project_program"),
    path('facility-projects/<str:pk>', facility_project, name="facility_project"),
    path('department-projects/<str:pk>', department_project, name="department_project"),
    path('department-all-projects/<str:pk>', department_filter_project, name="department_filter_project"),
    path('qi-managers-own-cqi/<int:pk>', qi_managers_filter_project, name="qi_managers_filter_project"),
    path('facility-all-projects/<str:pk>', facility_filter_project, name="facility_filter_project"),
    path('qicreator-all-projects/<str:pk>', qicreator_filter_project, name="qicreator_filter_project"),
    path('county-all-projects/<str:pk>', county_filter_project, name="county_filter_project"),
    path('subcounty-all-projects/<str:pk>', sub_county_filter_project, name="sub_county_filter_project"),
    path('qi-creator/<str:pk>', qi_creator, name="qi_creators"),
    path('qi-managers-projects/<int:pk>', qi_managers_projects, name="qi_managers_projects"),
    path('canceled-projects/<str:pk>', canceled_projects, name="canceled_projects"),
    path('not-started/<str:pk>', not_started, name="not_started"),
    path('completed-closed/<str:pk>', completed_closed, name="completed_closed"),
    path('add-lesson-learnt/<int:pk>', add_lesson_learnt, name="add_lesson_learnt"),
    path('lesson-learnt/', lesson_learnt, name="lesson_learnt"),
    # path('show-qi-cqi-comments/<int:pk>', show_project_comments, name="show_project_comments"),

    path('show-project-comments-facility/<int:pk>/<str:facility_name>/', show_project_comments, name='show_project_comments_facility'),
    path('show-project-comments-program/<int:pk>/<str:program_name>/', show_project_comments, name='show_project_comments_program'),

    path('like-dislike/<int:pk>', like_dislike, name="like_dislike"),
    path('show-sustainmentPlan/', show_sustainmentPlan, name="show_sustainmentPlan"),


    # path('archive-cqi/<int:project_id>', archive_project, name="archive_project"),
    # path('unarchive-cqi/<int:pk>', unarchive_project, name="unarchive_project"),
    path('unarchive-cqi/<int:project_id>', toggle_archive_project, name="toggle_archive_project"),
    path('ongoing-projects/<str:pk>', ongoing, name="ongoing"),
    path('measurement-frequency/<str:pk>', measurement_frequency, name="measurement_frequency"),
    path('postponed/<str:pk>', postponed, name="postponed"),
    path('add-stake-holders/<int:pk>', add_stake_holders, name="add_stake_holders"),
    path('add-qi-manager/', add_qi_manager, name="add_qi_manager"),
    path('add-department/', add_department, name="add_department"),
    path('add-category/', add_category, name="add_category"),
    path('add-subcounty/', add_subcounty, name="add_subcounty"),
    path('add-facility/', add_facility, name="add_facility"),
    path('add-hub/', add_hub, name="add_hub"),
    path('add-county/', add_county, name="add_county"),
    path('add-resources/', add_resources, name="add_resources"),
    path('add-cqi/', add_project, name="add_project"),
    path('choose-cqi-level/', choose_project_level, name="choose_project_level"),
    path('add-cqi/facility', add_project_facility, name="add_project_facility"),
    path('add-cqi/subcounty', add_project_subcounty, name="add_project_subcounty"),
    path('add-cqi/county', add_project_county, name="add_project_county"),
    path('add-cqi/hub', add_project_hub, name="add_project_hub"),
    path('add-cqi/program', add_project_program, name="add_project_program"),
    # path('add-qi-team-member/<int:pk>', add_qi_team_member, name="add_qi_team_member"),

    path('add-qi-team-member-facility/<int:pk>/<str:facility_name>/', add_qi_team_member, name='add_qi_team_member_facility'),
    path('add-qi-team-member-program/<int:pk>/<str:program_name>/', add_qi_team_member, name='add_qi_team_member_program'),

    # path('add-cqi-milestone/<int:pk>', add_project_milestone, name="add_project_milestone"),
    path('add-project-milestone-facility/<int:pk>/<str:facility_name>/', add_project_milestone, name='add_project_milestone_facility'),
    path('add-project-milestone-program/<int:pk>/<str:program_name>/', add_project_milestone, name='add_project_milestone_program'),
    # path('add-corrective-action/<int:pk>', add_corrective_action, name="add_corrective_action"),

    path('add-corrective-action-facility/<int:pk>/<str:facility_name>/', add_corrective_action, name='add_corrective_action_facility'),
    path('add-corrective-action-program/<int:pk>/<str:program_name>/', add_corrective_action, name='add_corrective_action_program'),

    path('add-lesson-learnt/', add_lesson_learnt, name="add_lesson_learnt"),
    path('add-sustainment-plan/<int:pk>', add_sustainmentplan, name="add_sustainmentplan"),
    # path('add-baseline-image/<int:pk>', add_baseline_image, name="add_baseline_image"),

    path('add-baseline-image-facility/<int:pk>/<str:facility_name>/', add_baseline_image, name='add_baseline_image_facility'),
    path('add-baseline-image-program/<int:pk>/<str:program_name>/', add_baseline_image, name='add_baseline_image_program'),

    path('add-image-facility/<int:pk>/<str:facility_name>/', add_images, name='add_image_facility'),
    path('add-image-program/<int:pk>/<str:program_name>/', add_images, name='add_image_program'),

    # path('add-image/<int:pk>', add_images, name="add_images"),
    # path('create-comment/<int:pk>', create_comment, name="create_comment"),
    path('create-comment-facility/<int:pk>/<str:facility_name>/', create_comment, name='create_comment_facility'),
    path('create-comment-program/<int:pk>/<str:program_name>/', create_comment, name='create_comment_program'),

    path('add-program/', add_program, name="add_program"),
    path('add-trigger/', add_trigger, name="add_trigger"),


    path('qi-projects-involved-in/<int:pk>', qi_team_involved, name="qi_team_involved"),

    path('facilities-landing-page/', facilities_landing_page, name="facilities_landing_page"),
    path('program-landing-page/', program_landing_page, name="program_landing_page"),
    # path('update-cqi/<int:pk>/', update_project, name="update_project"),
    path('update-project-facility/<int:pk>/<str:facility_name>/', update_project, name='update_project_facility'),
    path('update-project-program/<int:pk>/<str:program_name>/', update_project, name='update_project_program'),

    # path('tested-change/<int:pk>/', tested_change, name="tested_change"),
    path('add-tested-change-facility/<int:pk>/<str:facility_name>/', tested_change, name='tested_change_facility'),
    path('add-tested-change-program/<int:pk>/<str:program_name>/', tested_change, name='tested_change_program'),

    path('update-test-of-change/<int:pk>/', update_test_of_change, name="update_test_of_change"),
    path('update-resource/<int:pk>/', update_resource, name="update_resource"),
    path('update-qi-managers/<int:pk>/', update_qi_managers, name="update_qi_managers"),
    path('update-qi-team-member/<int:pk>/', update_qi_team_member, name="update_qi_team_member"),
    path('update-milestone/<int:pk>/', update_milestone, name="update_milestone"),
    path('update-sub-counties/<int:pk>/', update_sub_counties, name="update_sub_counties"),
    path('update-hub/<int:pk>/', update_hub, name="update_hub"),
    path('update-action-plan/<int:pk>/', update_action_plan, name="update_action_plan"),
    path('update-lesson-learnt/<int:pk>/', update_lesson_learnt, name="update_lesson_learnt"),
    path('update-baseline/<int:pk>/', update_baseline, name="update_baseline"),
    path('update-fields', update_fields, name="update_fields"),
    path('update-sustainable-plan/<int:pk>', update_sustainable_plan, name="update_sustainable_plan"),

    path('update-comments/<int:pk>/', update_comments, name="update_comments"),

    path('delete-test-of-change/<int:pk>/', delete_test_of_change, name="delete_test_of_change"),
    path('delete-cqi/<int:pk>', delete_project, name="delete_project"),
    path('delete-commment/<int:pk>/', delete_comment, name="delete_comment"),
    path('delete-response/<int:pk>/', delete_response, name="delete_response"),
    path('delete-resource/<int:pk>/', delete_resource, name="delete_resource"),
    path('delete-qi-team-member/<int:pk>/', delete_qi_team_member, name="delete_qi_team_member"),
    path('delete-milestone/<int:pk>/', delete_milestone, name="delete_milestone"),
    path('delete-action-plan/<int:pk>/', delete_action_plan, name="delete_action_plan"),
    path('delete-lesson-learnt/<int:pk>/', delete_lesson_learnt, name="delete_lesson_learnt"),
    path('delete-comments/<int:pk>/', delete_comments, name="delete_comments"),
    path('delete-sustainable-plan/<int:pk>/', delete_sustainable_plan, name="delete_sustainable_plan"),

    # DOWNLOADS

    path('download_lessons', download_lessons, name="download_lessons"),
    path('download_pdf', download_pdf, name="download_pdf"),


]
