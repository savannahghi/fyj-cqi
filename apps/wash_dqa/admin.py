from django.contrib import admin

from apps.wash_dqa.models import Counties, DataCollectionReportingManagement, DataConcordance, DataQualityAssessment, \
    DataQualitySystems, \
    Documentation, JphesPerformance, Period, \
    SubCounties, Ward, WashAuditTeam, WashDQAWorkPlan

# Register your models here.
admin.site.register(Counties)
admin.site.register(SubCounties)
admin.site.register(Ward)
admin.site.register(JphesPerformance)
admin.site.register(Period)
admin.site.register(Documentation)
admin.site.register(DataQualitySystems)
admin.site.register(DataCollectionReportingManagement)
admin.site.register(DataQualityAssessment)
admin.site.register(DataConcordance)
admin.site.register(WashAuditTeam)
admin.site.register(WashDQAWorkPlan)