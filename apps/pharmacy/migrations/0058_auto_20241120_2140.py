# Generated by Django 3.2.25 on 2024-11-20 18:40

import apps.pharmacy.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0057_auto_20241120_2138'),
    ]

    operations = [
        migrations.AddField(
            model_name='beginningbalance',
            name='al_6',
            field=models.IntegerField(default=0, validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AddField(
            model_name='beginningbalance',
            name='dmpa_im',
            field=models.IntegerField(default=0, validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AddField(
            model_name='beginningbalance',
            name='dmpa_sc',
            field=models.IntegerField(default=0, validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AddField(
            model_name='beginningbalance',
            name='family_planning_rod2',
            field=models.IntegerField(default=0, validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AddField(
            model_name='expired',
            name='al_6',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], default='N/A', max_length=4),
        ),
        migrations.AddField(
            model_name='expired',
            name='dmpa_im',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], default='N/A', max_length=4),
        ),
        migrations.AddField(
            model_name='expired',
            name='dmpa_sc',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], default='N/A', max_length=4),
        ),
        migrations.AddField(
            model_name='expired',
            name='family_planning_rod2',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], default='N/A', max_length=4),
        ),
        migrations.AddField(
            model_name='expiredunits',
            name='al_6',
            field=models.IntegerField(default=0, validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AddField(
            model_name='expiredunits',
            name='dmpa_im',
            field=models.IntegerField(default=0, validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AddField(
            model_name='expiredunits',
            name='dmpa_sc',
            field=models.IntegerField(default=0, validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AddField(
            model_name='expiredunits',
            name='family_planning_rod2',
            field=models.IntegerField(default=0, validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AddField(
            model_name='expirytracking',
            name='al_6',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], default='N/A', max_length=4),
        ),
        migrations.AddField(
            model_name='expirytracking',
            name='dmpa_im',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], default='N/A', max_length=4),
        ),
        migrations.AddField(
            model_name='expirytracking',
            name='dmpa_sc',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], default='N/A', max_length=4),
        ),
        migrations.AddField(
            model_name='expirytracking',
            name='family_planning_rod2',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], default='N/A', max_length=4),
        ),
        migrations.AddField(
            model_name='negativeadjustment',
            name='al_6',
            field=models.IntegerField(default=0, validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AddField(
            model_name='negativeadjustment',
            name='dmpa_im',
            field=models.IntegerField(default=0, validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AddField(
            model_name='negativeadjustment',
            name='dmpa_sc',
            field=models.IntegerField(default=0, validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AddField(
            model_name='negativeadjustment',
            name='family_planning_rod2',
            field=models.IntegerField(default=0, validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AddField(
            model_name='positiveadjustments',
            name='al_6',
            field=models.IntegerField(default=0, validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AddField(
            model_name='positiveadjustments',
            name='dmpa_im',
            field=models.IntegerField(default=0, validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AddField(
            model_name='positiveadjustments',
            name='dmpa_sc',
            field=models.IntegerField(default=0, validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AddField(
            model_name='positiveadjustments',
            name='family_planning_rod2',
            field=models.IntegerField(default=0, validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AddField(
            model_name='s11formavailability',
            name='al_6',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], default='N/A', max_length=4),
        ),
        migrations.AddField(
            model_name='s11formavailability',
            name='dmpa_im',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], default='N/A', max_length=4),
        ),
        migrations.AddField(
            model_name='s11formavailability',
            name='dmpa_sc',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], default='N/A', max_length=4),
        ),
        migrations.AddField(
            model_name='s11formavailability',
            name='family_planning_rod2',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], default='N/A', max_length=4),
        ),
        migrations.AddField(
            model_name='s11formendorsed',
            name='al_6',
            field=models.IntegerField(default=0, validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AddField(
            model_name='s11formendorsed',
            name='dmpa_im',
            field=models.IntegerField(default=0, validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AddField(
            model_name='s11formendorsed',
            name='dmpa_sc',
            field=models.IntegerField(default=0, validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AddField(
            model_name='s11formendorsed',
            name='family_planning_rod2',
            field=models.IntegerField(default=0, validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AddField(
            model_name='stockcards',
            name='al_6',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], default='N/A', max_length=4),
        ),
        migrations.AddField(
            model_name='stockcards',
            name='dmpa_im',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], default='N/A', max_length=4),
        ),
        migrations.AddField(
            model_name='stockcards',
            name='dmpa_sc',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], default='N/A', max_length=4),
        ),
        migrations.AddField(
            model_name='stockcards',
            name='family_planning_rod2',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], default='N/A', max_length=4),
        ),
        migrations.AddField(
            model_name='stockmanagement',
            name='al_6',
            field=models.IntegerField(default=0, validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AddField(
            model_name='stockmanagement',
            name='dmpa_im',
            field=models.IntegerField(default=0, validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AddField(
            model_name='stockmanagement',
            name='dmpa_sc',
            field=models.IntegerField(default=0, validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AddField(
            model_name='stockmanagement',
            name='family_planning_rod2',
            field=models.IntegerField(default=0, validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AddField(
            model_name='unitissued',
            name='al_6',
            field=models.IntegerField(default=0, validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AddField(
            model_name='unitissued',
            name='dmpa_im',
            field=models.IntegerField(default=0, validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AddField(
            model_name='unitissued',
            name='dmpa_sc',
            field=models.IntegerField(default=0, validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AddField(
            model_name='unitissued',
            name='family_planning_rod2',
            field=models.IntegerField(default=0, validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AddField(
            model_name='unitsupplied',
            name='al_6',
            field=models.IntegerField(default=0, validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AddField(
            model_name='unitsupplied',
            name='dmpa_im',
            field=models.IntegerField(default=0, validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AddField(
            model_name='unitsupplied',
            name='dmpa_sc',
            field=models.IntegerField(default=0, validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AddField(
            model_name='unitsupplied',
            name='family_planning_rod2',
            field=models.IntegerField(default=0, validators=[apps.pharmacy.models.validate_non_negative]),
        ),
    ]
