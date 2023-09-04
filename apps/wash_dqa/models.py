import uuid

from crum import get_current_user
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models

from apps.account.models import CustomUser


# Create your models here.
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


class Counties(BaseModel):
    name = models.CharField(max_length=250, unique=True)

    class Meta:
        verbose_name_plural = 'counties'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Ensure County name is in title case"""
        self.name = self.name.upper().strip()
        super().save(*args, **kwargs)


class SubCounties(BaseModel):
    name = models.CharField(max_length=250, unique=True)
    county = models.ForeignKey(Counties, on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = 'sub-counties'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Ensure County name is in title case"""
        self.name = self.name.title()
        super().save(*args, **kwargs)


class Ward(BaseModel):
    name = models.CharField(max_length=250, unique=True)
    ward_code = models.CharField(max_length=250, unique=True)
    sub_county = models.ForeignKey(SubCounties, on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = 'wards'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Ensure County name is in title case"""
        self.name = self.name.upper()
        super().save(*args, **kwargs)


class TableNames(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    model_name = models.CharField(max_length=25, blank=True, null=True)


class Period(BaseModel):
    YEAR_CHOICES = [(str(x), str(x)) for x in range(2021, 2099)]
    year = models.CharField(choices=YEAR_CHOICES, max_length=4)
    QUARTER_CHOICES = [
        ('Qtr1', 'Q1'),
        ('Qtr2', 'Q2'),
        ('Qtr3', 'Q3'),
        ('Qtr4', 'Q4'),
    ]
    quarter = models.CharField(choices=QUARTER_CHOICES, max_length=4)
    quarter_year = models.CharField(max_length=10, blank=True)

    class Meta:
        verbose_name_plural = "Periods"
        ordering = ['quarter_year']

    def save(self, *args, **kwargs):
        self.quarter_year = f"{self.quarter}-{self.year[2:]}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quarter} {self.year}"


class Framework(BaseModel):
    description = models.TextField()
    sub_county_name = models.ForeignKey(SubCounties, on_delete=models.CASCADE, blank=True, null=True)
    ward_name = models.ForeignKey(Ward, on_delete=models.CASCADE, blank=True, null=True)
    quarter_year = models.ForeignKey(Period, on_delete=models.CASCADE, blank=True, null=True)
    auditor_note = models.CharField(max_length=250, blank=True, null=True)
    # model_name = models.ForeignKey(TableNames, on_delete=models.CASCADE, blank=True, null=True)
    dqa_date = models.DateField(blank=True, null=True)


    def __str__(self):
        return f"{self.ward_name} - {self.quarter_year}"

    class Meta:
        abstract = True

class OptionsDqa(Framework):
    DROPDOWN_CHOICES = [("Fully meets all requirements", "Fully meets all requirements"),
                        ("Almost meets all requirements", "Almost meets all requirements"),
                        ("Partially meets all requirements", "Partially meets all requirements"),
                        ("Approaches basic requirements", "Approaches basic requirements"),
                        ("Does not meet requirements", "Does not meet requirements"),
                        ("N/A", "N/A")]
    verification_means = models.TextField()
    staff_involved = models.TextField()
    dropdown_option = models.CharField(max_length=50, choices=DROPDOWN_CHOICES, blank=True, null=True)
    calculations = models.FloatField(null=True, blank=True)
    class Meta:
        abstract=True

class Documentation(OptionsDqa):
    class Meta:
        verbose_name_plural = 'Documentation'
        unique_together = (("quarter_year", "description", "ward_name"),)
        ordering = ['ward_name']


class DataQualitySystems(OptionsDqa):
    class Meta:
        verbose_name_plural = 'Data Quality Systems'
        unique_together = (("quarter_year", "description", "ward_name"),)
        ordering = ['ward_name']


class DataCollectionReportingManagement(OptionsDqa):
    class Meta:
        verbose_name_plural = 'Data Collection, Reporting and Management'
        unique_together = (("quarter_year", "description", "ward_name"),)
        ordering = ['ward_name']

class DataQualityAssessment(Framework):
    DROPDOWN_CHOICES = [("Yes", "Yes"), ("No", "No"), ("N/A", "N/A")]

    number_trained = models.CharField(max_length=50, choices=DROPDOWN_CHOICES, blank=True, null=True)
    number_access_basic_water = models.CharField(max_length=50, choices=DROPDOWN_CHOICES, blank=True, null=True)
    number_access_safe_water = models.CharField(max_length=50, choices=DROPDOWN_CHOICES, blank=True, null=True)
    number_community_open_defecation = models.CharField(max_length=50, choices=DROPDOWN_CHOICES, blank=True, null=True)
    number_access_basic_sanitation = models.CharField(max_length=50, choices=DROPDOWN_CHOICES, blank=True, null=True)
    number_access_safe_sanitation = models.CharField(max_length=50, choices=DROPDOWN_CHOICES, blank=True, null=True)
    number_access_basic_sanitation_institutions = models.CharField(max_length=50, choices=DROPDOWN_CHOICES, blank=True,
                                                                   null=True)

    number_trained_numeric = models.PositiveIntegerField(blank=True, null=True)
    number_access_basic_water_numeric = models.PositiveIntegerField(blank=True, null=True)
    number_access_safe_water_numeric = models.PositiveIntegerField(blank=True, null=True)
    number_community_open_defecation_numeric = models.PositiveIntegerField(blank=True, null=True)
    number_access_basic_sanitation_numeric = models.PositiveIntegerField(blank=True, null=True)
    number_access_safe_sanitation_numeric = models.PositiveIntegerField(blank=True, null=True)
    number_access_basic_sanitation_institutions_numeric = models.PositiveIntegerField(blank=True, null=True)

    def save(self, *args, **kwargs):
        # Mapping of string choices to numeric values
        choices_mapping = {"N/A": 0, "No": 1, "Yes": 2}

        # Loop through fields in the model
        for field_name in [field for field in self._meta.fields if isinstance(field, models.CharField)]:
            # Get the value of the CharField
            field_value = getattr(self, field_name.attname)

            # Create the name of the corresponding numeric field
            numeric_field_name = f"{field_name.attname}_numeric"

            # Check if the field_value is one of the mapped choices
            if field_value in choices_mapping:
                # Set the corresponding numeric value in the numeric field
                setattr(self, numeric_field_name, choices_mapping[field_value])
            else:
                # Set the numeric field to None if the value is not in the mapping
                setattr(self, numeric_field_name, None)

        # Call the parent class's save method to save the instance
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ward_name} - {self.quarter_year} - {self.description}"

    class Meta:
        verbose_name_plural = 'Data Quality Assessment'
        unique_together = (("quarter_year", "description", "ward_name"),)
        ordering = ['ward_name','date_created']

class DataConcordance(BaseModel):
    # TODO: ALLOW USERS TO ADD INDICATORS
    INDICATOR_CHOICES = [
        ('', 'Select indicator'),

        ('HL.8.1-1: Number of people gaining access to basic drinking water services as a result of USG assistance',
         'HL.8.1-1: Number of people gaining access to basic drinking water services as a result of USG assistance'),
        ('HL.8.1-2: Number of people gaining access to a safely managed drinking water service',
         'HL.8.1-2: Number of people gaining access to a safely managed drinking water service'),
        ('HL.8.2-1: Number of communities certified as open defecation free (ODF) as a result of USG assistance',
         'HL.8.2-1: Number of communities certified as open defecation free (ODF) as a result of USG assistance'),
        ('HL.8.2-2: Number of people gaining access to a basic sanitation service as a result of USG assistance',
         'HL.8.2-2: Number of people gaining access to a basic sanitation service as a result of USG assistance'),
        (
        'HL.8.2-3: Number of people gaining access to safely managed sanitation services as a result of USG assistance.',
        'HL.8.2-3: Number of people gaining access to safely managed sanitation services as a result of USG assistance.'),
        (
        'HL.8.2-4: Number of basic sanitation facilities provided in institutional settings as a result of USG assistance',
        'HL.8.2-4: Number of basic sanitation facilities provided in institutional settings as a result of USG assistance'),
        ('HL.CUST MCH 12.0: Number of individuals trained to implement improved sanitation methods',
         'HL.CUST MCH 12.0: Number of individuals trained to implement improved sanitation methods'),
    ]
    indicator = models.CharField(choices=INDICATOR_CHOICES, max_length=250)
    quarter_year = models.ForeignKey(Period, on_delete=models.CASCADE)
    ward_name = models.ForeignKey(Ward, on_delete=models.CASCADE, blank=True, null=True)
    field_1 = models.CharField(validators=[RegexValidator(r'^\d+$')], max_length=100)
    field_2 = models.CharField(validators=[RegexValidator(r'^\d+$')], max_length=100)
    field_3 = models.CharField(validators=[RegexValidator(r'^\d+$')], max_length=100)
    total_source = models.CharField(validators=[RegexValidator(r'^\d+$')], max_length=100, blank=True)
    field_5 = models.CharField(validators=[RegexValidator(r'^\d+$')], max_length=100)
    field_6 = models.CharField(validators=[RegexValidator(r'^\d+$')], max_length=100)
    field_7 = models.CharField(validators=[RegexValidator(r'^\d+$')], max_length=100)
    total_monthly_report = models.CharField(validators=[RegexValidator(r'^\d+$')], max_length=100, blank=True)

    class Meta:
        unique_together = (("quarter_year", "indicator", "ward_name"),)

    def __str__(self):
        return f"{self.ward_name} {self.indicator} ({self.quarter_year})"

    def save(self, *args, **kwargs):
        self.total_source = int(self.field_1) + int(self.field_2) + int(self.field_3)
        self.total_monthly_report = int(self.field_5) + int(self.field_6) + int(self.field_7)
        super().save(*args, **kwargs)


class JphesPerformance(BaseModel):
    ward_code = models.CharField(max_length=100)
    ward_name = models.CharField(max_length=100)
    month = models.CharField(max_length=100)
    number_trained = models.PositiveIntegerField(blank=True, null=True)
    number_access_basic_water = models.PositiveIntegerField(blank=True, null=True)
    number_access_safe_water = models.PositiveIntegerField(blank=True, null=True)
    number_community_open_defecation = models.PositiveIntegerField(blank=True, null=True)
    number_access_basic_sanitation = models.PositiveIntegerField(blank=True, null=True)
    number_access_safe_sanitation= models.PositiveIntegerField(blank=True, null=True)
    number_access_basic_sanitation_institutions = models.PositiveIntegerField(blank=True, null=True)
    quarter_year = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        unique_together = (('ward_code', 'month'),)
        ordering=['ward_name']

    def __str__(self):
        return f"{self.ward_name} - {self.month}"

    def save(self, *args, **kwargs):
        # Get the month and year string from the `month` field
        month_str = self.month
        year_str = month_str.split()[-1]

        # Convert the year string to an integer
        year = int(year_str)

        # Get the month string
        month = month_str.split()[0]
        quarter = None

        # Determine the quarter based on the month while handling both full month names and abbreviated names
        if month in ["October", "November", "December", "Oct", "Nov", "Dec"]:
            # If the month is October, November, or December, the quarter is Qtr1
            quarter = "Qtr1"
        elif month in ["January", "February", "March", "Jan", "Feb", "Mar"]:
            # If the month is January, February, or March, the quarter is Qtr2
            quarter = "Qtr2"
        elif month in ["April", "May", "June", "Apr", "Jun"]:
            # If the month is April, May, or June, the quarter is Qtr3
            quarter = "Qtr3"
        elif month in ["July", "August", "September", "Jul", "Aug", "Sep"]:
            # If the month is July, August, or September, the quarter is Qtr4
            quarter = "Qtr4"

        # Increment the year by 1 if the quarter is Qtr1
        if quarter == "Qtr1":
            year += 1

        # Construct the quarter-year string
        self.quarter_year = quarter + "-" + str(year)[-2:]

        # Call the parent save method to save the object
        super().save(*args, **kwargs)


class WashAuditTeam(BaseModel):
    # list of carders
    carders = ["County WASH M/E", "County WASH Lead", "FYJ WASH M/E", "WASH Focal Person","WASH Mentor",
               "WASH Coordinator","Program Officer"]

    # create the choices
    CARDER_CHOICES = [(carder, carder) for carder in sorted(carders)]
    organizations = ["MOH","FYJ"]

    # create the choices
    ORGANIZATION_CHOICES = [(organization, organization) for organization in sorted(organizations)]
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    carder = models.CharField(max_length=255,choices=CARDER_CHOICES)
    organization = models.CharField(max_length=255,choices=ORGANIZATION_CHOICES)
    ward_name = models.ForeignKey(Ward, on_delete=models.CASCADE, blank=True, null=True)
    quarter_year = models.ForeignKey(Period, on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        verbose_name_plural="WASH Audit Team"
        ordering=['first_name']

    def __str__(self):
        return str(self.first_name) + " " +str(self.last_name)+ " - "+ str(self.quarter_year)

    def save(self, *args, **kwargs):
        # Check if there are already 30 records with the same facility_name and quarter_year combination but allow
        # updating existing records
        if WashAuditTeam.objects.filter(ward_name=self.ward_name, quarter_year=self.quarter_year).exclude(
                pk=self.pk).count() >= 30:
            raise ValidationError('Only 30 audit team members are allowed per ward per quarter.')
        self.first_name = self.first_name.title()
        self.last_name = self.last_name.title()
        # Call the super method to save the record
        super().save(*args, **kwargs)

class WashDQAWorkPlan(BaseModel):
    # list of areas
    areas = ["Documentation","Data Quality Assessment", "Data Quality Systems",
             "Data Collection, Reporting and Management","Data Verification"]

    # create the choices
    AREAS_CHOICES = [(area, area) for area in sorted(areas)]
    dqa_date = models.DateField(blank=True, null=True)
    ward_name = models.ForeignKey(Ward, on_delete=models.CASCADE, blank=True, null=True)
    quarter_year = models.ForeignKey(Period, on_delete=models.CASCADE, blank=True, null=True)
    individuals_conducting_dqa = models.TextField()
    program_areas_reviewed = models.CharField(choices=AREAS_CHOICES, max_length=255)
    strengths_identified = models.TextField()
    gaps_identified = models.TextField()
    recommendation = models.TextField()
    percent_completed = models.IntegerField()
    individuals_responsible = models.TextField()
    due_complete_by = models.DateField()
    comments = models.TextField(blank=True)
    progress = models.FloatField(null=True, blank=True)
    timeframe = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.ward_name} - {self.quarter_year}"

    class Meta:
        ordering = ['ward_name']
        verbose_name_plural = "WASH DQA Work-plan"


