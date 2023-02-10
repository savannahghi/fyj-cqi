from django.core.validators import RegexValidator
from django.db import models


#
# class Quarters(models.Model):
#     QUARTER_CHOICES = [
#         ('Q1', 'Q1'),
#         ('Q2', 'Q2'),
#         ('Q3', 'Q3'),
#         ('Q4', 'Q4'),
#     ]
#     quarter = models.CharField(choices=QUARTER_CHOICES, max_length=2)
#
#     def __str__(self):
#         return self.quarter
from account.models import NewUser
from project.models import Facilities


class Period(models.Model):
    YEAR_CHOICES = [(str(x), str(x)) for x in range(2021, 2099)]
    year = models.CharField(choices=YEAR_CHOICES, max_length=4)
    QUARTER_CHOICES = [
        ('Qtr1', 'Q1'),
        ('Qtr2', 'Q2'),
        ('Qtr3', 'Q3'),
        ('Qtr4', 'Q4'),
    ]
    quarter = models.CharField(choices=QUARTER_CHOICES, max_length=4)
    quarter_year = models.CharField(max_length=5, blank=True)

    class Meta:
        verbose_name_plural = "Periods"
        ordering = ['quarter_year']

    def save(self, *args, **kwargs):
        self.quarter_year = f"{self.quarter}-{self.year[2:]}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quarter} {self.year}"


#
#
class Indicators(models.Model):
    INDICATOR_CHOICES = [
        ('PrEP_New', 'PrEP_New'),
        ('Starting_TPT', 'Starting TPT'),
        ('GBV_Sexual violence', 'GBV_Sexual violence'),
        ('GBV_Emotional and /Physical Violence', 'GBV_Emotional and /Physical Violence'),
        ('Cervical Cancer Screening (Women on ART)', 'Cervical Cancer Screening (Women on ART)'),
        ('Total tested ', 'Total tested '),
        ('Number tested Positive aged <15 years', 'Number tested Positive aged <15 years'),
        ('Number tested Positive aged 15+ years', 'Number tested Positive aged 15+ years'),
        ('Number tested Positive _Total', 'Number tested Positive _Total'),
        ('Known Positive at 1st ANC', 'Known Positive at 1st ANC'),
        ('Positive Results_ANC', 'Positive Results_ANC'),
        ('On HAART at 1st ANC', 'On HAART at 1st ANC'),
        ('Start HAART ANC', 'Start HAART ANC'),
        ('Infant ARV Prophyl_ANC', 'Infant ARV Prophyl_ANC'),
        ('Positive Results_L&D', 'Positive Results_L&D'),
        ('Start HAART_L&D', 'Start HAART_L&D'),
        ('Infant ARV Prophyl_L&D', 'Infant ARV Prophyl_L&D'),
        ('Positive Results_PNC<=6 weeks', 'Positive Results_PNC<=6 weeks'),
        ('Start HAART_PNC<= 6 weeks', 'Start HAART_PNC<= 6 weeks'),
        ('Infant ARV Prophyl_PNC<= 6 weeks', 'Infant ARV Prophyl_PNC<= 6 weeks'),
        ('Total Positive (PMTCT)', 'Total Positive (PMTCT)'),
        ('Maternal HAART Total ', 'Maternal HAART Total '),
        ('Total Infant prophylaxis', 'Total Infant prophylaxis'),
        ('Under 15yrs Starting on ART', 'Under 15yrs Starting on ART'),
        ('Above 15yrs Starting on ART ', 'Above 15yrs Starting on ART '),
        ('Number of adults and children starting ART', 'Number of adults and children starting ART'),
        ('New & Relapse TB_Cases', 'New & Relapse TB_Cases'),
        ('Currently on ART <15Years', 'Currently on ART <15Years'),
        ('Currently on ART 15+ years', 'Currently on ART 15+ years'),
        ('Number of adults and children Currently on ART', 'Number of adults and children Currently on ART'),
    ]
    indicator = models.CharField(choices=INDICATOR_CHOICES, max_length=250)

    def __str__(self):
        return self.indicator


class DataVerification(models.Model):
    quarter_year = models.ForeignKey(Period, on_delete=models.CASCADE)
    # TODO: MODEL SHOULD ALLOW USER TO SAVE ONE INDICATOR PER QUARTER
    indicator = models.ForeignKey(Indicators, on_delete=models.CASCADE)
    facility_name = models.ForeignKey(Facilities, on_delete=models.CASCADE)
    field_1 = models.CharField(validators=[RegexValidator(r'^\d+$')], max_length=100)
    field_2 = models.CharField(validators=[RegexValidator(r'^\d+$')], max_length=100)
    field_3 = models.CharField(validators=[RegexValidator(r'^\d+$')], max_length=100)
    total_source = models.CharField(validators=[RegexValidator(r'^\d+$')], max_length=100,blank=True)
    field_5 = models.CharField(validators=[RegexValidator(r'^\d+$')], max_length=100)
    field_6 = models.CharField(validators=[RegexValidator(r'^\d+$')], max_length=100)
    field_7 = models.CharField(validators=[RegexValidator(r'^\d+$')], max_length=100)
    total_731moh = models.CharField(validators=[RegexValidator(r'^\d+$')], max_length=100,blank=True)
    field_9 = models.CharField(validators=[RegexValidator(r'^\d+$')], max_length=100)
    field_10 = models.CharField(validators=[RegexValidator(r'^\d+$')], max_length=100)
    field_11 = models.CharField(validators=[RegexValidator(r'^\d+$')], max_length=100)
    total_khis = models.CharField(validators=[RegexValidator(r'^\d+$')], max_length=100,blank=True)
    # TODO: 13TH FIELD SHOULD VERIFY DATA FROM FYJ DATIM PERFORMNACE. Create a model for this
    field_13 = models.CharField(validators=[RegexValidator(r'^\d+$')], max_length=100)

    created_by = models.ForeignKey(NewUser, on_delete=models.CASCADE)

    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.indicator} ({self.quarter_year})"

    def save(self, *args, **kwargs):
        self.total_source = int(self.field_1) + int(self.field_2) + int(self.field_3)
        self.total_731moh = int(self.field_5) + int(self.field_6) + int(self.field_7)
        self.total_khis = int(self.field_9) + int(self.field_10) + int(self.field_11)
        super().save(*args, **kwargs)


