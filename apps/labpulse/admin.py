from django.contrib import admin

from apps.labpulse.models import Cd4traker, Cd4TestingLabs
from django.contrib.auth.models import Permission

# Register your models here.
admin.site.register(Cd4TestingLabs)
admin.site.register(Cd4traker)
admin.site.register(Permission)
