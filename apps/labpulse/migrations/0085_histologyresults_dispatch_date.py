# Generated by Django 3.2.25 on 2024-07-29 10:57

import datetime
from django.db import migrations, models
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('labpulse', '0084_histologypdffile_histologyresults'),
    ]

    operations = [
        migrations.AddField(
            model_name='histologyresults',
            name='dispatch_date',
            field=models.DateTimeField(default=datetime.datetime(2024, 7, 29, 10, 57, 47, 157347, tzinfo=utc)),
            preserve_default=False,
        ),
    ]
