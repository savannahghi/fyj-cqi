from django import forms
from django.forms import ModelForm
from django.utils import timezone

from apps.cqi.models import Facilities
from apps.labpulse.models import Cd4traker, Cd4TestingLabs, Commodities, LabPulseUpdateButtonSettings, ReagentStock


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
    age_unit = forms.ChoiceField(choices=Cd4traker.AGE_UNIT_CHOICES, widget=forms.Select(
        attrs={'class': 'form-control'}))
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Pop the 'user' argument from kwargs
        super(Cd4trakerForm, self).__init__(*args, **kwargs)
        if user and user.groups.filter(name='referring_laboratory_staffs_labpulse').exists():
            # If the user is in the referring_lab_group, make disable all fields
            for field_name in self.fields:
                if field_name != 'tb_lam_results':  # Allow editing only for the 'tb_lam' field
                    self.fields[field_name].disabled = True

    class Meta:
        model = Cd4traker
        exclude = ['created_by', 'modified_by', 'date_dispatched', 'date_updated', 'testing_laboratory','report_type']
        labels = {
            'cd4_count_results': 'CD4 count results',
            'serum_crag_results': 'Serum CrAg Results',
            'reason_for_no_serum_crag': 'Reason for not doing serum CrAg',
            'cd4_percentage': 'CD4 % values',
            'tb_lam_results': 'TB LAM results',
        }

    def save(self, commit=True):
        instance = super(Cd4trakerForm, self).save(commit=False)
        instance.date_dispatched = timezone.now()
        if commit:
            instance.save()
        return instance

    # def clean(self):
    #     cleaned_data = super().clean()
    #
    #     # Check if CD4 test was performed
    #     if cleaned_data.get('cd4_count_results') is not None:
    #         cleaned_data['cd4_reagent_used'] = True
    #
    #     # Check if TB LAM test was performed
    #     if cleaned_data.get('tb_lam_results') is not None:
    #         cleaned_data['tb_lam_reagent_used'] = True
    #
    #     # Check if serum CRAG test was performed
    #     if cleaned_data.get('serum_crag_results') is not None:
    #         cleaned_data['serum_crag_reagent_used'] = True
    #
    #     return cleaned_data


class Cd4TestingLabsForm(forms.Form):
    testing_lab_name = forms.ModelChoiceField(
        queryset=Cd4TestingLabs.objects.all(),
        empty_label="Select Testing Lab ...",
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )
class facilities_lab_Form(forms.Form):
    facility_name = forms.ModelChoiceField(
        queryset=Facilities.objects.all(),
        # queryset=Facilities.objects.filter(fyj_facilities=True),
        empty_label="Select Testing Lab ...",
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )

class Cd4TestingLabForm(ModelForm):
    class Meta:
        model = Cd4TestingLabs
        fields = "__all__"


class LabPulseUpdateButtonSettingsForm(forms.ModelForm):
    hide_button_time = forms.TimeField(
        widget=forms.TimeInput(format='%H:%M'),
        label='Set time to hide update button in LabPulse module',
        help_text='Please select a time after 5pm. (HH:MM)'
    )

    class Meta:
        model = LabPulseUpdateButtonSettings
        fields = ('hide_button_time',)

    def clean_hide_button_time(self):
        hide_button_time = self.cleaned_data['hide_button_time']
        if hide_button_time.hour < 17:
            raise forms.ValidationError("The hide button time must be after 5pm.")
        return hide_button_time

class Cd4trakerManualDispatchForm(ModelForm):
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
    date_dispatched = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Dispatch date",
        required=True
    )

    class Meta:
        model = Cd4traker
        exclude = ['created_by', 'modified_by', 'date_updated', 'testing_laboratory','report_type']
        labels = {
            'cd4_count_results': 'CD4 count results',
            'serum_crag_results': 'Serum CrAg Results',
            'reason_for_no_serum_crag': 'Reason for not doing serum CrAg',
            'cd4_percentage': 'CD4 % values',
            'tb_lam_results': 'TB LAM results',
        }

class CommoditiesForm(ModelForm):
    date_commodity_received = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Date Commodity Received"
    )
    expiry_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Expiry Date",
        required=False
    )

    class Meta:
        model = Commodities
        exclude = ['created_by', 'modified_by', 'date_modified', 'date_created','facility_name']
        labels = {
            'number_received': 'Number of Reagents Received',
            'type_of_reagent': 'Type Of Reagent',
            'received_from': 'Received From',
            'negative_adjustment': 'Negative Adjustment',
            'positive_adjustment': 'Positive Adjustment',
        }
class ReagentStockForm(ModelForm):
    date_commodity_received = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Date Commodity Received"
    )
    expiry_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Expiry Date",
        required=False
    )

    class Meta:
        model = ReagentStock
        exclude = ['created_by', 'modified_by', 'date_modified', 'date_created','facility_name','quantity_used',
                   'remaining_quantity']
        labels = {
            'number_received': 'Number of Reagents Received',
            'type_of_reagent': 'Type Of Reagent',
            'received_from': 'Received From',
            'negative_adjustment': 'Negative Adjustment',
            'positive_adjustment': 'Positive Adjustment',
        }

