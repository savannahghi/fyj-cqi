# Generated by Django 3.2.19 on 2023-06-02 07:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0039_alter_tablenames_model_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='workplan',
            name='pharmacy_records',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='pharmacy.pharmacyrecords', unique=True),
        ),
    ]