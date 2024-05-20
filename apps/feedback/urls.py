from django.urls import path
from . import views

# app_name = 'feedback'

urlpatterns = [
    path('apps/', views.apps_list, name='apps_list'),
    path('create-apps/', views.create_app, name='create_app'),
    path('feedback/', views.feedback_list, name='feedback_list'),
    path('submit-feedback/', views.submit_feedback, name='submit_feedback'),
    path('feedback-with-response/', views.feedback_with_response, name='feedback_with_response'),
    path('feedback-without-response/', views.feedback_without_response, name='feedback_without_response'),

    path('feedback/<uuid:pk>/respond/', views.respond_to_feedback, name='respond_to_feedback'),
    path('apps/<uuid:pk>/', views.app_detail, name='app_detail'),
    path('single-feedback/<uuid:pk>/', views.feedback_detail, name='feedback_detail'),

    path('feedback/<uuid:pk>/update/', views.update_feedback, name='update_feedback'),
    path('app/<uuid:pk>/update/', views.update_app, name='update_app'),
    path('app/<uuid:pk>/delete/', views.AppDeleteView.as_view(), name='delete_app'),

    path('response/<uuid:pk>/update/', views.update_response, name='update_response'),
]
