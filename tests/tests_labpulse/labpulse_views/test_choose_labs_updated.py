import pytest
from django.contrib.auth.models import Permission
from django.test import Client
from django.urls import reverse

from apps.account.models import CustomUser
from apps.labpulse.models import Cd4TestingLabs

"""Code Analysis for choose_testing_lab and choose_testing_lab_manual views

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
- Redirects to same page on success to prevent duplicate submissions

Permission Restriction:
- For the choose_testing_lab_manual view, the user must have the 'view_add_retrospective_cd4_count' permission in addition to being in the 'laboratory_staffs_labpulse' group.

Error Handling:
- Checks permission and redirects or displays error response
- Displays errors if form is invalid

Additional aspects:
- The views use the 'login_required' and 'group_required' decorators to restrict access to authenticated users who belong to the 'laboratory_staffs_labpulse' group.
- The choose_testing_lab_manual view additionally requires the 'view_add_retrospective_cd4_count' permission.
- The views use the Cd4TestingLabForm to validate and save the new CD4 Testing Lab.
- The views display error messages if the form is not valid or a CD4 Testing Lab with the same name already exists.

Opportunities:
- Additional validation on fields
- Consistent error handling via exceptions
- Use Django messages for errors and success
- Improve readability with helper functions
"""



@pytest.mark.django_db
class TestChooseTestingLabs:
    @pytest.mark.parametrize('url_path', ['choose_testing_lab', 'choose_testing_lab_manual'])
    @pytest.mark.parametrize('group_client', ['laboratory_staffs_labpulse'], indirect=True)
    def test_valid_form(self, group_client, url_path):
        """
        Test that a valid form submission redirects to the appropriate add_cd4_count view with the correct URL.
        """
        if "manual" in url_path:
            # Give user required permission
            permission = Permission.objects.get(codename='view_add_retrospective_cd4_count')
            user = CustomUser.objects.get(username='test')
            user.user_permissions.add(permission)
            user.save()

        # Make the POST request to the target URL
        url = reverse(url_path)
        lab = Cd4TestingLabs.objects.create(testing_lab_name='Test Lab', mfl_code=1234)
        form_data = {'testing_lab_name': lab.pk}
        response = group_client.post(url, form_data)

        # Assert the response status code
        assert response.status_code == 302

        # Determine the report_type based on the URL path
        report_type = 'Retrospective' if "manual" in url_path else 'Current'

        # Generate the expected URL for the add_cd4_count view
        expected_url = reverse('add_cd4_count', kwargs={'report_type': report_type, 'pk_lab': lab.pk})

        # Assert that the response URL matches the expected URL
        assert response.url == expected_url

    @pytest.mark.parametrize('url_path', ['choose_testing_lab', 'choose_testing_lab_manual'])
    @pytest.mark.parametrize('group_client', ['laboratory_staffs_labpulse'], indirect=True)
    def test_invalid_form(self, group_client, url_path):
        """
        Test that an invalid form submission renders the appropriate view with the expected context.
        """
        if "manual" in url_path:
            # Give user required permission
            permission = Permission.objects.get(codename='view_add_retrospective_cd4_count')
            user = CustomUser.objects.get(username='test')
            user.user_permissions.add(permission)
            user.save()

        # Make the POST request to the target URL with empty form data
        url = reverse(url_path)
        form_data = {}
        response = group_client.post(url, form_data)

        # Assert the response status code
        assert response.status_code == 200

        # Assert the presence of expected context variables
        assert 'cd4_testing_lab_form' in response.context
        assert 'title' in response.context

    def test_user_not_logged_in(self):
        """
        Test that a user who is not logged in is redirected to the login page.
        """
        url = reverse('choose_testing_lab')
        client = Client()
        response = client.get(url)

        # Assert the response status code
        assert response.status_code == 302

        # Assert that the response URL starts with the login URL
        assert response.url.startswith(reverse('login'))

    def test_user_no_group_membership(self, authenticated_client):
        """
        Test that a user who does not have membership in the 'laboratory_staffs_labpulse' group
        is redirected to the login page.
        """
        url = reverse('choose_testing_lab')
        response = authenticated_client.get(url)

        # Assert the response status code
        assert response.status_code == 302

        # Assert that the response URL starts with the login URL
        assert response.url.startswith(reverse('login'))

    @pytest.mark.parametrize('url_path', ['choose_testing_lab', 'choose_testing_lab_manual'])
    @pytest.mark.parametrize('group_client', ['laboratory_staffs_labpulse'], indirect=True)
    def test_user_no_first_name(self, group_client, url_path):
        """
        Test that a user with no first name is redirected to the profile page
        when accessing the 'choose_testing_lab' or 'choose_testing_lab_manual' URLs.
        """
        user = CustomUser.objects.get(username='test')

        if "manual" in url_path:
            # Give user required permission
            permission = Permission.objects.get(codename='view_add_retrospective_cd4_count')
            user.first_name = ''
            user.user_permissions.add(permission)
            user.save()
        else:
            user.first_name = ''
            user.save()

        url = reverse(url_path)
        response = group_client.get(url)

        # Assert the response status code
        assert response.status_code == 302

        # Assert that the response URL starts with the profile URL
        assert response.url.startswith(reverse('profile'))

    @pytest.mark.parametrize('url_path', ['choose_testing_lab', 'choose_testing_lab_manual'])
    @pytest.mark.parametrize('group_client', ['laboratory_staffs_labpulse'], indirect=True)
    def test_GET_request_sets_session_variable(self, group_client, url_path):
        """
        Test that a GET request to the 'choose_testing_lab' or 'choose_testing_lab_manual'
        URLs sets the session variable 'page_from'.
        """
        if "manual" in url_path:
            # Give user required permission
            permission = Permission.objects.get(codename='view_add_retrospective_cd4_count')
            user = CustomUser.objects.get(username='test')
            user.user_permissions.add(permission)
            user.save()

        url = reverse(url_path)
        response = group_client.get(url)

        # Assert the response status code
        assert response.status_code == 200

        # Assert that the session variable 'page_from' is set
        assert 'page_from' in group_client.session
