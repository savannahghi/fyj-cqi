import uuid

from crum import get_current_user
from django.db import models

# Create your models here.
from apps.account.models import CustomUser
from apps.cqi.models import Facilities, Hub, Sub_counties, Counties
from apps.dqa.models import Period
from apps.pharmacy.models import TableNames


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    created_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                   on_delete=models.CASCADE)
    model_name = models.ForeignKey(TableNames, on_delete=models.CASCADE, blank=True, null=True)
    modified_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                    on_delete=models.CASCADE, related_name='+')
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    class Meta:
        # the BaseModel won't create a separate database table
        abstract = True

    def save(self, *args, **kwargs):
        if not self.pk:
            # Record is being created, set created_by and modified_by fields
            self.created_by = get_current_user()
            self.modified_by = self.created_by
        else:
            # Record is being updated, set modified_by field
            self.modified_by = get_current_user()

        return super().save(*args, **kwargs)


class FacilityStaffCarders(BaseModel):
    carder = models.CharField(max_length=250, blank=True, null=True, unique=True)

    def __str__(self):
        return f"{self.carder}"

    class Meta:
        ordering = ['carder']
        verbose_name_plural = 'Facility staff carders'


class FyjCarders(BaseModel):
    carder = models.CharField(max_length=250, blank=True, null=True, unique=True)

    def __str__(self):
        return f"{self.carder}"

    class Meta:
        ordering = ['carder']
        verbose_name_plural = 'FYJ carders'


class FacilityStaffDetails(BaseModel):
    carder = models.ForeignKey(FacilityStaffCarders, blank=True, null=True, default=get_current_user,
                               on_delete=models.CASCADE)
    staff_name = models.CharField(max_length=100)
    facility_name = models.ForeignKey(Facilities, on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return f"{self.facility_name} {self.carder} {self.staff_name}"

    class Meta:
        ordering = ['facility_name', 'staff_name']
        unique_together = (('staff_name', 'facility_name'),)
        verbose_name_plural = 'Facility staff details'


class ProgramAreas(BaseModel):
    program_area = models.CharField(max_length=250, unique=True)

    def __str__(self):
        return f"{self.program_area}"

    class Meta:
        ordering = ['program_area']
        verbose_name_plural = 'Program Areas'


class FyjStaffDetails(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    HUB_CHOICES = [
        ("All Hubs", "All Hubs"),
        ("Hub 1 Nairobi", "Hub 1 Nairobi"),
        ("Hub 2 Nairobi", "Hub 2 Nairobi"),
        ("Hub 3 Nairobi", "Hub 3 Nairobi"),
        ("Hub 1 Kajiado", "Hub 1 Kajiado"),
        ("Hub 2 Kajiado", "Hub 2 Kajiado"),
        ("Hub 3 Kajiado", "Hub 3 Kajiado"),
    ]
    name = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                             on_delete=models.CASCADE)
    carder = models.ForeignKey(FyjCarders, blank=True, null=True, default=get_current_user,
                               on_delete=models.CASCADE)
    hub = models.CharField(max_length=25, choices=HUB_CHOICES)
    # hub = models.ForeignKey(Hub, blank=True, null=True, on_delete=models.CASCADE)
    modified_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                    on_delete=models.CASCADE, related_name='+')

    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name__first_name']
        unique_together = (('name', 'carder'),)
        verbose_name_plural = 'FYJ staff details'

    def __str__(self):
        return f"{self.name} {self.carder}"

    def save(self, *args, **kwargs):
        if not self.pk:
            # Record is being created, set created_by and modified_by fields
            self.name = get_current_user()
            self.modified_by = self.name
        else:
            # Record is being updated, set modified_by field
            self.modified_by = get_current_user()

        return super().save(*args, **kwargs)


class BaseBooleanModel(BaseModel):
    CHOICES = [
        ("", "-"),
        ("Yes", "Yes"),
        ("No", "No"),
    ]
    description = models.TextField()
    drop_down_options = models.CharField(max_length=4, choices=CHOICES)
    facility_name = models.ForeignKey(Facilities, on_delete=models.CASCADE, blank=True, null=True)
    program_area = models.ForeignKey(ProgramAreas, on_delete=models.CASCADE, blank=True, null=True)
    quarter_year = models.ForeignKey(Period, on_delete=models.CASCADE, blank=True, null=True)
    date_of_interview = models.DateField(blank=True, null=True)
    comments = models.CharField(max_length=600, blank=True, null=True)
    sub_county = models.ForeignKey(Sub_counties, null=True, blank=True, on_delete=models.CASCADE)
    county = models.ForeignKey(Counties, null=True, blank=True, on_delete=models.CASCADE)

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.facility_name} {self.description} ({self.date_of_interview}- {self.program_area})"


class Introduction(BaseBooleanModel):
    class Meta:
        verbose_name_plural = 'Introduction'


class IdentificationGaps(BaseBooleanModel):
    class Meta:
        verbose_name_plural = 'Identification of gaps'


class PrepareCoachingSession(BaseBooleanModel):
    class Meta:
        verbose_name_plural = 'Preparing for coaching session'


class CoachingSession(BaseBooleanModel):
    class Meta:
        verbose_name_plural = 'Coaching session'


class FollowUp(BaseBooleanModel):
    class Meta:
        verbose_name_plural = 'Follow up'


class MentorshipWorkPlan(BaseModel):
    facility_name = models.ForeignKey(Facilities, on_delete=models.CASCADE, blank=True, null=True)
    action_plan = models.TextField()
    gaps_identified = models.TextField()
    recommendation = models.TextField()
    percent_completed = models.IntegerField()
    individuals_responsible = models.TextField()
    timeframe = models.FloatField(null=True, blank=True)
    complete_date = models.DateField()
    quarter_year = models.ForeignKey(Period, on_delete=models.CASCADE, blank=True, null=True)
    # follow_up_plan = models.TextField()
    progress = models.FloatField(null=True, blank=True)
    introduction = models.ForeignKey(Introduction, on_delete=models.CASCADE, blank=True, null=True)
    identification_gaps = models.ForeignKey(IdentificationGaps, on_delete=models.CASCADE, blank=True, null=True)
    prepare_coaching_session = models.ForeignKey(PrepareCoachingSession, on_delete=models.CASCADE, blank=True,
                                                 null=True)
    coaching_session = models.ForeignKey(CoachingSession, on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        verbose_name_plural = "Work Plan"
        ordering = ['facility_name']

    def __str__(self):
        return f"{self.facility_name}  ({self.introduction}) ({self.identification_gaps}) " \
               f"({self.prepare_coaching_session}) ({self.coaching_session}) ({self.follow_up})"
