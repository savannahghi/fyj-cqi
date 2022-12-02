import django_filters
from django_filters import CharFilter, DateFilter, NumberFilter

from .models import *


class QiprojectFilter(django_filters.FilterSet):
    start_date = DateFilter(field_name="start_date", lookup_expr="gte",label='From (dd/mm/yyyy)')
    end_date = DateFilter(field_name="start_date", lookup_expr="lte",label='To (dd/mm/yyyy)')
    # facility = CharFilter(field_name="facility", lookup_expr="icontains",label='Facility')
    project_title = CharFilter(field_name="project_title", lookup_expr="icontains",label='Project Title')
    objective = CharFilter(field_name="objective", lookup_expr="icontains",label='Objective')
    problem_background = CharFilter(field_name="problem_background", lookup_expr="icontains",label='Problem Background')
    # measurement_frequency = CharFilter(field_name="measurement_frequency", lookup_expr="icontains",label='Measurement Frequency')
    settings = CharFilter(field_name="settings", lookup_expr="icontains",label='Settings')

    class Meta:
        model = QI_Projects
        fields = ['project_title','departments', 'problem_background', 'facility', 'settings', 'created_by',
                  'start_date','measurement_frequency']
        exclude = ['process_analysis']



class TestedChangeFilter(django_filters.FilterSet):
    # start_date = DateFilter(field_name="start_date", lookup_expr="gte",label='From (dd/mm/yyyy)')
    # end_date = DateFilter(field_name="start_date", lookup_expr="lte",label='To (dd/mm/yyyy)')
    # # facility = CharFilter(field_name="facility", lookup_expr="icontains",label='Facility')
    # project_title = CharFilter(field_name="project_title", lookup_expr="icontains",label='Project Title')
    # objective = CharFilter(field_name="objective", lookup_expr="icontains",label='Objective')
    achievements = NumberFilter(field_name="achievements", lookup_expr="gte",label='Achievements')
    # # measurement_frequency = CharFilter(field_name="measurement_frequency", lookup_expr="icontains",label='Measurement Frequency')
    # settings = CharFilter(field_name="settings", lookup_expr="icontains",label='Settings')

    class Meta:
        # achievements = CharFilter(field_name="achievements", lookup_expr="gte",
        #                                 label='Achievements')
        model = TestedChange
        fields = ['achievements','project']
