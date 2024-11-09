import datetime

import pytest
from django.contrib.auth.models import Permission
from django.contrib.messages import get_messages
from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed

from apps.account.models import CustomUser
from apps.cqi.models import Counties, Facilities, Sub_counties
from apps.labpulse.forms import Cd4trakerForm, Cd4trakerManualDispatchForm
from apps.labpulse.models import Cd4TestingLabs, Cd4traker

"""
Code Analysis for add_cd4_count view

Overview:
- Allows adding a new CD4 count entry via a form
- Handles Current and Retrospective report types
- Restricted to users in 'laboratory_staffs_labpulse' group

Input Validation:
- Uses @login_required and @group_required decorators for access control
- Checks user has a first_name before proceeding 

Database Logic:
- Gets or creates the selected lab based on ID
- Loops through models to lookup related county/sub-county
- Filters facilities to find one matching form
- Creates new Cd4traker model instance from form  

Form Handling:
- Instantiates form class based on report type
- Renders form on GET request
- Validates and saves form on POST 
- Renders errors if form is invalid

Redirects:
- Redirects to profile page if no first_name
- Redirects to same page on success to prevent dupe submits

Error Handling:
- Checks permission and redirects or displays error response
- Displays errors if form is invalid

Additional aspects:
- The function uses the 'login_required' and 'group_required' decorators to restrict access
  to authenticated users who belong to the 'laboratory_staffs_labpulse' group.
- The function uses the Cd4TestingLabForm to validate and save the new CD4 Testing Lab.
- The function displays error messages if the form is not valid or a CD4 Testing Lab with the same name already exists.

Opportunities:
- Additional validation on fields
- Consistent error handling via exceptions
- Use Django messages for errors and success
- Improve readability with helper functions
"""


@pytest.fixture
def lab():
    return Cd4TestingLabs.objects.create(testing_lab_name='Test Lab', mfl_code=1234)


@pytest.fixture
def facility():
    return Facilities.objects.create(name='Test Facility', mfl_code=12345)


@pytest.fixture
def county():
    return Counties.objects.create(county_name='Test County')


@pytest.fixture
def sub_county():
    return Sub_counties.objects.create(sub_counties='Test sub county')


@pytest.mark.django_db
class TestAddCd4Counts:
    @pytest.mark.parametrize('group_client', ['laboratory_staffs_labpulse'], indirect=True)
    @pytest.mark.parametrize('report_type', ['Current', 'Retrospective'])
    def test_get_add_cd4_count_current_has_correct_form_fields(self, group_client, lab, report_type):
        """
        Test GET request returns correct form for valid user.

        Checks current and retrospective report views display expected form fields.
        """

        url = reverse('add_cd4_count', kwargs={'report_type': report_type, 'pk_lab': lab.id})

        if report_type != "Current":
            # Assign required permission for retrospective view
            permission = Permission.objects.get(codename='view_add_retrospective_cd4_count')
            user = CustomUser.objects.get(username='test')
            user.user_permissions.add(permission)
            user.save()

        # Send GET request
        response = group_client.get(url)

        # Assert 200 OK status
        assert response.status_code == 200

        # Check correct form is passed in context
        assert 'form' in response.context
        if report_type != "Current":
            assert isinstance(response.context['form'], Cd4trakerManualDispatchForm)
        else:
            assert isinstance(response.context['form'], Cd4trakerForm)

        # Validate form field labels
        # assert response.context['title'] == f"Add CD4 Results for {lab.testing_lab_name.title()} (Testing Laboratory)"
        assert response.context['form'].fields['tb_lam_results'].label == 'TB LAM results'
        assert response.context['form'].fields['age'].label == 'Age'
        assert response.context['form'].fields['patient_unique_no'].label == 'Patient unique no'
        if report_type != "Current":
            assert response.context['form'].fields['date_dispatched'].label == 'Dispatch date'

        # Check correct template used
        assertTemplateUsed(response, 'lab_pulse/add_cd4_data.html')

    @pytest.mark.parametrize('group_client', ['laboratory_staffs_labpulse'], indirect=True)
    def test_get_add_cd4_count_retrospective_should_fail(self, group_client, lab):
        """
        Test GET request without permission returns 403.

        Checks retrospective report type view requires permission.
        """

        url = reverse('add_cd4_count', kwargs={'report_type': 'Retrospective', 'pk_lab': lab.id})

        # Make request without view_add_retrospective permission
        response = group_client.get(url)

        # Assert 403 status code
        assert response.status_code == 403

        # Check response content for error message
        response_content = response.content.decode('utf-8')
        assert "You don't have permission to access this form." in response_content

    # @pytest.mark.parametrize('group_client', ['laboratory_staffs_labpulse'], indirect=True)
    # @pytest.mark.parametrize('report_type', ['Current', 'Retrospective'])
    # def test_valid_form_update_db_saves_and_redirects(self, group_client, lab, facility, county, report_type):
    #     """
    #     Test valid form submission saves data and redirects.
    #
    #     Covers both Current and Retrospective report types.
    #     """
    #
    #     if report_type != "Current":
    #         # Give user required retrospective permission
    #         permission = Permission.objects.get(codename='view_add_retrospective_cd4_count')
    #         user = CustomUser.objects.get(username='test')
    #         user.user_permissions.add(permission)
    #         user.save()
    #
    #     # Build URL with parameters
    #     url = reverse('add_cd4_count', kwargs={'report_type': report_type, 'pk_lab': lab.id})
    #
    #     # Valid form data
    #     form_data = {
    #         "received_status": "Rejected",
    #         "reason_for_rejection": "Improper Collection Technique",
    #         "sex": "M",
    #         "date_of_collection": datetime.date(2023, 1, 1),
    #         "date_sample_received": datetime.date(2023, 1, 1),
    #         "date_dispatched": datetime.date(2023, 1, 1),
    #         "cd4_count_results": "",
    #         "serum_crag_results": "",
    #         "cd4_percentage": "",
    #         "age": 34,
    #         "facility_name": facility.pk,
    #         "testing_laboratory": lab.pk,
    #         "patient_unique_no": "2345678901",
    #     }
    #
    #     # Submit valid form
    #     response = group_client.post(url, form_data)
    #     # Check success message
    #     messages = get_messages(response.wsgi_request)
    #     message_texts = [m.message for m in messages]
    #     assert "Record saved successfully!" in message_texts
    #
    #     # Assert redirect response
    #     assert response.status_code == 302
    #     assert response.url == reverse('add_cd4_count', kwargs={'report_type': report_type, 'pk_lab': lab.id})
    #
    #     # Check success message
    #     messages = get_messages(response.wsgi_request)
    #     message_texts = [m.message for m in messages]
    #     assert "Record saved successfully!" in message_texts
    #
    #     # Verify data was saved
    #     assert Cd4traker.objects.filter(
    #         received_status="Rejected",
    #         reason_for_rejection="Improper Collection Technique"
    #     ).exists()

    # @pytest.mark.parametrize('group_client', ['laboratory_staffs_labpulse'], indirect=True)
    # @pytest.mark.parametrize('report_type', ['Current', 'Retrospective'])
    # def test_invalid_form_update_db_stays_on_page_and_shows_errors(self, group_client, lab, facility, county,
    #                                                                report_type):
    #     """
    #     Test submitting an invalid form displays expected errors.
    #
    #     Covers both Current and Retrospective report types.
    #     """
    #
    #     if report_type != "Current":
    #         # Give user required retrospective permission
    #         permission = Permission.objects.get(codename='view_add_retrospective_cd4_count')
    #         user = CustomUser.objects.get(username='test')
    #         user.user_permissions.add(permission)
    #         user.save()
    #
    #     # Build URL and submit invalid form data
    #     url = reverse('add_cd4_count', kwargs={'report_type': report_type, 'pk_lab': lab.id})
    #     form_data = {"received_status": "Accepted",
    #                  "reason_for_rejection": "Improper Collection Technique",  # Invalid field
    #                  "sex": "M", "date_of_collection": datetime.date(2023, 1, 1),
    #                  "date_sample_received": datetime.date(2023, 1, 1),
    #                  "date_dispatched": datetime.date(2023, 1, 1),
    #                  "cd4_count_results": "", "serum_crag_results": "",
    #                  "cd4_percentage": "", "age": 34, "facility_name": facility.pk,
    #                  "testing_laboratory": lab.pk, "patient_unique_no": "2345678901", }
    #
    #     response = group_client.post(url, form_data)
    #
    #     # Check form errors
    #     form_errors = response.context['form'].errors
    #
    #     # Assert expected error messages
    #     assert "Check if this information is correct" in form_errors['received_status'][0]
    #     assert "Check if this information is correct" in form_errors['reason_for_rejection'][0]
