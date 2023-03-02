import django_filters
from django_filters import CharFilter, DateFilter, NumberFilter

from .models import *


class QiprojectFilter(django_filters.FilterSet):
    start_date = DateFilter(field_name="start_date", lookup_expr="gte", label='From')
    end_date = DateFilter(field_name="start_date", lookup_expr="lte", label='To')
    # facility = CharFilter(field_name="facility", lookup_expr="icontains",label='Facility')
    project_title = CharFilter(field_name="project_title", lookup_expr="icontains", label='Project Title')
    objective = CharFilter(field_name="objective", lookup_expr="icontains", label='Objective')
    problem_background = CharFilter(field_name="problem_background", lookup_expr="icontains",
                                    label='Problem Background')
    # measurement_frequency = CharFilter(field_name="measurement_frequency", lookup_expr="icontains",label='Measurement Frequency')
    settings = CharFilter(field_name="settings", lookup_expr="icontains", label='Settings')

    class Meta:
        model = QI_Projects
        fields = ['county', 'sub_county', 'project_title', 'departments', 'problem_background', 'facility_name',
                  'settings', 'created_by',
                  'start_date', 'measurement_frequency', 'measurement_status']
        exclude = ['process_analysis']


class ProgramQiprojectFilter(django_filters.FilterSet):
    start_date = DateFilter(field_name="start_date", lookup_expr="gte", label='From')
    end_date = DateFilter(field_name="start_date", lookup_expr="lte", label='To')
    # facility = CharFilter(field_name="facility", lookup_expr="icontains",label='Facility')
    project_title = CharFilter(field_name="project_title", lookup_expr="icontains", label='Project Title')
    objective = CharFilter(field_name="objective", lookup_expr="icontains", label='Objective')
    problem_background = CharFilter(field_name="problem_background", lookup_expr="icontains",
                                    label='Problem Background')
    # measurement_frequency = CharFilter(field_name="measurement_frequency", lookup_expr="icontains",label='Measurement Frequency')
    settings = CharFilter(field_name="settings", lookup_expr="icontains", label='Settings')

    class Meta:
        model = Program_qi_projects
        fields = ['project_title', 'departments', 'problem_background', 'program',
                  'settings', 'created_by',
                  'start_date', 'measurement_frequency', 'measurement_status']
        exclude = ['process_analysis']


class SubcountyQiprojectFilter(django_filters.FilterSet):
    start_date = DateFilter(field_name="start_date", lookup_expr="gte", label='From')
    end_date = DateFilter(field_name="start_date", lookup_expr="lte", label='To')
    # sub_county = CharFilter(field_name="sub_county", lookup_expr="icontains",label='Sub county')
    project_title = CharFilter(field_name="project_title", lookup_expr="icontains", label='Project Title')
    objective = CharFilter(field_name="objective", lookup_expr="icontains", label='Objective')
    problem_background = CharFilter(field_name="problem_background", lookup_expr="icontains",
                                    label='Problem Background')
    # measurement_frequency = CharFilter(field_name="measurement_frequency", lookup_expr="icontains",label='Measurement Frequency')
    settings = CharFilter(field_name="settings", lookup_expr="icontains", label='Settings')

    class Meta:
        model = Subcounty_qi_projects
        fields = ['project_title', 'departments', 'problem_background', 'sub_county',
                  'settings', 'created_by',
                  'start_date', 'measurement_frequency', 'measurement_status']
        exclude = ['process_analysis']


class CountyQiprojectFilter(django_filters.FilterSet):
    start_date = DateFilter(field_name="start_date", lookup_expr="gte", label='From')
    end_date = DateFilter(field_name="start_date", lookup_expr="lte", label='To')
    # county = CharFilter(field_name="county", lookup_expr="icontains",label='County')
    project_title = CharFilter(field_name="project_title", lookup_expr="icontains", label='Project Title')
    objective = CharFilter(field_name="objective", lookup_expr="icontains", label='Objective')
    problem_background = CharFilter(field_name="problem_background", lookup_expr="icontains",
                                    label='Problem Background')
    # measurement_frequency = CharFilter(field_name="measurement_frequency", lookup_expr="icontains",label='Measurement Frequency')
    settings = CharFilter(field_name="settings", lookup_expr="icontains", label='Settings')

    class Meta:
        model = County_qi_projects
        fields = ['project_title', 'departments', 'problem_background', 'county',
                  'settings', 'created_by',
                  'start_date', 'measurement_frequency', 'measurement_status']
        exclude = ['process_analysis']


class HubQiprojectFilter(django_filters.FilterSet):
    start_date = DateFilter(field_name="start_date", lookup_expr="gte", label='From')
    end_date = DateFilter(field_name="start_date", lookup_expr="lte", label='To')
    # hub = CharFilter(field_name="hub", lookup_expr="icontains",label='Hub')
    project_title = CharFilter(field_name="project_title", lookup_expr="icontains", label='Project Title')
    objective = CharFilter(field_name="objective", lookup_expr="icontains", label='Objective')
    problem_background = CharFilter(field_name="problem_background", lookup_expr="icontains",
                                    label='Problem Background')
    # measurement_frequency = CharFilter(field_name="measurement_frequency", lookup_expr="icontains",label='Measurement Frequency')
    settings = CharFilter(field_name="settings", lookup_expr="icontains", label='Settings')

    class Meta:
        model = Hub_qi_projects
        fields = ['project_title', 'departments', 'problem_background', 'hub',
                  'settings', 'created_by',
                  'start_date', 'measurement_frequency', 'measurement_status']
        exclude = ['process_analysis']


class ResourcesFilter(django_filters.FilterSet):
    # start_date = DateFilter(field_name="start_date", lookup_expr="gte", label='From')
    # end_date = DateFilter(field_name="start_date", lookup_expr="lte", label='To')
    # # facility = CharFilter(field_name="facility", lookup_expr="icontains",label='Facility')
    # project_title = CharFilter(field_name="project_title", lookup_expr="icontains", label='Project Title')
    resource_name = CharFilter(field_name="resource_name", lookup_expr="icontains", label='Resource Name')

    # problem_background = CharFilter(field_name="problem_background", lookup_expr="icontains",
    #                                 label='Problem Background')
    # # measurement_frequency = CharFilter(field_name="measurement_frequency", lookup_expr="icontains",label='Measurement Frequency')
    # settings = CharFilter(field_name="settings", lookup_expr="icontains", label='Settings')

    class Meta:
        model = Resources
        fields = ['resource_name', 'resource_type']
        exclude = ['resource']


class TestedChangeFilter(django_filters.FilterSet):
    # start_date = DateFilter(field_name="start_date", lookup_expr="gte",label='From (dd/mm/yyyy)')
    # end_date = DateFilter(field_name="start_date", lookup_expr="lte",label='To (dd/mm/yyyy)')
    # # facility = CharFilter(field_name="facility", lookup_expr="icontains",label='Facility')
    # project_title = CharFilter(field_name="project_title", lookup_expr="icontains",label='Project Title')
    # objective = CharFilter(field_name="objective", lookup_expr="icontains",label='Objective')
    achievements = NumberFilter(field_name="achievements", lookup_expr="gte", label='Achievements')

    # # measurement_frequency = CharFilter(field_name="measurement_frequency", lookup_expr="icontains",label='Measurement Frequency')
    # settings = CharFilter(field_name="settings", lookup_expr="icontains",label='Settings')

    class Meta:
        # achievements = CharFilter(field_name="achievements", lookup_expr="gte",
        #                                 label='Achievements')
        model = TestedChange
        fields = ['achievements', 'project']
