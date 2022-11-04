from django.urls import path
from project.views import *

urlpatterns = [
    path('', dashboard, name="dashboard"),
    path('fyj/deep-dive-facilities/', deep_dive_facilities, name="deep_dive_facilities"),
    path('fyj/deep-dive-chmt/', deep_dive_chmt, name="deep_dive_chmt"),
    path('fyj/qi-team-members/', qi_team_members, name="qi_team_members"),
    path('fyj/qi-managers/', qi_managers, name="qi_managers"),
    path('fyj/archived/', archived, name="archived"),
    path('fyj/audit-trail/', audit_trail, name="audit_trail"),
    path('fyj/comments/', comments, name="comments"),
    path('fyj/resources/', resources, name="resources"),
    path('fyj/single-project/', single_project, name="single_project"),
]
