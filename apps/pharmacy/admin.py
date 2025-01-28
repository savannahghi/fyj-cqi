from django.contrib import admin

# Register your models here.
from apps.pharmacy.models import DeliveryNotes, PharmacyFpModel, PharmacyFpQualitativeModel, PharmacyMalariaModel, \
    PharmacyMalariaQualitativeModel, \
    PharmacyRecords, StockCards, \
    TableNames, UnitSupplied, \
    BeginningBalance, \
    PositiveAdjustments, UnitIssued, NegativeAdjustment, ExpiredUnits, Expired, ExpiryTracking, \
    S11FormAvailability, S11FormEndorsed, StockManagement, WorkPlan


# class InventoryAdmin(admin.ModelAdmin):
#     search_fields = (
#         "facility_name__name", "facility_name__mfl_code", "quarter_year")
class InventoryAdmin(admin.ModelAdmin):
    search_fields = (
        "facility_name__name",
        "facility_name__mfl_code",
        "quarter_year__quarter_year",
        "quarter_year__quarter",
        "quarter_year__year", "date_of_interview","date_created"
    )


admin.site.register(PharmacyRecords,InventoryAdmin)
admin.site.register(StockCards, InventoryAdmin)
admin.site.register(UnitSupplied, InventoryAdmin)
admin.site.register(BeginningBalance, InventoryAdmin)
admin.site.register(PositiveAdjustments, InventoryAdmin)
admin.site.register(UnitIssued, InventoryAdmin)
admin.site.register(NegativeAdjustment, InventoryAdmin)
admin.site.register(ExpiredUnits, InventoryAdmin)
admin.site.register(Expired, InventoryAdmin)
admin.site.register(ExpiryTracking, InventoryAdmin)
admin.site.register(S11FormAvailability, InventoryAdmin)
admin.site.register(S11FormEndorsed, InventoryAdmin)
admin.site.register(StockManagement, InventoryAdmin)
admin.site.register(WorkPlan, InventoryAdmin)
admin.site.register(PharmacyFpQualitativeModel, InventoryAdmin)
admin.site.register(PharmacyMalariaModel, InventoryAdmin)
admin.site.register(PharmacyMalariaQualitativeModel, InventoryAdmin)
admin.site.register(DeliveryNotes, InventoryAdmin)
admin.site.register(TableNames)
admin.site.register(PharmacyFpModel, InventoryAdmin)
