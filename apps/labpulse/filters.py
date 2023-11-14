import django_filters
from django import forms
from django.db.models import DurationField, ExpressionWrapper, F
from django_filters import CharFilter, ChoiceFilter, DateFilter, NumberFilter

from apps.cqi.models import Facilities, Counties, Sub_counties
from apps.labpulse.models import BiochemistryResult, Cd4traker, Cd4TestingLabs, DrtResults


class Cd4trakerFilter(django_filters.FilterSet):
    start_date = DateFilter(field_name="date_of_collection", lookup_expr="gte", label='From (Collection Date)')
    end_date = DateFilter(field_name="date_of_collection", lookup_expr="lte", label='To (Collection Date)')
    patient_unique_no = CharFilter(field_name="patient_unique_no", lookup_expr="icontains", label='Patient Unique No.')
    cd4_count_results_gte = NumberFilter(field_name="cd4_count_results", lookup_expr="gte", label='CD4 Count >=')
    cd4_count_results_lte = NumberFilter(field_name="cd4_count_results", lookup_expr="lte", label='CD4 Count <=')
    cd4_percentage_gte = NumberFilter(field_name="cd4_percentage", lookup_expr="gte", label='CD4 % >=')
    cd4_percentage_lte = NumberFilter(field_name="cd4_percentage", lookup_expr="lte", label='CD4 % <=')
    age_lte = CharFilter(field_name="age", lookup_expr="lte", label='Age <=')
    age_gte = CharFilter(field_name="age", lookup_expr="gte", label='Age >=')
    AGE_UNIT_CHOICES = (('years', 'Years'), ('months', 'Months'), ('days', 'Days'),)
    age_unit = django_filters.ChoiceFilter(choices=AGE_UNIT_CHOICES, label='Age Unit')
    serum_crag_results = ChoiceFilter(choices=Cd4traker.CHOICES, field_name="serum_crag_results", lookup_expr="exact",
                                      label='Serum CrAg Test Results')
    tb_lam_results = ChoiceFilter(choices=Cd4traker.CHOICES, field_name="tb_lam_results", lookup_expr="exact",
                                  label='TB LAM Test Results')
    received_status = ChoiceFilter(choices=Cd4traker.RECEIVED_CHOICES, field_name="received_status",
                                   lookup_expr="exact",
                                   label='Received Status')
    reason_for_rejection = ChoiceFilter(choices=Cd4traker.REJECTION_CHOICES, field_name="reason_for_rejection",
                                        lookup_expr="exact",
                                        label='Reason For Rejection')
    report_type = ChoiceFilter(choices=(("Current", "Ongoing"), ("Retrospective", "Historical"),),
                               field_name="report_type", lookup_expr="exact", label='Report Type')
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

    # Define the custom TAT filters
    min_tat = django_filters.NumberFilter(
        field_name='tat_days',  # Filter by the calculated TAT in days
        lookup_expr='gte',
        label='Minimum TAT (>= days)',
        widget=forms.NumberInput(attrs={'placeholder': 'Minimum TAT (days)'}),
    )

    max_tat = django_filters.NumberFilter(
        field_name='tat_days',  # Filter by the calculated TAT in days
        lookup_expr='lte',
        label='Maximum TAT (<= days)',
        widget=forms.NumberInput(attrs={'placeholder': 'Maximum TAT (days)'}),
    )

    class Meta:
        model = Cd4traker
        fields = ['patient_unique_no', 'testing_laboratory', 'facility_name', 'age',
                  'created_by', 'received_status', 'serum_crag_results', 'sex',
                  'reason_for_rejection', 'tb_lam_results', 'cd4_percentage',
                  ]


class BiochemistryResultFilter(django_filters.FilterSet):
    collection_date_lte = DateFilter(field_name="collection_date", lookup_expr="lte", label='To (Collection Date)')
    collection_date_gte = DateFilter(field_name="collection_date", lookup_expr="gte", label='From (Collection Date)')
    result_time_gte = DateFilter(field_name="result_time", lookup_expr="gte", label='From (Result Date)')
    result_time_lte = DateFilter(field_name="result_time", lookup_expr="lte", label='To (ResultDate)')
    patient_id = CharFilter(field_name="patient_id", lookup_expr="icontains", label='Patient Unique No.')
    mfl_code = CharFilter(field_name="mfl_code", lookup_expr="icontains", label='MFL CODE.')
    sample_id = CharFilter(field_name="sample_id", lookup_expr="icontains", label='Sample Id.')

    full_name = django_filters.ChoiceFilter(choices=[], label='Test')
    results_interpretation = django_filters.ChoiceFilter(choices=[], label='Test Interpretation (Limit range)')

    result_gte = NumberFilter(field_name="result", lookup_expr="gte", label='Test result >=')
    result_lte = NumberFilter(field_name="result", lookup_expr="lte", label='Test result <=')

    def __init__(self, *args, **kwargs):
        """
        Custom initialization method for the BiochemistryResultFilter.

        Parameters:
            *args (tuple): Positional arguments.
            **kwargs (dict): Keyword arguments.

        This method is called when an instance of BiochemistryResultFilter is created.
        It retrieves unique 'test' and 'test interpretation' values from the BiochemistryResult model
        and sets them as choices for the corresponding filters.

        The 'test' choices are set for the 'full_name' filter.
        The 'test interpretation' choices are set for the 'results_interpretation' filter.
        """
        super().__init__(*args, **kwargs)

        # Get unique 'test' values from the database
        unique_tests = BiochemistryResult.objects.values_list('full_name', flat=True).distinct()

        # Create the choices for the 'test' field
        test_unit_choices = set([(test, test) for test in unique_tests])
        self.filters['full_name'].extra['choices'] = sorted(test_unit_choices)

        # Get unique 'test' values from the database
        unique_test_interpretation = BiochemistryResult.objects.values_list('results_interpretation',
                                                                            flat=True).distinct()

        # Create the choices for the 'test' field
        interpretation_choices = set([(test, test) for test in unique_test_interpretation])
        self.filters['results_interpretation'].extra['choices'] = sorted(interpretation_choices)

    class Meta:
        model = BiochemistryResult
        fields = ['sample_id','patient_id','test','full_name','collection_date','result_time','mfl_code',]


class DrtResultFilter(django_filters.FilterSet):
    collection_date_lte = DateFilter(field_name="collection_date", lookup_expr="lte", label='To (Collection Date)')
    collection_date_gte = DateFilter(field_name="collection_date", lookup_expr="gte", label='From (Collection Date)')
    patient_id = CharFilter(field_name="patient_id", lookup_expr="icontains", label='Patient Unique No.')
    facility_name = django_filters.ModelChoiceFilter(
        queryset=Facilities.objects.all(),
        field_name='facility_name__name',
        label='Facility Name',
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
        model = DrtResults
        fields = ['patient_id','collection_date_gte','county','sub_county','facility_name']
