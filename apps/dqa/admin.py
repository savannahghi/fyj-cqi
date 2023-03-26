from django.contrib import admin

# Register your models here.
from apps.dqa.models import Period, Indicators, DataVerification, FyjPerformance, DQAWorkPlan, SystemAssessment, \
    AuditTeam, KhisPerformance, UpdateButtonSettings

admin.site.register(Period)
admin.site.register(Indicators)
admin.site.register(DataVerification)
admin.site.register(FyjPerformance)
admin.site.register(DQAWorkPlan)
admin.site.register(SystemAssessment)
admin.site.register(AuditTeam)
admin.site.register(KhisPerformance)
admin.site.register(UpdateButtonSettings)
