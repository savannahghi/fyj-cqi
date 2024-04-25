from django.contrib import admin

# Register your models here.
from apps.dqa.models import Period, Indicators, DataVerification, FyjPerformance, DQAWorkPlan, SystemAssessment, \
    AuditTeam, KhisPerformance, UpdateButtonSettings


class FyjPerformanceAdmin(admin.ModelAdmin):
    search_fields = ("facility", "mfl_code", "quarter_year", "month")


admin.site.register(Period)
admin.site.register(Indicators)
admin.site.register(DataVerification)
admin.site.register(FyjPerformance, FyjPerformanceAdmin)
admin.site.register(DQAWorkPlan)
admin.site.register(SystemAssessment)
admin.site.register(AuditTeam)
admin.site.register(KhisPerformance)
admin.site.register(UpdateButtonSettings)
