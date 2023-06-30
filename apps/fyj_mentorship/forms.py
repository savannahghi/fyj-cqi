from django.forms import ModelForm, Textarea
from django import forms

from apps.cqi.models import Facilities
from apps.fyj_mentorship.models import FyjStaffDetails, FyjCarders, FacilityStaffCarders, FacilityStaffDetails, \
    ProgramAreas, Introduction, IdentificationGaps, PrepareCoachingSession, CoachingSession, FollowUp, \
    MentorshipWorkPlan
from apps.pharmacy.forms import BaseReportForm, BaseForm


class FyjStaffDetailsForm(ModelForm):
    class Meta:
        model = FyjStaffDetails
        exclude = ['created_by', 'modified_by', 'date_created', 'date_updated', 'name']
        fields = "__all__"


class FyjCardersForm(ModelForm):
    class Meta:
        model = FyjCarders
        exclude = ['created_by', 'modified_by', 'date_created', 'date_updated']


class FacilityStaffCardersForm(ModelForm):
    # facility_name = forms.ModelChoiceField(
    #     queryset=Facilities.objects.all(),
    #     empty_label="Select facility",
    #     widget=forms.Select(attrs={'class': 'form-control select2'}),
    #     initial=None  # Add this line to set the initial value to None
    # )
    class Meta:
        model = FacilityStaffCarders
        exclude = ['created_by', 'modified_by', 'date_created', 'date_updated']
        # labels = {
        #     'staff_name': 'First name and Last name',
        # }


class FacilityStaffDetailsForm(ModelForm):
    facility_name = forms.ModelChoiceField(
        queryset=Facilities.objects.all(),
        empty_label="Select facility",
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        initial=None,  # Add this line to set the initial value to None
    )

    class Meta:
        model = FacilityStaffDetails
        exclude = ['created_by', 'modified_by', 'date_created', 'date_updated']
        labels = {
            'staff_name': 'First name and Last name',
        }


class ProgramAreasForm(ModelForm):
    # program_area = forms.ModelChoiceField(
    #     queryset=ProgramAreas.objects.all(),
    #     empty_label="Select program area",
    #     widget=forms.Select(attrs={'class': 'form-control select2'}),
    #     initial=None  # Add this line to set the initial value to None
    # )
    class Meta:
        model = ProgramAreas
        exclude = ['created_by', 'modified_by', 'date_created', 'date_updated']
        # labels = {
        #     'staff_name': 'First name and Last name',
        # }


# class IntroductionForm(ModelForm):
#     facility_name = forms.ModelChoiceField(
#         queryset=Facilities.objects.all(),
#         empty_label="Select facility",
#         widget=forms.Select(attrs={'class': 'form-control select2'}),
#         initial=None  # Add this line to set the initial value to None
#     )
#
#     class Meta:
#         model = Introduction
#         exclude = ['created_by', 'modified_by', 'date_created', 'date_updated']
# labels = {
#     'staff_name': 'First name and Last name',
# }


# class IntroductionForm(BaseReportForm):
#     class Meta(BaseReportForm.Meta):
#         model = Introduction
#         widgets = {
#             'description': Textarea(attrs={'readonly': 'readonly', 'rows': '4',
#                                            'style': 'width: 400px; font-weight: bold; background-color: #6c757d;color: '
#                                                     'white; resize: none;padding: 8px; border: none; box-shadow: none;'
#                                                     'border-radius: 20px;'}),
#             'comments': forms.Textarea(attrs={'size': '40', 'rows': '3'})
#         }
#
#
# class IdentificationGapsForm(BaseReportForm):
#     class Meta(BaseReportForm.Meta):
#         model = IdentificationGaps
#         widgets = {
#             'description': Textarea(attrs={'readonly': 'readonly', 'rows': '4',
#                                            'style': 'width: 400px; font-weight: bold; background-color: #6c757d;color: '
#                                                     'white; resize: none;padding: 8px; border: none; box-shadow: none;'
#                                                     'border-radius: 20px;'}),
#             'comments': forms.Textarea(attrs={'size': '40', 'rows': '3'})
#         }
#
#
# class PrepareCoachingSessionForm(BaseReportForm):
#     class Meta(BaseReportForm.Meta):
#         model = PrepareCoachingSession
#         widgets = {
#             'description': Textarea(attrs={'readonly': 'readonly', 'rows': '4',
#                                            'style': 'width: 400px; font-weight: bold; background-color: #6c757d;color: '
#                                                     'white; resize: none;padding: 8px; border: none; box-shadow: none;'
#                                                     'border-radius: 20px;'}),
#             'comments': forms.Textarea(attrs={'size': '40', 'rows': '3'})
#         }
# from apps.pharmacy.forms import BaseReportForm

class BaseReportSubForm(BaseReportForm):
    class Meta(BaseReportForm.Meta):
        widgets = {
            'description': Textarea(attrs={'readonly': 'readonly', 'rows': '5',
                                           'style': 'width: 400px; font-weight: bold; background-color: #6c757d;color: '
                                                    'white; resize: none;padding: 8px; border: none; box-shadow: none;'
                                                    'border-radius: 20px;'}),
            'comments': forms.Textarea(attrs={'size': '40', 'rows': '4'})
        }


class IntroductionForm(BaseReportSubForm):
    class Meta(BaseReportSubForm.Meta):
        model = Introduction


class IdentificationGapsForm(BaseReportSubForm):
    class Meta(BaseReportSubForm.Meta):
        model = IdentificationGaps


class PrepareCoachingSessionForm(BaseReportSubForm):
    class Meta(BaseReportSubForm.Meta):
        model = PrepareCoachingSession


class CoachingSessionForm(BaseReportSubForm):
    class Meta(BaseReportSubForm.Meta):
        model = CoachingSession


class FollowUpForm(BaseReportSubForm):
    class Meta(BaseReportSubForm.Meta):
        model = FollowUp


class MentorshipWorkPlanForm(BaseForm):
    complete_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Action Plan Completion due date",
        required=False
    )

    class Meta(BaseReportForm.Meta):
        model = MentorshipWorkPlan
        widgets = {
            'action_plan': forms.Textarea(attrs={
                'placeholder': 'Enter the action plan for the mentorship checklist here... This should contain the '
                               'tasks, activities, and steps required to complete the project.'
                               }),

        }

class ProgramareaForm(forms.Form):
    program_area = forms.ModelChoiceField(
        queryset=ProgramAreas.objects.all(),
        empty_label="Select program area",
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        initial=None  # Add this line to set the initial value to None
    )
