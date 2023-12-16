import uuid

from crum import get_current_request, get_current_user
from django.core.validators import MaxValueValidator
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone

from apps.account.models import CustomUser
from apps.cqi.models import Facilities, Sub_counties, Counties
from apps.dqa.models import UpdateButtonSettings


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    created_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                   on_delete=models.CASCADE)
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


class Cd4TestingLabs(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    testing_lab_name = models.CharField(max_length=255, unique=True)
    mfl_code = models.IntegerField(unique=True, default=0)
    created_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                   on_delete=models.CASCADE)
    modified_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                    on_delete=models.CASCADE, related_name='+')
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "CD4 Testing Laboratories"
        ordering = ["testing_lab_name"]

    def __str__(self):
        return str(self.testing_lab_name)

    def save(self, *args, **kwargs):
        self.testing_lab_name = self.testing_lab_name.upper()
        super().save(*args, **kwargs)


# Create your models here.
class Cd4traker(models.Model):
    CHOICES = (
        ("Negative", "Negative"),
        ("Positive", "Positive"),
    )
    RECEIVED_CHOICES = (('Accepted', 'Accepted'), ('Rejected', 'Rejected'))
    REJECTION_CHOICES = sorted(
        (
            ("Improper Collection Technique", "Improper Collection Technique"),
            ("Requisition & Sample Mismatch", "Requisition & Sample Mismatch"),
            ("Missing Sample ( Physical Sample Missing)", "Missing Sample ( Physical Sample Missing)"),
            ("Insufficient Volume", "Insufficient Volume"),
            ("Clotted sample/ hemolysed sample", "Clotted Sample/ Hemolysed sample"),
            ("Sample Missing on Requisition Form", "Sample Missing On Requisition Form"),
            ("Others", "Others"),
        ),
        key=lambda x: x[0]
    )
    JUSTIFICATION_CHOICES = sorted(
        (
            ("Baseline (Tx_new)", "Baseline (Tx_new)"),
            ("Drug Resistance Test", "Drug Resistance Test"),
            ("Treatment Failure", "Treatment Failure"),
            ("Return to care > 3 months", "Return to care > 3 months"),
            ("On Fluconazole maintenance or Dapsone prophylaxis", "On Fluconazole maintenance or Dapsone prophylaxis"),
        ),
        key=lambda x: x[0]
    )
    AGE_UNIT_CHOICES = (("", "Select ..."), ("years", "Years"), ("months", "Months"), ("days", "Days"))

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    patient_unique_no = models.CharField(max_length=10)
    date_of_collection = models.DateTimeField()
    date_sample_received = models.DateTimeField()
    facility_name = models.ForeignKey(Facilities, on_delete=models.CASCADE, blank=True, null=True)
    sub_county = models.ForeignKey(Sub_counties, null=True, blank=True, on_delete=models.CASCADE)
    county = models.ForeignKey(Counties, null=True, blank=True, on_delete=models.CASCADE)
    age = models.PositiveIntegerField(validators=[MaxValueValidator(150)])
    age_unit = models.CharField(max_length=10, choices=AGE_UNIT_CHOICES,
                                default="years",  # Set "years" as the default value
                                )
    cd4_count_results = models.IntegerField(blank=True, null=True)
    cd4_percentage = models.IntegerField(blank=True, null=True)
    tb_lam_results = models.CharField(max_length=9, choices=CHOICES, blank=True, null=True)
    serum_crag_results = models.CharField(max_length=9, choices=CHOICES, blank=True, null=True)
    justification = models.CharField(max_length=50, choices=JUSTIFICATION_CHOICES, blank=True, null=True)
    sex = models.CharField(max_length=9, choices=(('M', 'M'), ('F', 'F')))
    received_status = models.CharField(max_length=9, choices=RECEIVED_CHOICES)
    reason_for_rejection = models.CharField(max_length=50, choices=REJECTION_CHOICES, blank=True, null=True)
    date_of_testing = models.DateTimeField(blank=True, null=True)
    reason_for_no_serum_crag = models.CharField(max_length=25, choices=(
        ('Reagents Stock outs', 'Reagents Stock outs'), ('Others', 'Others')),
                                                blank=True, null=True)
    testing_laboratory = models.ForeignKey(Cd4TestingLabs, on_delete=models.CASCADE, blank=True, null=True)

    created_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                   on_delete=models.CASCADE)
    modified_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                    on_delete=models.CASCADE, related_name='+')
    # date_dispatched = models.DateTimeField(auto_now_add=True)
    date_dispatched = models.DateTimeField(blank=True, null=True)
    report_type = models.CharField(max_length=25, blank=True, null=True, default="Current")
    date_updated = models.DateTimeField(auto_now=True)
    date_tb_lam_results_entered = models.DateTimeField(blank=True, null=True)
    date_serum_crag_results_entered = models.DateTimeField(blank=True, null=True)
    # Fields to track reagent usage
    cd4_reagent_used = models.BooleanField(default=False)
    tb_lam_reagent_used = models.BooleanField(default=False)
    serum_crag_reagent_used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        """
        Overrides the default save method to update created_by, modified_by, and timestamp fields.

        Args:
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Notes:
            - If the model instance has a primary key, it means it's being updated, and we don't modify the created_by field.
            - If the user is authenticated and not a new user (pk exists), assign the current user to the created_by and modified_by fields.
            - If self.tb_lam_results is set and date_tb_lam_results_entered is not set, set the current time as date_tb_lam_results_entered.
            - If self.serum_crag_results is set and date_serum_crag_results_entered is not set, set the current time as date_serum_crag_results_entered.
            - Call the parent class's save method to finalize the saving process.

        Returns:
            None
        """
        user = get_current_user()
        if user and not user.pk:
            user = None

        if not self.pk:
            # If the instance is being created, set the created_by field
            self.created_by = user
        self.modified_by = user

        if self.tb_lam_results and not self.date_tb_lam_results_entered:
            # If TB LAM result is set and date is not entered, set the date_tb_lam_results_entered to current time
            self.date_tb_lam_results_entered = timezone.now()
        if self.serum_crag_results and not self.date_serum_crag_results_entered:
            # If Serum Crag result is set and date is not entered, set the date_serum_crag_results_entered to current time
            self.date_serum_crag_results_entered = timezone.now()
        if self.pk or self.date_dispatched:
            try:
                # If the instance is being updated and date_dispatched already exists, do not update it
                obj = Cd4traker.objects.get(pk=self.pk)
                if self.report_type == "Current":
                    self.date_dispatched = obj.date_dispatched
                else:
                    self.date_dispatched = self.date_dispatched
            except Cd4traker.DoesNotExist:
                pass  # Handle the case where the object doesn't exist

        super().save(*args, **kwargs)  # Call parent class's save method

    class Meta:
        verbose_name_plural = "CD4 count tracker"
        ordering = ["-date_dispatched"]
        unique_together = (('patient_unique_no', 'facility_name', 'date_of_collection'),)
        permissions = [
            ("view_show_results", "Can view show results"),
            ("view_choose_testing_lab", "Can view choose testing lab"),
            ("view_add_cd4_count", "Can view add CD4 count"),
            ("view_add_retrospective_cd4_count", "Can view add retrospective CD4 count"),
            ("view_update_cd4_results", "Can view update CD4 results"),
        ]

    def __str__(self):
        return str(self.facility_name) + "_" + str(self.patient_unique_no) + "_" + str(self.date_of_collection)


class LabPulseUpdateButtonSettings(UpdateButtonSettings):
    def __str__(self):
        return str(self.hide_button_time)


class Commodities(BaseModel):
    type_of_reagent = models.CharField(max_length=25, choices=(
        ('CD4', 'CD4'), ('Serum CrAg', 'Serum CrAg'), ('TB LAM', 'TB LAM')))
    facility_name = models.ForeignKey(Facilities, on_delete=models.CASCADE, blank=True, null=True)
    sub_county = models.ForeignKey(Sub_counties, null=True, blank=True, on_delete=models.CASCADE)
    county = models.ForeignKey(Counties, null=True, blank=True, on_delete=models.CASCADE)
    number_received = models.IntegerField(blank=True, null=True)
    date_commodity_received = models.DateTimeField()
    expiry_date = models.DateTimeField(blank=True, null=True)
    received_from = models.CharField(max_length=25, choices=(
        ('KEMSA', 'KEMSA'), ('Another Facility', 'Another Facility')))
    negative_adjustment = models.IntegerField(blank=True, null=True)
    positive_adjustment = models.IntegerField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "Commodities"
        ordering = ['facility_name', 'date_created']

    def __str__(self):
        return str(self.facility_name) + "-" + str(self.type_of_reagent) + "-" + str(self.date_created)


class ReagentStock(BaseModel):
    REAGENT_CHOICES = (
        ('CD4', 'CD4'),
        ('TB LAM', 'TB LAM'),
        ('Serum CrAg', 'Serum CrAg')
    )

    reagent_type = models.CharField(max_length=25, choices=REAGENT_CHOICES)
    received_from = models.CharField(max_length=25, choices=(
        ('KEMSA', 'KEMSA'), ('Another Facility', 'Another Facility')))
    beginning_balance = models.IntegerField(default=0)
    quantity_received = models.IntegerField(default=0)
    positive_adjustments = models.IntegerField(default=0)
    quantity_used = models.IntegerField(default=0, blank=True)
    negative_adjustment = models.IntegerField(default=0)
    expiry_date = models.DateTimeField(blank=True, null=True)
    quantity_expired = models.IntegerField(default=0)
    remaining_quantity = models.IntegerField(default=0)
    facility_name = models.ForeignKey(Facilities, on_delete=models.CASCADE)
    date_commodity_received = models.DateTimeField(default=timezone.now)

    def calculate_remaining_quantity(self):
        remaining_quantity = (self.beginning_balance + self.quantity_received + self.positive_adjustments - \
                              self.quantity_used - self.negative_adjustment - self.quantity_expired)
        return remaining_quantity

    def save(self, *args, **kwargs):
        self.remaining_quantity = self.calculate_remaining_quantity()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name_plural = "Reagent stocks"
        ordering = ['facility_name', 'date_created', 'remaining_quantity']

    def __str__(self):
        return str(self.facility_name) + " - " + str(self.reagent_type) + \
            " Remaining quantity (" + str(self.remaining_quantity) + ")" + '-' + str(self.date_created)


class EnableDisableCommodities(BaseModel):
    use_commodities = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'Enable Disable Commodities'

    def __str__(self):
        return str(self.use_commodities)


class BiochemistryResult(BaseModel):
    sample_id = models.CharField(max_length=50)
    patient_id = models.CharField(max_length=10)
    test = models.CharField(max_length=100)
    full_name = models.CharField(max_length=255)
    result = models.FloatField()
    low_limit = models.FloatField()
    high_limit = models.FloatField()
    units = models.CharField(max_length=20)
    reference_class = models.CharField(max_length=100)
    collection_date = models.DateField()
    result_time = models.DateTimeField()
    mfl_code = models.IntegerField()
    results_interpretation = models.CharField(max_length=255)
    number_of_samples = models.IntegerField()
    performed_by = models.CharField(max_length=100,blank=True,null=True)

    def __str__(self):
        return f"{self.mfl_code} - {self.date_created} - {self.test} - {self.patient_id}"

    class Meta:
        ordering=['patient_id','collection_date']
        verbose_name = "Biochemistry Result"
        verbose_name_plural = "Biochemistry Results"
        unique_together=(('sample_id', 'patient_id','test','collection_date','result'),)

class DrtPdfFile(BaseModel):
    result = models.FileField(upload_to='drt_files')
    class Meta:
        verbose_name_plural = "DRT PDF Results"

    def __str__(self):
        # Fetch the first related result
        first_result = self.drt_results.order_by('patient_id','date_created').first()
        if first_result:
            return f"{first_result.patient_id} - {first_result.facility_name} - {first_result.collection_date}"
        # Return a default string if no related result exists
        return f"No related result for {self.id}"


class DrtResults(BaseModel):
    patient_id = models.BigIntegerField(validators=[MaxValueValidator(9999999999)])
    result = models.ForeignKey(DrtPdfFile, on_delete=models.CASCADE,related_name="drt_results")
    collection_date = models.DateTimeField()
    facility_name = models.ForeignKey(Facilities, on_delete=models.CASCADE, blank=True, null=True)
    sub_county = models.ForeignKey(Sub_counties, null=True, blank=True, on_delete=models.CASCADE)
    county = models.ForeignKey(Counties, null=True, blank=True, on_delete=models.CASCADE)
    drug = models.CharField(max_length=50)
    drug_abbreviation = models.CharField(max_length=10)
    resistance_level = models.CharField(max_length=250)
    sequence_summary = models.CharField(max_length=10)
    haart_class = models.CharField(max_length=50)
    date_received = models.DateTimeField()
    date_reported = models.DateTimeField()
    date_test_performed = models.DateTimeField()
    test_perfomed_by = models.CharField(max_length=50)
    age = models.PositiveIntegerField(validators=[MaxValueValidator(150)],null=True, blank=True,)
    age_unit = models.CharField(max_length=20,null=True, blank=True,)
    sex = models.CharField(max_length=10,null=True, blank=True,)
    tat_days = models.IntegerField(blank=True, null=True)

    class Meta:
        ordering = ['patient_id','date_created']
        unique_together=['patient_id','collection_date','drug']
        verbose_name_plural="DRT Results"

    def save(self, *args, **kwargs):
        # Make sure collection_date is timezone-aware
        if not self.collection_date.tzinfo:
            self.collection_date = timezone.make_aware(self.collection_date)

        # Calculate TAT and save it
        if self.collection_date:
            tat = (timezone.now() - self.collection_date).days
            self.tat_days = tat
        # Set date_modified
        self.date_modified = timezone.now()
        # Save the instance
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.patient_id)+ " - "+ str(self.facility_name)+ " - "+ str(self.date_created)