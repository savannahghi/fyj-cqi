# Generated by Django 3.2.25 on 2024-12-19 06:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('labpulse', '0105_auto_20241219_0839'),
    ]

    operations = [
        migrations.AlterField(
            model_name='biochemistrytestinglab',
            name='mfl_code',
            field=models.IntegerField(default=0, unique=True),
        ),
        migrations.AlterField(
            model_name='biochemistrytestinglab',
            name='testing_lab_name',
            field=models.CharField(default='', max_length=255, unique=True),
        ),
        migrations.AlterField(
            model_name='cd4testinglabs',
            name='mfl_code',
            field=models.IntegerField(default=0, unique=True),
        ),
        migrations.AlterField(
            model_name='cd4testinglabs',
            name='testing_lab_name',
            field=models.CharField(default='', max_length=255, unique=True),
        ),
    ]