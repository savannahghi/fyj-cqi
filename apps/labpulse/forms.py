from django import forms
from django.forms import ModelForm

from apps.cqi.models import Facilities
from apps.labpulse.models import Cd4traker, Cd4TestingLabs


class Cd4trakerForm(ModelForm):
    facility_name = forms.ModelChoiceField(
        queryset=Facilities.objects.all(),
        empty_label="Select facility",
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )
    date_of_collection = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Collection date"
    )
    date_of_testing = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Testing date",
        required=False
    )
    date_sample_received = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Date sample was received"
    )

    class Meta:
        model = Cd4traker
        exclude = ['created_by', 'modified_by', 'date_dispatched', 'date_updated', 'testing_laboratory']
        labels = {
            'cd4_count_results': 'CD4 count results',
            'serum_crag_results': 'Serum CRAG results',
            'reason_for_no_serum_crag': 'Reason for not doing serum CRAG',
            'cd4_percentage': 'CD4 % values',
            'tb_lam_results': 'TB-LAM results',
        }


class Cd4TestingLabsForm(forms.Form):
    testing_lab_name = forms.ModelChoiceField(
        queryset=Cd4TestingLabs.objects.all(),
        empty_label="Select Testing Lab ...",
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )


class Cd4TestingLabForm(ModelForm):
    class Meta:
        model = Cd4TestingLabs
        fields = "__all__"
