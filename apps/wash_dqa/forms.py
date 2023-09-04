import datetime

from django import forms
from django.forms import ModelForm, Textarea

from apps.wash_dqa.models import DataCollectionReportingManagement, DataConcordance, DataQualityAssessment, \
    DataQualitySystems, \
    Documentation, Period, Ward, WashAuditTeam, WashDQAWorkPlan


# class DocumentationForm(ModelForm):
#     class Meta:
#         model=Documentation
#         fields = ['description', 'dropdown_option', 'auditor_note',
#                   'verification_means',
#                   'staff_involved'
#                   ]
#         widgets = {
#             'description': Textarea(attrs={'readonly': 'readonly', 'rows': '6'}),
#             'verification_means': Textarea(attrs={'readonly': 'readonly', 'rows': '6'}),
#             'staff_involved': Textarea(attrs={'readonly': 'readonly', 'rows': '6'}),
#             'auditor_note': forms.Textarea(attrs={'size': '40', 'rows': '6'})
#         }
#
#
#         # This is the constructor method of the form
#
#     def __init__(self, *args, **kwargs):
#         # Call the parent constructor method
#         super().__init__(*args, **kwargs)
#         # Loop through all the fields in the form
#         for field in self.fields:
#             # Set the label of each field to False
#             self.fields[field].label = False
        # # If the user is in the referring_lab_group, make disable all fields
        # for field_name in self.fields:
        #     if field_name != 'auditor_note' and field_name != 'dropdown_option':  # Allow editing only for the 'tb_lam' field
        #         self.fields[field_name].disabled = True

    # def clean(self):
    #     cleaned_data = super().clean()
    #     for field_name in ['id', 'modified_by', 'date_created', 'date_modified']:
    #         if field_name in cleaned_data:
    #             del cleaned_data[field_name]
    #     return cleaned_data

class CommonForm(ModelForm):
    class Meta:
        fields = ['description',  'auditor_note',
                  # 'verification_means',
                  # 'staff_involved'
                  ]
        widgets = {
            'description': Textarea(attrs={'readonly': 'readonly', 'rows': '7'}),
            # 'verification_means': Textarea(attrs={'readonly': 'readonly', 'rows': '7'}),
            # 'staff_involved': Textarea(attrs={'readonly': 'readonly', 'rows': '7'}),
            'auditor_note': forms.Textarea(attrs={'size': '40', 'rows': '7'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].label = False

    def clean(self):
        cleaned_data = super().clean()
        for field_name in ['id', 'modified_by', 'date_created', 'date_modified']:
            if field_name in cleaned_data:
                del cleaned_data[field_name]
        return cleaned_data
class DqaAssessmentForm(CommonForm):
    class Meta(CommonForm.Meta):
        fields = CommonForm.Meta.fields + ['verification_means', 'staff_involved','dropdown_option',]
        widgets = {
            **CommonForm.Meta.widgets,
            'verification_means': forms.Textarea(attrs={'readonly': 'readonly', 'rows': '7'}),
            'staff_involved': forms.Textarea(attrs={'readonly': 'readonly', 'rows': '7'}),
        }


class DataQualityAssessmentForm(CommonForm):
    class Meta(CommonForm.Meta):
        model = DataQualityAssessment
        fields = CommonForm.Meta.fields + ['number_trained', 'number_access_basic_water',
                                           'number_access_safe_water','number_community_open_defecation',
                                           'number_access_basic_sanitation','number_access_safe_sanitation',
                                           'number_access_basic_sanitation_institutions']
        widgets = {
            'description': Textarea(attrs={'readonly': 'readonly', 'rows': '8','style': 'font-size: 12px'}),
            'auditor_note': forms.Textarea(attrs={'size': '40', 'rows': '7'})
        }

class DocumentationForm(DqaAssessmentForm):
    class Meta(DqaAssessmentForm.Meta):
        model = Documentation

class DataQualityForm(DqaAssessmentForm):
    class Meta(DqaAssessmentForm.Meta):
        model = DataQualitySystems

class DataCollectionForm(DqaAssessmentForm):
    class Meta(DqaAssessmentForm.Meta):
        model = DataCollectionReportingManagement



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
        choices=YEAR_CHOICES,
        label="FY"
    )


class DateSelectionForm(forms.Form):
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="DQA date"
    )

class WardSelectionForm(forms.Form):
    name = forms.ModelChoiceField(
        queryset=Ward.objects.all(),
        empty_label="Select ward",
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        initial=None , # Add this line to set the initial value to None
        label="Ward"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].initial = kwargs.get('initial', {}).get('name')

class DataConcordanceForm(ModelForm):
    # TODO: INCLUDE DJANGO-SELECT2 IN ALL THE DROP DOWNS
    ward_name = forms.ModelChoiceField(
        queryset=Ward.objects.all(),
        empty_label="Select ward",
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        initial=None,  # Add this line to set the initial value to None
        label="Ward"
    )
    indicator = forms.ChoiceField(choices=DataConcordance.INDICATOR_CHOICES,
                                  widget=forms.Select(attrs={'class': 'form-control select2'}))

    class Meta:
        model = DataConcordance
        exclude = ['created_by', 'quarter_year']

    # This is the constructor method of the form
    def __init__(self, *args, **kwargs):
        # Call the parent constructor method
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if "field" in field_name:
                field.label = False

class DataConcordanceFormUpdate(DataConcordanceForm):
    # This is the constructor method of the form
    def __init__(self, *args, **kwargs):
        # Call the parent constructor method
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.label = False

class AuditTeamForm(ModelForm):
    class Meta:
        model = WashAuditTeam
        exclude = ['ward_name', 'modified_by', 'created_by', 'quarter_year']
        labels = {
            'name': 'Name (First and Last name)',
        }

class WashDQAWorkPlanForm(ModelForm):
    due_complete_by = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="DQA date"
    )
    class Meta:
        model = WashDQAWorkPlan
        # fields = '__all__'
        exclude = ['ward_name', 'quarter_year', 'created_by',
                   # 'dqa_date'
                   ]
    def __init__(self, *args, **kwargs):
        # Call the parent constructor method
        super().__init__(*args, **kwargs)
        for field_name in self.fields:
            if field_name == 'dqa_date':  # Allow editing only for the 'tb_lam' field
                self.fields[field_name].disabled = True