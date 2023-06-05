# Generated by Django 3.2.19 on 2023-05-17 03:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0013_alter_registers_register_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pharmacyrecords',
            name='currently_in_use',
            field=models.CharField(blank=True, choices=[('Yes', 'Yes'), ('No', 'No')], max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='pharmacyrecords',
            name='last_month_copy',
            field=models.CharField(blank=True, choices=[('Yes', 'Yes'), ('No', 'No')], max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='pharmacyrecords',
            name='register_available',
            field=models.CharField(blank=True, choices=[('Yes', 'Yes'), ('No', 'No')], max_length=10, null=True),
        ),
    ]
