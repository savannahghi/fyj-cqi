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
        widgets = {
            'problem_background': forms.Textarea(attrs={
                'placeholder': 'Include current status, previous attempt, relevant research and studies, barriers, '
                               'importance of the change you intend to make and the need for improvement. For '
                               'example: The XYZ health center currently has a viral load uptake rate of 50%. '
                               'Despite previous efforts to increase uptake, barriers such as lack of resources, '
                               'education, and awareness among patients have hindered progress. Research has shown '
                               'that viral load testing is crucial in monitoring the effectiveness of antiretroviral '
                               'therapy (ART) and identifying potential resistance to ART. However, low viral load '
                               'uptake at the health center may lead to poor health outcomes for patients living with '
                               'HIV and hinder population-level HIV control. Given the importance of viral load '
                               'testing and the need for improvement at the XYZ health center, this CQI project aims '
                               'to increase viral load uptake from 50% to 100% by January 2023.'}),
            'objective': forms.Textarea(attrs={
                'placeholder': "A project objective is a clear and specific statement that defines the goal or "
                               "outcome that the project is aiming to achieve. It should be a summary of the problem "
                               "background and should indicate the gap between the current situation and the desired "
                               "outcome. For example: To increase the viral load uptake from 50% to 100% by January "
                               "2023, by implementing education and training for staff, providing better systems for "
                               "patients to receive their test results in a timely manner and collaborating with other "
                               "organizations to improve services."}),
            'project_title': forms.TextInput(attrs={
                'placeholder': "A project title is a brief, clear, and descriptive name for the project that "
                               "summarizes the main focus or objective of the project. "}),
        }
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
        # widgets = {
        #     'first_cycle_date': forms.DateInput(format=('%Y-%m-%d'),
        #                                         attrs={'class': 'form-control', 'placeholder': 'Select Date',
        #                                                'type': 'date', 'max': datetime.now().date}),
        # }

    field_order = ['qi_manager']


class QI_Projects_hubForm(ModelForm):
    class Meta:
        model = Hub_qi_projects
        fields = "__all__"
        exclude = ['created_by', 'modified_by', 'remote_addr', 'phone']
        # widgets = {
        #     'first_cycle_date': forms.DateInput(format=('%Y-%m-%d'),
        #                                         attrs={'class': 'form-control', 'placeholder': 'Select Date',
        #                                                'type': 'date', 'max': datetime.now().date}),
        # }

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
    # Define the form fields and their properties
    class Meta:
        model = ActionPlan  # specify the model that the form is based on
        fields = "__all__"  # include all fields from the model
        exclude = ['facility', 'qi_project', 'created_by', 'progress',
                   'timeframe']  # exclude these fields from the form
        widgets = {
            'responsible': forms.CheckboxSelectMultiple  # render the 'responsible' field as checkboxes
        }

    def __init__(self, facility, qi_projects, *args, **kwargs):
        # call the parent class's init method
        super(ActionPlanForm, self).__init__(*args, **kwargs)
        # filter the 'responsible' field's queryset based on the passed facility and qi_project
        self.fields['responsible'].queryset = Qi_team_members.objects.filter(facility=facility, qi_project=qi_projects)
        # check if an instance is passed to the form
        if 'instance' in kwargs:
            instance = kwargs.pop('instance')
            # set the initial value of the 'responsible' field to the current values of the instance
            self.fields['responsible'].initial = [tm.pk for tm in instance.responsible.all()]

    # def save(self, commit=True):
    #     instance = super().save(commit=False)
    #     # Save the instance
    #     if commit:
    #         instance.save()
    #     # Save many-to-many relationships
    #     self.save_m2m()
    #     return instance


class Lesson_learnedForm(ModelForm):
    # Define the form fields and their properties
    class Meta:
        model = Lesson_learned
        fields = "__all__"
        exclude = ['project_name', 'created_by', 'modified_by']
        widgets = {

            'key_successes': forms.Textarea(attrs={
                'placeholder': "Describe the successes that were encountered during the project. This "
                               "can help others understand what worked well, and how those lessons can be "
                               "applied to future projects.",
                'style': 'font-size: 14px;', }),

            'challenges': forms.Textarea(attrs={
                'placeholder': "Describe the challenges that were encountered during the project. This can"
                               " help others understand what what didn't work well, and how those lessons can be "
                               "applied to future projects.",
                'style': 'font-size: 14px;', }),
            'best_practices': forms.Textarea(attrs={
                'placeholder': "Include any best practices or recommendations that were identified during the "
                               "project. These can be used to improve the process in the future.",
                'style': 'font-size: 14px;', }),
            'resources': forms.Textarea(attrs={
                'placeholder': "List any resources that were used during the project, such as templates, forms, "
                               "or tools. This can help others access the same information and resources.",
                'style': 'font-size: 14px;', }),
            'future_plans': forms.Textarea(attrs={
                'placeholder': "Describe any future improvement plans identified during the project and how they "
                               "could be implemented.",
                'style': 'font-size: 14px;', }),
            'recommendations': forms.Textarea(attrs={
                'placeholder': "List the recommendations here",
                'style': 'font-size: 14px;', }),
            'problem_or_opportunity': forms.Textarea(attrs={
                'placeholder': "This field describes the problem or opportunity that the CQI project is addressing. "
                               "Please provide a brief description of the problem or opportunity the CQI project aims "
                               "to address, including any relevant goals, objectives, and desired outcomes.",
                'style': 'font-size: 14px;', }),
        }


class BaselineForm(ModelForm):
    class Meta:
        model = Baseline
        fields = "__all__"
        exclude = ['facility', 'qi_project']


class CommentForm(ModelForm):
    # content = forms.CharField()
    content = forms.CharField(widget=forms.TextInput(attrs={'class': 'full-width-input'}))

    # content = forms.CharField(widget=forms.Textarea(attrs={'rows': 10, 'cols': 120}))

    class Meta:
        model = Comment
        fields = ['content']
        exclude=['author','parent','parent_id','likes','dislikes']

