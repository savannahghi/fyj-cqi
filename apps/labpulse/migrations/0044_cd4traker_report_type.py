# Generated by Django 3.2.19 on 2023-07-05 06:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('labpulse', '0043_alter_cd4traker_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='cd4traker',
            name='report_type',
            field=models.CharField(blank=True, max_length=25, null=True),
        ),
    ]
