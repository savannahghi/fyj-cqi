# Generated by Django 3.2.25 on 2024-11-21 04:05

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0058_auto_20241120_2140'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='beginningbalance',
            name='al_24',
        ),
        migrations.RemoveField(
            model_name='beginningbalance',
            name='al_6',
        ),
        migrations.RemoveField(
            model_name='beginningbalance',
            name='dmpa_im',
        ),
        migrations.RemoveField(
            model_name='beginningbalance',
            name='dmpa_sc',
        ),
        migrations.RemoveField(
            model_name='beginningbalance',
            name='family_planning_rod',
        ),
        migrations.RemoveField(
            model_name='beginningbalance',
            name='family_planning_rod2',
        ),
        migrations.RemoveField(
            model_name='expired',
            name='al_24',
        ),
        migrations.RemoveField(
            model_name='expired',
            name='al_6',
        ),
        migrations.RemoveField(
            model_name='expired',
            name='dmpa_im',
        ),
        migrations.RemoveField(
            model_name='expired',
            name='dmpa_sc',
        ),
        migrations.RemoveField(
            model_name='expired',
            name='family_planning_rod',
        ),
        migrations.RemoveField(
            model_name='expired',
            name='family_planning_rod2',
        ),
        migrations.RemoveField(
            model_name='expiredunits',
            name='al_24',
        ),
        migrations.RemoveField(
            model_name='expiredunits',
            name='al_6',
        ),
        migrations.RemoveField(
            model_name='expiredunits',
            name='dmpa_im',
        ),
        migrations.RemoveField(
            model_name='expiredunits',
            name='dmpa_sc',
        ),
        migrations.RemoveField(
            model_name='expiredunits',
            name='family_planning_rod',
        ),
        migrations.RemoveField(
            model_name='expiredunits',
            name='family_planning_rod2',
        ),
        migrations.RemoveField(
            model_name='expirytracking',
            name='al_24',
        ),
        migrations.RemoveField(
            model_name='expirytracking',
            name='al_6',
        ),
        migrations.RemoveField(
            model_name='expirytracking',
            name='dmpa_im',
        ),
        migrations.RemoveField(
            model_name='expirytracking',
            name='dmpa_sc',
        ),
        migrations.RemoveField(
            model_name='expirytracking',
            name='family_planning_rod',
        ),
        migrations.RemoveField(
            model_name='expirytracking',
            name='family_planning_rod2',
        ),
        migrations.RemoveField(
            model_name='negativeadjustment',
            name='al_24',
        ),
        migrations.RemoveField(
            model_name='negativeadjustment',
            name='al_6',
        ),
        migrations.RemoveField(
            model_name='negativeadjustment',
            name='dmpa_im',
        ),
        migrations.RemoveField(
            model_name='negativeadjustment',
            name='dmpa_sc',
        ),
        migrations.RemoveField(
            model_name='negativeadjustment',
            name='family_planning_rod',
        ),
        migrations.RemoveField(
            model_name='negativeadjustment',
            name='family_planning_rod2',
        ),
        migrations.RemoveField(
            model_name='positiveadjustments',
            name='al_24',
        ),
        migrations.RemoveField(
            model_name='positiveadjustments',
            name='al_6',
        ),
        migrations.RemoveField(
            model_name='positiveadjustments',
            name='dmpa_im',
        ),
        migrations.RemoveField(
            model_name='positiveadjustments',
            name='dmpa_sc',
        ),
        migrations.RemoveField(
            model_name='positiveadjustments',
            name='family_planning_rod',
        ),
        migrations.RemoveField(
            model_name='positiveadjustments',
            name='family_planning_rod2',
        ),
        migrations.RemoveField(
            model_name='s11formavailability',
            name='al_24',
        ),
        migrations.RemoveField(
            model_name='s11formavailability',
            name='al_6',
        ),
        migrations.RemoveField(
            model_name='s11formavailability',
            name='dmpa_im',
        ),
        migrations.RemoveField(
            model_name='s11formavailability',
            name='dmpa_sc',
        ),
        migrations.RemoveField(
            model_name='s11formavailability',
            name='family_planning_rod',
        ),
        migrations.RemoveField(
            model_name='s11formavailability',
            name='family_planning_rod2',
        ),
        migrations.RemoveField(
            model_name='s11formendorsed',
            name='al_24',
        ),
        migrations.RemoveField(
            model_name='s11formendorsed',
            name='al_6',
        ),
        migrations.RemoveField(
            model_name='s11formendorsed',
            name='dmpa_im',
        ),
        migrations.RemoveField(
            model_name='s11formendorsed',
            name='dmpa_sc',
        ),
        migrations.RemoveField(
            model_name='s11formendorsed',
            name='family_planning_rod',
        ),
        migrations.RemoveField(
            model_name='s11formendorsed',
            name='family_planning_rod2',
        ),
        migrations.RemoveField(
            model_name='stockcards',
            name='al_24',
        ),
        migrations.RemoveField(
            model_name='stockcards',
            name='al_6',
        ),
        migrations.RemoveField(
            model_name='stockcards',
            name='dmpa_im',
        ),
        migrations.RemoveField(
            model_name='stockcards',
            name='dmpa_sc',
        ),
        migrations.RemoveField(
            model_name='stockcards',
            name='family_planning_rod',
        ),
        migrations.RemoveField(
            model_name='stockcards',
            name='family_planning_rod2',
        ),
        migrations.RemoveField(
            model_name='stockmanagement',
            name='al_24',
        ),
        migrations.RemoveField(
            model_name='stockmanagement',
            name='al_6',
        ),
        migrations.RemoveField(
            model_name='stockmanagement',
            name='dmpa_im',
        ),
        migrations.RemoveField(
            model_name='stockmanagement',
            name='dmpa_sc',
        ),
        migrations.RemoveField(
            model_name='stockmanagement',
            name='family_planning_rod',
        ),
        migrations.RemoveField(
            model_name='stockmanagement',
            name='family_planning_rod2',
        ),
        migrations.RemoveField(
            model_name='unitissued',
            name='al_24',
        ),
        migrations.RemoveField(
            model_name='unitissued',
            name='al_6',
        ),
        migrations.RemoveField(
            model_name='unitissued',
            name='dmpa_im',
        ),
        migrations.RemoveField(
            model_name='unitissued',
            name='dmpa_sc',
        ),
        migrations.RemoveField(
            model_name='unitissued',
            name='family_planning_rod',
        ),
        migrations.RemoveField(
            model_name='unitissued',
            name='family_planning_rod2',
        ),
        migrations.RemoveField(
            model_name='unitsupplied',
            name='al_24',
        ),
        migrations.RemoveField(
            model_name='unitsupplied',
            name='al_6',
        ),
        migrations.RemoveField(
            model_name='unitsupplied',
            name='dmpa_im',
        ),
        migrations.RemoveField(
            model_name='unitsupplied',
            name='dmpa_sc',
        ),
        migrations.RemoveField(
            model_name='unitsupplied',
            name='family_planning_rod',
        ),
        migrations.RemoveField(
            model_name='unitsupplied',
            name='family_planning_rod2',
        ),
    ]
