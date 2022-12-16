from django.contrib import admin

# Register your models here.
from project.models import *

admin.site.register(QI_Projects)
admin.site.register(TestedChange)
admin.site.register(ProjectComments)
admin.site.register(ProjectResponses)
admin.site.register(Counties)
admin.site.register(Sub_counties)
admin.site.register(Facilities)
admin.site.register(Department)
admin.site.register(Subcounty_qi_projects)
admin.site.register(County_qi_projects)
admin.site.register(Hub_qi_projects)
admin.site.register(Program_qi_projects)
admin.site.register(Resources)
admin.site.register(Qi_managers)
