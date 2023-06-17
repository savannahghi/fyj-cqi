import uuid

from crum import get_current_user
from django.core.validators import MaxValueValidator
from django.db import models

from apps.account.models import CustomUser
from apps.cqi.models import Facilities, Sub_counties, Counties


class Cd4TestingLabs(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    testing_lab_name=models.CharField(max_length=255,unique=True)

    class Meta:
        verbose_name_plural="CD4 Testing Laboratories"

    def __str__(self):
        return str(self.testing_lab_name)


# Create your models here.
class Cd4traker(models.Model):
    CHOICES=(
        ("Negative","Negative"),
        ("Positive","Positive"),
    )
    REJECTION_CHOICES = sorted(
        (
            ("Improper Collection Technique", "Improper Collection Technique"),
            ("Requisition & Sample Mismatch", "Requisition & Sample Mismatch"),
            ("Missing Sample ( Physical Sample Missing)", "Missing Sample ( Physical Sample Missing)"),
            ("Insufficient Volume", "Insufficient Volume"),
            ("Clotted sample/ hemolysed sample", "Clotted sample/ hemolysed sample"),
            ("Sample Missing on Requisition Form", "Sample Missing on Requisition Form"),
            ("Others", "Others"),
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
    serum_crag_results = models.CharField(max_length=9,choices=CHOICES, blank=True, null=True)
    sex = models.CharField(max_length=9,choices=(('M','M'),('F','F')))
    received_status = models.CharField(max_length=9,choices=(('Accepted','Accepted'),('Rejected','Rejected')))
    reason_for_rejection = models.CharField(max_length=50,choices=REJECTION_CHOICES, blank=True, null=True)
    date_of_testing = models.DateTimeField(blank=True, null=True)
    reason_for_no_serum_crag = models.CharField(max_length=25,choices=(('Reagents Stock outs','Reagents Stock outs'),('Others','Others')),
                                blank=True, null=True)
    testing_laboratory = models.ForeignKey(Cd4TestingLabs, on_delete=models.CASCADE, blank=True, null=True)

    created_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                   on_delete=models.CASCADE)
    modified_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                    on_delete=models.CASCADE, related_name='+')
    date_dispatched = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural="CD4 count tracker"
        ordering=["-date_dispatched"]
        unique_together=(('patient_unique_no','facility_name','date_of_collection'),)

    def __str__(self):
        return str(self.facility_name) +" "+ str(self.patient_unique_no) +""+ str(self.date_of_collection)
