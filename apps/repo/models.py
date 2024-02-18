from ckeditor.fields import RichTextField
from django.db import models
from django.template.defaultfilters import filesizeformat

from apps.account.models import CustomUser
from apps.labpulse.models import BaseModel


class Author(BaseModel):
    first_name = models.CharField(max_length=250)
    last_name = models.CharField(max_length=250)

    class Meta:
        unique_together = (("first_name","last_name"),)
        ordering = ['first_name']
        verbose_name_plural = "Authors"
    def __str__(self):
        return f"{self.first_name.title()} {self.last_name.upper()[0]}."



class Category(BaseModel):
    name = models.CharField(max_length=250)

    class Meta:
        unique_together = (('name'),)
        ordering = ['name']
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Journal(BaseModel):
    name = models.CharField(max_length=250)

    class Meta:
        unique_together = (('name'),)
        ordering = ['name']
        verbose_name_plural = "Journals"

    def __str__(self):
        return self.name
class Conference(BaseModel):
    name = models.CharField(max_length=250)

    class Meta:
        unique_together = (('name'),)
        ordering = ['name']
        verbose_name_plural = "Conferences"

    def __str__(self):
        return self.name

class Venue(BaseModel):
    name = models.CharField(max_length=250)

    class Meta:
        unique_together = (('name'),)
        ordering = ['name']
        verbose_name_plural = "Conference Venues"

    def __str__(self):
        return self.name


class Manuscript(BaseModel):
    STATUS_CHOICES = [
        ('draft', 'In Development'),
        ('submitted', 'Submitted'),
        ('published', 'Published'),
    ]
    ACCEPTANCE_STATUS_CHOICES = [
        ('yes', 'Yes'),
        ('no', 'No'),
    ]
    SUBMISSION_CHOICES = [
        ('conference', 'Conference'),
        ('journal', 'Journal'),
    ]

    title = models.CharField(max_length=255,null=True, blank=True)
    abstract = RichTextField(null=True, blank=True)
    authors = models.ManyToManyField(Author)
    publication_date = models.DateField(null=True, blank=True)
    keywords = models.TextField(null=True, blank=True)
    pdf_file = models.FileField(upload_to='manuscripts/', null=True, blank=True)
    file_size = models.PositiveIntegerField(default=0, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', null=True, blank=True)
    acceptance_status = models.CharField(max_length=20, choices=ACCEPTANCE_STATUS_CHOICES, default='no', null=True, blank=True)
    submission_type  = models.CharField(max_length=20, choices=SUBMISSION_CHOICES, null=True, blank=True)
    number_of_pages = models.PositiveIntegerField(default=0, null=True, blank=True)
    journal = models.ForeignKey(Journal, on_delete=models.SET_NULL, null=True, blank=True)
    categories = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    conference = models.ForeignKey(Conference, on_delete=models.SET_NULL, null=True, blank=True)
    venue = models.ForeignKey(Venue, on_delete=models.SET_NULL, null=True, blank=True)

    # Metrics
    citations = models.PositiveIntegerField(default=0, null=True, blank=True)
    downloads = models.PositiveIntegerField(default=0, null=True, blank=True)
    views = models.PositiveIntegerField(default=0, null=True, blank=True)
    # impact_factor = models.FloatField(default=0.0)
    # h_index = models.PositiveIntegerField(default=0)
    # i10_index = models.PositiveIntegerField(default=0)

    # Research-Specific Fields
    methodology = models.TextField(null=True, blank=True)
    results = models.TextField(null=True, blank=True)
    conclusion = models.TextField(null=True, blank=True)

    # Monitoring and Evaluation-Specific Fields
    indicators = models.TextField(null=True, blank=True)
    findings = models.TextField(null=True, blank=True)

    # Additional Fields for Unpublished Manuscripts
    data_started = models.DateField(null=True, blank=True)
    data_submitted = models.DateField(null=True, blank=True)

    # Other Fields
    version_control = models.PositiveIntegerField(default=1, null=True, blank=True)
    license = models.CharField(max_length=50, null=True, blank=True)
    source = models.CharField(max_length=100, null=True, blank=True)

    def is_published(self):
        return self.status == 'published'

    @property
    def is_data_required(self):
        # Check if data-related fields are required based on status
        return self.status in ['submitted', 'published']

    @property
    def is_acceptance_status_required(self):
        # Check if acceptance_status is required based on status
        return self.status == 'published'

    def formatted_file_size(self):
        return filesizeformat(self.file_size)

    class Meta:
        unique_together = (('number_of_pages', 'title'),)
        ordering = ['title', 'date_created', 'status']
        verbose_name_plural = "Manuscripts"

    def __str__(self):
        return f"{self.title} ({self.status}) date created: {self.date_created}"
