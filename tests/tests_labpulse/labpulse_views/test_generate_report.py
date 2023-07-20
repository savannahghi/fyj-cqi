import math

import pytest
from django.test import Client, RequestFactory
from django.urls import reverse
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseRedirect
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import pandas as pd

from apps.account.models import CustomUser
from apps.labpulse.views import GeneratePDF
from io import BytesIO
import PyPDF2

# @pytest.fixture
# def authenticated_client():
#     user = User.objects.create_user(username='testuser', password='testpass')
#     return user


@pytest.fixture
def generate_pdf_view():
    return GeneratePDF.as_view()


@pytest.fixture
def mock_list_of_projects_fac_dict():
    """Fixture to return mock report data for testing."""
    return {
        'Facility': ['Facility A', 'Facility B','Facility A', 'Facility B'],
        'MFL CODE': [123456, 789012,123456, 789012],
        'Collection Date': ['2023-01-01', '2023-01-02','2023-01-01', '2023-01-02'],
        'Testing date': ['2023-01-03', '2023-01-04','2023-01-03', '2023-01-04'],
        'Date Dispatch': ['2023-01-05', '2023-01-06','2023-01-05', '2023-01-06'],
        'CCC NO.': ['123', '456','123', '456'],
        'Age': [25, 30,25, 30],
        'Sex': ['M', 'F','M', 'F'],
        'CD4 Count': [500, 600, float('nan'), 150],
        'Serum Crag': ['Negative', 'Positive','Negative', 'Positive'],
        'Rejection reason': ['Missing Sample', 'Improper Collection','Missing Sample', 'Improper Collection'],
        'Testing Laboratory': ['Lab A', 'Lab B','Lab A', 'Lab B'],
        'TB LAM': ['Negative', 'Positive','Negative', 'Positive']
    }



@pytest.fixture
def mock_list_of_projects_fac(mock_list_of_projects_fac_dict):
    """Fixture to return mock report data as a pandas dataframe for testing."""
    return pd.DataFrame.from_dict(mock_list_of_projects_fac_dict)


@pytest.mark.django_db
class TestGenerateReport:
    def test_generate_pdf_authenticated_no_first_name(self, authenticated_client, generate_pdf_view):
        """Test authenticated user with no first name is redirected.

        This tests that an authenticated user without a first name is
        redirected to the profile page when attempting to generate a
        PDF report.
        """

        # Update test user to have no first name
        user = CustomUser.objects.get(username='test')
        user.first_name = ''
        user.save()

        # Request generate PDF view
        url = reverse('generate_cd4_report_pdf')
        response = authenticated_client.get(url)

        # Assert redirect to profile
        assert response.status_code == 302
        assert response.url == reverse('profile')

    # def test_generate_pdf_success(self, authenticated_client, generate_pdf_view, request_factory,
    #                               mock_list_of_projects_fac):
    #
    #     # Set the session variable 'page_from'
    #     session = authenticated_client.session
    #     session['list_of_projects_fac'] = mock_list_of_projects_fac.to_dict()
    #     session.save()
    #
    #     url = reverse('generate_cd4_report_pdf')
    #     response = authenticated_client.get(url)
    #
    #     assert isinstance(response, HttpResponse)
    #     assert response.status_code == 200
    #     assert response['Content-Disposition'] == 'filename="CD4 Count Report.pdf"'
    #     # Read the PDF content from the response
    #     pdf_content = response.content
    #
    #     # Open the PDF using PyPDF2
    #     pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_content))
    #
    #     # Assert the content of each page in the PDF
    #     for i, page in enumerate(pdf_reader.pages):
    #         expected_facility = mock_list_of_projects_fac.loc[i, 'Facility']
    #         expected_mfl_code = str(mock_list_of_projects_fac.loc[i, 'MFL CODE'])
    #         expected_collection_date = mock_list_of_projects_fac.loc[i, 'Collection Date']
    #         expected_testing_date = mock_list_of_projects_fac.loc[i, 'Testing date']
    #         expected_dispatch_date = mock_list_of_projects_fac.loc[i, 'Date Dispatch']
    #         expected_ccc_no = mock_list_of_projects_fac.loc[i, 'CCC NO.']
    #         expected_age = str(mock_list_of_projects_fac.loc[i, 'Age'])
    #         expected_sex = mock_list_of_projects_fac.loc[i, 'Sex']
    #         expected_cd4_count = mock_list_of_projects_fac.loc[i, 'CD4 Count']
    #         expected_crag = mock_list_of_projects_fac.loc[i, 'Serum Crag']
    #         expected_testing_lab = mock_list_of_projects_fac.loc[i, 'Testing Laboratory']
    #         expected_rejection_reason = mock_list_of_projects_fac.loc[i, 'Rejection reason']
    #         expected_tb_lam = mock_list_of_projects_fac.loc[i, 'TB LAM']
    #
    #         # Extract the text content from the page
    #         page_content = page.extract_text()
    #
    #         # Assert the presence of the expected values in the page content
    #         assert expected_facility in page_content
    #         assert expected_mfl_code in page_content
    #         assert expected_collection_date in page_content
    #         assert expected_testing_date in page_content
    #         assert expected_dispatch_date in page_content
    #         assert expected_ccc_no in page_content
    #         assert expected_age in page_content
    #         assert expected_sex in page_content
    #         # assert expected_cd4_count in page_content
    #         if math.isnan(expected_cd4_count):
    #             assert "Rejected" in page_content
    #             assert f"(Reason: {expected_rejection_reason})" in page_content
    #         elif int(expected_cd4_count) <= 200:
    #             assert str(int(expected_cd4_count)) in page_content
    #
    #         assert expected_crag in page_content
    #         assert expected_testing_lab in page_content
    #         assert expected_tb_lam in page_content

    def test_generate_pdf_success(self, authenticated_client, generate_pdf_view,
                                  mock_list_of_projects_fac):
        """Test successful PDF generation with mock data."""

        # Set mock data in session
        session = authenticated_client.session
        session['list_of_projects_fac'] = mock_list_of_projects_fac.to_dict()
        session.save()

        # Request generate PDF view
        url = reverse('generate_cd4_report_pdf')
        response = authenticated_client.get(url)

        # Assert PDF response
        assert isinstance(response, HttpResponse)
        assert response.status_code == 200
        assert response['Content-Disposition'] == 'filename="CD4 Count Report.pdf"'

        # Read PDF content
        pdf_content = response.content

        # Open PDF with PyPDF2
        pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_content))

        # Validate content on each page
        for i, page in enumerate(pdf_reader.pages):
            # Get expected values from mock data
            expected_facility = mock_list_of_projects_fac.loc[i, 'Facility']
            expected_mfl_code = str(mock_list_of_projects_fac.loc[i, 'MFL CODE'])
            expected_collection_date = mock_list_of_projects_fac.loc[i, 'Collection Date']
            expected_testing_date = mock_list_of_projects_fac.loc[i, 'Testing date']
            expected_dispatch_date = mock_list_of_projects_fac.loc[i, 'Date Dispatch']
            expected_ccc_no = mock_list_of_projects_fac.loc[i, 'CCC NO.']
            expected_age = str(mock_list_of_projects_fac.loc[i, 'Age'])
            expected_sex = mock_list_of_projects_fac.loc[i, 'Sex']
            expected_cd4_count = mock_list_of_projects_fac.loc[i, 'CD4 Count']
            expected_crag = mock_list_of_projects_fac.loc[i, 'Serum Crag']
            expected_testing_lab = mock_list_of_projects_fac.loc[i, 'Testing Laboratory']
            expected_rejection_reason = mock_list_of_projects_fac.loc[i, 'Rejection reason']
            expected_tb_lam = mock_list_of_projects_fac.loc[i, 'TB LAM']

            # Extract the text content from the page
            page_content = page.extract_text()

            # Assert the presence of the expected values in the page content
            assert expected_facility in page_content
            assert expected_mfl_code in page_content
            assert expected_collection_date in page_content
            assert expected_testing_date in page_content
            assert expected_dispatch_date in page_content
            assert expected_ccc_no in page_content
            assert expected_age in page_content
            assert expected_sex in page_content

            # Validate CD4 count display
            # expected_cd4_count = mock_list_of_projects_fac.loc[i, 'CD4 Count']
            if math.isnan(expected_cd4_count):
                # If rejected, check rejected reason
                assert "Rejected" in page_content
                assert f"(Reason: {expected_rejection_reason})" in page_content

            elif int(expected_cd4_count) <= 200:
                # Display CD4 if <= 200
                assert str(int(expected_cd4_count)) in page_content

            # Check other fields
            # expected_crag = mock_list_of_projects_fac.loc[i, 'Serum Crag']
            assert expected_crag in page_content

            # expected_testing_lab = mock_list_of_projects_fac.loc[i, 'Testing Laboratory']
            assert expected_testing_lab in page_content

            # expected_tb_lam = mock_list_of_projects_fac.loc[i, 'TB LAM']
            assert expected_tb_lam in page_content

