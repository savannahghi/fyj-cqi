# Generated by Django 3.2.22 on 2024-01-10 11:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('labpulse', '0072_cd4traker_tat_days'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cd4traker',
            name='tat_days',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
