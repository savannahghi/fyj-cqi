# Generated by Django 3.2.22 on 2023-11-28 11:15

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('labpulse', '0067_drtresults_tat_days'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='drtresults',
            unique_together={('patient_id', 'collection_date', 'drug')},
        ),
    ]
