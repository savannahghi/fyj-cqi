import uuid

from crum import get_current_user
from django.db import models

from apps.account.models import CustomUser
from apps.cqi.models import Facilities


class Cd4TestingLabs(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    testing_lab_name=models.CharField(max_length=255)

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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    patient_unique_no = models.CharField(max_length=10)
    date_of_collection = models.DateTimeField()
    facility_name = models.ForeignKey(Facilities, on_delete=models.CASCADE, blank=True, null=True)
    age = models.IntegerField()
    cd4_count_results = models.IntegerField(blank=True, null=True)
    serum_crag_results = models.CharField(max_length=9,choices=CHOICES, blank=True, null=True)
    sex = models.CharField(max_length=9,choices=(('M','M'),('F','F')), blank=True, null=True)
    date_of_testing = models.DateTimeField()
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

    def __str__(self):
        return str(self.facility_name) +" "+ str(self.patient_unique_no) +""+ str(self.date_of_collection)
