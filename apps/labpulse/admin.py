from django.contrib import admin

from apps.labpulse.models import BiochemistryResult, Cd4traker, Cd4TestingLabs, Commodities, DrtPdfFile, DrtProfile, \
    DrtResults, EnableDisableCommodities, HistologyPdfFile, HistologyResults, LabPulseUpdateButtonSettings, ReagentStock
from django.contrib.auth.models import Permission


class BioChemAdmin(admin.ModelAdmin):
    search_fields = ("facility__name", "facility__mfl_code", "test", "full_name", "patient_id", "age", "performed_by",
                     "date_created", "collection_date", "result_time")


class Cd4trakerAdmin(admin.ModelAdmin):
    search_fields = (
        "facility_name__name", "facility_name__mfl_code", "reason_for_rejection", "reason_for_no_serum_crag",
        "patient_unique_no", "received_status", "date_of_collection")


class DrtResultsAdmin(admin.ModelAdmin):
    search_fields = (
        "facility_name__name", "facility_name__mfl_code", "patient_id")


class ReagentStockAdmin(admin.ModelAdmin):
    search_fields = (
        "facility_name__name", "facility_name__mfl_code", "date_commodity_received")


class HistologyResultsPdfFileAdmin(admin.ModelAdmin):
    search_fields = (
        "facility_name__name", "facility_name__mfl_code", "patient_id")


# Register your models here.
admin.site.register(Cd4TestingLabs)
admin.site.register(Cd4traker, Cd4trakerAdmin)
admin.site.register(Permission)
admin.site.register(LabPulseUpdateButtonSettings)
admin.site.register(Commodities)
admin.site.register(ReagentStock,ReagentStockAdmin)
admin.site.register(EnableDisableCommodities)
admin.site.register(BiochemistryResult, BioChemAdmin)
admin.site.register(DrtResults, DrtResultsAdmin)
admin.site.register(DrtPdfFile)
admin.site.register(DrtProfile)
admin.site.register(HistologyPdfFile)
admin.site.register(HistologyResults, HistologyResultsPdfFileAdmin)
