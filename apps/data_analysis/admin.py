from django.contrib import admin

# Register your models here.
from apps.data_analysis.models import FYJHealthFacility, RTKData


class RtkDataAdmin(admin.ModelAdmin):
    search_fields = ("month", "facility_name", "commodity_name", "county")


class FYJHealthFacilityAdmin(admin.ModelAdmin):
    search_fields = ("facility", "mfl_code", "facility_type", "county","subcounty")


admin.site.register(FYJHealthFacility, FYJHealthFacilityAdmin)
admin.site.register(RTKData, RtkDataAdmin)
