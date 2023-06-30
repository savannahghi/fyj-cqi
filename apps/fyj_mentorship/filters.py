import django_filters
from django import forms
from django.db.models import Q
from django.forms import DateInput
from django_filters import DateFilter

from apps.account.models import CustomUser
from apps.cqi.models import Facilities, Sub_counties, Counties, Hub
from apps.dqa.models import Period
from apps.fyj_mentorship.models import ProgramAreas, Introduction


class MentorshipFilter(django_filters.FilterSet):
    date_of_interview_lte = DateFilter(field_name="date_of_interview", lookup_expr="gte", label='From (Interview date)',
                                       widget=DateInput(attrs={'type': 'date'}),
                                       )
    date_of_interview_gte = DateFilter(field_name="date_of_interview", lookup_expr="lte", label='To (Interview date)',
                                       widget=DateInput(attrs={'type': 'date'}),
                                       )

    program_area = django_filters.ModelChoiceFilter(
        queryset=ProgramAreas.objects.all(),
        field_name='program_area__program_area',
        label='Program Area',
        empty_label="Select program area",
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )
    year = django_filters.ChoiceFilter(
        choices=Period.YEAR_CHOICES,
        field_name='quarter_year__year',
        label='Year',
        empty_label="Select FY",
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )
    quarter = django_filters.ChoiceFilter(
        choices=Period.QUARTER_CHOICES,
        field_name='quarter_year__quarter',
        label='Quarter',
        empty_label="Select quarter",
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )
    sub_county = django_filters.ModelChoiceFilter(
        queryset=Sub_counties.objects.all(),
        field_name='sub_county__sub_counties',
        label='Sub-County',
        empty_label="Select sub-county",
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )
    county = django_filters.ModelChoiceFilter(
        queryset=Counties.objects.all(),
        field_name='county__county_name',
        label='County',
        empty_label="Select county",
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )
    hub = django_filters.ModelMultipleChoiceFilter(
        queryset=Hub.objects.all(),
        field_name='sub_county__hub',
        label='Hub',
        widget=forms.SelectMultiple(attrs={'class': 'form-control select2'}),
    )
    facility_name = django_filters.ModelChoiceFilter(
        queryset=Facilities.objects.all(),
        field_name='facility_name__name',
        label='Facility Name',
        empty_label="Select facility name",
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )
    fyj_staff = django_filters.ModelChoiceFilter(
        queryset=CustomUser.objects.all(),
        field_name='created_by',
        label='FYJ Staff',
        empty_label="Choose staff",
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Check if 'hub' field is present in the submitted form data
        if 'hub' in self.data:
            # Get the selected hub values from the form data
            hub_values = self.data.getlist('hub')
            # Filter facilities based on the selected hub values
            facilities = Facilities.objects.filter(sub_counties__hub__in=hub_values)
            # Assign the filtered facilities queryset to the 'facility_name' filter
            self.filters['facility_name'].field.queryset = facilities
            self.filters['sub_county'].field.queryset = Sub_counties.objects.filter(hub__in=hub_values)
            self.filters['county'].field.queryset = Counties.objects.filter(
                Q(sub_counties__hub__in=hub_values) |
                Q(sub_counties__isnull=True)
            ).distinct()


    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     print("MentorshipFilter: Rendered Fields")
    #     print(self.form)

    class Meta:
        model = Introduction
        fields = ['quarter_year', 'program_area', 'facility_name']
