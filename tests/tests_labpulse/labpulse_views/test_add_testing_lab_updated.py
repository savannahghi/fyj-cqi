import pytest
from django.contrib.messages import get_messages
from django.test import Client
from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed

from apps.account.models import CustomUser
from apps.labpulse.forms import Cd4TestingLabForm
from apps.labpulse.models import Cd4TestingLabs

"""
Code Analysis for add_testing_lab view

Overview:
- Allows adding a new CD4 testing lab entry via a form
- Handles form submission for both GET and POST requests
- Performs input validation and database operations
- Applies access control based on user authentication and group membership

Input Validation:
- Uses @login_required and @group_required decorators for access control
- Checks if the user has a first_name before proceeding

Database Logic:
- Retrieves all existing CD4 testing labs
- Performs database operations to get or create the selected lab
- Performs model lookups to retrieve related county and sub-county
- Filters facilities to find a match based on the form data

Form Handling:
- Instantiates the Cd4TestingLabForm based on the request method
- Renders the form on a GET request
- Validates the form and saves it on a POST request
- Adds form errors if the form is invalid
- Saves the form data and redirects on successful form submission

Redirects:
- Redirects to the profile page if the user doesn't have a first_name
- Redirects to the "choose_testing_lab" page on successful form submission

Error Handling:
- Checks user permissions and redirects or displays an error response
- Displays form errors if the form is invalid

Additional Aspects:
- The function uses the "login_required" and "group_required" decorators for access control and security.
- The Cd4TestingLabForm is used to validate and save the new CD4 testing lab entry.
- The function displays appropriate error messages if the form is not valid or a CD4 testing lab with the same name already exists.

Opportunities:
- Consistent error handling using exceptions could be considered.
- Django messages could be used for displaying errors and success messages.
- Readability could be improved by introducing helper functions.

"""
@pytest.mark.django_db
class TestAddTestingLabView:
    """
    Test cases for the add_testing_lab view.
    """

    def test_login_required_should_redirect(self, mock_lab_queryset):
        """
        Test that accessing the add testing labs view without login redirects to the login page.
        """
        client = Client()

        url = reverse('add_testing_lab')

        response = client.get(url)

        # Assert redirection to the login page
        assert response.status_code == 302
        assert '/login/' in response.url

    @pytest.mark.parametrize('group_client', ['laboratory_staffs_labpulse'], indirect=True)
    def test_login_required_should_succeed(self, mock_lab_queryset, group_client):
        """
        Test that accessing the add testing labs view with a logged-in user succeeds.
        """
        # Using reverse() to resolve the URL helps avoid hardcoding.
        url = reverse('add_testing_lab')

        # Make the request
        response = group_client.get(url)

        # Assert 200 OK status
        assert response.status_code == 200

        # Verify context data
        assert 'form' in response.context
        assert response.context['form'] is not None

    @pytest.mark.parametrize('group_client', ['laboratory_staffs_labpulse'], indirect=True)
    def test_first_name_should_redirect(self, mock_lab_queryset, group_client):
        """
        Test that accessing the add testing labs view without first_name redirects to the profile page.
        """

        url = reverse('add_testing_lab')

        # Remove first_name from user
        user = CustomUser.objects.get(username='test')
        user.first_name = ""
        user.save()

        response = group_client.get(url)

        # Assert redirection to the profile page
        assert response.status_code == 302
        assert '/profile/' in response.url

    @pytest.mark.parametrize('group_client', ['laboratory_staffs_labpulse'], indirect=True)
    def test_add_testing_lab_form_submission_success(self, group_client):
        """
        Test that a successful form submission redirects and shows the success message.
        """
        url = reverse('add_testing_lab')

        # Create a POST request with form data
        form_data = {
            'testing_lab_name': 'Test Lab',
            'mfl_code': 123456,
        }
        response = group_client.post(url, data=form_data)

        # Assert that the response redirects
        assert response.status_code == 302
        assert response.url == reverse('choose_testing_lab')

        # Check success message
        messages = get_messages(response.wsgi_request)
        message_texts = [m.message for m in messages]
        assert "Record saved successfully!" in message_texts

    @pytest.mark.parametrize('group_client', ['laboratory_staffs_labpulse'], indirect=True)
    def test_get_request_should_show_form(self, mock_lab_queryset, group_client):
        """
        Test that a GET request renders the add CD4 testing lab form.
        """
        # Resolve update URL dynamically
        url = reverse('add_testing_lab')
        response = group_client.get(url)

        # Verify successful response
        assert response.status_code == 200

        # Validate form in response context
        assert 'form' in response.context
        assert isinstance(response.context['form'], Cd4TestingLabForm)
        assert response.context['form'].fields['testing_lab_name'].label == 'Testing lab name'
        assert response.context['form'].fields['mfl_code'].label == 'Mfl code'

        # Confirm correct template used
        assertTemplateUsed(response, 'lab_pulse/add_cd4_data.html')

    @pytest.mark.parametrize('group_client', ['laboratory_staffs_labpulse'], indirect=True)
    def test_add_testing_lab_duplicate_name(self, group_client):
        """
        Test that a form error is displayed when trying to add a testing lab with a duplicate name.
        """
        url = reverse('add_testing_lab')

        # Create a testing lab with the same name as an existing one
        Cd4TestingLabs.objects.create(
            testing_lab_name='Test Lab',
            mfl_code=123456
        )

        # Create a POST request with form data
        form_data = {
            'testing_lab_name': 'Test Lab',
            'mfl_code': 1234567,
        }
        response = group_client.post(url, data=form_data)

        # Assert that the response renders the same page
        assert response.status_code == 200

        # Check form errors
        form_errors = response.context['form'].errors

        # Assert expected error message
        assert "Cd4 testing labs with this Testing lab name already exists." in form_errors['testing_lab_name'][0]
