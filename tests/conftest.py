from unittest.mock import MagicMock, Mock, patch

import pytest
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.test import Client

from apps.account.models import CustomUser
from apps.cqi.models import Counties, Facilities, Sub_counties
from apps.labpulse.models import Cd4TestingLabs, Cd4traker


@pytest.fixture
def authenticated_client():
    user = CustomUser.objects.create_user(
        username='test',
        first_name='Test',
        email='test@example.com',
        password='password'
    )
    client = Client()
    client.force_login(user)
    yield client

@pytest.fixture
def group_client(authenticated_client, request):
    """Assign the client's user to the specified group."""
    user = CustomUser.objects.get(username='test')
    group = Group.objects.create(name=request.param)
    user.groups.add(group)
    yield authenticated_client


@pytest.fixture
def mock_lab_queryset():
    """Mocks the Cd4TestingLabs model manager queryset.

    This patches the queryset objects manager to return a mocked instance
    with a specified primary key. Useful for isolating view tests from
    the database layer.
    """

    # Patch the actual queryset class with a mock
    with patch('apps.labpulse.models.Cd4TestingLabs.objects') as mocked_qs:
        # Create a mock instance with a set primary key
        # MagicMock will autogenerate the standard model field attributes so the model behaves as expected when iterated over.
        mocked_lab = MagicMock(spec=Cd4TestingLabs)
        mocked_lab.pk = '123e4567-e89b-12d3-a456-426614174000'

        # Make the mock return our mocked instance
        mocked_qs.get.return_value = mocked_lab

        # Yield the mocked queryset
        yield mocked_qs

@pytest.fixture
def mock_cd4_tracker_queryset():
    """Mocks the Cd4TestingLabs model manager queryset.

    This patches the queryset objects manager to return a mocked instance
    with a specified primary key. Useful for isolating view tests from
    the database layer.
    """

    # Patch the actual queryset class with a mock
    with patch('apps.labpulse.models.Cd4traker.objects') as mocked_qs:
        # Create a mock instance with a set primary key
        # MagicMock will autogenerate the standard model field attributes so the model behaves as expected when iterated over.
        mocked_cd4_tracker = MagicMock(spec=Cd4traker)
        mocked_cd4_tracker.pk = '123e4567-e89b-12d3-a456-426614174001'

        # Make the mock return our mocked instance
        mocked_qs.get.return_value = mocked_cd4_tracker

        # Yield the mocked queryset
        yield mocked_qs

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
