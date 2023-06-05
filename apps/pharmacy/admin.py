from django.contrib import admin

# Register your models here.
from apps.pharmacy.models import PharmacyRecords, StockCards, UnitSupplied, BeginningBalance, \
    PositiveAdjustments, UnitIssued, NegativeAdjustment, ExpiredUnits, Expired, ExpiryTracking, \
    S11FormAvailability, S11FormEndorsed, StockManagement, WorkPlan

admin.site.register(PharmacyRecords)
admin.site.register(StockCards)
admin.site.register(UnitSupplied)
admin.site.register(BeginningBalance)
# admin.site.register(UnitReceived)
admin.site.register(PositiveAdjustments)
admin.site.register(UnitIssued)
admin.site.register(NegativeAdjustment)
admin.site.register(ExpiredUnits)
admin.site.register(Expired)
admin.site.register(ExpiryTracking)
admin.site.register(S11FormAvailability)
admin.site.register(S11FormEndorsed)
admin.site.register(StockManagement)
admin.site.register(WorkPlan)
# admin.site.register(PharmacyAuditTeam)
