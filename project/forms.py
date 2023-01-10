from datetime import datetime

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field
from django.forms import ModelForm, CheckboxSelectMultiple
# from django.contrib.auth.forms import UserCreationForm

# from account.models import Account
from .models import *
from django import forms


class QI_ProjectsForm(ModelForm):
    # def __init__(self, *args, **kwargs):
    # Django Model Forms - Setting a required field (True/False)
    #     super().__init__(*args, **kwargs)
    #     self.fields['facility_name'].required = False
    class Meta:
        model = QI_Projects
        fields = "__all__"
        exclude = ['created_by', 'modified_by', 'remote_addr', 'phone', 'county', 'sub_county',
                   'department'
                   ]
        # widgets = {
        #     'first_cycle_date': forms.DateInput(format=('%Y-%m-%d'),
        #                                         attrs={'class': 'form-control', 'placeholder': 'Select Date',
        #                                                'type': 'date', 'max': datetime.now().date}),
        # }

    field_order = ['qi_manager']


class QI_ProjectsConfirmForm(ModelForm):
    class Meta:
        model = QI_Projects
        fields = "__all__"
        exclude = ['created_by', 'modified_by', 'remote_addr', 'phone',
                   'department'
                   ]

    field_order = ['qi_manager']


class QI_ProjectsSubcountyForm(ModelForm):
    class Meta:
        model = Subcounty_qi_projects
        fields = "__all__"
        exclude = ['created_by', 'modified_by', 'remote_addr', 'phone', 'county']
        # widgets = {
        #     'first_cycle_date': forms.DateInput(format=('%Y-%m-%d'),
        #                                         attrs={'class': 'form-control', 'placeholder': 'Select Date',
        #                                                'type': 'date', 'max': datetime.now().date}),
        # }
        # widgets = {
        #     'counties': forms.CheckboxSelectMultiple,
        #     'facilities': forms.CheckboxSelectMultiple,
        # }

    field_order = ['qi_manager']


class QI_Projects_countyForm(ModelForm):
    class Meta:
        model = County_qi_projects
        fields = "__all__"
        exclude = ['created_by', 'modified_by', 'remote_addr', 'phone']
        widgets = {
            'first_cycle_date': forms.DateInput(format=('%Y-%m-%d'),
                                                attrs={'class': 'form-control', 'placeholder': 'Select Date',
                                                       'type': 'date', 'max': datetime.now().date}),
        }

    field_order = ['qi_manager']


class QI_Projects_hubForm(ModelForm):
    class Meta:
        model = Hub_qi_projects
        fields = "__all__"
        exclude = ['created_by', 'modified_by', 'remote_addr', 'phone']
        widgets = {
            'first_cycle_date': forms.DateInput(format=('%Y-%m-%d'),
                                                attrs={'class': 'form-control', 'placeholder': 'Select Date',
                                                       'type': 'date', 'max': datetime.now().date}),
        }

    field_order = ['qi_manager']


class QI_Projects_programForm(ModelForm):
    class Meta:
        model = Program_qi_projects
        fields = "__all__"
        exclude = ['created_by', 'modified_by', 'remote_addr', 'phone']
        # widgets = {
        #     'first_cycle_date': forms.DateInput(format=('%Y-%m-%d'),
        #                                         attrs={'class': 'form-control', 'placeholder': 'Select Date',
        #                                                'type': 'date', 'max': datetime.now().date}),
        # }

    field_order = ['qi_manager']


class Close_projectForm(ModelForm):
    class Meta:
        model = Close_project
        fields = "__all__"


class TestedChangeForm(ModelForm):
    class Meta:
        model = TestedChange
        fields = "__all__"
        exclude = ['achievements', 'project']
        widgets = {
            'data_sources': forms.TextInput(attrs={
                'placeholder': 'Specify the tools or systems used to collect data for the metric',
                'style': 'font-size: 14px;',
            }),
            'tested_change': forms.TextInput(attrs={
                'placeholder': 'The specific change or improvement that was tested.',
                'style': 'font-size: 14px;',
            })
            # 'notes': forms.Textarea(attrs={'placeholder': 'Any additional notes or comments about the stakeholder, '
            #                                               'such as any specific expertise or experience he/she brings '
            #                                               'to the project.'}),
            # 'responsibility': forms.Textarea(attrs={
            #     'placeholder': 'Any specific tasks or responsibilities that stakeholder will be responsible for'}),
        }

        # widgets = {
        #     'month_year': forms.DateInput(format=('%Y-%m-%d'),
        #                                   attrs={'class': 'form-control', 'placeholder': 'Select Date',
        #                                          'type': 'date', 'max': datetime.now().date}),
        # }


class UpdateTestedChangeForm(ModelForm):
    class Meta:
        model = TestedChange
        fields = "__all__"
        exclude = ['achievements', 'project']

        widgets = {
            'month_year': forms.DateInput(format=('%Y-%m-%d'),
                                          attrs={'class': 'form-control', 'placeholder': 'Select Date',
                                                 'type': 'date', 'max': datetime.now().date}),
        }


# class CreateUserForm(UserCreationForm):
#     class Meta:
#         model = User
#         fields = ['username', 'email']


# class AccountForm(UserCreationForm):
#     class Meta:
#         model = Account
#         fields ='__all__'
class ProjectCommentsForm(ModelForm):
    class Meta:
        model = ProjectComments
        fields = ['comment']


class ProjectResponsesForm(ModelForm):
    class Meta:
        model = ProjectResponses
        fields = ['response']


class Qi_managersForm(ModelForm):
    class Meta:
        model = Qi_managers
        fields = "__all__"


class DepartmentForm(ModelForm):
    class Meta:
        model = Department
        fields = "__all__"


class CategoryForm(ModelForm):
    class Meta:
        model = Category
        fields = "__all__"


class Sub_countiesForm(ModelForm):
    class Meta:
        model = Sub_counties
        fields = "__all__"
        widgets = {
            'counties': forms.CheckboxSelectMultiple,
            # 'counties': forms.RadioSelect,
            'facilities': forms.CheckboxSelectMultiple
        }


class FacilitiesForm(ModelForm):
    class Meta:
        model = Facilities
        fields = "__all__"


class CountiesForm(ModelForm):
    class Meta:
        model = Counties
        fields = "__all__"


class ResourcesForm(ModelForm):
    class Meta:
        model = Resources
        fields = "__all__"
        exclude = ['uploaded_by']


class Qi_team_membersForm(ModelForm):
    class Meta:
        model = Qi_team_members
        fields = "__all__"
        exclude = ['facility', 'qi_project', 'created_by']
        labels = {
            'user': 'Team Member',
        }
        widgets = {
            'impact': forms.Textarea(attrs={'placeholder': 'How the stakeholder is impacted by the project, or how will'
                                                           ' he/she contribute to its success.',
                                            'style': 'font-size: 14px;', }),
            'notes': forms.Textarea(attrs={'placeholder': 'Any additional notes or comments about the stakeholder, '
                                                          'such as any specific expertise or experience he/she brings '
                                                          'to the project.',
                                           'style': 'font-size: 14px;', }),
            'responsibility': forms.Textarea(attrs={
                'placeholder': 'Any specific tasks or responsibilities that stakeholder will be responsible for',
                'style': 'font-size: 14px;', }),
        }

    field_order = ['facility']


class ArchiveProjectForm(ModelForm):
    class Meta:
        model = ArchiveProject
        fields = "__all__"
        exclude = ['qi_project']

    field_order = ['qi_project']


class StakeholderForm(ModelForm):
    class Meta:
        model = Stakeholder
        fields = "__all__"
        exclude = ['facility']

    field_order = ['facility']


class MilestoneForm(ModelForm):
    class Meta:
        model = Milestone
        fields = "__all__"
        exclude = ['facility', 'qi_project', 'created_by']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Major tasks or phases of the project'}),

            'description': forms.Textarea(attrs={
                'placeholder': 'A more detailed explanation of the tasks or activities that are included in the milestone',
                'style': 'font-size: 14px;', }),

            'notes': forms.Textarea(attrs={
                'placeholder': 'The purpose of the notes field is to provide a place to include any additional context or '
                               'details that might be relevant to the milestone but that do not fit in the other fields of '
                               'the model. For example, you might use the notes field to include details about any '
                               'dependencies or risks associated with the milestone or to provide instructions or guidance '
                               'for completing the tasks in the milestone.',
                'style': 'font-size: 14px;', }),
        }


class ActionPlanForm(ModelForm):
    class Meta:
        model = ActionPlan
        fields = "__all__"
        exclude= ['facility','qi_project','created_by','progress','timeframe']
        widgets = {
            'responsible': forms.CheckboxSelectMultiple
        }

    # def save(self, commit=True):
    #     instance = super().save(commit=False)
    #     # Save the instance
    #     if commit:
    #         instance.save()
    #     # Save many-to-many relationships
    #     self.save_m2m()
    #     return instance