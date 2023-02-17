from django.urls import path

from apps.account.views import register, update_profile, login_page, logout_page

urlpatterns = [
    path('register/', register,name="register"),
    path('profile/', update_profile,name="profile"),
    path('login/', login_page,name="login"),
    path('logout/', logout_page,name="logout"),
]