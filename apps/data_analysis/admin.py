from django.contrib import admin

# Register your models here.
from apps.data_analysis.models import FYJHealthFacility, RTKData

admin.site.register(FYJHealthFacility)
admin.site.register(RTKData)