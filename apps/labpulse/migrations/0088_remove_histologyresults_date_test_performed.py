# Generated by Django 3.2.25 on 2024-07-29 11:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('labpulse', '0087_remove_histologyresults_date_reported'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='histologyresults',
            name='date_test_performed',
        ),
    ]
