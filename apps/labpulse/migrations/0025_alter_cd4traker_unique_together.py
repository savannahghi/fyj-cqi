# Generated by Django 3.2.19 on 2023-06-15 15:37

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cqi', '0003_auto_20230426_1152'),
        ('labpulse', '0024_alter_cd4traker_unique_together'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='cd4traker',
            unique_together={('patient_unique_no', 'facility_name', 'date_of_collection')},
        ),
    ]