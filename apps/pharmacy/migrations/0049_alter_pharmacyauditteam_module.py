# Generated by Django 3.2.19 on 2023-06-05 11:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0048_pharmacyauditteam'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pharmacyauditteam',
            name='module',
            field=models.CharField(blank=True, default='Pharmacy', max_length=255, null=True),
        ),
    ]
