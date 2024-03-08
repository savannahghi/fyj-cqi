from datetime import datetime

from django.db import models

# Create your models here.

from django.db import models

from apps.labpulse.models import BaseModel


class FYJHealthFacility(models.Model):
    mfl_code = models.CharField(max_length=250)
    county = models.CharField(max_length=250)
    health_subcounty = models.CharField(max_length=250)
    subcounty = models.CharField(max_length=250)
    ward = models.CharField(max_length=250)
    facility = models.CharField(max_length=250)
    datim_mfl = models.CharField(max_length=250)
    m_and_e_mentor = models.CharField(max_length=250)
    m_and_e_assistant = models.CharField(max_length=250)
    care_and_treatment = models.CharField(max_length=250)
    hts = models.CharField(max_length=250)
    vmmc = models.CharField(max_length=250)
    key_pop = models.CharField(max_length=250)
    hub = models.CharField(max_length=250)
    facility_type = models.CharField(max_length=250)
    category = models.CharField(max_length=250)
    emr = models.CharField(max_length=250)

    class Meta:
        unique_together = (('mfl_code', 'facility'),)
        ordering=["facility"]

    def __str__(self):
        return str(self.facility) + "-" + str(self.mfl_code)

class RTKData(BaseModel):
    month = models.CharField(max_length=10)
    county = models.CharField(max_length=50)
    sub_county = models.CharField(max_length=50)
    mfl_code = models.IntegerField()
    facility_name = models.CharField(max_length=250)
    commodity_name = models.CharField(max_length=50)
    beginning_balance = models.IntegerField()
    quantity_received = models.IntegerField()
    quantity_used = models.IntegerField()
    quantity_requested = models.IntegerField()
    tests_done = models.IntegerField()
    losses = models.IntegerField()
    positive_adjustments = models.IntegerField()
    negative_adjustments = models.IntegerField()
    ending_balance = models.IntegerField()
    days_out_of_stock = models.IntegerField()
    quantity_expiring_in_6_months = models.IntegerField()
    month_column = models.DateTimeField(default=datetime.now)

    class Meta:
        unique_together = (('mfl_code', 'month','commodity_name'),)
        ordering=["facility_name","commodity_name"]

    def __str__(self):
        return f"{self.facility_name} - {self.month} - {self.commodity_name}"

