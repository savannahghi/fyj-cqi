import datetime

from django.forms import ModelForm, NumberInput, Select, Textarea
from django import forms

from apps.dqa.models import CareTreatment, Cqi, DataVerification, Gbv, Hts, Period, DQAWorkPlan, Pharmacy, Prep, \
    SystemAssessment, \
    AuditTeam, \
    Tb, UpdateButtonSettings, Vmmc
from apps.cqi.models import Facilities, Hub, Sub_counties, Counties, Program


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
        ],
        widget=forms.Select(attrs={'id': 'quarter-select'})
    )


class YearSelectionForm(forms.Form):
    current_year = datetime.datetime.now().year
    YEAR_CHOICES = [(str(x), str(x)) for x in range(2021, current_year + 2)]
    year = forms.ChoiceField(
        choices=YEAR_CHOICES,
        label="FY",
        widget=forms.Select(attrs={'id': 'year-select'})
    )


class DateSelectionForm(forms.Form):
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="DQA date"
    )


# class FacilitySelectionForm(forms.Form):
#     name = forms.ModelChoiceField(
#         queryset=Facilities.objects.all(),
#         empty_label="Select Facility",
#         widget=forms.Select(attrs={'class': 'form-control select2'}),
#         required=False,
#         initial=None  # Add this line to set the initial value to None
#     )
#
#     def __init__(self, *args, selected_year=None, selected_quarter=None, model_to_check=None, **kwargs):
#         initial = kwargs.get('initial', {})
#         super().__init__(*args, **kwargs)
#         self.fields['name'].initial = initial.get('name')
#
#         # Only filter the queryset if both selected_year and selected_quarter are provided and model_to_check is
#         # provided
#         if selected_year and selected_quarter and model_to_check:
#             # Get the IDs of facilities that have related records in the model_to_check
#             facility_ids = model_to_check.objects.filter(
#                 quarter_year__quarter_year=f"{selected_quarter}-{selected_year[-2:]}"
#             ).values_list('facility_name_id', flat=True)
#
#             # Update the queryset with the filtered facilities
#             self.fields['name'].queryset = Facilities.objects.filter(id__in=facility_ids)
#
#             # Preselect the first facility name if it exists
#             if self.fields['name'].queryset.exists():
#                 self.fields['name'].initial = self.fields['name'].queryset.first()
class BaseForm(forms.Form):
    def __init__(self, *args, model_to_check=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.model_to_check = model_to_check


class FacilitySelectionForm(BaseForm):
    name = forms.ModelChoiceField(
        queryset=Facilities.objects.all(),
        empty_label="Select Facility",
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        required=False,
        initial=None
    )

    def __init__(self, *args, selected_year=None, selected_quarter=None, **kwargs):
        super().__init__(*args, **kwargs)
        initial = kwargs.get('initial', {})
        self.fields['name'].initial = initial.get('name')

        # Only filter the queryset if both selected_year and selected_quarter are provided and model_to_check is provided
        if selected_year and selected_quarter and self.model_to_check:
            # Check if model_to_check is a single model or a list of models
            if isinstance(self.model_to_check, list):
                # Get the IDs of facilities that have related records in any of the models_to_check
                facility_ids = set()
                for model in self.model_to_check:
                    facility_ids.update(model.objects.filter(
                        quarter_year__quarter_year=f"{selected_quarter}-{selected_year[-2:]}"
                    ).values_list('facility_name_id', flat=True))
            else:
                # Get the IDs of facilities that have related records in the model_to_check
                facility_ids = self.model_to_check.objects.filter(
                    quarter_year__quarter_year=f"{selected_quarter}-{selected_year[-2:]}"
                ).values_list('facility_name_id', flat=True)

            # Update the queryset with the filtered facilities
            self.fields['name'].queryset = Facilities.objects.filter(id__in=facility_ids)

            # Preselect the first facility name if it exists
            if self.fields['name'].queryset.exists():
                self.fields['name'].initial = self.fields['name'].queryset.first()




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
            'description': Textarea(attrs={'readonly': 'readonly', 'rows': '5','class': 'my-textarea',}),
            'auditor_note': forms.Textarea(attrs={'size': '40', 'rows': '5','class': 'auditor-textarea',})
        }

    # This is the constructor method of the form
    def __init__(self, *args, **kwargs):
        # Call the parent constructor method
        super().__init__(*args, **kwargs)
        # Loop through all the fields in the form
        for field in self.fields:
            # Set the label of each field to False
            self.fields[field].label = False

    def clean(self):
        cleaned_data = super().clean()
        for field_name in ['id', 'modified_by', 'created_at', 'updated_at']:
            if field_name in cleaned_data:
                del cleaned_data[field_name]
        return cleaned_data
    # def clean(self):
    #     cleaned_data = super().clean()
    #     if not all(cleaned_data.values()):
    #         raise forms.ValidationError("All fields are required.")


class AuditTeamForm(ModelForm):
    class Meta:
        model = AuditTeam
        exclude = ['facility_name', 'modified_by', 'created_by', 'quarter_year']
        labels = {
            'name': 'Name (First and Last name)',
        }


class UpdateButtonSettingsForm(forms.ModelForm):
    class Meta:
        model = UpdateButtonSettings
        fields = ('hide_button_time',)
        widgets = {'hide_button_time': forms.TimeInput(format='%H:%M')}
        labels = {
            'hide_button_time': 'Time to hide update button in DQA module',
        }

    def clean_hide_button_time(self):
        hide_button_time = self.cleaned_data['hide_button_time']
        if hide_button_time.hour < 17:
            raise forms.ValidationError("The hide button time must be after 5pm.")
        return hide_button_time


class SubcountySelectionForm(forms.Form):
    subcounty = forms.ModelChoiceField(
        queryset=Sub_counties.objects.all(),
        empty_label="Select sub-county",
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        initial=None  # Add this line to set the initial value to None
    )

    # def __init__(self, *args, **kwargs):
    #     initial = kwargs.get('initial', {})
    #     print('Initial value:', initial.get('name'))
    #     super().__init__(*args, **kwargs)
    #     self.fields['name'].initial = initial.get('name')


class HubSelectionForm(forms.Form):
    hub = forms.ModelChoiceField(
        queryset=Hub.objects.all(),
        empty_label="Select Hub",
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        initial=None  # Add this line to set the initial value to None
    )


class CountySelectionForm(forms.Form):
    county = forms.ModelChoiceField(
        queryset=Counties.objects.all(),
        empty_label="Select county",
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        initial=None  # Add this line to set the initial value to None
    )


class ProgramSelectionForm(forms.Form):
    program = forms.ModelChoiceField(
        queryset=Program.objects.all(),
        empty_label="Select program",
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        initial=None  # Add this line to set the initial value to None
    )


class BaseSqaForm(forms.ModelForm):
    class Meta:
        exclude = ['created_by', 'modified_by', 'quarter_year', 'facility_name']
        abstract = True
        widgets = {
            'description': Textarea(attrs={'readonly': 'readonly', 'class': 'my-textarea', 'rows': '5'}),
            'verification': Textarea(attrs={'readonly': 'readonly', 'class': 'my-textarea', 'rows': '4'}),
            'numerator_description': Textarea(attrs={'readonly': 'readonly', 'class': 'my-textarea', 'rows': '5'}),
            'denominator_description': Textarea(attrs={'readonly': 'readonly', 'class': 'my-textarea', 'rows': '5'}),

            'numerator': NumberInput(attrs={'class': 'numerator-field', 'required': 'required'}),
            'denominator': NumberInput(attrs={'class': 'denominator-field', 'required': 'required'}),
            'dropdown_option': Select(
                attrs={'id': 'dropdown_option', 'class': 'dropdown-option-field', 'required': 'required'}),
            'auditor_note': Textarea(attrs={'id': 'auditor_note', 'class': 'auditor-textarea', 'rows': '5'}),

        }


class BaseForm(BaseSqaForm):
    class Meta(BaseSqaForm.Meta):
        abstract = True
        # Common meta options go here

    def __init__(self, *args, **kwargs):
        # Call the parent constructor method
        super().__init__(*args, **kwargs)
        # Loop through all the fields in the form
        for field in self.fields:
            # Set the label of each field to False
            self.fields[field].label = False


class GbvForm(BaseForm):
    class Meta(BaseForm.Meta):
        model = Gbv


class VmmcForm(BaseForm):
    class Meta(BaseForm.Meta):
        model = Vmmc


class HtsForm(BaseForm):
    class Meta(BaseForm.Meta):
        model = Hts


class PrepForm(BaseForm):
    class Meta(BaseForm.Meta):
        model = Prep


class TbForm(BaseForm):
    class Meta(BaseForm.Meta):
        model = Tb


class CareTreatmentForm(BaseForm):
    class Meta(BaseForm.Meta):
        model = CareTreatment


class PharmacyForm(BaseForm):
    class Meta(BaseForm.Meta):
        model = Pharmacy


class CqiForm(BaseForm):
    class Meta(BaseForm.Meta):
        model = Cqi
