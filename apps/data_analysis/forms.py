# forms.py

from django import forms


class DateFilterForm(forms.Form):
    from_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    to_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))


class FileUploadForm(forms.Form):
    file = forms.FileField()

class DataFilterForm(forms.Form):
    CHOICES = [
        ('All', 'All'),
        ('PMTCT', 'PMTCT'),
    ]
    filter_option = forms.ChoiceField(choices=CHOICES)
