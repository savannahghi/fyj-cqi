# from django.contrib.auth.models import User

from django.db import models
from crum import get_current_user, get_current_request
# from phonenumber_field.modelfields import PhoneNumberField

# Create your models here.
from account.models import NewUser
from project.utils import image_resize

import os

# This handles django [Errno 2] No such file or directory ERROR
file_ = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'media/files/facilities.txt')


# class CustomUser(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE)
#     phone_number = PhoneNumberField()
#
#     def __str__(self):
#         return self.user.username


class QI_Projects(models.Model):
    # read a local file with facility names
    data = open(file_, 'r').read()
    # split at new line
    facility_list = data.split("\n")
    # Make a tuple
    FACILITY_CHOICES = tuple((choice, choice) for choice in facility_list)
    DEPARTMENT_CHOICES = [('Care and Treatment clinic', 'Care and Treatment clinic'), ('TB clinic', 'TB clinic'),
                          ('Laboratory', 'Laboratory'), ('PMTCT', 'PMTCT'), ('Pharmacy', 'Pharmacy'),
                          ('Community', 'Community'),('VMMC', 'VMMC'), ('Nutrition clinic', 'Nutrition clinic'),
                          ('OPD', 'OPD'), ('IPD', 'IPD')]
    CATEGORY_CHOICES = (
        ('HVL', 'HVL'), ('IPT', 'IPT'), ('Index testing', 'Index testing'), ('HTS', 'HTS'),
        ('TX & RETENTION', 'TX & RETENTION'), ('PMTCT', 'PMTCT'), ('MMD/MMS', 'MMD/MMS'), ('LAB', 'LAB'), ('TB', 'TB'),
        ('Others', 'Others'),)
    department = models.CharField(max_length=200, choices=DEPARTMENT_CHOICES)
    project_category = models.CharField(max_length=200, choices=CATEGORY_CHOICES)
    project_title = models.CharField(max_length=250)
    facility = models.CharField(max_length=250, choices=FACILITY_CHOICES)
    settings = models.CharField(max_length=250)
    problem_background = models.TextField()
    process_analysis = models.ImageField(upload_to='images', default='images/default.png', null=True, blank=True)
    objective = models.TextField()
    participants = models.TextField()
    responsible_people = models.TextField()
    numerator = models.CharField(max_length=250)
    denominator = models.CharField(max_length=250)
    # created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    # created_by = models.ForeignKey('auth.User', blank=True, null=True,
    #                                   default=None, on_delete=models.CASCADE)

    created_by = models.ForeignKey(NewUser, blank=True, null=True,
                                   default=None, on_delete=models.CASCADE)
    STATUS_CHOICES = (
        ('Started or Ongoing', 'STARTED OR ONGOING'),
        ('Completed or Closed', 'COMPLETED OR CLOSED'),
        ('Canceled', 'CANCELED'),
        ('Not started', 'NOT STARTED'),
        ('Postponed', 'POSTPONED'),
    )
    measurement_status = models.CharField(max_length=250, choices=STATUS_CHOICES)
    FREQUENCY_CHOICES = (
        ('Daily', 'Daily'),
        ('Weekly', 'Weekly'),
        ('Fortnightly', 'Fortnightly'),
        ('Monthly', 'Monthly'),
        ('Quarterly', 'Quarterly'),
        ('Semi-annually', 'Semi-annually'),
        ('Annually', 'Annually'),
    )
    measurement_frequency = models.CharField(max_length=250, choices=FREQUENCY_CHOICES)
    comments = models.TextField(blank=True)

    start_date = models.DateTimeField(auto_now_add=True, auto_now=False)
    date_updated = models.DateTimeField(auto_now=True, auto_now_add=False)
    # modified_by = models.ForeignKey('auth.User', blank=True, null=True,
    #                                 default=None, on_delete=models.CASCADE, related_name='+')

    modified_by = models.ForeignKey(NewUser, blank=True, null=True,
                                    default=None, on_delete=models.CASCADE, related_name='+')
    remote_addr = models.CharField(blank=True, default='', max_length=250)
    first_cycle_date = models.DateField(auto_now=False, auto_now_add=False)

    # Django fix Admin plural
    class Meta:
        verbose_name_plural = "QI_Projects"

    # def save(self, *args, **kwargs):
    #     if not self.sales:
    #         self.sales = self.sales_name.sales
    #     return super().save(*args, **kwargs)

    def save(self, commit=True, *args, **kwargs):
        user = get_current_user()
        request = get_current_request()
        if user and not user.pk:
            user = None
        if not self.pk:
            self.created_by = user
        self.modified_by = user

        if request and not self.remote_addr:
            self.remote_addr = request.META['REMOTE_ADDR']
        if commit:
            image_resize(self.process_analysis, 800, 500)
            super().save(*args, **kwargs)
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.facility) + " : " + self.project_title


class Close_project(models.Model):
    project_id = models.ForeignKey(QI_Projects, on_delete=models.CASCADE)
    measurement_status_reason = models.CharField(max_length=250)
    measurement_status_date = models.DateTimeField(auto_now_add=True, auto_now=False)
    limitations = models.TextField()
    conclusion = models.TextField()

    # Django fix Admin plural
    class Meta:
        verbose_name_plural = "close_project"


class TestedChange(models.Model):
    project = models.ForeignKey(QI_Projects, on_delete=models.CASCADE, blank=True, null=True)
    month_year = models.DateField()
    tested_change = models.CharField(max_length=1000)
    comments = models.CharField(max_length=2000)
    numerator = models.IntegerField()
    denominator = models.IntegerField()
    achievements = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.tested_change + " - " + str(self.achievements) + "%" + " - " + str(self.project)
        # return self.tested_change

    def save(self, *args, **kwargs):
        self.achievements = round(self.numerator / self.denominator * 100, )
        super().save(*args, **kwargs)


class ProjectComments(models.Model):
    qi_project_title = models.ForeignKey(QI_Projects, on_delete=models.CASCADE, blank=True, null=True)
    commented_by = models.ForeignKey(NewUser, blank=True, null=True,
                                     default=None, on_delete=models.CASCADE)
    comment = models.TextField()
    comment_date = models.DateTimeField(auto_now_add=True, auto_now=False)
    comment_updated = models.DateTimeField(auto_now=True, auto_now_add=False)

    class Meta:
        verbose_name_plural = "Project comments"

    def __str__(self):
        return self.comment


class ProjectResponses(models.Model):
    response_by = models.ForeignKey(NewUser, blank=True, null=True,
                                    default=None, on_delete=models.CASCADE)
    comment = models.ForeignKey(ProjectComments, blank=True, null=True,
                                default=None, on_delete=models.CASCADE)
    response = models.TextField()
    response_date = models.DateTimeField(auto_now_add=True, auto_now=False)
    response_updated_date = models.DateTimeField(auto_now=True, auto_now_add=False)

    class Meta:
        verbose_name_plural = "Project responses"

    def __str__(self):
        return self.response
