import django_filters
from django import forms
from django.forms import DateInput
from django_filters import DateFilter, CharFilter

from apps.pmtct.models import PatientDetails
from apps.cqi.models import Facilities


class PatientDetailsFilter(django_filters.FilterSet):
    start_date = DateFilter(field_name="edd", lookup_expr="gte", label='EDD (>=)',
                            widget=DateInput(attrs={'type': 'date'}))
    end_date = DateFilter(field_name="edd", lookup_expr="lte", label='EDD (<=)',
                          widget=DateInput(attrs={'type': 'date'}))
    date_started_on_art = DateFilter(field_name="date_started_on_art", lookup_expr="lte", label='Date started on HAART (<=)')
    date_started_on_art_above = DateFilter(field_name="date_started_on_art", lookup_expr="gte", label='Date started on HAART (>=)')
    marital_status = CharFilter(field_name="marital_status", lookup_expr="icontains", label='Marital status')
    partner_status = CharFilter(field_name="partner_status", lookup_expr="icontains", label='Partner status')
    first_name = CharFilter(field_name="first_name", lookup_expr="icontains", label='First name')
    age = CharFilter(field_name="age", lookup_expr="gte", label='Age (>=):')
    age_below = CharFilter(field_name="age", lookup_expr="lte", label='Age (<=):')
    ccc_no = CharFilter(field_name="ccc_no", lookup_expr="icontains", label='CCC No')
    gestation_below = CharFilter(field_name="gestation_by_age", lookup_expr="lte", label='GBD (<=)')
    gestation_above = CharFilter(field_name="gestation_by_age", lookup_expr="gte", label='GBD (>=)')
    on_art = CharFilter(field_name="on_art", lookup_expr="icontains", label='On HAART')
    update_status = CharFilter(field_name="update_status", lookup_expr="icontains", label='Update Status')
    # use django_filter model choice filter
    facility_name = django_filters.ModelChoiceFilter(
        queryset=Facilities.objects.all(),
        empty_label="Select facility",
        widget=forms.Select(attrs={'class': 'form-control select2 input-sm'}),
        label='Facility'
    )
    class Meta:
        model = PatientDetails
        fields = {
            'first_name': ['icontains'],
            'last_name': ['icontains'],
            'ccc_no': ['icontains'],
            'facility_name': ['exact'],
        }
