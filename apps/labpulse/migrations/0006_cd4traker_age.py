# Generated by Django 3.2.19 on 2023-06-14 04:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('labpulse', '0005_remove_cd4traker_record_count'),
    ]

    operations = [
        migrations.AddField(
            model_name='cd4traker',
            name='age',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
