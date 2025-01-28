import uuid

from crum import get_current_user
from django.core.exceptions import ValidationError
from django.db import models

# Create your models here.
from apps.account.models import CustomUser
from apps.cqi.models import Facilities
from apps.dqa.models import Period


class Registers(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    register_name = models.CharField(max_length=250, unique=True, blank=True, null=True)

    def __str__(self):
        return self.register_name


def validate_non_negative(value):
    if value < 0:
        raise ValidationError("Negative values are not allowed.")


def validate_currently_in_use(value):
    if value.register_available == 'Yes' and not value.currently_in_use:
        raise ValidationError("Currently in use is required when register is available.")
    elif value.register_available == 'No' and value.currently_in_use:
        raise ValidationError("Currently in use should not be specified when register is not available.")


class TableNames(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    model_name = models.CharField(max_length=25, blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Table names'

    def __str__(self):
        return self.model_name


class PharmacyRecords(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    # TODO: ALLOW USERS TO ADD INDICATORS
    CHOICES = [
        ('', 'Select an option'),
        ("Yes", "Yes"),
        ("No", "No"),
        ("N/A", "N/A"),
    ]
    date_of_interview = models.DateField(blank=True, null=True)
    # register_name = models.CharField(max_length=150)
    register_name = models.ForeignKey(Registers, on_delete=models.CASCADE, blank=True, null=True)
    register_available = models.CharField(max_length=10,
                                          choices=CHOICES, blank=True, null=True, default="N/A"
                                          )
    currently_in_use = models.CharField(max_length=10, choices=[("", "-"), ("Yes", "Yes"), ("No", "No"), ("N/A", "N/A")]
                                        , blank=True, null=True,
                                        )
    last_month_copy = models.CharField(max_length=10,
                                       choices=CHOICES, blank=True, null=True, default="N/A"
                                       )
    comments = models.TextField(blank=True)
    date_report_submitted = models.DateField(null=True, blank=True)
    facility_name = models.ForeignKey(Facilities, on_delete=models.CASCADE, blank=True, null=True)
    quarter_year = models.ForeignKey(Period, on_delete=models.CASCADE, blank=True, null=True)
    created_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                   on_delete=models.CASCADE)
    modified_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                    on_delete=models.CASCADE, related_name='+')

    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (("quarter_year", "register_name", "facility_name", "date_of_interview"),)
        ordering = ['facility_name']
        verbose_name_plural = 'PharmacyRecords'

    def __str__(self):
        return f"{self.facility_name} {self.register_name} ({self.quarter_year}) ({self.date_of_interview})"

    def save(self, *args, **kwargs):
        if not self.pk:
            # Record is being created, set created_by and modified_by fields
            self.created_by = get_current_user()
            self.modified_by = self.created_by
        else:
            # Record is being updated, set modified_by field
            self.modified_by = get_current_user()

        return super().save(*args, **kwargs)

    def record_type(self):
        return "PharmacyRecord"


class DeliveryNotes(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    # TODO: ALLOW USERS TO ADD INDICATORS
    CHOICES = [
        ('', 'Select an option'),
        ("Yes", "Yes"),
        ("No", "No"),
        ("N/A", "N/A"),
    ]
    date_of_interview = models.DateField(blank=True, null=True)
    register_name = models.ForeignKey(Registers, on_delete=models.CASCADE, blank=True, null=True)
    register_available = models.CharField(max_length=10,
                                          choices=CHOICES
                                          )
    last_month_copy = models.CharField(max_length=10,
                                       choices=CHOICES
                                       )
    comments = models.TextField(blank=True)
    facility_name = models.ForeignKey(Facilities, on_delete=models.CASCADE, blank=True, null=True)
    quarter_year = models.ForeignKey(Period, on_delete=models.CASCADE, blank=True, null=True)
    created_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                   on_delete=models.CASCADE)
    modified_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                    on_delete=models.CASCADE, related_name='+')

    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (("quarter_year", "register_name", "facility_name", "date_of_interview"),)
        ordering = ['facility_name']
        verbose_name_plural = 'Delivery Notes'

    def __str__(self):
        return f"{self.facility_name} {self.register_name} ({self.quarter_year}) ({self.date_of_interview})"

    def save(self, *args, **kwargs):
        if not self.pk:
            # Record is being created, set created_by and modified_by fields
            self.created_by = get_current_user()
            self.modified_by = self.created_by
        else:
            # Record is being updated, set modified_by field
            self.modified_by = get_current_user()

        return super().save(*args, **kwargs)

    def record_type(self):
        return "DeliveryNote"


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    date_of_interview = models.DateField(blank=True, null=True)
    model_name = models.ForeignKey(TableNames, on_delete=models.CASCADE, blank=True, null=True)
    facility_name = models.ForeignKey(Facilities, on_delete=models.CASCADE, blank=True, null=True)
    quarter_year = models.ForeignKey(Period, on_delete=models.CASCADE, blank=True, null=True)
    created_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                   on_delete=models.CASCADE)
    modified_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                    on_delete=models.CASCADE, related_name='+')
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    class Meta:
        # the BaseModel won't create a separate database table
        abstract = True
        ordering = ['facility_name']
    def save(self, *args, **kwargs):
        if not self.pk:
            # Record is being created, set created_by and modified_by fields
            self.created_by = get_current_user()
            self.modified_by = self.created_by
        else:
            # Record is being updated, set modified_by field
            self.modified_by = get_current_user()

        return super().save(*args, **kwargs)


class BaseBooleanModel(BaseModel):
    CHOICES = [
        ("", "-"),
        ("Yes", "Yes"),
        ("No", "No"),
        ("N/A", "N/A"),
    ]
    description = models.TextField()
    adult_arv_tdf_3tc_dtg = models.CharField(max_length=4, choices=CHOICES, default="N/A")
    pead_arv_dtg_10mg = models.CharField(max_length=4, choices=CHOICES, default="N/A")
    pead_arv_dtg_50mg = models.CharField(max_length=4, choices=CHOICES, default="N/A")
    paed_arv_abc_3tc_120_60mg = models.CharField(max_length=4, choices=CHOICES, default="N/A")
    tb_3hp = models.CharField(max_length=4, choices=CHOICES, default="N/A")
    r_inh = models.CharField(max_length=4, choices=CHOICES, default="N/A")
    comments = models.CharField(max_length=600, blank=True, null=True)

    class Meta:
        abstract = True
        # unique_together = (("quarter_year", "description", "facility_name", "date_of_interview"),)


    def __str__(self):
        return f"{self.facility_name} {self.description} ({self.date_of_interview})"


class BaseReportModel(BaseModel):
    description = models.TextField()
    adult_arv_tdf_3tc_dtg = models.IntegerField(validators=[validate_non_negative], default=0)
    pead_arv_dtg_10mg = models.IntegerField(validators=[validate_non_negative], default=0)
    pead_arv_dtg_50mg = models.IntegerField(validators=[validate_non_negative], default=0)
    paed_arv_abc_3tc_120_60mg = models.IntegerField(validators=[validate_non_negative], default=0)
    tb_3hp = models.IntegerField(validators=[validate_non_negative], default=0)
    r_inh = models.IntegerField(validators=[validate_non_negative], default=0)
    comments = models.TextField(blank=True, null=True)

    class Meta:
        abstract = True
        unique_together = (("quarter_year", "description", "facility_name", "date_of_interview"),)
        ordering = ['facility_name']

    def __str__(self):
        return f"{self.facility_name} {self.description} ({self.date_of_interview})"


class PharmacyMalariaModel(BaseModel):
    description = models.TextField()
    al_24 = models.IntegerField(validators=[validate_non_negative], default=0)
    al_6 = models.IntegerField(validators=[validate_non_negative], default=0)
    comments = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = (("quarter_year", "description", "facility_name", "date_of_interview"),)
        ordering = ['facility_name']
        verbose_name_plural = 'Anti-Malaria'

    def __str__(self):
        return f"{self.facility_name} {self.description} ({self.date_of_interview})"


class PharmacyFpModel(BaseModel):
    description = models.TextField()
    family_planning_rod = models.IntegerField(validators=[validate_non_negative], default=0)
    family_planning_rod2 = models.IntegerField(validators=[validate_non_negative], default=0)
    dmpa_im = models.IntegerField(validators=[validate_non_negative], default=0)
    dmpa_sc = models.IntegerField(validators=[validate_non_negative], default=0)
    comments = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = (("quarter_year", "description", "facility_name", "date_of_interview"),)
        ordering = ['facility_name']
        verbose_name_plural = 'Family planning'

    def __str__(self):
        return f"{self.facility_name} {self.description} ({self.date_of_interview})"


class PharmacyMalariaQualitativeModel(BaseModel):
    CHOICES = [
        ("", "-"),
        ("Yes", "Yes"),
        ("No", "No"),
        ("N/A", "N/A"),
    ]
    description = models.TextField()
    al_24 = models.CharField(max_length=4, choices=CHOICES, default="N/A")
    al_6 = models.CharField(max_length=4, choices=CHOICES, default="N/A")
    comments = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = (("quarter_year", "description", "facility_name", "date_of_interview"),)
        ordering = ['facility_name']
        verbose_name_plural = 'Anti-Malaria Qualitative'

    def __str__(self):
        return f"{self.facility_name} {self.description} ({self.date_of_interview})"


class PharmacyFpQualitativeModel(BaseModel):
    CHOICES = [
        ("", "-"),
        ("Yes", "Yes"),
        ("No", "No"),
        ("N/A", "N/A"),
    ]
    description = models.TextField()
    family_planning_rod = models.CharField(max_length=4, choices=CHOICES, default="N/A")
    family_planning_rod2 = models.CharField(max_length=4, choices=CHOICES, default="N/A")
    dmpa_im = models.CharField(max_length=4, choices=CHOICES, default="N/A")
    dmpa_sc = models.CharField(max_length=4, choices=CHOICES, default="N/A")
    comments = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = (("quarter_year", "description", "facility_name", "date_of_interview"),)
        ordering = ['facility_name']
        verbose_name_plural = 'Family planning Qualitative'

    def __str__(self):
        return f"{self.facility_name} {self.description} ({self.date_of_interview})"


class StockCards(BaseBooleanModel):
    class Meta:
        verbose_name_plural = 'StockCards'
        unique_together = (("quarter_year", "description", "facility_name", "date_of_interview"),)


class UnitSupplied(BaseReportModel):
    class Meta:
        verbose_name_plural = 'Unit Supplied'
        unique_together = (("quarter_year", "description", "facility_name", "date_of_interview"),)


class BeginningBalance(BaseReportModel):
    class Meta:
        verbose_name_plural = 'Beginning Balance'
        unique_together = (("quarter_year", "description", "facility_name", "date_of_interview"),)


class PositiveAdjustments(BaseReportModel):
    class Meta:
        verbose_name_plural = 'Positive Adjustments'
        unique_together = (("quarter_year", "description", "facility_name", "date_of_interview"),)


class UnitIssued(BaseReportModel):
    class Meta:
        verbose_name_plural = 'Unit Issued'
        unique_together = (("quarter_year", "description", "facility_name", "date_of_interview"),)


class NegativeAdjustment(BaseReportModel):
    class Meta:
        verbose_name_plural = 'Negative Adjustment'
        unique_together = (("quarter_year", "description", "facility_name", "date_of_interview"),)


class ExpiredUnits(BaseReportModel):
    class Meta:
        verbose_name_plural = 'Expired Units'
        unique_together = (("quarter_year", "description", "facility_name", "date_of_interview"),)


class Expired(BaseBooleanModel):
    class Meta:
        verbose_name_plural = 'Expired'
        unique_together = (("quarter_year", "description", "facility_name", "date_of_interview"),)


class ExpiryTracking(BaseBooleanModel):
    class Meta:
        verbose_name_plural = 'ExpiryTracking'
        unique_together = (("quarter_year", "description", "facility_name", "date_of_interview"),)


class S11FormAvailability(BaseBooleanModel):
    class Meta:
        verbose_name_plural = 'S11 Form Availability'
        unique_together = (("quarter_year", "description", "facility_name", "date_of_interview"),)


class StockManagement(BaseReportModel):
    class Meta:
        verbose_name_plural = 'Stock Management'
        unique_together = (("quarter_year", "description", "facility_name", "date_of_interview"),)


class S11FormEndorsed(BaseReportModel):
    class Meta:
        verbose_name_plural = 'S11 Form Endorsed'
        unique_together = (("quarter_year", "description", "facility_name", "date_of_interview"),)


class WorkPlan(BaseModel):
    immediate_corrective_actions = models.TextField()
    action_plan = models.TextField()
    responsible_person = models.TextField()
    complete_date = models.DateField()
    follow_up_plan = models.TextField()
    progress = models.FloatField(null=True, blank=True)

    stock_cards = models.ForeignKey(StockCards, on_delete=models.CASCADE, blank=True, null=True)
    unit_supplied = models.ForeignKey(UnitSupplied, on_delete=models.CASCADE, blank=True, null=True)
    beginning_balance = models.ForeignKey(BeginningBalance, on_delete=models.CASCADE, blank=True, null=True)
    pharmacy_records = models.ForeignKey(PharmacyRecords, on_delete=models.CASCADE, blank=True, null=True)
    delivery_notes = models.ForeignKey(DeliveryNotes, on_delete=models.CASCADE, blank=True, null=True)
    positive_adjustments = models.ForeignKey(PositiveAdjustments, on_delete=models.CASCADE, blank=True, null=True)
    unit_issued = models.ForeignKey(UnitIssued, on_delete=models.CASCADE, blank=True, null=True)
    negative_adjustment = models.ForeignKey(NegativeAdjustment, on_delete=models.CASCADE, blank=True, null=True)
    expired_units = models.ForeignKey(ExpiredUnits, on_delete=models.CASCADE, blank=True, null=True)
    expired = models.ForeignKey(Expired, on_delete=models.CASCADE, blank=True, null=True)
    expiry_tracking = models.ForeignKey(ExpiryTracking, on_delete=models.CASCADE, blank=True, null=True)
    s11_form_availability = models.ForeignKey(S11FormAvailability, on_delete=models.CASCADE, blank=True, null=True)
    s11_form_endorsed = models.ForeignKey(S11FormEndorsed, on_delete=models.CASCADE, blank=True, null=True)
    stock_management = models.ForeignKey(StockManagement, on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        verbose_name_plural = "Work Plan"
        ordering = ['facility_name']

    def __str__(self):
        if self.pharmacy_records:
            return f"{self.facility_name}  ({self.pharmacy_records.quarter_year.quarter_year})"
        else:
            return f"{self.facility_name}  ({self.delivery_notes})"



class PharmacyAuditTeam(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=255)
    pharmacy_carder = models.CharField(max_length=255)
    pharmacy_organization = models.CharField(max_length=255)
    facility_name = models.ForeignKey(Facilities, on_delete=models.CASCADE, blank=True, null=True)
    quarter_year = models.ForeignKey(Period, on_delete=models.CASCADE, blank=True, null=True)
    module = models.CharField(max_length=255, blank=True, null=True, default="Pharmacy")
    created_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                   on_delete=models.CASCADE)
    modified_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                    on_delete=models.CASCADE, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.name) + "-" + str(self.quarter_year)

    def save(self, *args, **kwargs):
        # Check if there are already 30 records with the same facility_name and quarter_year combination but allow
        # updating existing records
        if PharmacyAuditTeam.objects.filter(facility_name=self.facility_name, quarter_year=self.quarter_year).exclude(
                pk=self.pk).count() >= 30:
            raise ValidationError('Only 30 audit team members are allowed per facility per quarter.')

        # Call the super method to save the record
        super().save(*args, **kwargs)
