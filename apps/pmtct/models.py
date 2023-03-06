import uuid

from crum import get_current_user
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db import models
from datetime import date
# Create your models here.
from apps.account.models import CustomUser
from apps.cqi.models import Facilities
from datetime import timedelta


def validate_ccc_no(value):
    if len(str(value)) != 10:
        raise ValidationError(
            f'{value} is not a valid CCC number. It should be a 10-digit number.',
            params={'value': value},
        )


def validate_date_started_art(value):
    today = timezone.now()
    print("validate_date_started_art:::::::::::::::::::::::::::::::::")
    print(today)
    print(value)
    if value > today:
        raise ValidationError('Date started on ART cannot be greater than today\'s date.')


def validate_lmp(value):
    today = timezone.now().date()
    if value > today:
        raise ValidationError('LMP cannot be greater than today\'s date.')
    elif value == today:
        raise ValidationError('LMP cannot be the same as today\'s date.')
    elif value > (today - timedelta(days=14)):
        raise ValidationError('LMP must be at least 2 weeks ago.')
    elif value < (today - timedelta(days=300)):
        raise ValidationError('LMP cannot be more than 10 months ago.')


def validate_age(value):
    today = date.today()
    age_limit = date(today.year - 9, today.month, today.day)  # 9 years ago from today
    dob = value.date()  # convert datetime object to date object
    if dob > timezone.now().date():
        raise ValidationError('DOB cannot be greater than today\'s date.')
    elif dob == timezone.now().date():
        raise ValidationError('DOB cannot be the same as today\'s date.')
    elif dob > age_limit:
        raise ValidationError(
            f"{dob} is not a valid date of birth. The client must be at least 9 years old.",
            params={'value': value},
        )


class PatientDetails(models.Model):
    MARITAL_STATUS_CHOICES = [
        ("Single", "Single"),
        ("Married", "Married"),
        ("Separated/Divorced", "Separated/DivorceSeparated"),
        ("Widowed", "Widowed"),
    ]
    PARTNER_STATUS_CHOICES = [
        ("Positive", "Positive"),
        ("Negative", "Negative"),
        ("Unknown", "Unknown"),
    ]
    ON_ART_CHOICES = [
        ("Yes", "Yes"),
        ("No", "No"),
    ]
    UPDATE_STATUS_CHOICES = [
        ("Positive", "Positive"),
        ("Negative", "Negative"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    first_name = models.CharField(max_length=250)
    middle_name = models.CharField(max_length=250)
    last_name = models.CharField(max_length=250)
    date_of_birth = models.DateTimeField(auto_now_add=False, auto_now=False, validators=[validate_age])
    age = models.IntegerField(blank=True, null=True)
    ccc_no = models.BigIntegerField(unique=True, validators=[validate_ccc_no])
    lmp = models.DateField(validators=[validate_lmp])
    edd = models.DateTimeField(auto_now_add=False, auto_now=False)
    gestation_by_age = models.IntegerField(blank=True, null=True)
    date_enrolled_anc = models.DateTimeField(auto_now_add=False, auto_now=False)
    marital_status = models.CharField(max_length=50, choices=MARITAL_STATUS_CHOICES,blank=True,null=True)
    partner_status = models.CharField(max_length=50, choices=PARTNER_STATUS_CHOICES,blank=True,null=True)
    on_art = models.CharField(max_length=50, choices=ON_ART_CHOICES,blank=True,null=True)
    date_started_on_art = models.DateTimeField(blank=True, null=True)
    update_status = models.CharField(max_length=50, choices=UPDATE_STATUS_CHOICES, blank=True, null=True)
    update_status_date = models.DateTimeField(auto_now_add=False, auto_now=False, blank=True, null=True)
    facility_name = models.ForeignKey(Facilities, on_delete=models.CASCADE, blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True, auto_now=False)
    date_updated = models.DateTimeField(auto_now=True, auto_now_add=False)
    modified_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                    on_delete=models.CASCADE, related_name='+')

    class Meta:
        verbose_name_plural = "Patient details"

    def save(self, *args, **kwargs):
        """Ensure manager name is in title case"""
        self.first_name = self.first_name.title()
        self.middle_name = self.middle_name.title()
        self.last_name = self.last_name.title()
        super().save(*args, **kwargs)


class RiskCategorization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    CHOICES = [
        ("Y", "Y"),
        ("N", "N"),
        ("NA", "NA"),
        ("-", "-"),
    ]
    pmtct_mother = models.ForeignKey(PatientDetails, on_delete=models.CASCADE)
    client_characteristics = models.TextField()
    baseline_assessment = models.CharField(max_length=50, choices=CHOICES,blank=True,null=True)
    early_anc = models.CharField(max_length=50, choices=CHOICES,blank=True,null=True)
    mid_anc = models.CharField(max_length=50, choices=CHOICES,blank=True,null=True)
    late_gestation = models.CharField(max_length=50, choices=CHOICES,blank=True,null=True)
    six_weeks_assessment = models.CharField(max_length=50, choices=CHOICES,blank=True,null=True)
    fourteen_weeks_assessment = models.CharField(max_length=50, choices=CHOICES,blank=True,null=True)
    six_month_assessment = models.CharField(max_length=50, choices=CHOICES,blank=True,null=True)
    nine_month_assessment = models.CharField(max_length=50, choices=CHOICES,blank=True,null=True)
    twelve_month_assessment = models.CharField(max_length=50, choices=CHOICES,blank=True,null=True)
    eighteen_month_assessment = models.CharField(max_length=50, choices=CHOICES,blank=True,null=True)
    twenty_four_month_assessment = models.CharField(max_length=50, choices=CHOICES,blank=True,null=True)
    created_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                   on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True, auto_now=False)
    date_updated = models.DateTimeField(auto_now=True, auto_now_add=False)
    modified_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                    on_delete=models.CASCADE, related_name='+')

    class Meta:
        verbose_name_plural = "Risk Categorization"
        unique_together = (("pmtct_mother", "client_characteristics"),)
        # ordering=["pmtct_mother"]

    def __str__(self):
        return str(self.pmtct_mother.id)


class RiskCategorizationTrial(models.Model):
    CLIENT_CATEGORIES = (
        ("1. Is the client a newly HIV Positive (<3mnths)", "1. Is the client a newly HIV Positive (<3mnths)"),
        (
        "2. (a) Is the client an adolescent <19 years of age?", "2. (a) Is the client an adolescent <19 years of age?"),
        ("2. (b) Is the client an adolescent @ School>20yrs", "2. (b) Is the client an adolescent @ School>20yrs"),
        ("3. Is the client’s current VL >200 copies/ml", "3. Is the client’s current VL >200 copies/ml"),
        ("4. (a) Client has poor adherence : Delayed ART", "4. (a) Client has poor adherence : Delayed ART"),
        ("4. (b) Client has poor adherence : Missed >1 clinic appointments in the last scheduled 3 visits",
         "4. (b) Client has poor adherence : Missed >1 clinic appointments in the last scheduled 3 visits"),
        ("4. (c) Client has poor adherence : LTFU/IIT", "4. (c) Client has poor adherence : LTFU/IIT"),
        ("4. (d) Client has poor adherence : Declined ART", "4. (d) Client has poor adherence : Declined ART"),
        ("4. (e) Client has poor adherence : Missed ART doses", "4. (e) Client has poor adherence : Missed ART doses"),
        ("5. The client NOT disclosed to partner", "5. The client NOT disclosed to partner"),
        (
            "6. Does the client have any social family issues and/or severe poverty that could hinder optimal adherence or other related issues",
            "6. Does the client have any social family issues and/or severe poverty that could hinder optimal adherence or other related issues"),
        ("7. Is the client experiencing intimate partner violence or at risk of intimate partner violence?",
         "7. Is the client experiencing intimate partner violence or at risk of intimate partner violence?"),
        ("8. Does the client have active comorbidities? TB, DM, OIs, painful, swollen/cracked nipples, etc.",
         "8. Does the client have active comorbidities? TB, DM, OIs, painful, swollen/cracked nipples, etc."),
        ("9. Is the client a lost to follow up/IIT who has returned to care",
         "9. Is the client a lost to follow up/IIT who has returned to care"),
        ("10. Client has malnourished HEI; SAM, MAM.", "10. Client has malnourished HEI; SAM, MAM."),
        ("11. Does the client have a mental disability or require close care? Use PHQ9 to assess",
         "11. Does the client have a mental disability or require close care? Use PHQ9 to assess")
    )

    client_characteristics = models.CharField(max_length=200, choices=CLIENT_CATEGORIES)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    CHOICES = [
        ("Y", "Y"),
        ("N", "N"),
        ("NA", "NA"),
    ]
    pmtct_mother = models.ForeignKey(PatientDetails, on_delete=models.CASCADE, blank=True, null=True)
    baseline_assessment = models.CharField(max_length=50, choices=CHOICES, blank=True, null=True)
    early_anc = models.CharField(max_length=50, choices=CHOICES, blank=True, null=True)
    mid_anc = models.CharField(max_length=50, choices=CHOICES, blank=True, null=True)
    late_gestation = models.CharField(max_length=50, choices=CHOICES, blank=True, null=True)
    six_weeks_assessment = models.CharField(max_length=50, choices=CHOICES, blank=True, null=True)
    fourteen_weeks_assessment = models.CharField(max_length=50, choices=CHOICES, blank=True, null=True)
    six_month_assessment = models.CharField(max_length=50, choices=CHOICES, blank=True, null=True)
    nine_month_assessment = models.CharField(max_length=50, choices=CHOICES, blank=True, null=True)
    twelve_month_assessment = models.CharField(max_length=50, choices=CHOICES, blank=True, null=True)
    eighteen_month_assessment = models.CharField(max_length=50, choices=CHOICES, blank=True, null=True)
    twenty_four_month_assessment = models.CharField(max_length=50, choices=CHOICES, blank=True, null=True)
    created_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                   on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True, auto_now=False)
    date_updated = models.DateTimeField(auto_now=True, auto_now_add=False)
    modified_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                    on_delete=models.CASCADE, related_name='+')

    class Meta:
        verbose_name_plural = "Risk Categorization trial"
        unique_together = (("pmtct_mother", "client_characteristics"),)


