from django import forms
from django.forms import ModelForm

from apps.pmtct.models import PatientDetails,  RiskCategorizationTrial
from apps.cqi.models import Facilities


class PatientDetailsForm(ModelForm):
    facility_name = forms.ModelChoiceField(
        queryset=Facilities.objects.all(),
        empty_label="Select facility",
        widget=forms.Select(attrs={'class': 'form-control select2 input-sm'}),
    )

    class Meta:
        model = PatientDetails
        exclude = ['age', 'edd', 'gestation_by_age']


# class RiskCategorizationForm(ModelForm):
#     pmtct_mother = forms.ModelChoiceField(queryset=PatientDetails.objects.all(), required=False)
#
#     class Meta:
#         model = RiskCategorization
#         fields = "__all__"
#         exclude = ['id']
#
#     # This is the constructor method of the form
#     def __init__(self, *args, **kwargs):
#         # Call the parent constructor method
#         super().__init__(*args, **kwargs)
#         # Loop through all the fields in the form
#         for field in self.fields:
#             # Set the label of each field to False
#             self.fields[field].label = False


class RiskCategorizationTrialForm(ModelForm):
    # pmtct_mother = forms.ModelChoiceField(queryset=PatientDetails.objects.all(), required=False)
    class Meta:
        model = RiskCategorizationTrial
        fields = "__all__"

    # This is the constructor method of the form
    def __init__(self, *args, **kwargs):
        # Call the parent constructor method
        super().__init__(*args, **kwargs)
        # Loop through all the fields in the form
        for field in self.fields:
            # Set the label of each field to False
            self.fields[field].label = False
