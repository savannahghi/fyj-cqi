import uuid
from datetime import date

from crum import get_current_user
from django.core.exceptions import ValidationError
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
from apps.account.models import CustomUser
from apps.cqi.models import Counties, Facilities, Sub_counties


class Period(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
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


class Indicators(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
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
        ('TX_ML', 'TX_ML'),
        ('RTT', 'RTT'),
        ('TB_PREV_N', 'TB_PREV_N'),
    ]
    indicator = models.CharField(choices=INDICATOR_CHOICES, max_length=250)

    def __str__(self):
        return self.indicator


class DataVerification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    # TODO: ALLOW USERS TO ADD INDICATORS
    INDICATOR_CHOICES = [
        ('', 'Select indicator'),
        ('PrEP_New', 'PrEP_New'),
        ('Starting_TPT', 'Starting TPT'),
        # ('Starting_TPTs', 'Starting TPTs'),
        ('GBV_Sexual violence', 'GBV_Sexual violence'),
        ('GBV_Emotional and /Physical Violence', 'GBV_Emotional and /Physical Violence'),
        ('Cervical Cancer Screening (Women on ART)', 'Cervical Cancer Screening (Women on ART)'),
        ('Total tested ', 'Total tested '),
        ('Number tested Positive aged <15 years', 'Number tested Positive aged <15 years'),
        ('Number tested Positive aged 15+ years', 'Number tested Positive aged 15+ years'),
        # ('Number tested Positive _Total', 'Number tested Positive _Total'),
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
        # ('Total Positive (PMTCT)', 'Total Positive (PMTCT)'),
        # ('Maternal HAART Total ', 'Maternal HAART Total '),
        # ('Total Infant prophylaxis', 'Total Infant prophylaxis'),
        ('Under 15yrs Starting on ART', 'Under 15yrs Starting on ART'),
        ('Above 15yrs Starting on ART ', 'Above 15yrs Starting on ART '),
        # ('Number of adults and children starting ART', 'Number of adults and children starting ART'),
        ('New & Relapse TB_Cases', 'New & Relapse TB_Cases'),
        ('Currently on ART <15Years', 'Currently on ART <15Years'),
        ('Currently on ART 15+ years', 'Currently on ART 15+ years'),
        ('TX_ML', 'TX_ML'),
        ('RTT', 'RTT'),
        ('TB_PREV_N', 'TB_PREV_N'),
        # ('Number of adults and children Currently on ART', 'Number of adults and children Currently on ART'),
    ]
    indicator = models.CharField(choices=INDICATOR_CHOICES, max_length=250)
    quarter_year = models.ForeignKey(Period, on_delete=models.CASCADE)
    # TODO: MODEL SHOULD ALLOW USER TO SAVE ONE INDICATOR PER QUARTER
    # indicator = models.ForeignKey(Indicators, on_delete=models.CASCADE)
    facility_name = models.ForeignKey(Facilities, on_delete=models.CASCADE)
    field_1 = models.CharField(validators=[RegexValidator(r'^\d+$')], max_length=100)
    field_2 = models.CharField(validators=[RegexValidator(r'^\d+$')], max_length=100)
    field_3 = models.CharField(validators=[RegexValidator(r'^\d+$')], max_length=100)
    total_source = models.CharField(validators=[RegexValidator(r'^\d+$')], max_length=100, blank=True)
    field_5 = models.CharField(validators=[RegexValidator(r'^\d+$')], max_length=100)
    field_6 = models.CharField(validators=[RegexValidator(r'^\d+$')], max_length=100)
    field_7 = models.CharField(validators=[RegexValidator(r'^\d+$')], max_length=100)
    total_731moh = models.CharField(validators=[RegexValidator(r'^\d+$')], max_length=100, blank=True)
    # field_9 = models.CharField(validators=[RegexValidator(r'^\d+$')], max_length=100)
    # field_10 = models.CharField(validators=[RegexValidator(r'^\d+$')], max_length=100)
    # field_11 = models.CharField(validators=[RegexValidator(r'^\d+$')], max_length=100)
    # total_khis = models.CharField(validators=[RegexValidator(r'^\d+$')], max_length=100, blank=True)

    created_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                   on_delete=models.CASCADE)

    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    class Meta:
        """
        The unique_together option in Django models specifies a set of fields that must have unique values across the
        instances of the model. In this case, the fields quarter_year, indicator and facility must be unique together,
        meaning that there cannot be two instances of the model with the same values for both of those fields. This
        constraint will ensure that the same quarter data for a specific indicator for a specific facility cannot be
        saved twice.
        """
        unique_together = (("quarter_year", "indicator", "facility_name"),)

    def __str__(self):
        return f"{self.facility_name} {self.indicator} ({self.quarter_year})"

    def save(self, *args, **kwargs):
        self.total_source = int(self.field_1) + int(self.field_2) + int(self.field_3)
        self.total_731moh = int(self.field_5) + int(self.field_6) + int(self.field_7)
        # self.total_khis = int(self.field_9) + int(self.field_10) + int(self.field_11)
        super().save(*args, **kwargs)


class FyjPerformance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    mfl_code = models.IntegerField()
    facility = models.CharField(max_length=100)
    month = models.CharField(max_length=100)
    tst_p = models.IntegerField()
    tst_a = models.IntegerField()
    tst_t = models.IntegerField()
    tst_pos_p = models.IntegerField()
    tst_pos_a = models.IntegerField()
    tst_pos_t = models.IntegerField()
    tx_new_p = models.IntegerField()
    tx_new_a = models.IntegerField()
    tx_new_t = models.IntegerField()
    tx_curr_p = models.IntegerField()
    tx_curr_a = models.IntegerField()
    tx_curr_t = models.IntegerField()
    pmtct_stat_d = models.IntegerField()
    pmtct_stat_n = models.IntegerField()
    pmtct_pos = models.IntegerField()
    pmtct_arv = models.IntegerField()
    pmtct_inf_arv = models.IntegerField()
    pmtct_eid = models.IntegerField()
    hei_pos = models.IntegerField()
    hei_pos_art = models.IntegerField()
    prep_new = models.IntegerField()
    gbv_sexual = models.IntegerField()
    gbv_emotional_physical = models.IntegerField()
    kp_anc = models.IntegerField()
    new_pos_anc = models.IntegerField()
    on_haart_anc = models.IntegerField()
    new_on_haart_anc = models.IntegerField()
    pos_l_d = models.IntegerField()
    pos_pnc = models.IntegerField()
    cx_ca = models.IntegerField()
    tb_stat_d = models.IntegerField()
    ipt = models.IntegerField()
    tb_prev_n = models.IntegerField()
    tx_ml = models.IntegerField()
    tx_rtt = models.IntegerField()
    quarter_year = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        unique_together = (('mfl_code', 'quarter_year'),)
        ordering = ['facility']

    def __str__(self):
        return f"{self.facility} - {self.month}"

    def save(self, *args, **kwargs):
        # Get the month and year string from the `month` field
        month_str = self.month
        year_str = month_str.split()[-1]

        # Convert the year string to an integer
        year = int(year_str)

        # Get the month string
        month = month_str.split("-")[0].strip()
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

        parts = month_str.split("-")

        self.month = parts[0].strip() + " - " + parts[1].strip()

        # Check if a record with the same mfl_code, quarter_year, and month already exists
        existing_record = FyjPerformance.objects.filter(
            mfl_code=self.mfl_code,
            quarter_year=self.quarter_year,
            month=self.month
        ).first()

        if existing_record:
            # If a duplicate is found, raise a ValidationError
            error_message = f"A record for {self.month} of {self.quarter_year} already exists."
            raise ValidationError(error_message)

        # Call the parent save method to save the object
        super().save(*args, **kwargs)


class DQAWorkPlan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    AREAS_CHOICES = [
        ("HTS/PREVENTION/PMTCT", "HTS/PREVENTION/PMTCT"),
        ("CHART ABSTRACTION", "CHART ABSTRACTION"),
        ("M&E SYSTEMS", "M&E SYSTEMS"),
        ("Data Management Systems", "Data Management Systems"),
        ("Service Quality Assessment", "Service Quality Assessment (SQA)")
    ]
    dqa_date = models.DateField()
    facility_name = models.ForeignKey(Facilities, on_delete=models.CASCADE, blank=True, null=True)
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    progress = models.FloatField(null=True, blank=True)
    timeframe = models.FloatField(null=True, blank=True)
    created_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                   on_delete=models.CASCADE)
    modified_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                    on_delete=models.CASCADE, related_name='+')

    def __str__(self):
        return f"{self.facility_name} - {self.quarter_year}"

    class Meta:
        ordering = ['facility_name']


class SystemAssessment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    description = models.TextField()
    dropdown_option = models.CharField(max_length=50, choices=[
        ("Yes", "Yes - completely"),
        ("Partly", "Partly"),
        ("No", "No - not at all"),
        ("N/A", "N/A")
    ], blank=True, null=True)
    facility_name = models.ForeignKey(Facilities, on_delete=models.CASCADE, blank=True, null=True)
    quarter_year = models.ForeignKey(Period, on_delete=models.CASCADE, blank=True, null=True)
    # component = models.CharField(max_length=250, blank=True, null=True)
    auditor_note = models.CharField(max_length=250, blank=True, null=True)
    supporting_documentation_required = models.CharField(max_length=10,
                                                         choices=[("", "-"), ("Yes", "Yes"), ("No", "No")]
                                                         , blank=True, null=True)
    dqa_date = models.DateField(blank=True, null=True)
    calculations = models.FloatField(null=True, blank=True)
    created_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                   on_delete=models.CASCADE)
    modified_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                    on_delete=models.CASCADE, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.facility_name} - {self.quarter_year}"

    class Meta:
        unique_together = (("quarter_year", "description", "facility_name"),)
        ordering = ['facility_name']


class AuditTeam(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=255)
    carder = models.CharField(max_length=255)
    organization = models.CharField(max_length=255)
    facility_name = models.ForeignKey(Facilities, on_delete=models.CASCADE, blank=True, null=True)
    quarter_year = models.ForeignKey(Period, on_delete=models.CASCADE, blank=True, null=True)
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
        if AuditTeam.objects.filter(facility_name=self.facility_name, quarter_year=self.quarter_year).exclude(
                pk=self.pk).count() >= 30:
            raise ValidationError('Only 30 audit team members are allowed per facility per quarter.')

        # Call the super method to save the record
        super().save(*args, **kwargs)


class KhisPerformance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    mfl_code = models.IntegerField()
    facility = models.CharField(max_length=100)
    month = models.CharField(max_length=100)
    tst_p = models.IntegerField()
    tst_a = models.IntegerField()
    tst_t = models.IntegerField()
    tst_pos_p = models.IntegerField()
    tst_pos_a = models.IntegerField()
    tst_pos_t = models.IntegerField()
    tx_new_p = models.IntegerField()
    tx_new_a = models.IntegerField()
    tx_new_t = models.IntegerField()
    tx_curr_p = models.IntegerField()
    tx_curr_a = models.IntegerField()
    tx_curr_t = models.IntegerField()
    pmtct_stat_d = models.IntegerField()
    pmtct_stat_n = models.IntegerField()
    pmtct_pos = models.IntegerField()
    pmtct_arv = models.IntegerField()
    pmtct_inf_arv = models.IntegerField()
    prep_new = models.IntegerField()
    gbv_sexual = models.IntegerField()
    infant_arv_prophyl_anc = models.IntegerField()
    infant_arv_prophyl_l_d = models.IntegerField()
    infant_arv_prophyl_lt8wks_pnc = models.IntegerField()
    haart_l_d = models.IntegerField()
    pos_results_pnc_lt6wks = models.IntegerField()
    start_haart_pnc_lt6wks = models.IntegerField()
    kp_anc = models.IntegerField()
    new_pos_anc = models.IntegerField()
    on_haart_anc = models.IntegerField()
    new_on_haart_anc = models.IntegerField()
    pos_l_d = models.IntegerField()
    pos_pnc = models.IntegerField()
    cx_ca = models.IntegerField()
    tb_stat_d = models.IntegerField()
    ipt = models.IntegerField()
    anc_initial_test = models.IntegerField()
    first_anc_visits = models.IntegerField()
    quarter_year = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        unique_together = (('mfl_code', 'month'),)
        ordering = ['facility']

    def __str__(self):
        return f"{self.facility} - {self.month}"

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


class UpdateButtonSettings(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    hide_button_time = models.TimeField()
    disable_all_dqa_update_buttons = models.BooleanField(default=False)  # add this line
    days_to_keep_update_button_enabled = models.PositiveIntegerField(default=0)

    def __str__(self):
        return str(self.hide_button_time)


class BaseModel(models.Model):
    # TODO: REFACTOR THE MODELS
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


class TableNames(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    model_name = models.CharField(max_length=25, blank=True, null=True)


class BaseSqa(BaseModel):
    CHOICES = [
        ("Yes", "Yes - completely"),
        ("Partly", "Partly"),
        ("No", "No - not at all"),
        ("N/A", "N/A")
    ]
    description = models.TextField()
    dropdown_option = models.CharField(max_length=50, choices=CHOICES, blank=True, null=True)
    verification = models.TextField()
    facility_name = models.ForeignKey(Facilities, on_delete=models.CASCADE, blank=True, null=True)
    sub_county = models.ForeignKey(Sub_counties, null=True, blank=True, on_delete=models.CASCADE)
    county = models.ForeignKey(Counties, null=True, blank=True, on_delete=models.CASCADE)
    quarter_year = models.ForeignKey(Period, on_delete=models.CASCADE, blank=True, null=True)
    dqa_date = models.DateTimeField(auto_now_add=True)
    numerator_description = models.TextField(blank=True, null=True)
    denominator_description = models.TextField(blank=True, null=True)
    numerator = models.PositiveIntegerField(blank=True, null=True)
    denominator = models.PositiveIntegerField(blank=True, null=True)
    calculations = models.FloatField(null=True, blank=True)
    indicator_performance = models.FloatField(null=True, blank=True)
    auditor_note = models.CharField(max_length=800, blank=True, null=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.facility_name} {self.description} ({self.date_created})"


class Gbv(BaseSqa):
    class Meta:
        verbose_name_plural = 'GBV'


class Vmmc(BaseSqa):
    class Meta:
        verbose_name_plural = 'VMMC'


class Hts(BaseSqa):
    class Meta:
        verbose_name_plural = 'HTS'


class Prep(BaseSqa):
    class Meta:
        verbose_name_plural = 'PrEP'


class Tb(BaseSqa):
    class Meta:
        verbose_name_plural = 'TB'


class CareTreatment(BaseSqa):
    class Meta:
        verbose_name_plural = 'Care and Treatment'


class Pharmacy(BaseSqa):
    class Meta:
        verbose_name_plural = 'Pharmacy'


class Cqi(BaseSqa):
    class Meta:
        verbose_name_plural = 'CQI'
