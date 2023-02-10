from django.urls import path

from dqa.views import add_data_verification, add_period, show_data_verification, update_data_verification, \
    delete_data_verification

urlpatterns = [
    path('add-data-verification/', add_data_verification,name="add_data_verification"),
    path('choose-period/', add_period,name="add_period"),
    path('show-data-verification/', show_data_verification,name="show_data_verification"),

    path('update-data-verification/<int:pk>', update_data_verification,name="update_data_verification"),
    path('delete-data-verification/<int:pk>', delete_data_verification,name="delete_data_verification"),

]