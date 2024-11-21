import pytest
from django.contrib.auth.models import Permission
from django.core.exceptions import ObjectDoesNotExist
from django.test import Client
from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed

from apps.account.models import CustomUser
from apps.labpulse.forms import Cd4TestingLabForm
from apps.labpulse.models import Cd4TestingLabs

"""
Code Analysis

Objective:
The objective of the "update_testing_labs" function is to update the details of a CD4 testing lab in the database and redirect the user to the previous page.

Inputs:
- "request": the HTTP request object containing metadata and data about the user's request
- "pk": the primary key of the CD4 testing lab to be updated

Flow:
1. Check if the user has a first name, if not, redirect them to their profile page
2. If the request method is GET, store the previous page URL in the session
3. Retrieve the CD4 testing lab object with the given primary key
4. If the request method is POST, validate the form data and save the updated object to the database
5. If the form is valid, display a success message and redirect the user to the previous page
6. If the request method is not POST, display the form with the current data
7. Render the "update results" template with the form and title as context

Outputs:
- Rendered HTML template containing the form for updating CD4 testing lab details
- Success message displayed if the form is valid and the object is updated
- Redirect to the previous page after successful update

Additional aspects:
- The function uses the "Cd4TestingLabForm" form class and "Cd4TestingLabs" model class from the "labpulse" app
- The function checks if the user has a first name before allowing them to update the CD4 testing lab details
- The function stores the previous page URL in the session to redirect the user after a successful update
- The function uses the "messages" module to display success messages to the user
"""

@pytest.mark.django_db
class TestUpdateTestingLabsView:
    """Tests for the update_testing_labs view."""

    def test_login_required_should_redirect(self, mock_lab_queryset):
        """
        Test that accessing the update testing labs view without login redirects to the login page.
        """
        client = Client()

        url = reverse('update_testing_labs', args=['123e4567-e89b-12d3-a456-426614174000'])

        response = client.get(url)

        # Assert redirection to the login page
        assert response.status_code == 302
        assert '/login/' in response.url

    @pytest.mark.parametrize('group_client', ['laboratory_staffs_labpulse'], indirect=True)
    def test_login_required_should_succeed(self, mock_lab_queryset, group_client):
        """
        Test that accessing the update testing labs view with a logged-in user succeeds.
        """
        # Using reverse() to resolve the URL helps avoid hardcoding.
        url = reverse('update_testing_labs', args=['123e4567-e89b-12d3-a456-426614174000'])
        # Ensure the user is authenticated
        user = CustomUser.objects.get(username='test')
        group_client.force_login(user)  # Log in the user

        # Assign required permissions for the user
        permission_current = Permission.objects.get(
            codename='view_update_cd4_results')  # Adjust this codename as needed
        user.user_permissions.add(permission_current)

        user.save()  # Save the user with updated permissions

        # Make request
        response = group_client.get(url)

        # Assert 200 OK status
        assert response.status_code == 200
        # Verify context data
        assert 'form' in response.context
        assert response.context['form'] is not None

    @pytest.mark.parametrize('group_client', ['laboratory_staffs_labpulse'], indirect=True)
    def test_first_name_should_redirect(self, mock_lab_queryset, group_client):
        """
        Test that accessing the update testing labs view without first_name redirects to the profile page.
        """

        url = reverse('update_testing_labs', args=['123e4567-e89b-12d3-a456-426614174000'])
        # remove first_name from user
        user = CustomUser.objects.get(username='test')
        user.first_name = ""
        user.save()

        # Ensure the user is authenticated
        user = CustomUser.objects.get(username='test')
        group_client.force_login(user)  # Log in the user

        # Assign required permissions for the user
        permission_current = Permission.objects.get(
            codename='view_update_cd4_results')  # Adjust this codename as needed
        user.user_permissions.add(permission_current)

        user.save()  # Save the user with updated permissions

        response = group_client.get(url)

        # Assert redirection to the login page
        assert response.status_code == 302
        assert '/profile/' in response.url

    @pytest.mark.parametrize('group_client', ['laboratory_staffs_labpulse'], indirect=True)
    def test_get_request_should_show_update_form(self, mock_lab_queryset, group_client):
        """Test that a GET request renders the update form for testing labs."""

        # Resolve update URL dynamically
        url = reverse('update_testing_labs', args=['123e4567-e89b-12d3-a456-426614174000'])
        # Ensure the user is authenticated
        user = CustomUser.objects.get(username='test')
        group_client.force_login(user)  # Log in the user

        # Assign required permissions for the user
        permission_current = Permission.objects.get(
            codename='view_update_cd4_results')  # Adjust this codename as needed
        user.user_permissions.add(permission_current)

        user.save()  # Save the user with updated permissions
        response = group_client.get(url)
        # Verify successful response
        assert response.status_code == 200

        # Validate form in response context
        assert 'form' in response.context
        assert isinstance(response.context['form'], Cd4TestingLabForm)
        assert response.context['form'].fields['testing_lab_name'].label == 'Testing lab name'
        assert response.context['form'].fields['mfl_code'].label == 'Mfl code'

        # Confirm correct template used
        assertTemplateUsed(response, 'lab_pulse/update results.html')

    @pytest.mark.parametrize('group_client', ['laboratory_staffs_labpulse'], indirect=True)
    def test_valid_post_request_should_update(self, group_client):
        """
        Valid POST request should update the Cd4TestingLabs instance.
        """

        # Set the 'page_from' session variable to check redirect
        session = group_client.session
        session['page_from'] = '/previous-page/'
        session.save()

        # Create lab instance to be updated by POST request
        item = Cd4TestingLabs.objects.create(
            testing_lab_name='Lab 1',
            mfl_code=1234
        )

        # Define updated data to submit
        form_data = {
            'testing_lab_name': 'Updated Lab',
            'mfl_code': 5678
        }
        # Ensure the user is authenticated
        user = CustomUser.objects.get(username='test')
        group_client.force_login(user)  # Log in the user

        # Assign required permissions for the user
        permission_current = Permission.objects.get(
            codename='view_update_cd4_results')  # Adjust this codename as needed
        user.user_permissions.add(permission_current)

        user.save()  # Save the user with updated permissions

        # Submit POST request to update_testing_labs view
        response = group_client.post(
            reverse('update_testing_labs', args=[str(item.pk)]),
            form_data
        )

        # Verify redirect status
        assert response.status_code == 302

        # Reload instance and assert attributes updated
        lab = Cd4TestingLabs.objects.get(pk=item.pk)
        assert lab.testing_lab_name == 'UPDATED LAB'
        assert lab.mfl_code == 5678

    @pytest.mark.parametrize('group_client', ['laboratory_staffs_labpulse'], indirect=True)
    def test_item_does_not_exist(self, group_client):
        """
        Attempting to update a non-existent item should raise ObjectDoesNotExist.
        """

        # Try to access update view for an item PK that does not exist
        invalid_pk = 'a94785f2-448c-4594-8d5f-cd76ec228219'

        # Verify ObjectDoesNotExist raised
        with pytest.raises(ObjectDoesNotExist):
            # Ensure the user is authenticated
            user = CustomUser.objects.get(username='test')
            group_client.force_login(user)  # Log in the user

            # Assign required permissions for the user
            permission_current = Permission.objects.get(
                codename='view_update_cd4_results')  # Adjust this codename as needed
            user.user_permissions.add(permission_current)

            user.save()  # Save the user with updated permissions
            group_client.get(
                reverse('update_testing_labs', args=[invalid_pk])
            )

    @pytest.mark.parametrize('group_client', ['laboratory_staffs_labpulse'], indirect=True)
    def test_invalid_form_not_updated_should_fail(self, group_client):
        """
        Posting an invalid form should not update the instance.
        """

        # Existing lab instance
        item = Cd4TestingLabs.objects.create(
            testing_lab_name='Lab 1',
            mfl_code=1234
        )

        # Submit invalid form data
        form_data = {
            'testing_lab_name': '',
            'mfl_code': 5678
        }
        # Ensure the user is authenticated
        user = CustomUser.objects.get(username='test')
        group_client.force_login(user)  # Log in the user

        # Assign required permissions for the user
        permission_current = Permission.objects.get(
            codename='view_update_cd4_results')  # Adjust this codename as needed
        user.user_permissions.add(permission_current)

        user.save()  # Save the user with updated permissions

        response = group_client.post(
            reverse('update_testing_labs', args=[item.pk]),
            form_data
        )

        # Reload item from DB
        item.refresh_from_db()

        # Check form errors
        assert response.status_code == 200
        assert response.context['form'].errors

        # Verify item fields unchanged
        assert item.testing_lab_name == 'LAB 1'
        assert item.mfl_code == 1234

    @pytest.mark.parametrize('group_client', ['laboratory_staffs_labpulse'], indirect=True)
    def test_post_request_redirects_to_previous_page_should_redirect(self, group_client):
        """
        After valid POST, should redirect to 'page_from' session variable.
        """
        # Existing lab instance
        item = Cd4TestingLabs.objects.create(
            testing_lab_name='Lab 1',
            mfl_code=1234
        )
        # Ensure the user is authenticated
        user = CustomUser.objects.get(username='test')
        group_client.force_login(user)  # Log in the user

        # Assign required permissions for the user
        permission_current = Permission.objects.get(
            codename='view_update_cd4_results')  # Adjust this codename as needed
        user.user_permissions.add(permission_current)

        user.save()  # Save the user with updated permissions

        # Set 'page_from' session var
        session = group_client.session
        session['page_from'] = '/previous-page/'
        session.save()

        # Valid form data
        form_data = {
            'testing_lab_name': 'Updated Lab',
            'mfl_code': 5678
        }

        # Make POST request
        response = group_client.post(
            reverse('update_testing_labs', args=[item.pk]),
            form_data,
            HTTP_REFERER='/previous-page/'
        )

        # Check redirect to 'page_from'
        assert response.status_code == 302
        assert response.url == '/previous-page/'
