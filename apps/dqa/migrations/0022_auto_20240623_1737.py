# Generated by Django 3.2.25 on 2024-06-23 14:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dqa', '0021_auto_20240605_1437'),
    ]

    operations = [
        migrations.AddField(
            model_name='caretreatment',
            name='auditor_note',
            field=models.CharField(blank=True, max_length=800, null=True),
        ),
        migrations.AddField(
            model_name='cqi',
            name='auditor_note',
            field=models.CharField(blank=True, max_length=800, null=True),
        ),
        migrations.AddField(
            model_name='gbv',
            name='auditor_note',
            field=models.CharField(blank=True, max_length=800, null=True),
        ),
        migrations.AddField(
            model_name='hts',
            name='auditor_note',
            field=models.CharField(blank=True, max_length=800, null=True),
        ),
        migrations.AddField(
            model_name='pharmacy',
            name='auditor_note',
            field=models.CharField(blank=True, max_length=800, null=True),
        ),
        migrations.AddField(
            model_name='prep',
            name='auditor_note',
            field=models.CharField(blank=True, max_length=800, null=True),
        ),
        migrations.AddField(
            model_name='tb',
            name='auditor_note',
            field=models.CharField(blank=True, max_length=800, null=True),
        ),
        migrations.AddField(
            model_name='vmmc',
            name='auditor_note',
            field=models.CharField(blank=True, max_length=800, null=True),
        ),
    ]
