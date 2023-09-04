# Generated by Django 3.2.19 on 2023-08-30 18:20

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('wash_dqa', '0013_auto_20230830_2044'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='counties',
            name='created_by',
        ),
        migrations.RemoveField(
            model_name='counties',
            name='modified_by',
        ),
        migrations.AlterUniqueTogether(
            name='datacollectionreportingmanagement',
            unique_together=None,
        ),
        migrations.RemoveField(
            model_name='datacollectionreportingmanagement',
            name='created_by',
        ),
        migrations.RemoveField(
            model_name='datacollectionreportingmanagement',
            name='modified_by',
        ),
        migrations.RemoveField(
            model_name='datacollectionreportingmanagement',
            name='quarter_year',
        ),
        migrations.RemoveField(
            model_name='datacollectionreportingmanagement',
            name='sub_county_name',
        ),
        migrations.RemoveField(
            model_name='datacollectionreportingmanagement',
            name='ward_name',
        ),
        migrations.AlterUniqueTogether(
            name='dataconcordance',
            unique_together=None,
        ),
        migrations.RemoveField(
            model_name='dataconcordance',
            name='created_by',
        ),
        migrations.RemoveField(
            model_name='dataconcordance',
            name='modified_by',
        ),
        migrations.RemoveField(
            model_name='dataconcordance',
            name='quarter_year',
        ),
        migrations.RemoveField(
            model_name='dataconcordance',
            name='sub_county_name',
        ),
        migrations.RemoveField(
            model_name='dataconcordance',
            name='ward_name',
        ),
        migrations.AlterUniqueTogether(
            name='dataqualityassessment',
            unique_together=None,
        ),
        migrations.RemoveField(
            model_name='dataqualityassessment',
            name='created_by',
        ),
        migrations.RemoveField(
            model_name='dataqualityassessment',
            name='modified_by',
        ),
        migrations.RemoveField(
            model_name='dataqualityassessment',
            name='quarter_year',
        ),
        migrations.RemoveField(
            model_name='dataqualityassessment',
            name='sub_county_name',
        ),
        migrations.RemoveField(
            model_name='dataqualityassessment',
            name='ward_name',
        ),
        migrations.AlterUniqueTogether(
            name='dataqualitysystems',
            unique_together=None,
        ),
        migrations.RemoveField(
            model_name='dataqualitysystems',
            name='created_by',
        ),
        migrations.RemoveField(
            model_name='dataqualitysystems',
            name='modified_by',
        ),
        migrations.RemoveField(
            model_name='dataqualitysystems',
            name='quarter_year',
        ),
        migrations.RemoveField(
            model_name='dataqualitysystems',
            name='sub_county_name',
        ),
        migrations.RemoveField(
            model_name='dataqualitysystems',
            name='ward_name',
        ),
        migrations.AlterUniqueTogether(
            name='documentation',
            unique_together=None,
        ),
        migrations.RemoveField(
            model_name='documentation',
            name='created_by',
        ),
        migrations.RemoveField(
            model_name='documentation',
            name='modified_by',
        ),
        migrations.RemoveField(
            model_name='documentation',
            name='quarter_year',
        ),
        migrations.RemoveField(
            model_name='documentation',
            name='sub_county_name',
        ),
        migrations.RemoveField(
            model_name='documentation',
            name='ward_name',
        ),
        migrations.RemoveField(
            model_name='period',
            name='created_by',
        ),
        migrations.RemoveField(
            model_name='period',
            name='modified_by',
        ),
        migrations.RemoveField(
            model_name='subcounties',
            name='county',
        ),
        migrations.RemoveField(
            model_name='subcounties',
            name='created_by',
        ),
        migrations.RemoveField(
            model_name='subcounties',
            name='modified_by',
        ),
        migrations.DeleteModel(
            name='TableNames',
        ),
        migrations.RemoveField(
            model_name='ward',
            name='created_by',
        ),
        migrations.RemoveField(
            model_name='ward',
            name='modified_by',
        ),
        migrations.RemoveField(
            model_name='ward',
            name='sub_county',
        ),
        migrations.DeleteModel(
            name='Counties',
        ),
        migrations.DeleteModel(
            name='DataCollectionReportingManagement',
        ),
        migrations.DeleteModel(
            name='DataConcordance',
        ),
        migrations.DeleteModel(
            name='DataQualityAssessment',
        ),
        migrations.DeleteModel(
            name='DataQualitySystems',
        ),
        migrations.DeleteModel(
            name='Documentation',
        ),
        migrations.DeleteModel(
            name='Period',
        ),
        migrations.DeleteModel(
            name='SubCounties',
        ),
        migrations.DeleteModel(
            name='Ward',
        ),
    ]
