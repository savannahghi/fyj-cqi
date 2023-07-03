from django.contrib import admin

# Register your models here.
from apps.fyj_mentorship.models import FyjCarders, FyjStaffDetails, FacilityStaffCarders, FacilityStaffDetails, \
    ProgramAreas, Introduction, IdentificationGaps, PrepareCoachingSession, CoachingSession, FollowUp, \
    MentorshipWorkPlan

admin.site.register(FyjCarders)
admin.site.register(FyjStaffDetails)
admin.site.register(FacilityStaffCarders)
admin.site.register(FacilityStaffDetails)
admin.site.register(ProgramAreas)
admin.site.register(Introduction)
admin.site.register(IdentificationGaps)
admin.site.register(PrepareCoachingSession)
admin.site.register(CoachingSession)
admin.site.register(FollowUp)
admin.site.register(MentorshipWorkPlan)
