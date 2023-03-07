from django.urls import path

from apps.pmtct.views import add_patient_details, show_patient_details,add_client_characteristics_trial, \
    update_client_characteristics_trial

urlpatterns = [
    path('patient-details/', add_patient_details, name="add_patient_details"),
    # path('add-client-characteristics/<uuid:pk>', add_client_characteristics, name="add_client_characteristics"),
    path('add_client_characteristics_trial/<uuid:pk>', add_client_characteristics_trial, name="add_client_characteristics_trial"),
    # path('client-characterisation/<uuid:pk>', show_client_characterisation, name="show_client_characterisation"),
    # path('update-client-characteristics/<uuid:pk>', update_client_characteristics, name="update_client_characteristics"),
    path('update_client_characteristics_trial/<uuid:pk>', update_client_characteristics_trial, name="update_client_characteristics_trial"),
    path('show-patient-details/', show_patient_details, name="show_patient_details"),
    # path('try_adding_details/<uuid:pk>', try_adding_details, name="try_adding_details"),
]
