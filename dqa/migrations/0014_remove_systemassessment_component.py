# Generated by Django 3.2.5 on 2023-02-16 06:18

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dqa', '0013_auto_20230215_2154'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='systemassessment',
            name='component',
        ),
    ]