import django_filters
from django import forms
from django_filters import CharFilter, DateFilter, NumberFilter

from apps.cqi.models import Facilities, Counties, Sub_counties
from apps.labpulse.models import Cd4traker, Cd4TestingLabs


class Cd4trakerFilter(django_filters.FilterSet):
    start_date = DateFilter(field_name="date_of_collection", lookup_expr="gte", label='From (Collection Date)')
    end_date = DateFilter(field_name="date_of_collection", lookup_expr="lte", label='To (Collection Date)')
    patient_unique_no = CharFilter(field_name="patient_unique_no", lookup_expr="icontains", label='Patient Unique No.')
    cd4_count_results_gte = CharFilter(field_name="cd4_count_results", lookup_expr="gte", label='CD4 count >=')
    cd4_count_results_lte = CharFilter(field_name="cd4_count_results", lookup_expr="lte", label='CD4 count <=')
    age_lte = CharFilter(field_name="age", lookup_expr="lte", label='Age <=')
    age_gte = CharFilter(field_name="age", lookup_expr="gte", label='Age >=')
    facility_name = django_filters.ModelChoiceFilter(
        queryset=Facilities.objects.all(),
        field_name='facility_name__name',
        label='Facility Name',
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )
    testing_laboratory = django_filters.ModelChoiceFilter(
        queryset=Cd4TestingLabs.objects.all(),
        field_name='testing_laboratory__testing_lab_name',
        label='Testing Laboratory',
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )
    county = django_filters.ModelChoiceFilter(
        queryset=Counties.objects.all(),
        field_name='county__county_name',
        label='County',
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )
    sub_county = django_filters.ModelChoiceFilter(
        queryset=Sub_counties.objects.all(),
        field_name='sub_county__sub_counties',
        label='Sub-County',
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )

    class Meta:
        model = Cd4traker
        fields = ['patient_unique_no', 'testing_laboratory','facility_name',
                  'created_by','received_status','serum_crag_results','sex',
                  'reason_for_rejection',
                  ]