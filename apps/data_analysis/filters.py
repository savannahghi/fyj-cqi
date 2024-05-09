import datetime

import django_filters
from django import forms
from django.forms import DateInput
from django.http import QueryDict
from django.utils import timezone
from django_filters import CharFilter, DateFilter, NumberFilter

from apps.cqi.models import Counties, Facilities, Sub_counties
from apps.data_analysis.models import RTKData


# class RTKDataFilter(django_filters.FilterSet):
#     start_date = DateFilter(field_name="month_column", lookup_expr="gte", label='From (Reporting Month)')
#     end_date = DateFilter(field_name="month_column", lookup_expr="lte", label='To (Reporting Month)')
#
#     class Meta:
#         model = RTKData
#         fields = "__all__"
#
#     sub_county = django_filters.ChoiceFilter(choices=[], label='Sub-County',
#                                              widget=forms.Select(attrs={'class': 'form-control select2'}))
#     commodity_name = django_filters.ChoiceFilter(choices=[], label='Commodity Type',
#                                              widget=forms.Select(attrs={'class': 'form-control select2'}))
#     county = django_filters.ChoiceFilter(choices=[], label='County',
#                                          widget=forms.Select(attrs={'class': 'form-control select2'}))
#     facility_name = django_filters.ChoiceFilter(choices=[], label='Facility Name',
#                                              widget=forms.Select(attrs={'class': 'form-control select2'}))
#     month = django_filters.ChoiceFilter(choices=[], label='Month-Year',
#                                                 widget=forms.Select(attrs={'class': 'form-control select2'}))
#
#     def __init__(self, *args, **kwargs):
#         """
#         Custom initialization method for the BiochemistryResultFilter.
#
#         Parameters:
#             *args (tuple): Positional arguments.
#             **kwargs (dict): Keyword arguments.
#
#         This method is called when an instance of BiochemistryResultFilter is created.
#         It retrieves unique 'test' and 'test interpretation' values from the BiochemistryResult model
#         and sets them as choices for the corresponding filters.
#
#         The 'test' choices are set for the 'full_name' filter.
#         The 'test interpretation' choices are set for the 'results_interpretation' filter.
#         """
#         super().__init__(*args, **kwargs)
#
#         # Get unique 'test' values from the database
#         unique_tests = RTKData.objects.values_list('facility_name', flat=True).distinct()
#
#         # Create the choices for the 'test' field
#         test_unit_choices = set([(test, test) for test in unique_tests])
#         self.filters['facility_name'].extra['choices'] = sorted(test_unit_choices)
#
#         # Get unique 'test' values from the database
#         unique_tests = RTKData.objects.values_list('sub_county', flat=True).distinct()
#
#         # Create the choices for the 'test' field
#         test_unit_choices = set([(test, test) for test in unique_tests])
#         self.filters['sub_county'].extra['choices'] = sorted(test_unit_choices)
#
#         # Get unique 'test' values from the database
#         unique_tests = RTKData.objects.values_list('county', flat=True).distinct()
#
#         # Create the choices for the 'test' field
#         test_unit_choices = set([(test, test) for test in unique_tests])
#         self.filters['county'].extra['choices'] = sorted(test_unit_choices)
#
#         # Get unique 'test' values from the database
#         unique_tests = RTKData.objects.values_list('commodity_name', flat=True).distinct()
#
#         # Create the choices for the 'test' field
#         test_unit_choices = set([(test, test) for test in unique_tests])
#         self.filters['commodity_name'].extra['choices'] = sorted(test_unit_choices)
#
#         # Get unique 'test' values from the database
#         unique_tests = RTKData.objects.values_list('month', flat=True).distinct()
#
#         # Create the choices for the 'test' field
#         test_unit_choices = set([(test, test) for test in unique_tests])
#         self.filters['month'].extra['choices'] = sorted(test_unit_choices)
class RTKDataFilter(django_filters.FilterSet):
    start_date = DateFilter(field_name="month_column", lookup_expr="gte", label='From (Reporting Month)',
                            widget=DateInput(attrs={'type': 'date'}))
    end_date = DateFilter(field_name="month_column", lookup_expr="lte", label='To (Reporting Month)',
                          widget=DateInput(attrs={'type': 'date'}))

    class Meta:
        model = RTKData
        fields = "__all__"

    sub_county = django_filters.MultipleChoiceFilter(choices=[], label='Sub-County',
                                                     widget=forms.SelectMultiple(
                                                         attrs={'class': 'form-control select2'}))

    commodity_name = django_filters.MultipleChoiceFilter(choices=[], label='Commodity Type',
                                                         widget=forms.SelectMultiple(
                                                             attrs={'class': 'form-control select2'}))
    county = django_filters.MultipleChoiceFilter(choices=[], label='County',
                                                 widget=forms.SelectMultiple(
                                                     attrs={'class': 'form-control select2'}))
    facility_name = django_filters.ChoiceFilter(choices=[], label='Facility Name',
                                                widget=forms.Select(attrs={'class': 'form-control select2'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Get unique values from the database for all fields in a single query
        unique_values = RTKData.objects.values('facility_name', 'sub_county', 'county', 'commodity_name',
                                               ).distinct()

        # Create the choices for each field
        for field_name in ['facility_name', 'sub_county', 'county', 'commodity_name']:
            test_unit_choices = set([(item[field_name], item[field_name]) for item in unique_values])
            self.filters[field_name].extra['choices'] = sorted(test_unit_choices)


class RTKInventoryFilter(RTKDataFilter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Create a mutable copy of the QueryDict instance
        mutable_data = QueryDict('', mutable=True)
        mutable_data.update(self.data)

        # Subtract one month from the start_date supplied by the user
        if 'start_date' in self.data and self.data['start_date']:
            start_date = datetime.datetime.strptime(self.data['start_date'], '%Y-%m-%d')

            # Calculate the last day of the previous quarter based on the start_date
            last_month_of_quarter = (start_date.month - 1) // 3 * 3 + 1
            last_day_of_previous_quarter = datetime.datetime(start_date.year, last_month_of_quarter,
                                                             1) - datetime.timedelta(days=1)

            mutable_data['start_date'] = last_day_of_previous_quarter.strftime('%Y-%m-%d')

        # Assign the mutable_data back to self.data
        self.data = mutable_data
