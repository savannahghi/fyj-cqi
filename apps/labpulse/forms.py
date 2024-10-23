from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator
from django.forms import ModelForm
from django.utils import timezone
from multiupload.fields import MultiFileField

from apps.cqi.models import Facilities
from apps.labpulse.models import Cd4traker, Cd4TestingLabs, Commodities, DrtPdfFile, DrtResults, \
    HistologyPdfFile, HistologyResults, LabPulseUpdateButtonSettings, \
    ReagentStock


class Cd4trakerForm(ModelForm):
    # facility_name = forms.ModelChoiceField(
    #     queryset=Facilities.objects.all(),
    #     empty_label="Select facility",
    #     widget=forms.Select(attrs={'class': 'form-control select2'}),
    # )
    facility_name = forms.ChoiceField(
        choices=[],
        required=True,
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )
    date_of_collection = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Collection date"
    )
    date_of_testing = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Testing date",
        required=False
    )
    date_sample_received = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Date sample was received"
    )
    age_unit = forms.ChoiceField(choices=Cd4traker.AGE_UNIT_CHOICES, widget=forms.Select(
        attrs={'class': 'form-control'}))

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Pop the 'user' argument from kwargs
        super(Cd4trakerForm, self).__init__(*args, **kwargs)
        if user and user.groups.filter(name='referring_laboratory_staffs_labpulse').exists():
            # If the user is in the referring_lab_group, make disable all fields
            for field_name in self.fields:
                if field_name != 'tb_lam_results':  # Allow editing only for the 'tb_lam' field
                    self.fields[field_name].disabled = True

        # Populate the choices for the facility_name field
        facilities = Facilities.objects.all()  # Fetch all Facilities objects from the database
        # Create a list of choices for the facility_name field
        # Prepend an empty choice for the initial, empty label ("Select facility")
        self.fields['facility_name'].choices = [('', 'Select facility')] + [
            # Generate a tuple for each facility with its primary key as the value
            # and a display string combining name and MFL code
            (str(facility.pk), f"{facility.name} ({facility.mfl_code})") for facility in facilities]

    def clean(self):
        cleaned_data = super().clean()  # Get the cleaned data from the form
        facility_id = cleaned_data.get('facility_name')  # Get the selected facility's ID

        try:
            facility = Facilities.objects.get(pk=facility_id)  # Retrieve the selected Facilities instance
            cleaned_data['facility_name'] = facility  # Set the actual Facilities instance
        except Facilities.DoesNotExist:
            # Raise a validation error if the selected facility does not exist
            raise forms.ValidationError("Invalid facility selected")

        return cleaned_data  # Return the cleaned data after validation

    class Meta:
        model = Cd4traker
        exclude = ['created_by', 'modified_by', 'date_dispatched', 'date_updated', 'testing_laboratory', 'report_type']
        labels = {
            'cd4_count_results': 'CD4 count results',
            'serum_crag_results': 'Serum CrAg Results',
            'reason_for_no_serum_crag': 'Reason for not doing serum CrAg',
            'cd4_percentage': 'CD4 % values',
            'tb_lam_results': 'TB LAM results',
        }

    def save(self, commit=True):
        instance = super(Cd4trakerForm, self).save(commit=False)
        instance.date_dispatched = timezone.now()
        if commit:
            instance.save()
        return instance

    # def clean(self):
    #     cleaned_data = super().clean()
    #
    #     # Check if CD4 test was performed
    #     if cleaned_data.get('cd4_count_results') is not None:
    #         cleaned_data['cd4_reagent_used'] = True
    #
    #     # Check if TB LAM test was performed
    #     if cleaned_data.get('tb_lam_results') is not None:
    #         cleaned_data['tb_lam_reagent_used'] = True
    #
    #     # Check if serum CRAG test was performed
    #     if cleaned_data.get('serum_crag_results') is not None:
    #         cleaned_data['serum_crag_reagent_used'] = True
    #
    #     return cleaned_data


class Cd4TestingLabsForm(forms.Form):
    testing_lab_name = forms.ModelChoiceField(
        queryset=Cd4TestingLabs.objects.all(),
        empty_label="Select Testing Lab ...",
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )


class facilities_lab_Form(forms.Form):
    facility_name = forms.ModelChoiceField(
        queryset=Facilities.objects.all(),
        # queryset=Facilities.objects.filter(fyj_facilities=True),
        empty_label="Select Testing Lab ...",
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )


class Cd4TestingLabForm(ModelForm):
    class Meta:
        model = Cd4TestingLabs
        fields = "__all__"


class LabPulseUpdateButtonSettingsForm(forms.ModelForm):
    hide_button_time = forms.TimeField(
        widget=forms.TimeInput(format='%H:%M'),
        label='Set time to hide update button in LabPulse module',
        help_text='Please select a time after 5pm. (HH:MM)'
    )

    class Meta:
        model = LabPulseUpdateButtonSettings
        fields = ('hide_button_time',)

    def clean_hide_button_time(self):
        hide_button_time = self.cleaned_data['hide_button_time']
        if hide_button_time.hour < 17:
            raise forms.ValidationError("The hide button time must be after 5pm.")
        return hide_button_time


class Cd4trakerManualDispatchForm(ModelForm):
    facility_name = forms.ModelChoiceField(
        queryset=Facilities.objects.all(),
        empty_label="Select facility",
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )
    date_of_collection = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Collection date"
    )
    date_of_testing = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Testing date",
        required=False
    )
    date_sample_received = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Date sample was received"
    )
    date_dispatched = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Dispatch date",
        required=True
    )

    class Meta:
        model = Cd4traker
        exclude = ['created_by', 'modified_by', 'date_updated', 'testing_laboratory', 'report_type']
        labels = {
            'cd4_count_results': 'CD4 count results',
            'serum_crag_results': 'Serum CrAg Results',
            'reason_for_no_serum_crag': 'Reason for not doing serum CrAg',
            'cd4_percentage': 'CD4 % values',
            'tb_lam_results': 'TB LAM results',
        }


class CommoditiesForm(ModelForm):
    date_commodity_received = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Date Commodity Received"
    )
    expiry_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Expiry Date",
        required=False
    )

    class Meta:
        model = Commodities
        exclude = ['created_by', 'modified_by', 'date_modified', 'date_created', 'facility_name']
        labels = {
            'number_received': 'Number of Reagents Received',
            'type_of_reagent': 'Type Of Reagent',
            'received_from': 'Received From',
            'negative_adjustment': 'Negative Adjustment',
            'positive_adjustment': 'Positive Adjustment',
        }


class ReagentStockForm(ModelForm):
    facility_received_from = forms.ModelChoiceField(
        queryset=Facilities.objects.all(),
        empty_label="Select facility",
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )
    facility_dispensed_to = forms.ModelChoiceField(
        queryset=Facilities.objects.all(),
        empty_label="Select facility",
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )
    date_commodity_received = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Date Commodity Received"
    )
    date_commodity_dispensed = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Date Commodity Dispensed"
    )
    expiry_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Expiry Date",
        required=False
    )

    class Meta:
        model = ReagentStock
        exclude = ['created_by', 'modified_by', 'date_modified', 'date_created', 'facility_name', 'quantity_used',
                   'remaining_quantity']
        labels = {
            'number_received': 'Number of Reagents Received',
            'type_of_reagent': 'Type Of Reagent',
            'received_from': 'Received From',
            'negative_adjustment': 'Negative Adjustment',
            'positive_adjustment': 'Positive Adjustment',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set files field as not required initially
        self.fields['facility_dispensed_to'].required = False
        self.fields['facility_received_from'].required = False
        self.fields['quantity_received'].required = False
        self.fields['negative_adjustment'].required = False
        self.fields['positive_adjustments'].required = False
        self.fields['date_commodity_dispensed'].required = False
        self.fields['date_commodity_received'].required = False
        self.fields['received_from'].required = False


class DrtResultsForm(ModelForm):
    facility_name = forms.ModelChoiceField(
        queryset=Facilities.objects.all(),
        empty_label="Select Facility ...",
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )

    # result = MultiFileField(min_num=1, max_num=12, max_file_size=1024 * 1024 * 5)
    class Meta:
        model = DrtResults
        fields = ["facility_name"]


class MultipleUploadForm(forms.Form):
    files = MultiFileField(min_num=1, max_num=12,
                           max_file_size=1024 * 1024 * 5)  # Adjust max_num and max_file_size as needed


def validate_name(name):
    # Custom validation logic for ensuring two names
    names = name.split()
    if len(names) < 2:
        raise forms.ValidationError("Please enter both first and last names.")


class DrtForm(MultipleUploadForm):
    patient_name = forms.CharField(max_length=150)
    sex = forms.ChoiceField(
        choices=[
            ('', 'Select gender'),
            ("M", "M"),
            ("F", "F"),
        ]
    )
    sequence_summary = forms.ChoiceField(
        choices=[
            ('', 'Select Sequence Summary'),
            ("PASSED", "PASSED"),
            ("FAILED", "FAILED"),
        ]
    )
    # files = forms.FileField(required=False)
    patient_unique_no = forms.IntegerField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(9999999999),  # Assuming you want an 10-digit number
        ],
        required=False
    )

    AGE_UNIT_CHOICES = [("", "Select ..."), ("years", "Years"), ("months", "Months"), ("days", "Days")]
    age = forms.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(150)]
    )
    age_unit = forms.ChoiceField(choices=AGE_UNIT_CHOICES)
    contact = forms.CharField(max_length=150, required=False)
    specimen_type = forms.CharField(max_length=150)
    request_from = forms.CharField(max_length=150)
    requesting_clinician = forms.CharField(max_length=150)
    performed_by = forms.CharField(max_length=150)
    reviewed_by = forms.CharField(max_length=150)
    date_collected = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Date Collected"
    )
    date_received = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Date Received"
    )
    date_reported = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Date Reported"
    )
    date_tested = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Date Tested"
    )
    date_reviewed = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Date Reviewed"
    )

    def clean_performed_by(self):
        performed_by = self.cleaned_data['performed_by']
        validate_name(performed_by)
        return performed_by

    def clean_reviewed_by(self):
        reviewed_by = self.cleaned_data['reviewed_by']
        validate_name(reviewed_by)
        return reviewed_by

    def clean_patient_name(self):
        patient_name = self.cleaned_data['patient_name']
        validate_name(patient_name)
        return patient_name

    # Override clean method to conditionally set files field required
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set files field as not required initially
        self.fields['files'].required = False

    def clean(self):
        cleaned_data = super().clean()
        sequence_summary = cleaned_data.get('sequence_summary')

        if sequence_summary == 'FAILED':
            # If sequence summary is 'FAILED', mark files field as not required
            self.fields['files'].required = False

        return cleaned_data


class DrtPdfFileForm(ModelForm):
    class Meta:
        model = DrtPdfFile
        fields = ["result"]
        labels = {
            'result': 'DRT Results',
        }


class BiochemistryForm(MultipleUploadForm):
    performed_by = forms.CharField(max_length=100, label="Test Performed by")


class HistologyResultsForm(ModelForm):
    facility_name = forms.ModelChoiceField(
        queryset=Facilities.objects.all(),
        empty_label="Select Facility ...",
        widget=forms.Select(attrs={'class': 'form-control select2'}),
    )
    SPECIMEN_CHOICES = [("", "Select ..."), ("cervical biopsy", "Cervical Biopsy"),
                        ("breast tissue biopsy", "Breast Tissue Biopsy"),
                        ("liver biopsy", "Liver biopsy"), ("lymph node biopsy", "Lymph Node biopsy")
                        ]
    specimen_type = forms.ChoiceField(choices=SPECIMEN_CHOICES)

    # result = MultiFileField(min_num=1, max_num=12, max_file_size=1024 * 1024 * 5)
    class Meta:
        model = HistologyResults
        fields = ["facility_name"]


class HistologyForm(MultipleUploadForm):
    patient_name = forms.CharField(max_length=150)
    sex = forms.ChoiceField(
        choices=[
            ('', 'Select gender'),
            ("M", "M"),
            ("F", "F"),
        ]
    )
    # sequence_summary = forms.ChoiceField(
    #     choices=[
    #         ('', 'Select Sequence Summary'),
    #         ("PASSED", "PASSED"),
    #         ("FAILED", "FAILED"),
    #     ]
    # )
    # files = forms.FileField(required=False)
    patient_unique_no = forms.IntegerField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(9999999999),  # Assuming you want an 10-digit number
        ],
        required=False
    )

    # AGE_UNIT_CHOICES = [("", "Select ..."), ("years", "Years"), ("months", "Months"), ("days", "Days")]
    age = forms.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(150)]
    )
    # age_unit = forms.ChoiceField(choices=AGE_UNIT_CHOICES)
    # contact = forms.CharField(max_length=150, required=False)
    # specimen_type = forms.CharField(max_length=150)
    # request_from = forms.CharField(max_length=150)
    # requesting_clinician = forms.CharField(max_length=150)
    performed_by = forms.CharField(max_length=150)
    reviewed_by = forms.CharField(max_length=150)
    date_collected = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Date Collected"
    )
    date_received = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Date Received"
    )
    date_reported = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Date Reported"
    )
    date_tested = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Date Tested"
    )
    date_reviewed = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Date Reviewed"
    )

    def clean_performed_by(self):
        performed_by = self.cleaned_data['performed_by']
        validate_name(performed_by)
        return performed_by

    def clean_reviewed_by(self):
        reviewed_by = self.cleaned_data['reviewed_by']
        validate_name(reviewed_by)
        return reviewed_by

    def clean_patient_name(self):
        patient_name = self.cleaned_data['patient_name']
        validate_name(patient_name)
        return patient_name

    # Override clean method to conditionally set files field required
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set files field as not required initially
        self.fields['files'].required = False

    # def clean(self):
    #     cleaned_data = super().clean()
    #     sequence_summary = cleaned_data.get('sequence_summary')
    #
    #     if sequence_summary == 'FAILED':
    #         # If sequence summary is 'FAILED', mark files field as not required
    #         self.fields['files'].required = False
    #
    #     return cleaned_data


class MultipleUploadForm(forms.Form):
    files = MultiFileField(min_num=1, max_num=12, max_file_size=1024 * 1024 * 5)


class HistologyPdfFileForm(forms.ModelForm):
    class Meta:
        model = HistologyPdfFile
        fields = ['result']
        labels = {
            'result': 'HISTOLOGY Results',
        }
