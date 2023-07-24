import uuid

from crum import get_current_user
from django.core.validators import MaxValueValidator
from django.db import models
from django.utils import timezone

from apps.account.models import CustomUser
from apps.cqi.models import Facilities, Sub_counties, Counties
from apps.dqa.models import UpdateButtonSettings


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
            ("Treatment Failure", "Treatment Failure"),
            ("Return to care > 3 months", "Return to care > 3 months"),
        ),
        key=lambda x: x[0]
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    patient_unique_no = models.CharField(max_length=10)
    date_of_collection = models.DateTimeField()
    date_sample_received = models.DateTimeField()
    facility_name = models.ForeignKey(Facilities, on_delete=models.CASCADE, blank=True, null=True)
    sub_county = models.ForeignKey(Sub_counties, null=True, blank=True, on_delete=models.CASCADE)
    county = models.ForeignKey(Counties, null=True, blank=True, on_delete=models.CASCADE)
    age = models.IntegerField(validators=[MaxValueValidator(150)])
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
    report_type = models.CharField(max_length=25,blank=True, null=True,default="Current")
    date_updated = models.DateTimeField(auto_now=True)
    date_tb_lam_results_entered = models.DateTimeField(blank=True, null=True)
    date_serum_crag_results_entered = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.tb_lam_results and not self.date_tb_lam_results_entered:
            self.date_tb_lam_results_entered = timezone.now()
        if self.serum_crag_results and not self.date_serum_crag_results_entered:
            self.date_serum_crag_results_entered = timezone.now()
        super().save(*args, **kwargs)

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
        return str(self.facility_name) + " " + str(self.patient_unique_no) + "" + str(self.date_of_collection)


class LabPulseUpdateButtonSettings(UpdateButtonSettings):
    def __str__(self):
        return str(self.hide_button_time)