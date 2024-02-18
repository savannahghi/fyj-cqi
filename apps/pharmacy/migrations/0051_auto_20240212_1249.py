# Generated by Django 3.2.22 on 2024-02-12 09:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0050_alter_workplan_pharmacy_records'),
    ]

    operations = [
        migrations.AlterField(
            model_name='expired',
            name='adult_arv_tdf_3tc_dtg',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], max_length=4),
        ),
        migrations.AlterField(
            model_name='expired',
            name='al_24',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], max_length=4),
        ),
        migrations.AlterField(
            model_name='expired',
            name='family_planning_rod',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], max_length=4),
        ),
        migrations.AlterField(
            model_name='expired',
            name='paed_arv_abc_3tc_120_60mg',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], max_length=4),
        ),
        migrations.AlterField(
            model_name='expired',
            name='pead_arv_dtg_10mg',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], max_length=4),
        ),
        migrations.AlterField(
            model_name='expired',
            name='tb_3hp',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], max_length=4),
        ),
        migrations.AlterField(
            model_name='expirytracking',
            name='adult_arv_tdf_3tc_dtg',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], max_length=4),
        ),
        migrations.AlterField(
            model_name='expirytracking',
            name='al_24',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], max_length=4),
        ),
        migrations.AlterField(
            model_name='expirytracking',
            name='family_planning_rod',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], max_length=4),
        ),
        migrations.AlterField(
            model_name='expirytracking',
            name='paed_arv_abc_3tc_120_60mg',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], max_length=4),
        ),
        migrations.AlterField(
            model_name='expirytracking',
            name='pead_arv_dtg_10mg',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], max_length=4),
        ),
        migrations.AlterField(
            model_name='expirytracking',
            name='tb_3hp',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], max_length=4),
        ),
        migrations.AlterField(
            model_name='s11formavailability',
            name='adult_arv_tdf_3tc_dtg',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], max_length=4),
        ),
        migrations.AlterField(
            model_name='s11formavailability',
            name='al_24',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], max_length=4),
        ),
        migrations.AlterField(
            model_name='s11formavailability',
            name='family_planning_rod',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], max_length=4),
        ),
        migrations.AlterField(
            model_name='s11formavailability',
            name='paed_arv_abc_3tc_120_60mg',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], max_length=4),
        ),
        migrations.AlterField(
            model_name='s11formavailability',
            name='pead_arv_dtg_10mg',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], max_length=4),
        ),
        migrations.AlterField(
            model_name='s11formavailability',
            name='tb_3hp',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], max_length=4),
        ),
        migrations.AlterField(
            model_name='stockcards',
            name='adult_arv_tdf_3tc_dtg',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], max_length=4),
        ),
        migrations.AlterField(
            model_name='stockcards',
            name='al_24',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], max_length=4),
        ),
        migrations.AlterField(
            model_name='stockcards',
            name='family_planning_rod',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], max_length=4),
        ),
        migrations.AlterField(
            model_name='stockcards',
            name='paed_arv_abc_3tc_120_60mg',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], max_length=4),
        ),
        migrations.AlterField(
            model_name='stockcards',
            name='pead_arv_dtg_10mg',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], max_length=4),
        ),
        migrations.AlterField(
            model_name='stockcards',
            name='tb_3hp',
            field=models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], max_length=4),
        ),
    ]
