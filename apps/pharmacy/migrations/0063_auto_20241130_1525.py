# Generated by Django 3.2.25 on 2024-11-30 12:25

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cqi', '0012_remove_platformupdate_title'),
        ('dqa', '0023_alter_dqaworkplan_program_areas_reviewed'),
        ('pharmacy', '0062_auto_20241130_0853'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='beginningbalance',
            unique_together={('quarter_year', 'description', 'facility_name', 'date_of_interview')},
        ),
        migrations.AlterUniqueTogether(
            name='expired',
            unique_together={('quarter_year', 'description', 'facility_name', 'date_of_interview')},
        ),
        migrations.AlterUniqueTogether(
            name='expiredunits',
            unique_together={('quarter_year', 'description', 'facility_name', 'date_of_interview')},
        ),
        migrations.AlterUniqueTogether(
            name='expirytracking',
            unique_together={('quarter_year', 'description', 'facility_name', 'date_of_interview')},
        ),
        migrations.AlterUniqueTogether(
            name='negativeadjustment',
            unique_together={('quarter_year', 'description', 'facility_name', 'date_of_interview')},
        ),
        migrations.AlterUniqueTogether(
            name='positiveadjustments',
            unique_together={('quarter_year', 'description', 'facility_name', 'date_of_interview')},
        ),
        migrations.AlterUniqueTogether(
            name='s11formavailability',
            unique_together={('quarter_year', 'description', 'facility_name', 'date_of_interview')},
        ),
        migrations.AlterUniqueTogether(
            name='s11formendorsed',
            unique_together={('quarter_year', 'description', 'facility_name', 'date_of_interview')},
        ),
        migrations.AlterUniqueTogether(
            name='stockcards',
            unique_together={('quarter_year', 'description', 'facility_name', 'date_of_interview')},
        ),
        migrations.AlterUniqueTogether(
            name='stockmanagement',
            unique_together={('quarter_year', 'description', 'facility_name', 'date_of_interview')},
        ),
        migrations.AlterUniqueTogether(
            name='unitissued',
            unique_together={('quarter_year', 'description', 'facility_name', 'date_of_interview')},
        ),
        migrations.AlterUniqueTogether(
            name='unitsupplied',
            unique_together={('quarter_year', 'description', 'facility_name', 'date_of_interview')},
        ),
    ]
