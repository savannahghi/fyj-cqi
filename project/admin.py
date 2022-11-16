from django.contrib import admin

# Register your models here.
from project.models import QI_Projects, TestedChange, ProjectComments

admin.site.register(QI_Projects)
admin.site.register(TestedChange)
admin.site.register(ProjectComments)
