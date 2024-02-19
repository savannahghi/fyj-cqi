import re

import PyPDF2
import django_filters
from PyPDF2.errors import PdfReadError
from django import forms
from django.core.exceptions import ValidationError

from .models import Author, Category, Conference, Journal, Manuscript, Venue


class ManuscriptForm(forms.ModelForm):
    authors = forms.ModelMultipleChoiceField(
        queryset=Author.objects.all(),
        widget=forms.CheckboxSelectMultiple,
    )
    journal = forms.ModelChoiceField(
        queryset=Journal.objects.all(),
        empty_label="Select Journal ...",
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )
    categories = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        empty_label="Select Category ...",
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )
    publication_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Publication Date",
        required=False
    )
    data_started = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Date Started Writing",
        # required=False
    )
    data_submitted = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Date Submitted",
        required=False
    )

    class Meta:
        model = Manuscript
        fields = '__all__'  # Use all fields from the Manuscript model
        labels = {
            'acceptance_status': 'Accepted?',
            'status': 'Current Status?',
            'journal': 'Journal Name',
            'citations': 'Number of citations so far',
            'pdf_file': 'Upload PDF file here',
            'venue': 'Conference Venue',
        }
        widgets = {
            'keywords': forms.Textarea(attrs={
                'placeholder': "",
                'rows': 4,  # Adjust the number of rows as needed
            }),
        }

        help_texts = {
            'keywords': 'Separate keywords with a comma (,) or semicolon (;)',
        }

    def clean_submission_type(self):
        """
        Custom cleaning method for the 'submission_type' field.

        Dynamically adjusts the 'required' attribute of 'journal' and 'conference' fields
        based on the chosen 'submission_type'.

        Returns:
            str: The cleaned 'submission_type'.
        """
        submission_type = self.cleaned_data.get('submission_type')

        # Make 'journal' and 'conference' required based on 'submission_type'
        if submission_type == 'journal':
            self.fields['journal'].required = True
            self.fields['conference'].required = False
            self.fields['venue'].required = False
        elif submission_type == 'conference':
            self.fields['conference'].required = True
            self.fields['venue'].required = True
            self.fields['journal'].required = False
        else:
            self.fields['journal'].required = False
            self.fields['conference'].required = False
            self.fields['venue'].required = False

        return submission_type

    def clean_keywords(self):
        keywords = self.cleaned_data['keywords']
        keyword_list = """"""
        # Check if the field is not empty
        if keywords:
            # Split the entered keywords by commas or semicolons
            keyword_list = [kw.strip() for kw in re.split(r'[;,]', keywords) if kw.strip()]

            # Optionally, you can enforce a minimum or maximum number of keywords
            # For example, require at least 2 keywords
            if len(keyword_list) < 2:
                raise forms.ValidationError(
                    'Please enter at least 2 keywords separated with a comma (,) or semicolon (;)')

        return '; '.join(keyword_list)

    def clean(self):
        cleaned_data = super().clean()
        data_started = cleaned_data.get('data_started')
        data_submitted = cleaned_data.get('data_submitted')
        publication_date = cleaned_data.get('publication_date')

        if data_started and data_submitted and data_started >= data_submitted:
            self.add_error('data_started', "The 'Date started' should be before the 'Date submitted'.")
            self.add_error('data_submitted', "The 'Date started' should be before the 'Date submitted'.")

        if data_submitted and publication_date and data_submitted >= publication_date:
            self.add_error('data_submitted', "The 'Date submitted' should not be after the 'Publication date'.")
            self.add_error('publication_date', "The 'Date submitted' should not be after the 'Publication date'.")

        if data_started and publication_date and data_started >= publication_date:
            self.add_error('data_started', "The 'Date started' should be before the 'Publication date'.")
            self.add_error('publication_date', "The 'Date started' should be before the 'Publication date'.")

        return cleaned_data


class ManuscriptFilter(django_filters.FilterSet):
    title_contains = django_filters.CharFilter(lookup_expr='icontains', field_name='title')
    abstract_contains = django_filters.CharFilter(lookup_expr='icontains', field_name='abstract')
    keywords_contains = django_filters.CharFilter(lookup_expr='icontains', field_name='keywords')
    status_choice = django_filters.ChoiceFilter(choices=Manuscript.STATUS_CHOICES, field_name='status')
    acceptance_status_choice = django_filters.ChoiceFilter(choices=Manuscript.ACCEPTANCE_STATUS_CHOICES,
                                                           field_name='acceptance_status')
    journal_choice = django_filters.ModelChoiceFilter(queryset=Journal.objects.all(), field_name='journal')
    venue_choice = django_filters.ModelChoiceFilter(queryset=Venue.objects.all(), field_name='venue',label='Conference Venue')
    conference_choice = django_filters.ModelChoiceFilter(queryset=Conference.objects.all(), field_name='conference')
    categories_choice = django_filters.ModelChoiceFilter(queryset=Category.objects.all(), field_name='categories')
    citations_lte = django_filters.CharFilter(field_name="citations", lookup_expr="lte", label='Citations <=')
    citations_gte = django_filters.CharFilter(field_name="citations", lookup_expr="gte", label='Citations >=')
    start_date = django_filters.DateFilter(field_name="data_started", lookup_expr="gte",
                                           label='From (Date started writing)')
    end_date = django_filters.DateFilter(field_name="data_started", lookup_expr="lte",
                                         label='To (Date started writing)')
    data_submitted_from = django_filters.DateFilter(field_name="data_submitted", lookup_expr="gte",
                                                    label='From (Date Submitted)')
    data_submitted_to = django_filters.DateFilter(field_name="data_submitted", lookup_expr="lte",
                                                  label='To (Date Submitted))')
    authors = django_filters.ModelMultipleChoiceFilter(
        queryset=Author.objects.all(),
        widget=forms.CheckboxSelectMultiple,

    )

    class Meta:
        model = Manuscript
        fields = ['title_contains', 'status']
