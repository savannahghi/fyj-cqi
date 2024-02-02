# forms.py

from django import forms
from multiupload.fields import MultiFileField


class DateFilterForm(forms.Form):
    from_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    to_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))


class FileUploadForm(forms.Form):
    file = forms.FileField()
class MultipleUploadForm(forms.Form):
    files = MultiFileField(min_num=1, max_num=12,
                           # max_file_size=1024 * 1024 * 5
                           )  # Adjust max_num and max_file_size as needed

class DataFilterForm(forms.Form):
    CHOICES = [
        ('All', 'All'),
        ('PMTCT', 'PMTCT'),
    ]
    filter_option = forms.ChoiceField(choices=CHOICES)
