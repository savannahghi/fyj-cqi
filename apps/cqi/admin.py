from django.contrib import admin

# Register your models here.
from apps.cqi.forms import QI_ProjectsForm
from apps.cqi.models import *


class QI_ProjectsAdmin(admin.ModelAdmin):
    """This class includes the follow-up triggers as checkboxes through the Django administration interface.To add
    the follow-up triggers as checkboxes, you need to create a custom form class, such as QI_ProjectsForm,
    which will allow you to include the desired checkboxes and then use this form in your custom QI_ProjectsAdmin
    class by setting form = QI_ProjectsForm. Once you have created this custom form, you can register your custom
    admin class instead of the model class like this: admin.site.register( QI_Projects, QI_ProjectsAdmin). """
    search_fields = ("facility_name__name", "facility_name__mfl_code", "project_title", "created_by__first_name",
                     "created_by__username")


class Hub_ProjectsAdmin(admin.ModelAdmin):
    search_fields = ("hub__hub", "project_title", "created_by__first_name", "created_by__username")


class Subcounty_ProjectsAdmin(admin.ModelAdmin):
    search_fields = ("sub_county__sub_counties", "project_title", "created_by__first_name", "created_by__username")


class County_ProjectsAdmin(admin.ModelAdmin):
    search_fields = ("county__county_name", "project_title", "created_by__first_name", "created_by__username")


class Program_ProjectsAdmin(admin.ModelAdmin):
    search_fields = ("program__program", "project_title", "created_by__first_name", "created_by__username")


@admin.register(PlatformUpdate)
class PlatformUpdateAdmin(admin.ModelAdmin):
    list_display = ('update_type', 'created_at', 'is_active')
    list_filter = ('update_type', 'is_active')
    search_fields = ('update_type', 'description')


# admin.site.register(QI_Projects, QI_ProjectsAdmin)
admin.site.register(QI_Projects, QI_ProjectsAdmin)
admin.site.register(TestedChange)
admin.site.register(ProjectComments)
admin.site.register(ProjectResponses)
admin.site.register(Counties)
admin.site.register(Sub_counties)
admin.site.register(Facilities)
admin.site.register(Department)
admin.site.register(Subcounty_qi_projects, Subcounty_ProjectsAdmin)
admin.site.register(County_qi_projects, County_ProjectsAdmin)
admin.site.register(Hub_qi_projects, Hub_ProjectsAdmin)
admin.site.register(Program_qi_projects, Program_ProjectsAdmin)
admin.site.register(Resources)
admin.site.register(Qi_managers)
admin.site.register(Qi_team_members)
admin.site.register(ArchiveProject)
admin.site.register(ActionPlan)
admin.site.register(Baseline)
admin.site.register(Comment)
admin.site.register(Trigger)
admin.site.register(Hub)
admin.site.register(SustainmentPlan)
admin.site.register(Program)
admin.site.register(RootCauseImages)
admin.site.register(Milestone)
admin.site.register(Lesson_learned)
admin.site.register(Category)
