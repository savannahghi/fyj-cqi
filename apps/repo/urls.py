from django.urls import path

from apps.repo.views import AuthorCreateView, AuthorUpdateView, CategoryCreateView, CategoryUpdateView, \
    ConferenceCreateView, ConferenceUpdateView, JournalCreateView, JournalUpdateView, ManuscriptCreateView, \
    ManuscriptDeleteView, \
    ManuscriptDetailView, \
    ManuscriptListView, \
    ManuscriptUpdateView, VenueCreateView, VenueUpdateView

urlpatterns = [
    path('create/', ManuscriptCreateView.as_view(), name='create_manuscript'),
    path('manuscript/list/', ManuscriptListView.as_view(), name='manuscript_list'),
    path('manuscript/<uuid:pk>/update/', ManuscriptUpdateView.as_view(), name='manuscript_update'),
    path('manuscript/<uuid:pk>/delete/', ManuscriptDeleteView.as_view(), name='manuscript_delete'),
    path('manuscript/<uuid:pk>/', ManuscriptDetailView.as_view(), name='manuscript_detail'),

    path('create/author/', AuthorCreateView.as_view(), name='create-author'),
    path('create/category/', CategoryCreateView.as_view(), name='create-category'),
    path('create/journal/', JournalCreateView.as_view(), name='create-journal'),
    path('create/conference/', ConferenceCreateView.as_view(), name='create-conference'),
    path('create/venue/', VenueCreateView.as_view(), name='create-venue'),

    path('update/author/<pk>/', AuthorUpdateView.as_view(), name='update-author'),
    path('update/category/<pk>/', CategoryUpdateView.as_view(), name='update-category'),
    path('update/journal/<pk>/', JournalUpdateView.as_view(), name='update-journal'),
    path('update/conference/<pk>/', ConferenceUpdateView.as_view(), name='update-conference'),
    path('update/venue/<pk>/', VenueUpdateView.as_view(), name='update-venue'),
]
