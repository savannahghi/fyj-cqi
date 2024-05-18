"""config URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin

from django.urls import path, include
from django_select2 import urls as django_select2_urls
from django.contrib.staticfiles.storage import staticfiles_storage
from django.views.generic.base import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    # https://stackoverflow.com/a/57042608
    path('favicon.ico', RedirectView.as_view(url=staticfiles_storage.url('images/favicon.png'))),
    path('', include('apps.cqi.urls')),
    path('', include('apps.account.urls')),
    path('', include('apps.dqa.urls')),
    path('', include('apps.pmtct.urls')),
    path('feedback-hub/fyj/', include('apps.feedback.urls')),
    path('dac/', include('apps.data_analysis.urls')),
    path('pharmacy_dqa/fyj/', include('apps.pharmacy.urls')),
    path('lab_pulse/fyj/', include('apps.labpulse.urls')),
    path('fyj_mentorship/fyj/', include('apps.fyj_mentorship.urls')),
    path('wash_dqa/fyj/', include('apps.wash_dqa.urls')),
    path('repository/fyj/', include('apps.repo.urls')),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path('select2/', include(django_select2_urls)),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
