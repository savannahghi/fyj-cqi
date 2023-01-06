# Generated by Django 3.2.5 on 2023-01-06 17:00

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('project', '0014_auto_20230106_1837'),
    ]

    operations = [
        migrations.AddField(
            model_name='actionplan',
            name='date_created',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='actionplan',
            name='date_updated',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='actionplan',
            name='progress',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='actionplan',
            name='timeframe',
            field=models.FloatField(blank=True, null=True),
        ),
    ]
