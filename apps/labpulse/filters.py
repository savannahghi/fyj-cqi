import django_filters
from django import forms
from django.forms import DateInput
from django_filters import CharFilter, ChoiceFilter, DateFilter, NumberFilter

from apps.cqi.models import Counties, Facilities, Sub_counties
from apps.labpulse.models import BiochemistryResult, BiochemistryTestingLab, Cd4TestingLabs, Cd4traker, DrtPdfFile, \
    DrtResults, \
    HistologyPdfFile, HistologyResults


class Cd4trakerFilter(django_filters.FilterSet):
    start_date = DateFilter(field_name="date_of_collection", lookup_expr="gte", label='From (Collection Date)',
                            widget=DateInput(attrs={'type': 'date'}))
    end_date = DateFilter(field_name="date_of_collection", lookup_expr="lte", label='To (Collection Date)',
                          widget=DateInput(attrs={'type': 'date'}))
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
    lab_type = ChoiceFilter(choices=(("Testing Laboratory", "Testing Laboratory"),
                                     ("Spoke Laboratory", "Spoke Laboratory"),), field_name="lab_type",
                            lookup_expr="exact", label='Laboratory Type')
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
    result_time_gte = DateFilter(field_name="result_time", lookup_expr="gte", label='From (Testing Date)')
    result_time_lte = DateFilter(field_name="result_time", lookup_expr="lte", label='To (Testing Date)')
    patient_id = CharFilter(field_name="patient_id", lookup_expr="icontains", label='Patient Unique No.')
    mfl_code = CharFilter(field_name="mfl_code", lookup_expr="icontains", label='MFL CODE.')
    sample_id = CharFilter(field_name="sample_id", lookup_expr="icontains", label='Sample Id.')

    full_name = django_filters.ChoiceFilter(choices=[], label='Test')
    results_interpretation = django_filters.ChoiceFilter(choices=[], label='Test Interpretation')
    facility = django_filters.ChoiceFilter(choices=[], label='Facility Name',
                                           widget=forms.Select(attrs={'class': 'form-control select2'}))
    testing_lab = django_filters.ChoiceFilter(choices=[], label='Testing Lab',
                                           widget=forms.Select(attrs={'class': 'form-control select2'}))

    sub_county = django_filters.ChoiceFilter(choices=[], label='Sub-County',
                                             widget=forms.Select(attrs={'class': 'form-control select2'}))
    county = django_filters.ChoiceFilter(choices=[], label='County',
                                         widget=forms.Select(attrs={'class': 'form-control select2'}))
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
        testing_lab_queryset = kwargs.pop('testing_lab_queryset', None)
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

        # Get unique 'facility' values from the database, considering only those with related BiochemistryResult entries
        unique_facilities = BiochemistryResult.objects.exclude(facility__isnull=True).values_list('facility__id',
                                                                                                  'facility__name').distinct()

        # Create the choices for the 'facility' field
        facility_choices = [(str(uuid), name) for uuid, name in unique_facilities]

        # Remove duplicates by converting to a set and back to a list
        unique_facility_choices = list(set(facility_choices))

        # Sort the choices and set them in the filter
        self.filters['facility'].extra['choices'] = sorted(unique_facility_choices, key=lambda x: x[1] if x[1] else '')
        # if testing_lab_queryset is not None:
        #     self.filters['testing_lab'].queryset = testing_lab_queryset
        # else:
        #     # If no queryset is provided, use all labs associated with BiochemistryResult
        #     lab_ids = BiochemistryResult.objects.exclude(testing_lab__isnull=True).values_list('testing_lab__id',
        #                                                                                        flat=True).distinct()
        #     self.filters['testing_lab'].queryset = BiochemistryTestingLab.objects.filter(id__in=lab_ids)
        #
        # # Filter to include only labs with associated BiochemistryResult data
        # lab_ids_with_data = BiochemistryResult.objects.exclude(testing_lab__isnull=True).values_list(
        #     'testing_lab__id', flat=True).distinct()
        # self.filters['testing_lab'].queryset = base_queryset.filter(id__in=lab_ids_with_data)
        #
        # # Update choices based on the current queryset
        # current_queryset = self.filters['testing_lab'].queryset
        # unique_testing_lab = current_queryset.values_list('id', 'testing_lab_name').distinct()
        # unique_testing_lab_choices = [(str(uuid), name) for uuid, name in unique_testing_lab]
        #
        # # Sort the choices and set them in the filter
        # self.filters['testing_lab'].extra['choices'] = sorted(unique_testing_lab_choices,
        #                                                       key=lambda x: x[1] if x[1] else '')
        # Define base_queryset
        if testing_lab_queryset is not None:
            base_queryset = testing_lab_queryset
        else:
            base_queryset = BiochemistryTestingLab.objects.all()

        # Filter to include only labs with associated BiochemistryResult data
        lab_ids_with_data = BiochemistryResult.objects.exclude(testing_lab__isnull=True).values_list('testing_lab__id',
                                                                                                     flat=True).distinct()
        filtered_queryset = base_queryset.filter(id__in=lab_ids_with_data)

        # Set the queryset for the testing_lab filter
        self.filters['testing_lab'].queryset = filtered_queryset

        # Update choices based on the filtered queryset
        unique_testing_lab = filtered_queryset.values_list('id', 'testing_lab_name').distinct()
        unique_testing_lab_choices = [(str(uuid), name) for uuid, name in unique_testing_lab]

        # Sort the choices and set them in the filter
        self.filters['testing_lab'].extra['choices'] = sorted(unique_testing_lab_choices,
                                                              key=lambda x: x[1] if x[1] else '')

        # # Get unique 'facility' values from the database, considering only those with related BiochemistryResult entries
        # unique_testing_lab = BiochemistryResult.objects.exclude(testing_lab__isnull=True).values_list('testing_lab__id',
        #                                                                                           'testing_lab__testing_lab_name').distinct()
        #
        # # Create the choices for the 'facility' field
        # unique_testing_lab_choices = [(str(uuid), name) for uuid, name in unique_testing_lab]
        #
        # # Remove duplicates by converting to a set and back to a list
        # unique_testing_lab_choices = list(set(unique_testing_lab_choices))
        #
        # # Sort the choices and set them in the filter
        # self.filters['testing_lab'].extra['choices'] = sorted(unique_testing_lab_choices, key=lambda x: x[1] if x[1] else '')

        ##########################
        # Get unique 'facility' values from the database, considering only those with related BiochemistryResult entries
        unique_sub_county = BiochemistryResult.objects.exclude(sub_county__isnull=True).values_list('sub_county__id',
                                                                                                    'sub_county__sub_counties').distinct()

        # Create the choices for the 'facility' field
        unique_sub_county_choices = [(str(uuid), name) for uuid, name in unique_sub_county]

        # Remove duplicates by converting to a set and back to a list
        unique_sub_county_choices = list(set(unique_sub_county_choices))

        # Sort the choices and set them in the filter
        self.filters['sub_county'].extra['choices'] = sorted(unique_sub_county_choices,
                                                             key=lambda x: x[1] if x[1] else '')

        ##########################
        # Get unique 'facility' values from the database, considering only those with related BiochemistryResult entries
        unique_county = BiochemistryResult.objects.exclude(sub_county__isnull=True).values_list('county__id',
                                                                                                'county__county_name').distinct()

        # Create the choices for the 'facility' field
        unique_county_choices = [(str(uuid), name) for uuid, name in unique_county]

        # Remove duplicates by converting to a set and back to a list
        unique_county_choices = list(set(unique_county_choices))

        # Sort the choices and set them in the filter
        self.filters['county'].extra['choices'] = sorted(unique_county_choices,
                                                         key=lambda x: x[1] if x[1] else '')

    class Meta:
        model = BiochemistryResult
        fields = ['sample_id', 'patient_id', 'test', 'full_name', 'collection_date', 'result_time', 'mfl_code', ]


class DrtResultFilter(django_filters.FilterSet):
    collection_date_lte = DateFilter(field_name="drt_results__collection_date", lookup_expr="lte",
                                     label='To (Collection Date)')
    collection_date_gte = DateFilter(field_name="drt_results__collection_date", lookup_expr="gte",
                                     label='From (Collection Date)')
    age_lte = CharFilter(field_name="drt_results__age", lookup_expr="lte",
                         label='Age <=')
    age_gte = CharFilter(field_name="drt_results__age", lookup_expr="gte",
                         label='Age >=')
    patient_id = CharFilter(field_name="drt_results__patient_id", lookup_expr="icontains", label='Patient Unique No.')
    facility_names = django_filters.ModelChoiceFilter(
        queryset=Facilities.objects.all(),
        field_name='drt_results__facility_name__name',
        empty_label="Select Facility ...",
        label='Facility Name',
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )

    county = django_filters.ModelChoiceFilter(
        queryset=Counties.objects.all(),
        field_name='drt_results__county__county_name',
        empty_label="Select County ...",
        label='County',
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )
    sub_county = django_filters.ModelChoiceFilter(
        queryset=Sub_counties.objects.all(),
        field_name='drt_results__sub_county__sub_counties',
        empty_label="Select Sub-County ...",
        label='Sub-County',
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )
    sequence_summary = django_filters.ChoiceFilter(choices=[("", ""), ], field_name='drt_results__sequence_summary',
                                                   label='Sequence Summary'
                                                   )
    resistance_level = django_filters.ChoiceFilter(choices=[("", ""), ], field_name='drt_results__resistance_level',
                                                   label='Resistant Level'
                                                   )
    haart_class = django_filters.ChoiceFilter(choices=[("", ""), ], field_name='drt_results__haart_class',
                                              label='HAART Class'
                                              )
    sex = django_filters.ChoiceFilter(choices=[("", ""), ], field_name='drt_results__sex',
                                      label='Sex'
                                      )

    class Meta:
        model = DrtResults
        fields = ['patient_id', 'collection_date_gte', 'county', 'sub_county', 'facility_name', 'sequence_summary']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Define fields to optimize
        fields_to_optimize = [
            ('sequence_summary', 'drt_results__sequence_summary'),
            ('resistance_level', 'drt_results__resistance_level'),
            ('haart_class', 'drt_results__haart_class'),
            ('sex', 'drt_results__sex'),
        ]

        for field_name, lookup_expr in fields_to_optimize:
            self.optimize_field_choices(field_name, lookup_expr)

    def optimize_field_choices(self, field_name, lookup_expr):
        unique_values = DrtPdfFile.objects.values_list(lookup_expr, flat=True).distinct()

        # Create choices for the field
        choices = [(value, value) for value in sorted(unique_values) if "nan" not in value]
        self.filters[field_name].extra['choices'] = choices


class HistologyResultFilter(django_filters.FilterSet):
    collection_date_lte = DateFilter(field_name="histology_results__collection_date", lookup_expr="lte",
                                     label='To (Collection Date)')
    collection_date_gte = DateFilter(field_name="histology_results__collection_date", lookup_expr="gte",
                                     label='From (Collection Date)')
    age_lte = CharFilter(field_name="histology_results__age", lookup_expr="lte",
                         label='Age <=')
    age_gte = CharFilter(field_name="histology_results__age", lookup_expr="gte",
                         label='Age >=')
    patient_id = CharFilter(field_name="histology_results__patient_id", lookup_expr="icontains",
                            label='Patient Unique No.')
    facility_names = django_filters.ModelChoiceFilter(
        queryset=Facilities.objects.all(),
        field_name='histology_results__facility_name__name',
        empty_label="Select Facility ...",
        label='Facility Name',
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )

    county = django_filters.ModelChoiceFilter(
        queryset=Counties.objects.all(),
        field_name='histology_results__county__county_name',
        empty_label="Select County ...",
        label='County',
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )
    sub_county = django_filters.ModelChoiceFilter(
        queryset=Sub_counties.objects.all(),
        field_name='histology_results__sub_county__sub_counties',
        empty_label="Select Sub-County ...",
        label='Sub-County',
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )
    # sequence_summary = django_filters.ChoiceFilter(choices=[("", ""),],field_name='histology_results__sequence_summary',
    #                                                label='Sequence Summary'
    #                                                )
    # resistance_level = django_filters.ChoiceFilter(choices=[("", ""), ], field_name='histology_results__resistance_level',
    #                                                label='Resistant Level'
    #                                                )
    # haart_class = django_filters.ChoiceFilter(choices=[("", ""), ], field_name='histology_results__haart_class',
    #                                                label='HAART Class'
    #                                                )
    sex = django_filters.ChoiceFilter(choices=[("", ""), ], field_name='histology_results__sex',
                                      label='Sex'
                                      )

    class Meta:
        model = HistologyResults
        fields = ['patient_id', 'collection_date_gte', 'county', 'sub_county', 'facility_name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Define fields to optimize
        fields_to_optimize = [
            # ('sequence_summary', 'drt_results__sequence_summary'),
            # ('resistance_level', 'drt_results__resistance_level'),
            # ('haart_class', 'drt_results__haart_class'),
            ('sex', 'histology_results__sex'),
        ]

        for field_name, lookup_expr in fields_to_optimize:
            self.optimize_field_choices(field_name, lookup_expr)

    def optimize_field_choices(self, field_name, lookup_expr):
        unique_values = HistologyPdfFile.objects.values_list(lookup_expr, flat=True).distinct()

        # Create choices for the field
        choices = [(value, value) for value in sorted(unique_values) if "nan" not in value]
        self.filters[field_name].extra['choices'] = choices
