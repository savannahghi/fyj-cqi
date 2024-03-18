# from django.contrib.auth.models import User
import re
import uuid

from django.core.exceptions import ValidationError
from django.db import models
from crum import get_current_user, get_current_request
# from phonenumber_field.modelfields import PhoneNumberField

# Create your models here.
# from django.template.defaultfilters import slugify
# from multiselectfield import MultiSelectField
from phonenumber_field.modelfields import PhoneNumberField

from apps.account.models import CustomUser

from apps.cqi.utils import image_resize
def read_txt(file_):
    # read a local file with facility names
    data = open(file_, 'r').read()
    # split at new line
    facility_list = data.split("\n")
    # Make a tuple
    FACILITY_CHOICES = tuple((choice, choice) for choice in facility_list)
    return FACILITY_CHOICES

class GetFirstAttributeMixin:
    def get_first_attribute(self, attributes):
        for attr in attributes:
            attribute = getattr(self, attr, None)
            if attribute is not None:
                return str(attribute)

        return ''  # Or any default value you want to return if none of the attributes exist



class Program(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    program = models.CharField(max_length=250, unique=True)
    class Meta:
        verbose_name_plural = 'Programs'
        ordering = ['program']

    def __str__(self):
        return self.program

    def save(self, *args, **kwargs):
        """Ensure hub name is in title case"""
        self.program = self.program.upper().strip()
        super().save(*args, **kwargs)


class Hub(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    hub = models.CharField(max_length=250, unique=True)

    class Meta:
        verbose_name_plural = 'Hubs'
        ordering = ['hub']

    def __str__(self):
        return self.hub

    def save(self, *args, **kwargs):
        """Ensure hub name is in title case"""
        self.hub = self.hub.upper().strip()
        super().save(*args, **kwargs)


class Facilities(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=250, unique=True)
    mfl_code = models.IntegerField(unique=True)
    fyj_facilities = models.BooleanField(default=False,blank=True)  # Set default value to False

    class Meta:
        verbose_name_plural = 'facilities'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Ensure facility name is in title case and replace any symbol with an underscore"""
        self.name = re.sub(r'[^\w\s]', ' ', self.name).title().strip()
        super().save(*args, **kwargs)


class Counties(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    county_name = models.CharField(max_length=250, unique=True)

    class Meta:
        verbose_name_plural = 'counties'
        ordering = ['county_name']

    def __str__(self):
        return self.county_name

    def save(self, *args, **kwargs):
        """Ensure County name is in title case"""
        self.county_name = self.county_name.upper().strip()
        super().save(*args, **kwargs)


class Sub_counties(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    sub_counties = models.CharField(max_length=250, unique=True)
    counties = models.ManyToManyField(Counties)
    facilities = models.ManyToManyField(Facilities)
    hub = models.ManyToManyField(Hub)

    class Meta:
        verbose_name_plural = 'sub-counties'
        ordering = ['sub_counties']

    def __str__(self):
        return self.sub_counties

    def save(self, *args, **kwargs):
        """Ensure County name is in title case"""
        self.sub_counties = self.sub_counties.title()
        super().save(*args, **kwargs)


class Trigger(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=200)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Ensure Trigger name is in title case"""
        self.name = self.name.upper()
        super().save(*args, **kwargs)


class Department(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    # TODO: EXPLORE HOW TO SHARE QI PROJECTS
    department = models.CharField(max_length=250, unique=True)

    class Meta:
        ordering = ['department']

    def __str__(self):
        return self.department

    def save(self, *args, **kwargs):
        """Ensure department name is in title case"""
        self.department = self.department.upper().replace("/", "_")
        super().save(*args, **kwargs)


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    # TODO: INCLUDE USER USAGE FOR THE ENTIRE APP (LOGINS AND PAGE VIEWS)
    category = models.CharField(max_length=250, unique=True)

    class Meta:
        ordering = ['category']

    def __str__(self):
        return self.category

    def save(self, *args, **kwargs):
        """Ensure County name is in title case"""
        self.category = self.category.upper()
        super().save(*args, **kwargs)


class QI_Projects(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    # TODO: INCLUDE SIMS REPORTS,DQAs AND CBS REPORTS SHOWING AREAS OF IMPROVEMENT (SHARED EVERY 2 WEEKS) care&rx,
    #  covid,etc
    # TODO: TRACK USAGE
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
    project_category = models.ForeignKey(Category, on_delete=models.CASCADE)
    project_title = models.CharField(max_length=250)
    facility_name = models.ForeignKey(Facilities, on_delete=models.CASCADE)
    county = models.ForeignKey(Counties, on_delete=models.CASCADE)
    sub_county = models.ForeignKey(Sub_counties, null=True, blank=True, on_delete=models.CASCADE)
    hub = models.ForeignKey(Hub, null=True, blank=True, on_delete=models.CASCADE)
    settings = models.CharField(max_length=250)
    problem_background = models.TextField()
    process_analysis = models.ImageField(upload_to='images', null=True, blank=True)
    objective = models.TextField()
    numerator = models.CharField(max_length=250)
    denominator = models.CharField(max_length=250)
    qi_manager = models.ForeignKey('Qi_managers', on_delete=models.CASCADE, null=True)
    created_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                   on_delete=models.CASCADE)
    STATUS_CHOICES = (
        ('Started or Ongoing', 'STARTING OR ONGOING'),
        ('Completed-or-Closed', 'COMPLETED OR CLOSED'),
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

    start_date = models.DateTimeField(auto_now_add=True, auto_now=False)
    date_updated = models.DateTimeField(auto_now=True, auto_now_add=False)

    modified_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                    on_delete=models.CASCADE, related_name='+')
    remote_addr = models.CharField(blank=True, default='', max_length=250)
    triggers = models.ManyToManyField(Trigger, blank=True)

    # Django fix Admin plural
    class Meta:
        verbose_name_plural = "QI_Projects"
        ordering = ['facility_name','start_date']

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
        self.project_title = self.project_title.title()
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.facility_name) + " : " + str(self.project_title)


class Subcounty_qi_projects(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    DEPARTMENT_CHOICES = [('Care and TX clinic', 'Care and TX clinic'), ('TB clinic', 'TB clinic'),
                          ('Laboratory', 'Laboratory'), ('PMTCT', 'PMTCT'), ('Pharmacy', 'Pharmacy'),
                          ('Community', 'Community'), ('VMMC', 'VMMC'), ('Nutrition clinic', 'Nutrition clinic'),
                          ('OPD', 'OPD'), ('IPD', 'IPD')]
    CATEGORY_CHOICES = (
        ('HVL', 'HVL'), ('IPT', 'IPT'), ('Index testing', 'Index testing'), ('HTS', 'HTS'),
        ('TX & RETENTION', 'TX & RETENTION'), ('PMTCT', 'PMTCT'), ('MMD/MMS', 'MMD/MMS'), ('LAB', 'LAB'), ('TB', 'TB'),
        ('Others', 'Others'),)

    departments = models.ForeignKey(Department, on_delete=models.CASCADE)
    project_category = models.ForeignKey(Category, on_delete=models.CASCADE)
    project_title = models.CharField(max_length=250)
    county = models.ForeignKey(Counties, on_delete=models.CASCADE)
    sub_county = models.ForeignKey(Sub_counties, on_delete=models.CASCADE)
    settings = models.CharField(max_length=250)
    problem_background = models.TextField()
    process_analysis = models.ImageField(upload_to='images', null=True, blank=True)
    objective = models.TextField()
    numerator = models.CharField(max_length=250)
    denominator = models.CharField(max_length=250)
    qi_manager = models.ForeignKey('Qi_managers', on_delete=models.CASCADE, null=True)
    created_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                   on_delete=models.CASCADE)
    STATUS_CHOICES = (
        ('Started or Ongoing', 'STARTING OR ONGOING'),
        ('Completed-or-Closed', 'COMPLETED OR CLOSED'),
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

    modified_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                    on_delete=models.CASCADE, related_name='+')
    remote_addr = models.CharField(blank=True, default='', max_length=250)
    triggers = models.ManyToManyField(Trigger, blank=True)

    # Django fix Admin plural
    class Meta:
        verbose_name_plural = "QI_Projects_sub_counties"
        ordering = ['sub_county','start_date']

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
        return str(self.sub_county)+"  - "+str(self.project_title)


class County_qi_projects(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    # COUNTY_CHOICES = read_txt(county_file)
    DEPARTMENT_CHOICES = [('Care and TX clinic', 'Care and TX clinic'), ('TB clinic', 'TB clinic'),
                          ('Laboratory', 'Laboratory'), ('PMTCT', 'PMTCT'), ('Pharmacy', 'Pharmacy'),
                          ('Community', 'Community'), ('VMMC', 'VMMC'), ('Nutrition clinic', 'Nutrition clinic'),
                          ('OPD', 'OPD'), ('IPD', 'IPD')]
    CATEGORY_CHOICES = (
        ('HVL', 'HVL'), ('IPT', 'IPT'), ('Index testing', 'Index testing'), ('HTS', 'HTS'),
        ('TX & RETENTION', 'TX & RETENTION'), ('PMTCT', 'PMTCT'), ('MMD/MMS', 'MMD/MMS'), ('LAB', 'LAB'), ('TB', 'TB'),
        ('Others', 'Others'),)

    departments = models.ForeignKey(Department, on_delete=models.CASCADE)
    project_category = models.ForeignKey(Category, on_delete=models.CASCADE)
    project_title = models.CharField(max_length=250)
    county = models.ForeignKey(Counties, on_delete=models.CASCADE)
    settings = models.CharField(max_length=250)
    problem_background = models.TextField()
    process_analysis = models.ImageField(upload_to='images', null=True, blank=True)
    objective = models.TextField()
    numerator = models.CharField(max_length=250)
    denominator = models.CharField(max_length=250)
    qi_manager = models.ForeignKey('Qi_managers', on_delete=models.CASCADE, null=True)

    created_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                   on_delete=models.CASCADE)
    STATUS_CHOICES = (
        ('Started or Ongoing', 'STARTING OR ONGOING'),
        ('Completed-or-Closed', 'COMPLETED OR CLOSED'),
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

    modified_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                    on_delete=models.CASCADE, related_name='+')
    remote_addr = models.CharField(blank=True, default='', max_length=250)
    triggers = models.ManyToManyField(Trigger, blank=True)

    # Django fix Admin plural
    class Meta:
        verbose_name_plural = "QI_Projects_counties"
        ordering=['county']

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
        return str(self.county)+"  - "+str(self.project_title)


class Hub_qi_projects(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    DEPARTMENT_CHOICES = [('Care and TX clinic', 'Care and TX clinic'), ('TB clinic', 'TB clinic'),
                          ('Laboratory', 'Laboratory'), ('PMTCT', 'PMTCT'), ('Pharmacy', 'Pharmacy'),
                          ('Community', 'Community'), ('VMMC', 'VMMC'), ('Nutrition clinic', 'Nutrition clinic'),
                          ('OPD', 'OPD'), ('IPD', 'IPD')]
    CATEGORY_CHOICES = (
        ('HVL', 'HVL'), ('IPT', 'IPT'), ('Index testing', 'Index testing'), ('HTS', 'HTS'),
        ('TX & RETENTION', 'TX & RETENTION'), ('PMTCT', 'PMTCT'), ('MMD/MMS', 'MMD/MMS'), ('LAB', 'LAB'), ('TB', 'TB'),
        ('Others', 'Others'),)

    departments = models.ForeignKey(Department, on_delete=models.CASCADE)
    project_category = models.ForeignKey(Category, on_delete=models.CASCADE)
    project_title = models.CharField(max_length=250)
    hub = models.ForeignKey(Hub, null=True, blank=True, on_delete=models.CASCADE)
    settings = models.CharField(max_length=250)
    problem_background = models.TextField()
    process_analysis = models.ImageField(upload_to='images', null=True, blank=True)
    objective = models.TextField()
    numerator = models.CharField(max_length=250)
    denominator = models.CharField(max_length=250)
    qi_manager = models.ForeignKey('Qi_managers', on_delete=models.CASCADE, null=True)

    created_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                   on_delete=models.CASCADE)
    STATUS_CHOICES = (
        ('Started or Ongoing', 'STARTING OR ONGOING'),
        ('Completed-or-Closed', 'COMPLETED OR CLOSED'),
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

    modified_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                    on_delete=models.CASCADE, related_name='+')
    remote_addr = models.CharField(blank=True, default='', max_length=250)
    triggers = models.ManyToManyField(Trigger, blank=True)

    # Django fix Admin plural
    class Meta:
        verbose_name_plural = "QI_Projects_hub"
        ordering = ['hub','start_date']

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
        return str(self.hub)+"  - "+str(self.project_title)


class Program_qi_projects(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    DEPARTMENT_CHOICES = [('Care and TX clinic', 'Care and TX clinic'), ('TB clinic', 'TB clinic'),
                          ('Laboratory', 'Laboratory'), ('PMTCT', 'PMTCT'), ('Pharmacy', 'Pharmacy'),
                          ('Community', 'Community'), ('VMMC', 'VMMC'), ('Nutrition clinic', 'Nutrition clinic'),
                          ('OPD', 'OPD'), ('IPD', 'IPD')]
    CATEGORY_CHOICES = (
        ('HVL', 'HVL'), ('IPT', 'IPT'), ('Index testing', 'Index testing'), ('HTS', 'HTS'),
        ('TX & RETENTION', 'TX & RETENTION'), ('PMTCT', 'PMTCT'), ('MMD/MMS', 'MMD/MMS'), ('LAB', 'LAB'), ('TB', 'TB'),
        ('Others', 'Others'),)

    departments = models.ForeignKey(Department, on_delete=models.CASCADE)
    project_category = models.ForeignKey(Category, on_delete=models.CASCADE)
    project_title = models.CharField(max_length=250)
    program = models.ForeignKey(Program, on_delete=models.CASCADE)
    settings = models.CharField(max_length=250)
    problem_background = models.TextField()
    process_analysis = models.ImageField(upload_to='images', null=True, blank=True)
    objective = models.TextField()
    numerator = models.CharField(max_length=250)
    denominator = models.CharField(max_length=250)
    qi_manager = models.ForeignKey('Qi_managers', on_delete=models.CASCADE, null=True)

    created_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                   on_delete=models.CASCADE)
    STATUS_CHOICES = (
        ('Started or Ongoing', 'STARTING OR ONGOING'),
        ('Completed-or-Closed', 'COMPLETED OR CLOSED'),
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

    modified_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                    on_delete=models.CASCADE, related_name='+')
    remote_addr = models.CharField(blank=True, default='', max_length=250)
    triggers = models.ManyToManyField(Trigger, blank=True)

    # Django fix Admin plural
    class Meta:
        verbose_name_plural = "QI_Projects_program"
        ordering = ['program','start_date']

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
        return str(self.program) + " : " + str(self.project_title)


class Close_project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    project_id = models.ForeignKey(QI_Projects, on_delete=models.CASCADE, blank=True, null=True)
    program_id = models.ForeignKey(Program_qi_projects, on_delete=models.CASCADE, blank=True, null=True)
    subcounty_id = models.ForeignKey(Subcounty_qi_projects, on_delete=models.CASCADE, blank=True, null=True)
    county_id = models.ForeignKey(County_qi_projects, on_delete=models.CASCADE, blank=True, null=True)
    hub_id = models.ForeignKey(Hub_qi_projects, on_delete=models.CASCADE, blank=True, null=True)
    measurement_status_reason = models.CharField(max_length=250)
    measurement_status_date = models.DateTimeField(auto_now_add=True, auto_now=False)
    limitations = models.TextField()
    conclusion = models.TextField()

    # Django fix Admin plural
    class Meta:
        verbose_name_plural = "close_project"


class TestedChange(models.Model,GetFirstAttributeMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    project = models.ForeignKey(QI_Projects, on_delete=models.CASCADE, blank=True, null=True)
    program_project = models.ForeignKey(Program_qi_projects, on_delete=models.CASCADE, blank=True, null=True)
    subcounty_project = models.ForeignKey(Subcounty_qi_projects, on_delete=models.CASCADE,
                                          blank=True, null=True)
    hub_project = models.ForeignKey(Hub_qi_projects, on_delete=models.CASCADE,
                                    blank=True, null=True)
    county_project = models.ForeignKey(County_qi_projects, on_delete=models.CASCADE,
                                       blank=True, null=True)
    month_year = models.DateField(verbose_name="Date")
    numerator = models.IntegerField()
    denominator = models.IntegerField()
    data_sources = models.CharField(max_length=250)
    tested_change = models.CharField(max_length=1000)
    comments = models.TextField()
    achievements = models.FloatField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "Test of change"
        ordering = ['project', 'subcounty_project', 'county_project', 'hub_project','program_project']

    def __str__(self):
        return self.get_first_attribute(
            ['project', 'subcounty_project', 'county_project', 'hub_project', 'program_project'])

    def save(self, *args, **kwargs):
        self.achievements = round(self.numerator / self.denominator * 100, )
        super().save(*args, **kwargs)


class Comment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    content = models.TextField()
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    qi_project_title = models.ForeignKey(QI_Projects, on_delete=models.CASCADE, null=True, blank=True)
    program_qi_project_title = models.ForeignKey(Program_qi_projects, on_delete=models.CASCADE, null=True, blank=True)
    subcounty_qi_project_title = models.ForeignKey(Subcounty_qi_projects, on_delete=models.CASCADE, null=True,
                                                   blank=True)
    county_project_title = models.ForeignKey(County_qi_projects, on_delete=models.CASCADE, null=True, blank=True)
    hub_qi_project_title = models.ForeignKey(Hub_qi_projects, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE)
    likes = models.IntegerField(default=0)
    dislikes = models.IntegerField(default=0)
    comment_date = models.DateTimeField(auto_now_add=True, auto_now=False)
    comment_updated = models.DateTimeField(auto_now=True, auto_now_add=False)

    class Meta:
        verbose_name_plural = "Comments"
        ordering = ['qi_project_title', 'subcounty_qi_project_title', 'county_project_title',
                    'hub_qi_project_title', 'program_qi_project_title']
    def __str__(self):
        if self.qi_project_title is not None:
            return str(self.qi_project_title) + "  - (" + str(self.author)+ ")"
        elif self.program_qi_project_title is not None:
            return str(self.program_qi_project_title) + "  - (" + str(self.author)+ ")"
        elif self.hub_qi_project_title is not None:
            return str(self.hub_qi_project_title) + "  - (" + str(self.author)+ ")"
        elif self.subcounty_qi_project_title is not None:
            return str(self.subcounty_qi_project_title) + "  - (" + str(self.author)+ ")"
        elif self.county_project_title is not None:
            return str(self.county_project_title) + "  - (" + str(self.author)+ ")"


class LikeDislike(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE)
    like = models.BooleanField(default=False)
    dislike = models.BooleanField(default=False)


class ProjectComments(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    qi_project_title = models.ForeignKey(QI_Projects, on_delete=models.CASCADE, blank=True, null=True)
    commented_by = models.ForeignKey(CustomUser, blank=True, null=True,
                                     default=None, on_delete=models.CASCADE)
    comment = models.TextField()
    comment_date = models.DateTimeField(auto_now_add=True, auto_now=False)
    comment_updated = models.DateTimeField(auto_now=True, auto_now_add=False)

    class Meta:
        verbose_name_plural = "Project comments"
        ordering=['qi_project_title']

    def __str__(self):
        return self.comment


class ProjectResponses(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    response_by = models.ForeignKey(CustomUser, blank=True, null=True,
                                    default=None, on_delete=models.CASCADE)
    comment = models.ForeignKey(ProjectComments, blank=True, null=True,
                                default=None, on_delete=models.CASCADE)
    response = models.TextField()
    response_date = models.DateTimeField(auto_now_add=True, auto_now=False)
    response_updated_date = models.DateTimeField(auto_now=True, auto_now_add=False)

    class Meta:
        verbose_name_plural = "Project responses"
        ordering = ['comment']

    def __str__(self):
        return self.response


class Resources(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    RESOURCE_TYPE = (
        ("articles", "Articles"),
        ("case studies", "Case Studies"),
        ("guides", "Guides"),
        ("research papers", "Research Papers"),
    )
    resource_name = models.CharField(max_length=250)
    resource_type = models.CharField(max_length=250, choices=RESOURCE_TYPE)
    resource = models.FileField(upload_to='resources')
    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, blank=True, null=True)
    description = models.TextField(max_length=1000)

    uploaded_date = models.DateTimeField(auto_now_add=True, auto_now=False)
    upload_date_updated = models.DateTimeField(auto_now=True, auto_now_add=False)

    class Meta:
        ordering = ['-upload_date_updated']

    def __str__(self):
        return self.resource_name

    def save(self, commit=True, *args, **kwargs):
        user = get_current_user()
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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    TEAM_MEMBER_LEVEL_CHOICES = [
        ('Facility QI team member', 'Facility QI team member'),
        ('Sub-county QI team member', 'Sub-county QI team member'),
        ('County QI team member', 'County QI team member'), ('Hub QI team member', 'Hub QI team member'),
        ('Program QI team member', 'Program QI team member'),
    ]
    designation = models.CharField(max_length=250)
    role = models.CharField(max_length=250, null=True, blank=True)

    department = models.CharField(max_length=250, null=True, blank=True)
    choose_qi_team_member_level = models.CharField(max_length=250, choices=TEAM_MEMBER_LEVEL_CHOICES)
    impact = models.TextField()
    notes = models.TextField()
    facility = models.ForeignKey(Facilities, on_delete=models.CASCADE, blank=True, null=True)
    program = models.ForeignKey(Program, on_delete=models.CASCADE, blank=True, null=True)
    qi_project = models.ForeignKey(QI_Projects, on_delete=models.CASCADE, related_name="qi_team_members", blank=True,
                                   null=True)
    program_qi_project = models.ForeignKey(Program_qi_projects, on_delete=models.CASCADE,
                                           related_name="qi_team_members", blank=True, null=True)
    subcounty_qi_project = models.ForeignKey(Subcounty_qi_projects, on_delete=models.CASCADE,
                                             related_name="qi_team_members", blank=True, null=True)
    hub_qi_project = models.ForeignKey(Hub_qi_projects, on_delete=models.CASCADE,
                                       related_name="qi_team_members", blank=True, null=True)
    county_qi_project = models.ForeignKey(County_qi_projects, on_delete=models.CASCADE,
                                          related_name="qi_team_members", blank=True, null=True)
    created_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                   on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, default=None, on_delete=models.CASCADE, related_name="team_member")

    date_created = models.DateTimeField(auto_now_add=True, auto_now=False)
    date_updated = models.DateTimeField(auto_now=True, auto_now_add=False)

    class Meta:
        verbose_name_plural = "qi team members"
        ordering = ['created_by__first_name']

    def __str__(self):
        if self.user.phone_number:
            return self.user.first_name + " " + self.user.last_name
        else:
            return self.user.username

    def save(self, *args, **kwargs):
        """Ensure manager name is in title case"""
        self.designation = self.designation.upper()
        self.department = self.department.upper()
        self.role = self.role.title()
        super().save(*args, **kwargs)


class ArchiveProject(models.Model,GetFirstAttributeMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    qi_project = models.ForeignKey(QI_Projects, on_delete=models.CASCADE, blank=True, null=True)
    program = models.ForeignKey(Program_qi_projects, on_delete=models.CASCADE, blank=True, null=True)
    subcounty = models.ForeignKey(Subcounty_qi_projects, on_delete=models.CASCADE, blank=True, null=True)
    hub = models.ForeignKey(Hub_qi_projects, on_delete=models.CASCADE, blank=True, null=True)
    county = models.ForeignKey(County_qi_projects, on_delete=models.CASCADE, blank=True, null=True)
    archive_project = models.BooleanField(default=False)
    start_date = models.DateTimeField(auto_now_add=True, auto_now=False)
    date_updated = models.DateTimeField(auto_now=True, auto_now_add=False)

    class Meta:
        verbose_name_plural = "archived projects"
        ordering=['qi_project', 'subcounty', 'county', 'hub', 'program']

    def __str__(self):
        return self.get_first_attribute(
        ['qi_project', 'subcounty', 'county', 'hub', 'program'])


class Stakeholder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=200)
    role = models.CharField(max_length=200)
    department = models.CharField(max_length=200)
    contact_info = models.CharField(max_length=200)
    impact = models.TextField()
    notes = models.TextField(blank=True, null=True)
    facility = models.ForeignKey(Facilities, on_delete=models.CASCADE)


class Milestone(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=200, verbose_name='Milestone name')
    start_date = models.DateField()
    end_date = models.DateField()
    description = models.TextField()
    notes = models.TextField(blank=True, null=True)
    facility = models.ForeignKey(Facilities, on_delete=models.CASCADE, blank=True, null=True)
    program = models.ForeignKey(Program, on_delete=models.CASCADE, blank=True, null=True)
    qi_project = models.ForeignKey(QI_Projects, on_delete=models.CASCADE, blank=True, null=True)
    program_qi_project = models.ForeignKey(Program_qi_projects, on_delete=models.CASCADE, blank=True, null=True)
    subcounty_qi_project = models.ForeignKey(Subcounty_qi_projects, on_delete=models.CASCADE, blank=True, null=True)
    county_qi_project = models.ForeignKey(County_qi_projects, on_delete=models.CASCADE, blank=True, null=True)
    hub_qi_project = models.ForeignKey(Hub_qi_projects, on_delete=models.CASCADE, blank=True, null=True)
    created_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                   on_delete=models.CASCADE)

    def clean(self):
        if self.start_date > self.end_date:
            raise ValidationError('Start date cannot be greater than end date')
        elif self.end_date < self.start_date:
            raise ValidationError('Due date cannot be less than start date')
        elif self.end_date == self.start_date:
            raise ValidationError('Due date cannot be the same as start date')

    class Meta:
        verbose_name_plural = "Milestone"
        ordering = ['facility','subcounty_qi_project','county_qi_project','hub_qi_project','program', 'start_date']

    def __str__(self):
        qi_project_str = str(self.qi_project) + " - " if self.qi_project else ""
        program_qi_project_str = str(self.program_qi_project) + " - " if self.program_qi_project else ""
        subcounty_qi_project_str = str(self.subcounty_qi_project) + " - " if self.subcounty_qi_project else ""
        hub_qi_project_str = str(self.hub_qi_project) + " - " if self.hub_qi_project else ""
        county_qi_project_str = str(self.county_qi_project) if self.county_qi_project else ""

        date_str = self.start_date.strftime('%Y-%m-%d %H:%M:%S')

        return f"{qi_project_str}{program_qi_project_str}{subcounty_qi_project_str}{hub_qi_project_str}{county_qi_project_str} ({date_str})"


class ActionPlan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    corrective_action = models.TextField()
    resources_required = models.TextField()
    responsible = models.ManyToManyField(Qi_team_members)
    constraints = models.TextField()
    indicator = models.CharField(max_length=250)
    percent_completed = models.IntegerField()
    start_date = models.DateField()
    due_date = models.DateField()
    facility = models.ForeignKey(Facilities, on_delete=models.CASCADE, null=True, blank=True)
    program = models.ForeignKey(Program, on_delete=models.CASCADE, null=True, blank=True)
    qi_project = models.ForeignKey(QI_Projects, on_delete=models.CASCADE, null=True, blank=True)
    program_qi_project = models.ForeignKey(Program_qi_projects, on_delete=models.CASCADE, null=True, blank=True)
    subcounty_qi_project = models.ForeignKey(Subcounty_qi_projects, on_delete=models.CASCADE, null=True, blank=True)
    county_qi_project = models.ForeignKey(County_qi_projects, on_delete=models.CASCADE, null=True, blank=True)
    hub_qi_project = models.ForeignKey(Hub_qi_projects, on_delete=models.CASCADE, null=True, blank=True)
    created_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                   on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True, auto_now=False)
    date_updated = models.DateTimeField(auto_now=True, auto_now_add=False)
    progress = models.FloatField(null=True, blank=True)
    timeframe = models.FloatField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "Action plans"
        ordering = ['qi_project', 'subcounty_qi_project', 'county_qi_project', 'hub_qi_project',
                    'program']

    def clean(self):
        if self.start_date > self.due_date:
            raise ValidationError('Start date cannot be greater than due date')
        elif self.due_date < self.start_date:
            raise ValidationError('Due date cannot be less than start date')
        elif self.due_date == self.start_date:
            raise ValidationError('Due date cannot be the same as start date')

    def __str__(self):
        if self.qi_project is not None:
            return str(self.qi_project) + "  - " + self.corrective_action
        elif self.program_qi_project is not None:
            return str(self.program_qi_project) + "  - " + self.corrective_action
        elif self.hub_qi_project is not None:
            return str(self.hub_qi_project) + "  - " + self.corrective_action
        elif self.subcounty_qi_project is not None:
            return str(self.subcounty_qi_project) + "  - " + self.corrective_action
        elif self.county_qi_project is not None:
            return str(self.county_qi_project) + "  - " + self.corrective_action


class Lesson_learned(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    project_name = models.ForeignKey(QI_Projects, on_delete=models.CASCADE, blank=True, null=True, )
    program = models.ForeignKey(Program_qi_projects, on_delete=models.CASCADE, blank=True, null=True, )
    subcounty = models.ForeignKey(Subcounty_qi_projects, on_delete=models.CASCADE, blank=True, null=True, )
    county = models.ForeignKey(County_qi_projects, on_delete=models.CASCADE, blank=True, null=True, )
    hub = models.ForeignKey(Hub_qi_projects, on_delete=models.CASCADE, blank=True, null=True, )
    problem_or_opportunity = models.TextField()
    key_successes = models.TextField()
    challenges = models.TextField()
    best_practices = models.TextField()
    recommendations = models.TextField()
    resources = models.TextField()
    created_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                   on_delete=models.CASCADE)
    modified_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                    on_delete=models.CASCADE, related_name='+')
    future_plans = models.TextField()
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Lesson learnt"
        ordering = ['project_name', 'subcounty', 'county', 'hub','program']

    def __str__(self):
        qi_project_str = str(self.project_name) + " - " if self.project_name else ""
        program_qi_project_str = str(self.program) + " - " if self.program else ""
        subcounty_qi_project_str = str(self.subcounty) + " - " if self.subcounty else ""
        hub_qi_project_str = str(self.hub) + " - " if self.hub else ""
        county_qi_project_str = str(self.county) if self.county else ""

        date_str = self.date_created.strftime('%Y-%m-%d %H:%M:%S')

        return f"{qi_project_str}{program_qi_project_str}{subcounty_qi_project_str}{hub_qi_project_str}{county_qi_project_str} ({date_str})"


class Baseline(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    baseline_status = models.ImageField(upload_to='images')
    facility = models.ForeignKey(Facilities, on_delete=models.CASCADE, null=True, blank=True)
    program = models.ForeignKey(Program, on_delete=models.CASCADE, null=True, blank=True)
    qi_project = models.ForeignKey(QI_Projects, on_delete=models.CASCADE, null=True, blank=True)
    program_qi_project = models.ForeignKey(Program_qi_projects, on_delete=models.CASCADE, null=True, blank=True)
    subcounty_qi_project = models.ForeignKey(Subcounty_qi_projects, on_delete=models.CASCADE,
                                             blank=True, null=True)
    hub_qi_project = models.ForeignKey(Hub_qi_projects, on_delete=models.CASCADE,
                                       blank=True, null=True)
    county_qi_project = models.ForeignKey(County_qi_projects, on_delete=models.CASCADE,
                                          blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Baseline status"
        ordering = ['qi_project', 'subcounty_qi_project', 'county_qi_project__county', 'hub_qi_project__hub', 'program']

    def __str__(self):
        qi_project_str = str(self.qi_project) + " - " if self.qi_project else ""
        program_qi_project_str = str(self.program_qi_project) + " - " if self.program_qi_project else ""
        subcounty_qi_project_str = str(self.subcounty_qi_project) + " - " if self.subcounty_qi_project else ""
        hub_qi_project_str = str(self.hub_qi_project) + " - " if self.hub_qi_project else ""
        county_qi_project_str = str(self.county_qi_project) if self.county_qi_project else ""

        date_str = self.date_created.strftime('%Y-%m-%d %H:%M:%S')

        return f"{qi_project_str}{program_qi_project_str}{subcounty_qi_project_str}{hub_qi_project_str}{county_qi_project_str} ({date_str})"

    def save(self, commit=True, *args, **kwargs):
        if commit:
            image_resize(self.baseline_status, 800, 500)
        super().save(*args, **kwargs)


class SustainmentPlan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    # TODO: HAVE DASHBOARDS AND REPORTS TO TRACK HOW THE PROJECT IS DOING DURING SUSTAINMENT PHASE. EXPLORE HOW GANNT
    #  CHART AND RACI MATRIX CHART CAN BE INCORPORATED

    # ForeignKey to link the SustainmentPlan to the QIProject it is associated with
    qi_project = models.ForeignKey(QI_Projects, on_delete=models.CASCADE, null=True, blank=True)
    program = models.ForeignKey(Program_qi_projects, on_delete=models.CASCADE, null=True, blank=True)
    subcounty = models.ForeignKey(Subcounty_qi_projects, on_delete=models.CASCADE, null=True, blank=True)
    county = models.ForeignKey(County_qi_projects, on_delete=models.CASCADE, null=True, blank=True)
    hub = models.ForeignKey(Hub_qi_projects, on_delete=models.CASCADE, null=True, blank=True)
    # Field to capture the objectives of the sustainment plan
    objectives = models.TextField()
    # Field to capture the metrics that will be used to measure the success of the sustainment plan
    metrics = models.TextField()
    # Field to capture the start date for implementing the sustainment plan
    start_date = models.DateTimeField()
    # Field to capture the end date for implementing the sustainment plan
    end_date = models.DateTimeField()
    # Field to capture the communication plan for ensuring all stakeholders are aware of the sustainment plan and its
    # progress
    communication_plan = models.TextField()
    # # Field to capture the names and roles of the individuals responsible for implementing and managing the
    # # sustainment plan
    # Field to capture the budget allocated for the sustainment plan
    budget = models.TextField()
    # Field to capture any potential risks associated with the sustainment plan and the steps that will be taken to
    # mitigate these risks
    risks = models.TextField()
    mitigation = models.TextField()
    # Field to capture the training and support that will be provided to staff to ensure they are equipped to
    # maintain the improvements made during the QI cqi
    training_and_support = models.TextField()
    # Field to capture the mechanisms in place for receiving feedback from staff, patients, and other stakeholders
    # about the sustainability of the improvements
    feedback_mechanisms = models.TextField()
    # Field to capture the steps that will be taken if the sustainment plan fails to achieve its objectives
    reaction_plan = models.TextField()
    # # Field to specify the user responsible for the objective
    responsible = models.TextField()
    # Field to specify the user accountable for the objective
    accountable = models.TextField()
    # Field to specify the user consulted for the objective
    consulted = models.TextField()
    # Field to specify the user informed about the objective
    informed = models.TextField()
    created_by = models.ForeignKey(CustomUser, blank=True, null=True, default=get_current_user,
                                   on_delete=models.CASCADE)

    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_created']

    def __str__(self):
        qi_project_str = str(self.qi_project) + " - " if self.qi_project else ""
        program_qi_project_str = str(self.program) + " - " if self.program else ""
        subcounty_qi_project_str = str(self.subcounty) + " - " if self.subcounty else ""
        hub_qi_project_str = str(self.hub) + " - " if self.hub else ""
        county_qi_project_str = str(self.county) if self.county else ""

        date_str = self.date_created.strftime('%Y-%m-%d %H:%M:%S')

        return f"{qi_project_str}{program_qi_project_str}{subcounty_qi_project_str}{hub_qi_project_str}{county_qi_project_str} ({date_str})"


class RootCauseImages(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    root_cause_image = models.ImageField(upload_to='images')
    facility = models.ForeignKey(Facilities, on_delete=models.CASCADE, null=True, blank=True)
    program = models.ForeignKey(Program, on_delete=models.CASCADE, null=True, blank=True)
    qi_project = models.ForeignKey(QI_Projects, on_delete=models.CASCADE, null=True, blank=True)
    program_qi_project = models.ForeignKey(Program_qi_projects, on_delete=models.CASCADE, null=True, blank=True)
    subcounty_qi_project = models.ForeignKey(Subcounty_qi_projects, on_delete=models.CASCADE, null=True, blank=True)
    county_qi_project = models.ForeignKey(County_qi_projects, on_delete=models.CASCADE, null=True, blank=True)
    hub_qi_project = models.ForeignKey(Hub_qi_projects, on_delete=models.CASCADE, null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "cqi's images status"
        ordering = ['qi_project', 'subcounty_qi_project', 'county_qi_project', 'hub_qi_project',
                    'program']

    def __str__(self):
        qi_project_str = str(self.qi_project) + " - " if self.qi_project else ""
        program_qi_project_str = str(self.program_qi_project) + " - " if self.program_qi_project else ""
        subcounty_qi_project_str = str(self.subcounty_qi_project) + " - " if self.subcounty_qi_project else ""
        hub_qi_project_str = str(self.hub_qi_project) + " - " if self.hub_qi_project else ""
        county_qi_project_str = str(self.county_qi_project) if self.county_qi_project else ""

        date_str = self.date_created.strftime('%Y-%m-%d %H:%M:%S')

        return f"{qi_project_str}{program_qi_project_str}{subcounty_qi_project_str}{hub_qi_project_str}{county_qi_project_str} ({date_str})"

    def save(self, commit=True, *args, **kwargs):
        if commit:
            image_resize(self.root_cause_image, 500, 500)
        super().save(*args, **kwargs)
