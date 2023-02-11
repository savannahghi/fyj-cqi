from django.contrib import admin

# Register your models here.
from dqa.models import Period, Indicators, DataVerification, FyjPerformance

# admin.site.register(Quarters)
admin.site.register(Period)
admin.site.register(Indicators)
admin.site.register(DataVerification)
admin.site.register(FyjPerformance)
