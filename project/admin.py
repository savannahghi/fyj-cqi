from django.contrib import admin

# Register your models here.
from project.forms import QI_ProjectsForm
from project.models import *


class QI_ProjectsAdmin(admin.ModelAdmin):
    """This class includes the follow-up triggers as checkboxes through the Django administration interface.To add
    the follow-up triggers as checkboxes, you need to create a custom form class, such as QI_ProjectsForm,
    which will allow you to include the desired checkboxes and then use this form in your custom QI_ProjectsAdmin
    class by setting form = QI_ProjectsForm. Once you have created this custom form, you can register your custom
    admin class instead of the model class like this: admin.site.register( QI_Projects, QI_ProjectsAdmin). """
    form = QI_ProjectsForm


admin.site.register(QI_Projects, QI_ProjectsAdmin)
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
admin.site.register(Qi_team_members)
admin.site.register(ArchiveProject)
admin.site.register(ActionPlan)
admin.site.register(Baseline)
admin.site.register(Comment)
admin.site.register(Trigger)
admin.site.register(Hub)
admin.site.register(SustainmentPlan)
# admin.site.register(RACI)

# admin.site.register(QI_Projects, SimpleHistoryAdmin)
# admin.site.register(TestedChange, SimpleHistoryAdmin)
# admin.site.register(QI_Projects, SimpleHistoryAdmin)
# admin.site.register(QI_Projects, SimpleHistoryAdmin)
# admin.site.register(QI_Projects, SimpleHistoryAdmin)
# admin.site.register(QI_Projects, SimpleHistoryAdmin)
# admin.site.register(QI_Projects, SimpleHistoryAdmin)
# admin.site.register(QI_Projects, SimpleHistoryAdmin)
