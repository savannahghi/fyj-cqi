import pytest
from django.utils import timezone

from apps.cqi.models import Facilities, Counties, Sub_counties
from apps.labpulse.models import Cd4TestingLabs, Cd4traker

"""
Code Analysis

Main functionalities:
The Cd4traker class is a Django model that represents a CD4 count tracker. It stores information about patients' CD4 count results, including their unique patient number, date of collection, facility name, sub-county, county, age, CD4 count results, CD4 percentage, TB LAM results, serum CRAG results, justification, sex, received status, reason for rejection, date of testing, reason for no serum CRAG, testing laboratory, created by, modified by, date dispatched, report type, date updated, date TB LAM results entered, and date serum CRAG results entered. The class also has various permissions for viewing and adding CD4 count results.

Methods:
- save(): Overrides the default save method to set the date TB LAM results entered and date serum CRAG results entered if they are not already set before saving the object.
- __str__(): Returns a string representation of the object, which includes the facility name, patient unique number, and date of collection.

Fields:
- CHOICES: A tuple of tuples that defines the choices for the TB LAM results and serum CRAG results fields.
- REJECTION_CHOICES: A tuple of tuples that defines the choices for the reason for rejection field.
- JUSTIFICATION_CHOICES: A tuple of tuples that defines the choices for the justification field.
- id: A UUIDField that serves as the primary key for the object.
- patient_unique_no: A CharField that stores the unique patient number.
- date_of_collection: A DateTimeField that stores the date of collection.
- date_sample_received: A DateTimeField that stores the date the sample was received.
- facility_name: A ForeignKey that links to the Facilities model and stores the facility name.
- sub_county: A ForeignKey that links to the Sub_counties model and stores the sub-county.
- county: A ForeignKey that links to the Counties model and stores the county.
- age: An IntegerField that stores the patient's age.
- cd4_count_results: An IntegerField that stores the CD4 count results.
- cd4_percentage: An IntegerField that stores the CD4 percentage.
- tb_lam_results: A CharField that stores the TB LAM results.
- serum_crag_results: A CharField that stores the serum CRAG results.
- justification: A CharField that stores the justification.
- sex: A CharField that stores the patient's sex.
- received_status: A CharField that stores the received status.
- reason_for_rejection: A CharField that stores the reason for rejection.
- date_of_testing: A DateTimeField that stores the date of testing.
- reason_for_no_serum_crag: A CharField that stores the reason for no serum CRAG.
- testing_laboratory: A ForeignKey that links to the Cd4TestingLabs model and stores the testing laboratory.
- created_by: A ForeignKey that links to the CustomUser model and stores the user who created the object.
- modified_by: A ForeignKey that links to the CustomUser model and stores the user who last modified the object.
- date_dispatched: A DateTimeField that stores the date the object was dispatched.
- report_type: A CharField that stores the report type.
- date_updated: A DateTimeField that stores the date the object was last updated.
- date_tb_lam_results_entered: A DateTimeField that stores the date the TB LAM results were entered.
- date_serum_crag_results_entered: A DateTimeField that stores the date the serum CRAG results were entered.
"""
@pytest.mark.django_db
class TestCd4traker:
    #  Tests that a valid instance of Cd4Traker can be saved
    def test_save_valid_instance(self):
        facility = Facilities.objects.create(name='Test Facility', mfl_code=12345)
        county = Counties.objects.create(county_name='Test_County')
        sub_county = Sub_counties.objects.create(sub_counties='Testing Sub-county')
        cd4_testing_lab = Cd4TestingLabs.objects.create(testing_lab_name='Testing Lab', mfl_code=12345)
        cd4_tracker = Cd4traker.objects.create(
            patient_unique_no='1234567890',
            date_of_collection=timezone.now(),
            date_sample_received=timezone.now(),
            facility_name=facility,
            sub_county=sub_county,
            county=county,
            age=30,
            cd4_count_results=500,
            cd4_percentage=50,
            tb_lam_results='Positive',
            serum_crag_results='Negative',
            justification='Baseline (Tx_new)',
            sex='M',
            received_status='Accepted',
            testing_laboratory=cd4_testing_lab
        )
        assert cd4_tracker.id is not None

    #  Tests that an existing instance of Cd4Traker can be updated
    def test_update_existing_instance(self):
        facility = Facilities.objects.create(name='Test Facility', mfl_code=12346)
        county = Counties.objects.create(county_name='Testing County')
        sub_county = Sub_counties.objects.create(sub_counties='Test Sub-county')
        cd4_testing_lab = Cd4TestingLabs.objects.create(testing_lab_name='Testing Labs', mfl_code=12345)
        cd4_tracker = Cd4traker.objects.create(
            patient_unique_no='1234567890',
            date_of_collection=timezone.now(),
            date_sample_received=timezone.now(),
            facility_name=facility,
            sub_county=sub_county,
            county=county,
            age=30,
            cd4_count_results=500,
            cd4_percentage=50,
            tb_lam_results='Positive',
            serum_crag_results='Negative',
            justification='Baseline (Tx_new)',
            sex='M',
            received_status='Accepted',
            testing_laboratory=cd4_testing_lab
        )
        cd4_tracker.cd4_count_results = 600
        cd4_tracker.save()
        assert cd4_tracker.cd4_count_results == 600

    #  Tests that an instance of Cd4Traker can be retrieved
    def test_retrieve_instance(self):
        facility = Facilities.objects.create(name='Test Facility', mfl_code=12347)
        county = Counties.objects.create(county_name='Test County')
        sub_county = Sub_counties.objects.create(sub_counties='Test Sub-county')
        cd4_testing_lab = Cd4TestingLabs.objects.create(testing_lab_name='Test Lab', mfl_code=12345)
        cd4_tracker = Cd4traker.objects.create(
            patient_unique_no='1234567890',
            date_of_collection=timezone.now(),
            date_sample_received=timezone.now(),
            facility_name=facility,
            sub_county=sub_county,
            county=county,
            age=30,
            cd4_count_results=500,
            cd4_percentage=50,
            tb_lam_results='Positive',
            serum_crag_results='Negative',
            justification='Baseline (Tx_new)',
            sex='M',
            received_status='Accepted',
            testing_laboratory=cd4_testing_lab
        )
        retrieved_cd4_tracker = Cd4traker.objects.get(id=cd4_tracker.id)
        assert retrieved_cd4_tracker == cd4_tracker

    #  Tests that an instance of Cd4Traker cannot be saved with missing required fields
    def test_missing_required_fields(self):
        with pytest.raises(Exception):
            Cd4traker.objects.create()

        with pytest.raises(Exception):
            Cd4traker.objects.create(patient_unique_no='1234567890')

        with pytest.raises(Exception):
            Cd4traker.objects.create(date_of_collection=timezone.make_aware(timezone.datetime(2022, 1, 1)),)

        with pytest.raises(Exception):
            Cd4traker.objects.create(facility_name=Facilities.objects.create(name='Test Facility', mfl_code=123456))

        with pytest.raises(Exception):
            Cd4traker.objects.create(sub_county=Sub_counties.objects.create(sub_counties='Test Sub County'))

        with pytest.raises(Exception):
            Cd4traker.objects.create(county=Counties.objects.create(county_name='Test County'))

        with pytest.raises(Exception):
            Cd4traker.objects.create(age=200)

        with pytest.raises(Exception):
            Cd4traker.objects.create(sex='X')

        with pytest.raises(Exception):
            Cd4traker.objects.create(received_status='Invalid')

    #  Tests that an instance of Cd4Traker cannot be saved with invalid fields
    def test_invalid_fields(self):
        with pytest.raises(Exception):
            facility = Facilities.objects.create(name='Test Facility', mfl_code=12348)
            county = Counties.objects.create(county_name='Test County')
            sub_county = Sub_counties.objects.create(sub_counties='Test Sub-county')
            cd4_testing_lab = Cd4TestingLabs.objects.create(testing_lab_name='Test Lab', mfl_code=12345)
            cd4_tracker = Cd4traker.objects.create(
                patient_unique_no='1234567890',
                date_of_collection=timezone.now(),
                date_sample_received=timezone.now(),
                facility_name=facility,
                sub_county=sub_county,
                county=county,
                age=200,
                cd4_count_results=500,
                cd4_percentage=50,
                tb_lam_results='Positive',
                serum_crag_results='Negative',
                justification='Baseline (Tx_new)',
                sex='X',
                received_status='Accepted',
                testing_laboratory=cd4_testing_lab
            )
            cd4_tracker.full_clean()
            cd4_tracker.save()
