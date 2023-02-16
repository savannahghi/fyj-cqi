import datetime

from django.db.models import Count
from django.forms import ModelForm
from django import forms
from django_select2.forms import ModelSelect2Widget

from dqa.models import DataVerification, Period, DQAWorkPlan, Indicators, SystemAssessment
from project.models import Facilities


class DataVerificationForm(ModelForm):
    # TODO: INCLUDE DJANGO-SELECT2 IN ALL THE DROP DOWNS
    facility_name = forms.ModelChoiceField(
        queryset=Facilities.objects.all(),
        empty_label="Select facility",
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )
    indicator = forms.ChoiceField(choices=DataVerification.INDICATOR_CHOICES,
                                  widget=forms.Select(attrs={'class': 'form-control select2'}))

    class Meta:
        model = DataVerification
        fields = "__all__"
        exclude = ['created_by', 'quarter_year', 'Number tested Positive _Total']

    # This is the constructor method of the form
    def __init__(self, *args, **kwargs):
        # Call the parent constructor method
        super().__init__(*args, **kwargs)
        # Loop through all the fields in the form
        for field in self.fields:
            # Set the label of each field to False
            self.fields[field].label = False


class PeriodForm(ModelForm):
    class Meta:
        model = Period
        fields = "__all__"


class QuarterSelectionForm(forms.Form):
    quarter = forms.ChoiceField(
        choices=[
            ('Qtr1', 'Qtr1'),
            ('Qtr2', 'Qtr2'),
            ('Qtr3', 'Qtr3'),
            ('Qtr4', 'Qtr4'),
        ]
    )


class YearSelectionForm(forms.Form):
    current_year = datetime.datetime.now().year
    YEAR_CHOICES = [(str(x), str(x)) for x in range(2021, current_year + 1)]
    year = forms.ChoiceField(
        choices=YEAR_CHOICES
    )


class DateSelectionForm(forms.Form):
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'})
    )


class FacilitySelectionForm(forms.Form):
    # facilities = forms.ModelChoiceField(
    #     queryset=Facilities.objects.all(),
    #     empty_label="Select facility",
    #     widget=forms.Select(attrs={'class': 'form-control'}),
    # )
    facilities = forms.ModelChoiceField(
        queryset=Facilities.objects.all(),
        empty_label="Select facility",
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )


class DQAWorkPlanForm(ModelForm):
    class Meta:
        model = DQAWorkPlan
        fields = '__all__'
        exclude = ['facility_name', 'quarter_year', 'created_by']


class SystemAssessmentForm(ModelForm):
    facility_name = forms.ModelChoiceField(
        queryset=Facilities.objects.all(),
        empty_label="Select facility",
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )

    class Meta:
        model = SystemAssessment
        fields = "__all__"
        exclude = ['calculations', 'created_by', 'modified_by', 'quarter_year', 'facility_name']
