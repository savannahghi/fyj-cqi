import datetime

from django.forms import ModelForm, Textarea
from django import forms

from apps.cqi.models import Facilities
from apps.dqa.form import AuditTeamForm
from apps.pharmacy.models import PharmacyRecords, StockCards, UnitSupplied, BeginningBalance, \
    PositiveAdjustments, UnitIssued, NegativeAdjustment, ExpiredUnits, Expired, ExpiryTracking, \
    StockManagement, S11FormAvailability, S11FormEndorsed, WorkPlan, PharmacyAuditTeam


class RegistersForm(forms.Form):
    register_name = forms.ChoiceField(
        choices=[
            ('', 'Select indicator'),
            ("Malaria Commodities DAR (MoH 645)", "Malaria Commodities DAR (MoH 645)"),
            ("ARV Daily Activity Register (DAR) (MOH 367A)/WebADT",
             "ARV Daily Activity Register (DAR) (MOH 367A)/WebADT"),
            ("ARV F-MAPS (MOH 729B)", "ARV F-MAPS (MOH 729B)"),
            ("DADR-Anti TB register", "DADR-Anti TB register"),
            ("Family Planning Commodities Daily Activity Register (DAR) (MOH 512)",
             "Family Planning Commodities Daily Activity Register (DAR) (MOH 512)"),
            ("Delivery notes file", "Delivery notes file"),
        ]
    )


class ReportNameForm(forms.Form):
    report_name = forms.ChoiceField(
        choices=[
            ('', 'Select indicator'),
            ("stock_cards", "stock_cards"),
            ("unit_supplied", "unit_supplied"),
            ("quantity_delivered", "quantity_delivered"),
            ("beginning_balance", "beginning_balance"),
            ("unit_received", "unit_received"),
            ("s11_form", "s11_form"),
            ("positive_adjustments", "positive_adjustments"),
            ("unit_issued", "unit_issued"),
            ("negative_adjustment", "negative_adjustment"),
            ("stock_outs", "stock_outs"),
            ("expiries", "expiries"),
            ("expired_units", "expired_units"),
            ("expiry_tracking", "expiry_tracking"),
            ("stock_management", "stock_management"),
        ]
    )


class DateSelectionForm(forms.Form):
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Interview date"
    )


class BaseForm(forms.ModelForm):
    class Meta:
        exclude = ['created_by', 'modified_by', 'quarter_year', 'facility_name']
        abstract = True
        widgets = {
            'description': Textarea(attrs={'readonly': 'readonly', 'rows': '4',
                                           'style': 'width: 250px; font-weight: bold; background-color: #6c757d;color: '
                                                    'white; resize: none;padding: 8px; border: none; box-shadow: none;'
                                                    'border-radius: 10px;'}),
            'comments': forms.Textarea(attrs={'size': '40', 'rows': '3'})
        }


class PharmacyRecordsForm(forms.ModelForm):
    date_report_submitted = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="",
        required=False
    )

    class Meta(BaseForm.Meta):
        model = PharmacyRecords
        exclude = BaseForm.Meta.exclude + ['register_name']
        labels = {
            'date_of_interview': '',
            'register_available': '',
            'currently_in_use': '',
            'last_month_copy': '',
            'comments': '',
            'facility_name': '',
            'quarter_year': '',
        }


class BaseReportForm(BaseForm):
    class Meta(BaseForm.Meta):
        abstract = True
        # Common meta options go here

    def __init__(self, *args, **kwargs):
        # Call the parent constructor method
        super().__init__(*args, **kwargs)
        # Loop through all the fields in the form
        for field in self.fields:
            # Set the label of each field to False
            self.fields[field].label = False


class StockCardsForm(BaseReportForm):
    class Meta(BaseReportForm.Meta):
        model = StockCards


class UnitSuppliedForm(BaseReportForm):
    class Meta(BaseReportForm.Meta):
        model = UnitSupplied


class BeginningBalanceForm(BaseReportForm):
    class Meta(BaseReportForm.Meta):
        model = BeginningBalance


# class UnitReceivedForm(BaseReportForm):
#     class Meta(BaseReportForm.Meta):
#         model = UnitReceived


class PositiveAdjustmentsForm(BaseReportForm):
    class Meta(BaseReportForm.Meta):
        model = PositiveAdjustments


class UnitIssuedForm(BaseReportForm):
    class Meta(BaseReportForm.Meta):
        model = UnitIssued


class NegativeAdjustmentForm(BaseReportForm):
    class Meta(BaseReportForm.Meta):
        model = NegativeAdjustment


class ExpiredUnitsForm(BaseReportForm):
    class Meta(BaseReportForm.Meta):
        model = ExpiredUnits


class ExpiredForm(BaseReportForm):
    class Meta(BaseReportForm.Meta):
        model = Expired


class ExpiryTrackingForm(BaseReportForm):
    class Meta(BaseReportForm.Meta):
        model = ExpiryTracking


class StockManagementForm(BaseReportForm):
    class Meta(BaseReportForm.Meta):
        model = StockManagement


class S11FormAvailabilityForm(BaseReportForm):
    class Meta(BaseReportForm.Meta):
        model = S11FormAvailability


class S11FormEndorsedForm(BaseReportForm):
    class Meta(BaseReportForm.Meta):
        model = S11FormEndorsed


class WorkPlanForm(BaseForm):
    complete_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Due Date for Action Plan Completion",
        required=False
    )

    class Meta(BaseReportForm.Meta):
        model = WorkPlan
        # exclude = ['stock_cards', 'unit_supplied', 'beginning_balance', 'pharmacy_records',
        #            'positive_adjustments', 'unit_issued', 'negative_adjustment', 'expired_units',
        #            'expired', 'expiry_tracking', 's11_form_availability', 's11_form_endorsed',
        #            'stock_management']


class PharmacyAuditTeamForm(ModelForm):
    class Meta:
        model = PharmacyAuditTeam
        exclude = ['facility_name', 'modified_by', 'created_by', 'quarter_year']
        labels = {
            'name': 'Name (First and Last name)',
        }


class FacilityForm(forms.Form):
    name = forms.ModelChoiceField(
        queryset=Facilities.objects.none(),  # Start with an empty queryset
        empty_label="All Facilities",
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        required=False,
        initial=None,
    )

    def __init__(self, *args, selected_year=None, selected_quarter=None, **kwargs):
        initial = kwargs.get('initial', {})
        super().__init__(*args, **kwargs)
        self.fields['name'].initial = initial.get('name')

        # Only filter the queryset if both selected_year and selected_quarter are provided
        if selected_year and selected_quarter:
            models_to_check = [
                StockCards, UnitSupplied, BeginningBalance, PositiveAdjustments, UnitIssued,
                NegativeAdjustment, ExpiredUnits, Expired, ExpiryTracking, S11FormAvailability,
                S11FormEndorsed, StockManagement,
            ]

            # Get the IDs of facilities that have related records in the models_to_check
            facility_ids = set()
            for model in models_to_check:
                facility_ids.update(
                    model.objects.filter(
                        quarter_year__quarter_year=f"{selected_quarter}-{selected_year[-2:]}"
                    ).values_list('facility_name_id', flat=True)
                )

            # Update the queryset with the filtered facilities
            self.fields['name'].queryset = Facilities.objects.filter(id__in=facility_ids)


class YearSelectForm(forms.Form):
    current_year = datetime.datetime.now().year
    YEAR_CHOICES = [(str(x), str(x)) for x in range(2021, current_year + 1)]
    year = forms.ChoiceField(
        choices=YEAR_CHOICES,
        label="FY",
        widget=forms.Select(attrs={'id': 'year-select'})
    )


class QuarterSelectForm(forms.Form):
    quarter = forms.ChoiceField(
        choices=[
            ('Qtr1', 'Qtr1'),
            ('Qtr2', 'Qtr2'),
            ('Qtr3', 'Qtr3'),
            ('Qtr4', 'Qtr4'),
        ],
        widget=forms.Select(attrs={'id': 'quarter-select'})
    )
