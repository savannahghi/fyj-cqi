from django.contrib import admin
from apps.dqa.models import (
    CareTreatment, Cqi, Gbv, Hts, Period, Indicators, DataVerification, FyjPerformance,
    DQAWorkPlan, Pharmacy, Prep, SystemAssessment, AuditTeam, KhisPerformance, Tb,
    UpdateButtonSettings, Vmmc
)


class BaseAdmin(admin.ModelAdmin):
    search_fields = ("facility_name__name", "facility_name__mfl_code", "quarter_year__quarter_year",
                     "quarter_year__year", "quarter_year__quarter")


class FyjPerformanceAdmin(admin.ModelAdmin):
    search_fields = ("facility", "mfl_code", "quarter_year", "month")


admin_classes = {
    FyjPerformance: FyjPerformanceAdmin,
    Gbv: BaseAdmin,
    Vmmc: BaseAdmin,
    Hts: BaseAdmin,
    Prep: BaseAdmin,
    Tb: BaseAdmin,
    CareTreatment: BaseAdmin,
    Pharmacy: BaseAdmin,
    Cqi: BaseAdmin,
}

for model, admin_class in admin_classes.items():
    admin.site.register(model, admin_class)

admin.site.register(Period)
admin.site.register(Indicators)
admin.site.register(DataVerification)
admin.site.register(DQAWorkPlan)
admin.site.register(SystemAssessment)
admin.site.register(AuditTeam)
admin.site.register(KhisPerformance)
admin.site.register(UpdateButtonSettings)
