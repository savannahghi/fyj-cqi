from django.db import models

# Create your models here.

from django.db import models


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

    def __str__(self):
        return str(self.facility) + "-" + str(self.mfl_code)

