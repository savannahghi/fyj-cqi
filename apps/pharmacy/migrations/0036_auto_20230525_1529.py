# Generated by Django 3.2.19 on 2023-05-25 12:29

import apps.pharmacy.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0035_auto_20230522_0928'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='workplan',
            name='quantity_delivered',
        ),
        migrations.AlterField(
            model_name='beginningbalance',
            name='adult_arv_tdf_3tc_dtg',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='beginningbalance',
            name='al_24',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='beginningbalance',
            name='family_planning_rod',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='beginningbalance',
            name='paed_arv_abc_3tc_120_60mg',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='beginningbalance',
            name='pead_arv_dtg_10mg',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='beginningbalance',
            name='tb_3hp',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='expiredunits',
            name='adult_arv_tdf_3tc_dtg',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='expiredunits',
            name='al_24',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='expiredunits',
            name='family_planning_rod',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='expiredunits',
            name='paed_arv_abc_3tc_120_60mg',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='expiredunits',
            name='pead_arv_dtg_10mg',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='expiredunits',
            name='tb_3hp',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='negativeadjustment',
            name='adult_arv_tdf_3tc_dtg',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='negativeadjustment',
            name='al_24',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='negativeadjustment',
            name='family_planning_rod',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='negativeadjustment',
            name='paed_arv_abc_3tc_120_60mg',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='negativeadjustment',
            name='pead_arv_dtg_10mg',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='negativeadjustment',
            name='tb_3hp',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='positiveadjustments',
            name='adult_arv_tdf_3tc_dtg',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='positiveadjustments',
            name='al_24',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='positiveadjustments',
            name='family_planning_rod',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='positiveadjustments',
            name='paed_arv_abc_3tc_120_60mg',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='positiveadjustments',
            name='pead_arv_dtg_10mg',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='positiveadjustments',
            name='tb_3hp',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='s11formendorsed',
            name='adult_arv_tdf_3tc_dtg',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='s11formendorsed',
            name='al_24',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='s11formendorsed',
            name='family_planning_rod',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='s11formendorsed',
            name='paed_arv_abc_3tc_120_60mg',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='s11formendorsed',
            name='pead_arv_dtg_10mg',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='s11formendorsed',
            name='tb_3hp',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='stockmanagement',
            name='adult_arv_tdf_3tc_dtg',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='stockmanagement',
            name='al_24',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='stockmanagement',
            name='family_planning_rod',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='stockmanagement',
            name='paed_arv_abc_3tc_120_60mg',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='stockmanagement',
            name='pead_arv_dtg_10mg',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='stockmanagement',
            name='tb_3hp',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='unitissued',
            name='adult_arv_tdf_3tc_dtg',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='unitissued',
            name='al_24',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='unitissued',
            name='family_planning_rod',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='unitissued',
            name='paed_arv_abc_3tc_120_60mg',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='unitissued',
            name='pead_arv_dtg_10mg',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='unitissued',
            name='tb_3hp',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='unitreceived',
            name='adult_arv_tdf_3tc_dtg',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='unitreceived',
            name='al_24',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='unitreceived',
            name='family_planning_rod',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='unitreceived',
            name='paed_arv_abc_3tc_120_60mg',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='unitreceived',
            name='pead_arv_dtg_10mg',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='unitreceived',
            name='tb_3hp',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='unitsupplied',
            name='adult_arv_tdf_3tc_dtg',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='unitsupplied',
            name='al_24',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='unitsupplied',
            name='family_planning_rod',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='unitsupplied',
            name='paed_arv_abc_3tc_120_60mg',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='unitsupplied',
            name='pead_arv_dtg_10mg',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.AlterField(
            model_name='unitsupplied',
            name='tb_3hp',
            field=models.IntegerField(validators=[apps.pharmacy.models.validate_non_negative]),
        ),
        migrations.DeleteModel(
            name='QuantityDelivered',
        ),
    ]
