# Generated by Django 3.2.25 on 2025-01-23 05:07

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0064_auto_20250122_1149'),
    ]

    operations = [
        migrations.AddField(
            model_name='workplan',
            name='delivery_notes',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='pharmacy.deliverynotes'),
        ),
    ]
