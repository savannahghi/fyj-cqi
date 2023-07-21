import datetime
from datetime import timedelta

# Generated by CodiumAI

import pytest
from django.contrib import messages
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

from apps.labpulse.models import LabPulseUpdateButtonSettings, Cd4TestingLabs
from apps.labpulse.views import disable_update_buttons

"""
Code Analysis

Objective:
- The objective of the 'disable_update_buttons' function is to disable update buttons for a specified time and days ago based on the settings in the LabPulseUpdateButtonSettings model.

Inputs:
- request: the HTTP request object
- audit_team: a queryset of objects to disable update buttons for
- relevant_date_field: the name of the field in the objects that contains the relevant date for disabling update buttons

Flow:
- Get the local timezone and the LabPulseUpdateButtonSettings object
- Check if the 'disable_all_dqa_update_buttons' setting is True, and if so, disable all update buttons in the queryset
- If the setting is False, get the 'hide_button_time' and 'days_to_keep_update_button_enabled' settings
- Calculate the datetime when the update button should be hidden based on the relevant date field and the 'hide_button_time' setting
- Loop through the queryset and set the 'hide_update_button' attribute based on the calculated datetime and the 'days_to_keep_update_button_enabled' setting
- If the 'hide_button_time' setting is not found, display a message to the user

Outputs:
- Redirect to the current page with updated queryset objects that have the 'hide_update_button' attribute set

Additional aspects:
- The function uses the LabPulseUpdateButtonSettings model to get the settings for disabling update buttons
- The function displays messages to the user if certain settings are not found or if a CD4 Testing Lab with the same name already exists
"""
@pytest.mark.django_db
class TestDisableAllDQAUpdateButtons:
    def test_disable_all_dqa_update_buttons(self):
        # Create the LabPulseUpdateButtonSettings object with disable_all_dqa_update_buttons flag set to True
        LabPulseUpdateButtonSettings.objects.create(disable_all_dqa_update_buttons=True,
                                                     hide_button_time=datetime.time(12, 0))

        # Create a list of mock audit team data objects
        audit_team = [Cd4TestingLabs() for _ in range(3)]

        # Create a request object using the RequestFactory
        request = RequestFactory().get('/')

        # Call the view function
        disable_update_buttons(request, audit_team, 'date_created')

        # Assert that all DQA update buttons are disabled
        for data in audit_team:
            assert data.hide_update_button is True

    def test_disable_dqa_update_buttons_for_old_data(self):
        # Create the LabPulseUpdateButtonSettings object with hide_button_time and days_to_keep_update_button_enabled attributes
        settings = LabPulseUpdateButtonSettings.objects.create(
            hide_button_time=datetime.time(12, 0),
            days_to_keep_update_button_enabled=7
        )

        # Create a list of mock audit team data objects with date_created older than 7 days
        audit_team = [
            Cd4TestingLabs(date_created=timezone.now() - timedelta(days=10))
            for _ in range(3)
        ]

        # Create a request object using the RequestFactory
        request = RequestFactory().get('/')

        # Call the view function
        disable_update_buttons(request, audit_team, 'date_created')