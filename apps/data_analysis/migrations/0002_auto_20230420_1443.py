# Generated by Django 3.2.18 on 2023-04-20 11:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_analysis', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fyjhealthfacility',
            name='care_and_treatment',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='fyjhealthfacility',
            name='emr',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='fyjhealthfacility',
            name='hts',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='fyjhealthfacility',
            name='key_pop',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='fyjhealthfacility',
            name='vmmc',
            field=models.CharField(max_length=100),
        ),
    ]
