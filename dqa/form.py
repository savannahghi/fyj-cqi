from django.forms import ModelForm
from django import forms

from dqa.models import DataVerification, Period
from project.models import Facilities


class DataVerificationForm(ModelForm):
    class Meta:
        model = DataVerification
        fields = "__all__"
        exclude = ['created_by']


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
    YEAR_CHOICES = [(str(x), str(x)) for x in range(2021, 2099)]
    year = forms.ChoiceField(
        choices=YEAR_CHOICES
    )


class FacilitySelectionForm(forms.Form):
    facilities = forms.ModelChoiceField(
        queryset=Facilities.objects.all(),
        empty_label="Select facility",
        widget=forms.Select(attrs={'class': 'form-control'}),
    )

