# Generated by Django 3.2.22 on 2023-11-24 15:05

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('labpulse', '0061_drtresults'),
    ]

    operations = [
        migrations.RenameField(
            model_name='drtresults',
            old_name='date_test_perfomed',
            new_name='date_test_performed',
        ),
    ]
