# Generated by Django 3.2.25 on 2024-07-29 09:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0051_auto_20240212_1249'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pharmacyrecords',
            name='currently_in_use',
            field=models.CharField(blank=True, choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='pharmacyrecords',
            name='last_month_copy',
            field=models.CharField(choices=[('', 'Select an option'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], max_length=10),
        ),
        migrations.AlterField(
            model_name='pharmacyrecords',
            name='register_available',
            field=models.CharField(choices=[('', 'Select an option'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], max_length=10),
        ),
    ]
