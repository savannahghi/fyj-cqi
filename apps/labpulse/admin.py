from django.contrib import admin

from apps.labpulse.models import BiochemistryResult, Cd4traker, Cd4TestingLabs, Commodities, DrtResults, \
    EnableDisableCommodities, \
    LabPulseUpdateButtonSettings, ReagentStock
from django.contrib.auth.models import Permission

# Register your models here.
admin.site.register(Cd4TestingLabs)
admin.site.register(Cd4traker)
admin.site.register(Permission)
admin.site.register(LabPulseUpdateButtonSettings)
admin.site.register(Commodities)
admin.site.register(ReagentStock)
admin.site.register(EnableDisableCommodities)
admin.site.register(BiochemistryResult)
admin.site.register(DrtResults)
