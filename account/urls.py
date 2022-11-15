from django.urls import path

from account.views import *

urlpatterns = [
    path('register/', register,name="register"),
    path('profile/', update_profile,name="profile"),
    path('login/', login_page,name="login"),
    path('logout/', logout_page,name="logout"),
]