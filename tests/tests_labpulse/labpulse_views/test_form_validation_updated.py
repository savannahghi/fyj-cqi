from datetime import date, timedelta
import pytest
from apps.labpulse.views import validate_cd4_count_form

"""CD4 form validation.

Validates a CD4 tracking form for adding/updating records.

Validation Details:

- Date validation:
  - Checks date order is logical (eg: collection < receipt etc)
  - Rejects any future dates
- Rejected status:
  - Ensures reason is provided
  - Clears other field values
- Accepted status:
  - Checks for required fields like testing date and CD4 result
  - Validates field combinations like CD4 count vs CRAG result
- Age-based rules:
  - Requires CD4% for age <= 5 
  - Rejects CD4% if age > 5
- CRAG rules:
  - Requires reason if no CRAG result for CD4 <= 200
- Field data types:
  - Validates expected types for fields like integers etc  

Error Handling:

- Adds error messages to specific fields when validation fails
- Stops validation on certain failures, returning errors
- Returns False if any errors, True if validation passes

"""

class MockForm:
    """
    Mock form class used for testing validation.

    Mimics attributes and methods of a Django Form for testing
    form validation functions.
    """

    def __init__(self, cleaned_data):
        """
        Initialize the mock form.
        Args:
            cleaned_data (dict): The form cleaned data to validate.
        """
        self.cleaned_data = cleaned_data
        self.errors = {}

    def add_error(self, field, error):
        """
        Add an error to the form.

        Args:
            field (str): The form field name.
            error (str): The error message.
        """
        if field not in self.errors:
            self.errors[field] = []
        self.errors[field].append(error)


@pytest.mark.django_db
class TestCd4FormValidation:
    """Tests for cd4 form validation."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Fixture to provide baseline form data for tests.

        This fixture runs automatically for all test cases. It provides
        common valid form data that tests can copy and modify as needed.

        Returns:
            dict: Baseline form data with valid fields populated.
        """
        self.base_form_data = {
            'received_status': 'Accepted',
            'reason_for_rejection': '',
            'date_of_collection': date.today(),
            'date_sample_received': date.today(),
            'date_of_testing': date.today(),
            'cd4_count_results': 250,
            'serum_crag_results': 'Negative',
            'reason_for_no_serum_crag': '',
            'cd4_percentage': '',
            'age': 35,
            'patient_unique_no': '1234',
        }

    def test_valid_data(self):
        """Test validation with valid form data."""
        form_data = MockForm(self.base_form_data)
        assert validate_cd4_count_form(form_data, 'Current')

    @pytest.mark.parametrize('report_type', ["Current", "Retrospective"])
    def test_future_dates(self, report_type):
        """Test validation fails with future date fields."""

        form_data = self.base_form_data.copy()

        # Set future dates
        form_data['date_of_collection'] = date.today() + timedelta(days=1)
        form_data['date_sample_received'] = date.today() + timedelta(days=1)
        form_data['date_of_testing'] = date.today() + timedelta(days=1)

        # Add dispatch date for retrospective flow
        if report_type != "Current":
            form_data['date_dispatched'] = date.today()

        form = MockForm(form_data)

        # Validate form
        assert not validate_cd4_count_form(form, report_type)

        # Check form errors
        assert len(form.errors) > 0

        # Check errors based on report type
        if report_type != "Current":
            # Retrospective has dispatch date
            assert 'date_dispatched' in form.errors

        else:
            # Current flow checks other dates
            assert 'date_of_collection' in form.errors
            assert 'date_sample_received' in form.errors
            assert 'date_of_testing' in form.errors

    @pytest.mark.parametrize('report_type', ["Current", "Retrospective"])
    def test_accepted_status_rules(self, report_type):

        """Test validation fails for accepted status with invalid fields."""

        # Test with missing testing date
        form_data = self.base_form_data.copy()
        form_data['date_of_testing'] = None

        # Add dispatch date for retrospective
        if report_type != "Current":
            form_data['date_dispatched'] = date.today()

        form = MockForm(form_data)

        # Validate form
        validate_cd4_count_form(form, report_type)

        # Check for testing date error
        assert 'date_of_testing' in form.errors
        assert 'received_status' in form.errors

        # Test with missing CD4 result
        form_data = self.base_form_data.copy()
        form_data['cd4_count_results'] = None

        if report_type != "Current":
            form_data['date_dispatched'] = date.today()

        form = MockForm(form_data)

        # Validate form
        validate_cd4_count_form(form, report_type)

        # Check for CD4 result error
        assert 'cd4_count_results' in form.errors
        assert 'received_status' in form.errors

    @pytest.mark.parametrize('report_type', ["Current", "Retrospective"])
    def test_invalid_age_cd4_should_fail(self, report_type):

        """Test validation fails for invalid age and CD4% combination."""

        # Set invalid age and CD4%
        form_data = self.base_form_data.copy()
        form_data['age'] = 10
        form_data['cd4_percentage'] = 80

        # Add dispatch date for retrospective flow
        if report_type != "Current":
            form_data['date_dispatched'] = date.today()

        form = MockForm(form_data)

        # Validate form
        validate_cd4_count_form(form, report_type)

        # Check for errors on both fields
        assert 'age' in form.errors
        assert 'cd4_percentage' in form.errors

        # Validate error messages
        assert form.errors['age'][0] == "CD4 % values ought to be for <=5yrs."
        assert form.errors['cd4_percentage'][0] == "CD4 % values ought to be for <=5yrs."

    @pytest.mark.parametrize('report_type', ["Current", "Retrospective"])
    def test_invalid_cd4_crag_combo_should_fail(self, report_type):

        """Test validation fails for invalid CD4/CRAG combination."""

        # Set invalid CD4/CRAG values
        form_data = self.base_form_data.copy()
        form_data['cd4_count_results'] = 250
        form_data['serum_crag_results'] = None
        form_data['reason_for_no_serum_crag'] = 'Reason'

        # Add dispatch date for retrospective
        if report_type != "Current":
            form_data['date_dispatched'] = date.today()

        form = MockForm(form_data)

        # Validate form
        validate_cd4_count_form(form, 'Current')

        # Check for errors on all fields
        assert 'cd4_count_results' in form.errors
        assert 'serum_crag_results' in form.errors
        assert 'reason_for_no_serum_crag' in form.errors

        # Validate error messages
        assert form.errors['cd4_count_results'][0] == "Check if the information is correct"
        assert form.errors['serum_crag_results'][0] == "Check if the information is correct"
        assert form.errors['reason_for_no_serum_crag'][0] == "Check if the information is correct"

    @pytest.mark.parametrize('report_type', ["Current", "Retrospective"])
    def test_invalid_date_order_should_fail(self, report_type):

        """Test validation fails for invalid date order."""

        # Set invalid date order
        form_data = self.base_form_data.copy()
        form_data['date_of_collection'] = date(2023, 2, 1)
        form_data['date_sample_received'] = date(2023, 1, 30)

        # Add dispatch date for retrospective flow
        if report_type != "Current":
            form_data['date_dispatched'] = date.today()

        form = MockForm(form_data)

        # Validate form
        validate_cd4_count_form(form, report_type)

        # Check for errors on date fields
        assert 'date_of_collection' in form.errors
        assert 'date_sample_received' in form.errors

    @pytest.mark.parametrize('cd4_percentage', [-1, 101])
    @pytest.mark.parametrize('report_type', ["Current", "Retrospective"])
    def test_invalid_cd4_percentage_should_fail(self, cd4_percentage, report_type):

        """Test validation fails for invalid CD4 percentage values."""

        # Set valid age
        form_data = self.base_form_data.copy()
        form_data['age'] = 3

        # Set invalid CD4 percentage
        form_data['cd4_percentage'] = cd4_percentage

        # Add dispatch date for retrospective
        if report_type != "Current":
            form_data['date_dispatched'] = date.today()

        form = MockForm(form_data)

        # Validate form
        validate_cd4_count_form(form, report_type)

        # Check for errors on both fields
        assert len(form.errors) == 0
        assert 'age' not in form.errors
        assert 'cd4_percentage' not in form.errors

    @pytest.mark.parametrize('received_status', ['Rejected', 'Accepted'])
    def test_invalid_received_status(self, received_status):

        """Test validation fails for invalid received status values."""

        # Copy baseline form data
        form_data = self.base_form_data.copy()

        # Set invalid received status
        form_data['received_status'] = received_status

        # Remove required fields based on status
        if received_status == 'Rejected':
            form_data['reason_for_rejection'] = ''

        elif received_status == 'Accepted':
            form_data['cd4_count_results'] = None

        # Create form and validate
        form = MockForm(form_data)
        validate_cd4_count_form(form, 'Current')

        # Check for expected error
        if received_status == 'Rejected':
            assert 'reason_for_rejection' in form.errors

        elif received_status == 'Accepted':
            assert 'cd4_count_results' in form.errors

    def test_future_dispatch_date_fails(self):

        """Test validation fails with future dispatch date."""

        # Copy baseline form data
        form_data = self.base_form_data.copy()

        # Set future dispatch date
        form_data['date_dispatched'] = date.today() + timedelta(days=1)

        form = MockForm(form_data)

        # Validate form
        assert not validate_cd4_count_form(form, "Retrospective")

        # Check for dispatch date error
        assert 'date_dispatched' in form.errors

        # Validate error message
        assert form.errors['date_dispatched'][0] == "Date of sample dispatched cannot be in the future."

    def test_received_after_dispatch_fails(self):

        """Test validation fails if received date is after dispatch date."""

        # Copy baseline form data
        form_data = self.base_form_data.copy()

        # Set dispatch date
        form_data['date_dispatched'] = date.today()

        # Set received date after dispatch
        form_data['date_sample_received'] = date.today() + timedelta(days=1)

        form = MockForm(form_data)

        # Validate form
        assert not validate_cd4_count_form(form, 'Retrospective')

        # Check for errors on both date fields
        assert 'date_sample_received' in form.errors
        assert 'date_dispatched' in form.errors

    def test_testing_after_dispatch_fails(self):

        """Test validation fails if testing date is after dispatch date."""

        # Copy baseline form data
        form_data = self.base_form_data.copy()

        # Set dispatch date
        form_data['date_dispatched'] = date.today()

        # Set testing date after dispatch
        form_data['date_of_testing'] = date.today() + timedelta(days=1)

        form = MockForm(form_data)

        # Validate form
        assert not validate_cd4_count_form(form, 'Retrospective')

        # Check for errors on both date fields
        assert 'date_of_testing' in form.errors
        assert 'date_dispatched' in form.errors

    @pytest.mark.parametrize('report_type', ['Current', 'Retrospective'])
    def test_testing_less_collection_date_should_fails(self, report_type):

        """Test validation fails if testing date is less than collection date."""

        # Copy baseline form data
        form_data = self.base_form_data.copy()

        # Set accepted status
        form_data['received_status'] = "Accepted"

        # Set invalid date order
        form_data['date_of_collection'] = date.today() + timedelta(days=1)
        form_data['date_of_testing'] = date.today()

        # Add dispatch date for retrospective
        if report_type != "Current":
            form_data['date_dispatched'] = date.today()

        form = MockForm(form_data)

        # Validate form
        assert not validate_cd4_count_form(form, report_type)

        # Check for expected errors
        if report_type != "Current":
            # Retrospective checks dispatch date
            assert 'date_dispatched' in form.errors
        else:
            # Current checks collection date
            assert 'date_of_collection' in form.errors

    @pytest.mark.parametrize('report_type', ['Current', 'Retrospective'])
    def test_testing_before_collection_fails(self, report_type):

        """Test validation fails if testing date is before collection date."""

        # Copy baseline form data
        form_data = self.base_form_data.copy()

        # Set accepted status
        form_data['received_status'] = "Accepted"

        # Set testing before collection
        form_data['date_of_collection'] = date.today()
        form_data['date_of_testing'] = date.today() - timedelta(days=1)

        # Add dispatch date for retrospective
        if report_type != "Current":
            form_data['date_dispatched'] = date.today()

        form = MockForm(form_data)

        # Validate form
        validate_cd4_count_form(form, report_type)

        # Check for errors on both date fields
        assert len(form.errors) == 2
        assert 'date_of_testing' in form.errors
        assert 'date_of_collection' in form.errors

    @pytest.mark.parametrize('report_type', ['Current', 'Retrospective'])
    def test_testing_before_received_fails(self, report_type):

        """Test validation fails if testing date is before received date."""

        # Copy baseline form data
        form_data = self.base_form_data.copy()

        # Set accepted status
        form_data['received_status'] = "Accepted"

        # Set testing before received
        form_data['date_of_collection'] = date(2020, 1, 1)
        form_data['date_sample_received'] = date(2020, 2, 1)
        form_data['date_of_testing'] = date(2020, 1, 1)

        # Add dispatch date
        if report_type != "Current":
            form_data['date_dispatched'] = date.today()

        form = MockForm(form_data)

        # Validate form
        validate_cd4_count_form(form, report_type)

        # Check for errors on date fields
        assert len(form.errors) == 2
        assert 'date_of_testing' in form.errors
        assert 'date_sample_received' in form.errors

    def test_rejected_no_reason(self):

        """Test validation fails when rejected status with no reason."""

        # Copy baseline form data
        form_data = self.base_form_data.copy()

        # Set rejected status
        form_data['received_status'] = 'Rejected'

        # Leave reason blank
        form_data['reason_for_rejection'] = ''

        form = MockForm(form_data)

        # Validate form
        assert not validate_cd4_count_form(form, 'Current')

        # Check for missing reason error
        assert 'reason_for_rejection' in form.errors

    def test_rejected_with_other_fields(self):

        """Test validation fails when rejected status has other fields filled."""

        # Copy baseline form data
        form_data = self.base_form_data.copy()

        # Set rejected status
        form_data['received_status'] = 'Rejected'

        # Add valid reason
        form_data['reason_for_rejection'] = 'Insufficient Volume'


        # Invalid - fields
        form_data['cd4_count_results'] = 250
        form_data['reason_for_no_serum_crag'] = 'Reagents Stock outs'

        form = MockForm(form_data)

        # Validate form
        assert not validate_cd4_count_form(form, 'Current')

        # Check for CD4 result error
        assert 'cd4_count_results' in form.errors
        assert 'reason_for_no_serum_crag' in form.errors

    def test_missing_cd4_percent_under_5_fails(self):
        """Test validation fails if CD4 percentage missing when age <= 5."""

        # Copy baseline valid form data
        form_data = self.base_form_data.copy()

        # Set age <= 5
        form_data['age'] = 3

        # Remove CD4 percentage
        form_data['cd4_percentage'] = None

        # Create form and validate
        form = MockForm(form_data)
        assert  validate_cd4_count_form(form, 'Current')

        # Check for errors on both age and cd4_percentage
        assert len(form.errors) == 0
        assert 'age' not in form.errors
        assert 'cd4_percentage' not in form.errors

    def test_no_crag_reason_under_200_cd4_fails(self):
        """Test validation fails if no CRAG reason when CD4 <= 200."""

        # Copy valid form data
        form_data = self.base_form_data.copy()

        # Set CD4 <= 200
        form_data['cd4_count_results'] = 180

        # Set no CRAG result
        form_data['serum_crag_results'] = None

        # Set no reason for no CRAG
        form_data['reason_for_no_serum_crag'] = None

        # Create form and validate
        form = MockForm(form_data)
        assert not validate_cd4_count_form(form, 'Current')

        # Check for errors on all fields
        assert len(form.errors) == 3
        assert 'cd4_count_results' in form.errors
        assert 'serum_crag_results' in form.errors
        assert 'reason_for_no_serum_crag' in form.errors

    def test_crag_and_reason_fails(self):
        """Test validation fails if both CRAG result and no CRAG reason given."""

        # Copy valid form data
        form_data = self.base_form_data.copy()

        # Set CRAG result
        form_data['serum_crag_results'] = 'Positive'

        # Also set reason for no CRAG
        form_data['reason_for_no_serum_crag'] = 'Reason'

        # Create form and validate
        form = MockForm(form_data)
        assert not validate_cd4_count_form(form, 'Current')

        # Check for errors on both fields
        assert len(form.errors) == 2
        assert 'serum_crag_results' in form.errors
        assert 'reason_for_no_serum_crag' in form.errors
