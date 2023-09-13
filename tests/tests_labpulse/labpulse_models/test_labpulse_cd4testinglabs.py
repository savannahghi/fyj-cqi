import datetime
import uuid

import pytest
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.contrib.auth import get_user_model
from apps.account.models import CustomUser
from apps.labpulse.models import Cd4TestingLabs
User = get_user_model()

"""
Code Analysis

Main functionalities:
The Cd4TestingLabs class is responsible for storing information about the different CD4 testing laboratories. It has fields for the name of the laboratory, its MFL code, and the user who created and last modified the record. The class also has methods for displaying the name of the laboratory and for ordering the records by the name of the laboratory.

Methods:
- __str__(self): returns the name of the testing laboratory as a string
- Meta: defines the plural name of the class, orders the records by the name of the laboratory

Fields:
- id: UUIDField, primary key of the record
- testing_lab_name: CharField, name of the testing laboratory
- mfl_code: IntegerField, MFL code of the testing laboratory
- created_by: ForeignKey to CustomUser, user who created the record
- modified_by: ForeignKey to CustomUser, user who last modified the record
- date_created: DateTimeField, date and time when the record was created
- date_updated: DateTimeField, date and time when the record was last updated
"""
@pytest.mark.django_db
class TestCd4TestingLabs:
    #  Tests that a new Cd4TestingLabs instance can be created with valid parameters
    def test_create_new_instance_valid_params(self):
        user = CustomUser.objects.create(username='test_user')  # Create a CustomUser instance
        lab = Cd4TestingLabs.objects.create(
            testing_lab_name='Test Lab',
            mfl_code=12345,
            created_by=user,
            modified_by=user
        )
        assert lab.testing_lab_name == 'TEST LAB'
        assert lab.mfl_code == 12345
        assert isinstance(lab.id, uuid.UUID)
        assert isinstance(lab.created_by, CustomUser)
        assert isinstance(lab.modified_by, CustomUser)
        assert isinstance(lab.date_created, datetime.datetime)
        assert isinstance(lab.date_updated, datetime.datetime)

    #  Tests that an existing Cd4TestingLabs instance can be retrieved
    def test_retrieve_existing_instance(self):
        lab = Cd4TestingLabs.objects.create(testing_lab_name='Test Lab', mfl_code=12345)
        retrieved_lab = Cd4TestingLabs.objects.get(id=lab.id)
        assert retrieved_lab == lab

    #  Tests that an existing Cd4TestingLabs instance can be updated with valid parameters
    def test_update_existing_instance_valid_params(self):
        lab = Cd4TestingLabs.objects.create(testing_lab_name='Test Lab', mfl_code=12345)
        lab.testing_lab_name = 'Updated Lab'
        lab.mfl_code = 54321
        lab.save()
        updated_lab = Cd4TestingLabs.objects.get(id=lab.id)
        assert updated_lab.testing_lab_name == 'UPDATED LAB'
        assert updated_lab.mfl_code == 54321

    #  Tests that an existing Cd4TestingLabs instance can be deleted
    def test_delete_existing_instance(self):
        lab = Cd4TestingLabs.objects.create(testing_lab_name='Test Lab', mfl_code=12345)
        lab_id = lab.id
        lab.delete()
        with pytest.raises(ObjectDoesNotExist):
            Cd4TestingLabs.objects.get(id=lab_id)

    #  Tests that a new Cd4TestingLabs instance cannot be created with a duplicate testing_lab_name
    def test_create_new_instance_duplicate_testing_lab_name(self):
        Cd4TestingLabs.objects.create(testing_lab_name='Test Lab', mfl_code=12345)
        with pytest.raises(IntegrityError):
            Cd4TestingLabs.objects.create(testing_lab_name='Test Lab', mfl_code=67890)

    #  Tests that a new Cd4TestingLabs instance cannot be created with a duplicate mfl_code
    def test_create_new_instance_duplicate_mfl_code(self):
        Cd4TestingLabs.objects.create(testing_lab_name='Test Lab', mfl_code=12345)
        with pytest.raises(IntegrityError):
            Cd4TestingLabs.objects.create(testing_lab_name='Another Lab', mfl_code=12345)

    #  Tests that a non-existent Cd4TestingLabs instance cannot be retrieved
    def test_retrieve_nonexistent_instance(self):
        with pytest.raises(ObjectDoesNotExist):
            Cd4TestingLabs.objects.get(id=uuid.uuid4())

    #  Tests that an existing Cd4TestingLabs instance cannot be updated with a duplicate testing_lab_name
    def test_update_existing_instance_duplicate_testing_lab_name(self):
        lab1 = Cd4TestingLabs.objects.create(testing_lab_name='Test Lab 1', mfl_code=12345)
        lab2 = Cd4TestingLabs.objects.create(testing_lab_name='Test Lab 2', mfl_code=67890)
        lab2.testing_lab_name = lab1.testing_lab_name
        with pytest.raises(IntegrityError):
            lab2.save()

    #  Tests that an existing Cd4TestingLabs instance cannot be updated with a duplicate mfl_code
    def test_update_existing_instance_duplicate_mfl_code(self):
        lab1 = Cd4TestingLabs.objects.create(testing_lab_name='Test Lab 1', mfl_code=12345)
        lab2 = Cd4TestingLabs.objects.create(testing_lab_name='Test Lab 2', mfl_code=67890)
        lab2.mfl_code = lab1.mfl_code
        with pytest.raises(IntegrityError):
            lab2.save()

    #  Tests that a non-existent Cd4TestingLabs instance cannot be deleted
    def test_delete_nonexistent_instance(self):
        nonexistent_id = uuid.uuid4()
        with pytest.raises(ObjectDoesNotExist):
            lab = Cd4TestingLabs.objects.get(id=nonexistent_id)
            lab.delete()

