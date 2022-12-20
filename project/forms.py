from datetime import datetime

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field
from django.forms import ModelForm
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
        widgets = {
            'first_cycle_date': forms.DateInput(format=('%Y-%m-%d'),
                                                attrs={'class': 'form-control', 'placeholder': 'Select Date',
                                                       'type': 'date', 'max': datetime.now().date}),
        }

    field_order = ['qi_manager']


class QI_ProjectsSubcountyForm(ModelForm):
    class Meta:
        model = Subcounty_qi_projects
        fields = "__all__"
        exclude = ['created_by', 'modified_by', 'remote_addr', 'phone', 'county']
        widgets = {
            'first_cycle_date': forms.DateInput(format=('%Y-%m-%d'),
                                                attrs={'class': 'form-control', 'placeholder': 'Select Date',
                                                       'type': 'date', 'max': datetime.now().date}),
        }

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
        widgets = {
            'first_cycle_date': forms.DateInput(format=('%Y-%m-%d'),
                                                attrs={'class': 'form-control', 'placeholder': 'Select Date',
                                                       'type': 'date', 'max': datetime.now().date}),
        }

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
            'month_year': forms.DateInput(format=('%Y-%m-%d'),
                                          attrs={'class': 'form-control', 'placeholder': 'Select Date',
                                                 'type': 'date', 'max': datetime.now().date}),
        }


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
    field_order = ['facility']
