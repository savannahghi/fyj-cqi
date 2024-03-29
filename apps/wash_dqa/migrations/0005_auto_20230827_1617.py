# Generated by Django 3.2.19 on 2023-08-27 13:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wash_dqa', '0004_auto_20230826_1143'),
    ]

    operations = [
        migrations.AlterField(
            model_name='datacollectionreportingmanagement',
            name='dropdown_option',
            field=models.CharField(blank=True, choices=[('Fully meets all requirements', '(5) Fully meets all requirements'), ('Almost meets all requirements', '(4) Almost meets all requirements'), ('Partially meets all requirements', '(3) Partially meets all requirements'), ('Approaches basic requirements', '(2) Approaches basic requirements'), ('Does not meet requirements', '(1) Does not meet requirements'), ('N/A', '(0) N/A')], max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='dataqualitysystems',
            name='dropdown_option',
            field=models.CharField(blank=True, choices=[('Fully meets all requirements', '(5) Fully meets all requirements'), ('Almost meets all requirements', '(4) Almost meets all requirements'), ('Partially meets all requirements', '(3) Partially meets all requirements'), ('Approaches basic requirements', '(2) Approaches basic requirements'), ('Does not meet requirements', '(1) Does not meet requirements'), ('N/A', '(0) N/A')], max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='documentation',
            name='dropdown_option',
            field=models.CharField(blank=True, choices=[('Fully meets all requirements', '(5) Fully meets all requirements'), ('Almost meets all requirements', '(4) Almost meets all requirements'), ('Partially meets all requirements', '(3) Partially meets all requirements'), ('Approaches basic requirements', '(2) Approaches basic requirements'), ('Does not meet requirements', '(1) Does not meet requirements'), ('N/A', '(0) N/A')], max_length=50, null=True),
        ),
    ]
