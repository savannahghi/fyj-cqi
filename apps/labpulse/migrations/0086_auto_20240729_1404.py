# Generated by Django 3.2.25 on 2024-07-29 11:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('labpulse', '0085_histologyresults_dispatch_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='histologyresults',
            name='reported_by',
            field=models.CharField(max_length=250),
        ),
        migrations.AlterField(
            model_name='histologyresults',
            name='test_performed_by',
            field=models.CharField(max_length=250),
        ),
    ]
