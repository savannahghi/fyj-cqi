import datetime

import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed

from apps.account.models import CustomUser
from apps.labpulse.forms import Cd4trakerForm, Cd4trakerManualDispatchForm
from apps.labpulse.models import Cd4traker

"""
Code Analysis

Objective:
- The objective of the function is to update CD4 results for a specific lab and report type, while ensuring that the user is authenticated and has the required group membership.

Inputs:
- The function takes in the following inputs:
  - request: the HTTP request object containing metadata about the request
  - report_type: a string indicating the type of CD4 report being updated (either "Current" or "Retrospective")
  - pk: the primary key of the CD4traker object being updated

Flow:
- The function first checks if the user is authenticated and has the required group membership, and redirects to the login page if not.
- It then retrieves the CD4traker object with the given primary key and checks if the request method is GET or POST.
- If the request method is GET, it renders the update results page with a form pre-populated with the CD4traker object's data.
- If the request method is POST, it validates the form data and saves the updated CD4traker object to the database, along with the associated sub-county and county data.
- If the form data is invalid, it returns the form with error messages.
- Finally, it redirects the user back to the previous page and displays a success message.

Outputs:
- The main outputs of the function are:
  - A rendered HTML page containing a form for updating CD4 results
  - A success message displayed after the CD4traker object has been successfully updated

Additional aspects:
- The function uses custom decorators to ensure that the user is authenticated and has the required group membership.
- It also checks if the user has the required permission to update retrospective CD4 counts, and returns an error message if not.
- The function retrieves associated sub-county and county data based on the selected facility, and saves it along with the CD4traker object.
"""

@pytest.mark.django_db
class TestuUpdateCd4Results:
    #  Tests that GET request renders update results page with form
    # @pytest.mark.parametrize('group_client', ['laboratory_staffs_labpulse'], indirect=True)
    # @pytest.mark.parametrize('report_type', ['Current', 'Retrospective'])
    # def test_update_results_GET_request(self, group_client, report_type,mock_cd4_tracker_queryset):
    #     # Arrange
    #     if report_type !="Current":
    #         # Give user required permission
    #         permission = Permission.objects.get(codename='view_add_retrospective_cd4_count')
    #         user = CustomUser.objects.get(username='test')
    #         user.user_permissions.add(permission)
    #         user.save()
    #     url = reverse('update_cd4_results', kwargs={'report_type': report_type, 'pk': "123e4567-e89b-12d3-a456-426614174001"})
    #     # Act
    #     response = group_client.get(url)
    #     # Assert
    #     assert response.status_code == 200
    #     assertTemplateUsed(response, 'lab_pulse/update results.html')
    #     assert 'form' in response.context
    #     if report_type != 'Current':
    #         assert isinstance(response.context['form'], Cd4trakerManualDispatchForm)
    #     else:
    #         assert isinstance(response.context['form'], Cd4trakerForm)

    #  Tests that POST request updates Cd4traker object and redirects to previous page
    # @pytest.mark.parametrize('group_client', ['laboratory_staffs_labpulse'], indirect=True)
    # @pytest.mark.parametrize('report_type', ['Current', 'Retrospective'])
    # def test_update_results_POST_request(self, group_client, report_type,mock_cd4_tracker_queryset,facility,lab):
    #     # Arrange
    #     if report_type !="Current":
    #         # Give user required permission
    #         permission = Permission.objects.get(codename='view_add_retrospective_cd4_count')
    #         user = CustomUser.objects.get(username='test')
    #         user.user_permissions.add(permission)
    #         user.save()
    #     url = reverse('update_cd4_results', kwargs={'report_type': report_type, 'pk': "123e4567-e89b-12d3-a456-426614174001"})
    #     # Set the session variable 'page_from'
    #     session = group_client.session
    #     session['page_from'] = '/previous-page/'
    #     session.save()
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
    #     # Act
    #     response = group_client.post(url, form_data)
    #     # Assert
    #     assert response.status_code == 302
    #     assert response.url == '/previous-page/'

    #  Tests that user not logged in is redirected to login page
    def test_update_results_user_not_logged_in(self, client,mock_cd4_tracker_queryset):
        # Arrange
        url = reverse('update_cd4_results', kwargs={'report_type': 'Current', 'pk': "123e4567-e89b-12d3-a456-426614174001"})
        # Act
        response = client.get(url)
        # Assert
        assert response.status_code == 302
        assert '/login/' in response.url

    #  Tests that user without required group membership is redirected to login page
    @pytest.mark.parametrize('authenticated_client', ['authenticated_client'], indirect=True)
    def test_update_results_user_no_group_membership(self, authenticated_client,mock_cd4_tracker_queryset):
        # Arrange
        url = reverse('update_cd4_results', kwargs={'report_type': 'Current', 'pk': "123e4567-e89b-12d3-a456-426614174001"})
        # Act
        response = authenticated_client.get(url)
        # Assert
        assert response.status_code == 302
        assert '/login/' in response.url

    #  Tests that POST request fails validation and returns form with error messages
    # @pytest.mark.parametrize('group_client', ['laboratory_staffs_labpulse'], indirect=True)
    # @pytest.mark.parametrize('report_type', ['Current', 'Retrospective'])
    # def test_update_results_post_request_validation_fails(self, group_client, report_type,mock_cd4_tracker_queryset,
    #                                                       facility,lab):
    #     # Arrange
    #     if report_type !="Current":
    #         # Give user required permission
    #         permission = Permission.objects.get(codename='view_add_retrospective_cd4_count')
    #         user = CustomUser.objects.get(username='test')
    #         user.user_permissions.add(permission)
    #         user.save()
    #     url = reverse('update_cd4_results', kwargs={'report_type': report_type, 'pk': "123e4567-e89b-12d3-a456-426614174001"})
    #     # Set the session variable 'page_from'
    #     session = group_client.session
    #     session['page_from'] = '/previous-page/'
    #     session.save()
    #     form_data = {
    #         "received_status": "Accepted",
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
    #     # Act
    #     response = group_client.post(url, form_data)
    #     # Assert
    #     # Check form errors
    #     assert response.context['form'].errors
    #     form_errors = response.context['form'].errors
    #
    #     # Assert expected error messages
    #     assert "Check if this information is correct" in form_errors['received_status'][0]
    #     assert "Check if this information is correct" in form_errors['reason_for_rejection'][0]

    #  Tests that form is pre-populated with existing data for editing
    # @pytest.mark.parametrize('group_client', ['laboratory_staffs_labpulse'], indirect=True)
    # @pytest.mark.parametrize('report_type', ['Current', 'Retrospective'])
    # def test_update_results_form_prepopulated(self, group_client, report_type, mock_cd4_tracker_queryset):
    #     # Arrange
    #     if report_type != "Current":
    #         # Give user required permission
    #         permission = Permission.objects.get(codename='view_add_retrospective_cd4_count')
    #         user = CustomUser.objects.get(username='test')
    #         user.user_permissions.add(permission)
    #         user.save()
    #     url = reverse('update_cd4_results',
    #                   kwargs={'report_type': report_type, 'pk': "123e4567-e89b-12d3-a456-426614174001"})
    #
    #     # Act
    #     response = group_client.get(url)
    #
    #     # Assert
    #     assert response.status_code == 200
    #     assertTemplateUsed(response, 'lab_pulse/update results.html')
    #     assert 'form' in response.context
    #
    #     # Assert form fields
    #     form = response.context['form']
    #     assert form.fields['patient_unique_no'].label == 'Patient unique no'
    #     assert form.fields['date_of_collection'].label == 'Collection date'
    #     assert form.fields['date_sample_received'].label == 'Date sample was received'
    #     assert form.fields['age'].label == 'Age'
    #     assert form.fields['tb_lam_results'].label == 'TB LAM results'


