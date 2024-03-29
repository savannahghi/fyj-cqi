# Generated by Django 3.2.19 on 2023-08-28 06:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wash_dqa', '0007_auto_20230828_0926'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dataqualityassessment',
            name='number_access_basic_sanitation',
            field=models.CharField(blank=True, choices=[('N/A', 'N/A'), ('No', 'No'), ('Yes', 'Yes')], max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='dataqualityassessment',
            name='number_access_basic_sanitation_institutions',
            field=models.CharField(blank=True, choices=[('N/A', 'N/A'), ('No', 'No'), ('Yes', 'Yes')], max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='dataqualityassessment',
            name='number_access_basic_water',
            field=models.CharField(blank=True, choices=[('N/A', 'N/A'), ('No', 'No'), ('Yes', 'Yes')], max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='dataqualityassessment',
            name='number_access_safe_sanitation',
            field=models.CharField(blank=True, choices=[('N/A', 'N/A'), ('No', 'No'), ('Yes', 'Yes')], max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='dataqualityassessment',
            name='number_access_safe_water',
            field=models.CharField(blank=True, choices=[('N/A', 'N/A'), ('No', 'No'), ('Yes', 'Yes')], max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='dataqualityassessment',
            name='number_community_open_defecation',
            field=models.CharField(blank=True, choices=[('N/A', 'N/A'), ('No', 'No'), ('Yes', 'Yes')], max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='dataqualityassessment',
            name='number_trained',
            field=models.CharField(blank=True, choices=[('N/A', 'N/A'), ('No', 'No'), ('Yes', 'Yes')], max_length=50, null=True),
        ),
    ]
