from django.contrib import admin

# Register your models here.
from apps.pmtct.models import PatientDetails, RiskCategorizationTrial

# admin.site.register(RiskCategorization)
admin.site.register(PatientDetails)
admin.site.register(RiskCategorizationTrial)
