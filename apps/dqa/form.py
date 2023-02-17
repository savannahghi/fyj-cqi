import datetime

from django.forms import ModelForm
from django import forms

from apps.dqa.models import DataVerification, Period, DQAWorkPlan, SystemAssessment
from apps.cqi.models import Facilities


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
    name = forms.ModelChoiceField(
        queryset=Facilities.objects.all(),
        empty_label="Select facility",
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )


class DQAWorkPlanForm(ModelForm):
    class Meta:
        model = DQAWorkPlan
        fields = '__all__'
        exclude = ['facility_name', 'quarter_year', 'created_by']


# class SystemAssessmentForm(forms.ModelForm):
#     name = forms.ModelChoiceField(
#         queryset=Facilities.objects.all(),
#         empty_label="Select facility",
#         widget=forms.Select(attrs={'class': 'form-control select2'}),
#     )
#     class Meta:
#         model = SystemAssessment
#         fields = [
#             'description',
#             'dropdown_option',
#             'auditor_note',
#             'supporting_documentation_required',
#         ]
#
#     description = forms.CharField(disabled=True)

class SystemAssessmentForm(ModelForm):
    name = forms.ModelChoiceField(
        queryset=Facilities.objects.all(),
        empty_label="Select facility",
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )

    class Meta:
        model = SystemAssessment
        # fields = "__all__"
        exclude = ['calculations', 'created_by', 'modified_by', 'quarter_year', 'facility_name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk is None and 'initial' in kwargs:
            self.fields['description'].initial = kwargs['initial']['description']

    # def save(self, commit=True):
    #     instances = super().save(commit=False)
    #     for instance in instances:
    #         dropdown_option = instance.dropdown_option
    #         if dropdown_option == "Yes":
    #             instance.calculations = 3
    #         elif dropdown_option == "Partly":
    #             instance.calculations = 2
    #         elif dropdown_option == "No":
    #             instance.calculations = 1
    #         if commit:
    #             instance.save()
    #     return instances

    # def clean(self):
    #     cleaned_data = super().clean()
    #     dropdown_option = cleaned_data.get('dropdown_option')
    #     if dropdown_option == 'Yes':
    #         cleaned_data['calculations'] = 3
    #     elif dropdown_option == 'Partly':
    #         cleaned_data['calculations'] = 2
    #     elif dropdown_option == 'No':
    #         cleaned_data['calculations'] = 1
    #     return cleaned_data
