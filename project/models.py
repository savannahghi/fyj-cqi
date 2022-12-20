# from django.contrib.auth.models import User

from django.db import models
from crum import get_current_user, get_current_request
# from phonenumber_field.modelfields import PhoneNumberField

# Create your models here.
from django.template.defaultfilters import slugify
from multiselectfield import MultiSelectField
from phonenumber_field.modelfields import PhoneNumberField

from account.models import NewUser
from project.utils import image_resize

import os

# This handles django [Errno 2] No such file or directory ERROR
file_ = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'media/files/facilities.txt')
sub_county_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'media/files/subcounties.txt')
county_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'media/files/counties.txt')


# class CustomUser(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE)
#     phone_number = PhoneNumberField()
#
#     def __str__(self):
#         return self.user.username


def read_txt(file_):
    # read a local file with facility names
    data = open(file_, 'r').read()
    # split at new line
    facility_list = data.split("\n")
    # Make a tuple
    FACILITY_CHOICES = tuple((choice, choice) for choice in facility_list)
    return FACILITY_CHOICES


class Facilities(models.Model):
    # FACILITY_CHOICES = read_txt(file_)
    # facilities = models.CharField(max_length=250, choices=FACILITY_CHOICES, unique=True)
    facilities = models.CharField(max_length=250, unique=True)
    mfl_code = models.IntegerField(unique=True)

    class Meta:
        verbose_name_plural = 'facilities'
        ordering = ['facilities']

    def __str__(self):
        return self.facilities

    def save(self, *args, **kwargs):
        """Ensure manager name is in title case"""
        self.facilities = self.facilities.upper().strip()
        super().save(*args, **kwargs)


class Counties(models.Model):
    county_name = models.CharField(max_length=250, unique=True)

    # sub_counties = models.ManyToManyField(Sub_counties)

    class Meta:
        verbose_name_plural = 'counties'
        ordering = ['county_name']

    def __str__(self):
        return self.county_name

    def save(self, *args, **kwargs):
        """Ensure manager name is in title case"""
        self.county_name = self.county_name.upper()
        super().save(*args, **kwargs)


class Sub_counties(models.Model):
    sub_counties = models.CharField(max_length=250, unique=True)
    counties = models.ManyToManyField(Counties)
    facilities = models.ManyToManyField(Facilities)

    class Meta:
        verbose_name_plural = 'sub-counties'
        ordering = ['sub_counties']

    def __str__(self):
        return self.sub_counties


class Department(models.Model):
    department = models.CharField(max_length=250, unique=True)

    class Meta:
        ordering = ['department']

    def __str__(self):
        return self.department


class Category(models.Model):
    category = models.CharField(max_length=250, unique=True)

    class Meta:
        ordering = ['category']

    def __str__(self):
        return self.category


class QI_Projects(models.Model):
    FACILITY_CHOICES = read_txt(file_)
    SUB_COUNTY_CHOICES = read_txt(sub_county_file)
    COUNTY_CHOICES = read_txt(county_file)
    DEPARTMENT_CHOICES = [('Care and TX clinic', 'Care and TX clinic'), ('TB clinic', 'TB clinic'),
                          ('Laboratory', 'Laboratory'), ('PMTCT', 'PMTCT'), ('Pharmacy', 'Pharmacy'),
                          ('Community', 'Community'), ('VMMC', 'VMMC'), ('Nutrition clinic', 'Nutrition clinic'),
                          ('OPD', 'OPD'), ('IPD', 'IPD')]
    CATEGORY_CHOICES = (
        ('HVL', 'HVL'), ('IPT', 'IPT'), ('Index testing', 'Index testing'), ('HTS', 'HTS'),
        ('TX & RETENTION', 'TX & RETENTION'), ('PMTCT', 'PMTCT'), ('MMD/MMS', 'MMD/MMS'), ('LAB', 'LAB'), ('TB', 'TB'),
        ('Others', 'Others'),)

    departments = models.ForeignKey(Department, on_delete=models.CASCADE)
    department = models.CharField(max_length=200, choices=DEPARTMENT_CHOICES, blank=True, null=True, default=0)
    # project_category = models.ForeignKey(Category, on_delete=models.CASCADE)
    project_category = models.ForeignKey(Category, on_delete=models.CASCADE)
    project_title = models.CharField(max_length=250)
    # facility = models.CharField(max_length=250, choices=FACILITY_CHOICES)
    facility_name = models.ForeignKey(Facilities, on_delete=models.CASCADE)
    county = models.ForeignKey(Counties, on_delete=models.CASCADE)
    sub_county = models.ForeignKey(Sub_counties, null=True, blank=True, on_delete=models.CASCADE)
    # sub_county = models.CharField(max_length=250, choices=SUB_COUNTY_CHOICES)
    # county = models.CharField(max_length=250, choices=COUNTY_CHOICES)
    settings = models.CharField(max_length=250)
    problem_background = models.TextField()
    process_analysis = models.ImageField(upload_to='images', default='images/default.png', null=True, blank=True)
    objective = models.TextField()
    participants = models.TextField()
    responsible_people = models.TextField()
    numerator = models.CharField(max_length=250)
    denominator = models.CharField(max_length=250)
    qi_manager = models.ForeignKey('Qi_managers', on_delete=models.CASCADE, null=True)
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
        return str(self.facility_name) + " : " + str(self.project_title)


class Subcounty_qi_projects(models.Model):
    # FACILITY_CHOICES = read_txt(file_)
    SUB_COUNTY_CHOICES = read_txt(sub_county_file)
    COUNTY_CHOICES = read_txt(county_file)
    DEPARTMENT_CHOICES = [('Care and TX clinic', 'Care and TX clinic'), ('TB clinic', 'TB clinic'),
                          ('Laboratory', 'Laboratory'), ('PMTCT', 'PMTCT'), ('Pharmacy', 'Pharmacy'),
                          ('Community', 'Community'), ('VMMC', 'VMMC'), ('Nutrition clinic', 'Nutrition clinic'),
                          ('OPD', 'OPD'), ('IPD', 'IPD')]
    CATEGORY_CHOICES = (
        ('HVL', 'HVL'), ('IPT', 'IPT'), ('Index testing', 'Index testing'), ('HTS', 'HTS'),
        ('TX & RETENTION', 'TX & RETENTION'), ('PMTCT', 'PMTCT'), ('MMD/MMS', 'MMD/MMS'), ('LAB', 'LAB'), ('TB', 'TB'),
        ('Others', 'Others'),)

    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    # department = models.CharField(max_length=200, choices=DEPARTMENT_CHOICES, blank=True, null=True, default=0)
    project_category = models.ForeignKey(Category, on_delete=models.CASCADE)
    project_title = models.CharField(max_length=250)
    # facility = models.CharField(max_length=250, choices=FACILITY_CHOICES)
    # facility_name = models.ForeignKey(Facilities, on_delete=models.CASCADE)
    county = models.ForeignKey(Counties, on_delete=models.CASCADE)
    sub_county = models.ForeignKey(Sub_counties, on_delete=models.CASCADE)
    # sub_counties = MultiSelectField(choices=SUB_COUNTY_CHOICES)
    # county = models.CharField(max_length=250, choices=COUNTY_CHOICES)
    settings = models.CharField(max_length=250)
    problem_background = models.TextField()
    process_analysis = models.ImageField(upload_to='images', default='images/default.png', null=True, blank=True)
    objective = models.TextField()
    participants = models.TextField()
    responsible_people = models.TextField()
    numerator = models.CharField(max_length=250)
    denominator = models.CharField(max_length=250)
    qi_manager = models.ForeignKey('Qi_managers', on_delete=models.CASCADE, null=True)
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
        verbose_name_plural = "QI_Projects_sub_counties"

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
        return str(self.project_title)


class County_qi_projects(models.Model):
    # FACILITY_CHOICES = read_txt(file_)
    # SUB_COUNTY_CHOICES = read_txt(sub_county_file)
    COUNTY_CHOICES = read_txt(county_file)
    DEPARTMENT_CHOICES = [('Care and TX clinic', 'Care and TX clinic'), ('TB clinic', 'TB clinic'),
                          ('Laboratory', 'Laboratory'), ('PMTCT', 'PMTCT'), ('Pharmacy', 'Pharmacy'),
                          ('Community', 'Community'), ('VMMC', 'VMMC'), ('Nutrition clinic', 'Nutrition clinic'),
                          ('OPD', 'OPD'), ('IPD', 'IPD')]
    CATEGORY_CHOICES = (
        ('HVL', 'HVL'), ('IPT', 'IPT'), ('Index testing', 'Index testing'), ('HTS', 'HTS'),
        ('TX & RETENTION', 'TX & RETENTION'), ('PMTCT', 'PMTCT'), ('MMD/MMS', 'MMD/MMS'), ('LAB', 'LAB'), ('TB', 'TB'),
        ('Others', 'Others'),)

    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    # department = models.CharField(max_length=200, choices=DEPARTMENT_CHOICES, blank=True, null=True, default=0)
    project_category = models.ForeignKey(Category, on_delete=models.CASCADE)
    project_title = models.CharField(max_length=250)
    # facility = models.CharField(max_length=250, choices=FACILITY_CHOICES)
    # facility_name = models.ForeignKey(Facilities, on_delete=models.CASCADE)
    county = models.ForeignKey(Counties, on_delete=models.CASCADE)
    # sub_county = models.ForeignKey(Sub_counties,on_delete=models.CASCADE)
    # sub_counties = MultiSelectField(choices=SUB_COUNTY_CHOICES)
    # county = models.CharField(max_length=250, choices=COUNTY_CHOICES)
    settings = models.CharField(max_length=250)
    problem_background = models.TextField()
    process_analysis = models.ImageField(upload_to='images', default='images/default.png', null=True, blank=True)
    objective = models.TextField()
    participants = models.TextField()
    responsible_people = models.TextField()
    numerator = models.CharField(max_length=250)
    denominator = models.CharField(max_length=250)
    qi_manager = models.ForeignKey('Qi_managers', on_delete=models.CASCADE, null=True)
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
        verbose_name_plural = "QI_Projects_counties"

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
        return str(self.project_title)


class Hub_qi_projects(models.Model):
    # FACILITY_CHOICES = read_txt(file_)
    # SUB_COUNTY_CHOICES = read_txt(sub_county_file)
    # COUNTY_CHOICES = read_txt(county_file)
    DEPARTMENT_CHOICES = [('Care and TX clinic', 'Care and TX clinic'), ('TB clinic', 'TB clinic'),
                          ('Laboratory', 'Laboratory'), ('PMTCT', 'PMTCT'), ('Pharmacy', 'Pharmacy'),
                          ('Community', 'Community'), ('VMMC', 'VMMC'), ('Nutrition clinic', 'Nutrition clinic'),
                          ('OPD', 'OPD'), ('IPD', 'IPD')]
    CATEGORY_CHOICES = (
        ('HVL', 'HVL'), ('IPT', 'IPT'), ('Index testing', 'Index testing'), ('HTS', 'HTS'),
        ('TX & RETENTION', 'TX & RETENTION'), ('PMTCT', 'PMTCT'), ('MMD/MMS', 'MMD/MMS'), ('LAB', 'LAB'), ('TB', 'TB'),
        ('Others', 'Others'),)

    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    # department = models.CharField(max_length=200, choices=DEPARTMENT_CHOICES, blank=True, null=True, default=0)
    project_category = models.ForeignKey(Category, on_delete=models.CASCADE)
    project_title = models.CharField(max_length=250)
    # facility = models.CharField(max_length=250, choices=FACILITY_CHOICES)
    # facility_name = models.ForeignKey(Facilities, on_delete=models.CASCADE)
    hub = models.CharField(max_length=250)
    # sub_county = models.ForeignKey(Sub_counties,on_delete=models.CASCADE)
    # sub_counties = MultiSelectField(choices=SUB_COUNTY_CHOICES)
    # county = models.CharField(max_length=250, choices=COUNTY_CHOICES)
    settings = models.CharField(max_length=250)
    problem_background = models.TextField()
    process_analysis = models.ImageField(upload_to='images', default='images/default.png', null=True, blank=True)
    objective = models.TextField()
    participants = models.TextField()
    responsible_people = models.TextField()
    numerator = models.CharField(max_length=250)
    denominator = models.CharField(max_length=250)
    qi_manager = models.ForeignKey('Qi_managers', on_delete=models.CASCADE, null=True)
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
        verbose_name_plural = "QI_Projects_hub"

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
        return str(self.project_title)


class Program_qi_projects(models.Model):
    # FACILITY_CHOICES = read_txt(file_)
    # SUB_COUNTY_CHOICES = read_txt(sub_county_file)
    # COUNTY_CHOICES = read_txt(county_file)
    DEPARTMENT_CHOICES = [('Care and TX clinic', 'Care and TX clinic'), ('TB clinic', 'TB clinic'),
                          ('Laboratory', 'Laboratory'), ('PMTCT', 'PMTCT'), ('Pharmacy', 'Pharmacy'),
                          ('Community', 'Community'), ('VMMC', 'VMMC'), ('Nutrition clinic', 'Nutrition clinic'),
                          ('OPD', 'OPD'), ('IPD', 'IPD')]
    CATEGORY_CHOICES = (
        ('HVL', 'HVL'), ('IPT', 'IPT'), ('Index testing', 'Index testing'), ('HTS', 'HTS'),
        ('TX & RETENTION', 'TX & RETENTION'), ('PMTCT', 'PMTCT'), ('MMD/MMS', 'MMD/MMS'), ('LAB', 'LAB'), ('TB', 'TB'),
        ('Others', 'Others'),)

    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    # department = models.CharField(max_length=200, choices=DEPARTMENT_CHOICES, blank=True, null=True, default=0)
    project_category = models.ForeignKey(Category, on_delete=models.CASCADE)
    project_title = models.CharField(max_length=250)
    # facility = models.CharField(max_length=250, choices=FACILITY_CHOICES)
    # facility_name = models.ForeignKey(Facilities, on_delete=models.CASCADE)
    program = models.CharField(max_length=250)
    # sub_county = models.ForeignKey(Sub_counties,on_delete=models.CASCADE)
    # sub_counties = MultiSelectField(choices=SUB_COUNTY_CHOICES)
    # county = models.CharField(max_length=250, choices=COUNTY_CHOICES)
    settings = models.CharField(max_length=250)
    problem_background = models.TextField()
    process_analysis = models.ImageField(upload_to='images', default='images/default.png', null=True, blank=True)
    objective = models.TextField()
    participants = models.TextField()
    responsible_people = models.TextField()
    numerator = models.CharField(max_length=250)
    denominator = models.CharField(max_length=250)
    qi_manager = models.ForeignKey('Qi_managers', on_delete=models.CASCADE, null=True)
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
        verbose_name_plural = "QI_Projects_program"

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
        return str(self.project_title)


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
        return str(self.project)
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


class Resources(models.Model):
    resource_name = models.CharField(max_length=250)
    resource = models.FileField(upload_to='resources')
    uploaded_by = models.ForeignKey(NewUser, on_delete=models.CASCADE)
    description = models.TextField(max_length=1000)
    uploaded_date = models.DateTimeField(auto_now_add=True, auto_now=False)
    upload_date_updated = models.DateTimeField(auto_now=True, auto_now_add=False)

    def __str__(self):
        return self.resource_name

    def save(self, commit=True, *args, **kwargs):
        user = get_current_user()
        # request = get_current_request()
        if user and not user.pk:
            user = None
        if not self.pk:
            self.uploaded_by = user
            super().save(*args, **kwargs)
        super().save(*args, **kwargs)

    def delete(self, commit=True, *args, **kwargs):
        """This ensures file is deleted from the file system"""
        self.resource.delete()
        super().delete(*args, **kwargs)


class Qi_managers(models.Model):
    first_name = models.CharField(max_length=250)
    last_name = models.CharField(max_length=250)
    phone_number = PhoneNumberField(null=True, blank=True)
    designation = models.CharField(max_length=250)
    email = models.EmailField(null=True, blank=True, unique=True)
    date_created = models.DateTimeField(auto_now_add=True, auto_now=False)
    date_updated = models.DateTimeField(auto_now=True, auto_now_add=False)

    class Meta:
        ordering = ['first_name']
        verbose_name_plural = "qi managers"

    def __str__(self):
        return self.first_name + " " + self.last_name

    def save(self, *args, **kwargs):
        """Ensure manager name is in title case"""
        self.first_name = self.first_name.title()
        self.last_name = self.last_name.title()
        super().save(*args, **kwargs)


class Qi_team_members(models.Model):
    TEAM_MEMBER_LEVEL_CHOICES = [
        ('Facility QI team member', 'Facility QI team member'),
        ('Sub-county QI team member', 'Sub-county QI team member'),
        ('County QI team member', 'County QI team member'), ('Hub QI team member', 'Hub QI team member'),
        ('Program QI team member', 'Program QI team member'),
    ]
    first_name = models.CharField(max_length=250)
    last_name = models.CharField(max_length=250)
    phone_number = PhoneNumberField(null=True, blank=True)
    designation = models.CharField(max_length=250)
    email = models.EmailField(null=True, blank=True, unique=True)
    choose_qi_team_member_level = models.CharField(max_length=250, choices=TEAM_MEMBER_LEVEL_CHOICES)
    facility = models.ForeignKey(Facilities,on_delete=models.CASCADE)
    # qi_project = models.ForeignKey(QI_Projects,on_delete=models.CASCADE)

    date_created = models.DateTimeField(auto_now_add=True, auto_now=False)
    date_updated = models.DateTimeField(auto_now=True, auto_now_add=False)

    class Meta:
        ordering = ['first_name']
        verbose_name_plural = "qi team members"

    def __str__(self):
        return self.first_name + " " + self.last_name

    def save(self, *args, **kwargs):
        """Ensure manager name is in title case"""
        self.first_name = self.first_name.title()
        self.last_name = self.last_name.title()
        super().save(*args, **kwargs)
