# Generated by Django 3.2.19 on 2023-08-31 07:27

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('wash_dqa', '0019_remove_dataconcordance_sub_county_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='ward',
            name='ward_code',
            field=models.CharField(default=django.utils.timezone.now, max_length=250, unique=True),
            preserve_default=False,
        ),
    ]
