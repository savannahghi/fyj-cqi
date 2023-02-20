import datetime

from django.forms import ModelForm, Textarea
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
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="DQA date"
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
    class Meta:
        model = SystemAssessment
        fields = ['description', 'dropdown_option', 'auditor_note', 'supporting_documentation_required']
        widgets = {
            'description': Textarea(attrs={'readonly': 'readonly','rows': '5'}),
            'auditor_note': forms.Textarea(attrs={'size': '40','rows': '5'})
        }

    def clean(self):
        cleaned_data = super().clean()
        for field_name in ['id','modified_by', 'created_at', 'updated_at']:
            if field_name in cleaned_data:
                del cleaned_data[field_name]
        return cleaned_data
    # def clean(self):
    #     cleaned_data = super().clean()
    #     if not all(cleaned_data.values()):
    #         raise forms.ValidationError("All fields are required.")