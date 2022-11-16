from datetime import datetime
from django.forms import ModelForm
# from django.contrib.auth.forms import UserCreationForm

# from account.models import Account
from .models import *
from django import forms


class QI_ProjectsForm(ModelForm):
    class Meta:
        model = QI_Projects
        fields = "__all__"
        exclude = ['created_by', 'modified_by', 'remote_addr', 'phone']
        widgets = {
            'first_cycle_date': forms.DateInput(format=('%Y-%m-%d'),
                                                attrs={'class': 'form-control', 'placeholder': 'Select Date',
                                                       'type': 'date', 'max': datetime.now().date}),
        }


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
