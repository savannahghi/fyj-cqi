# Generated by Django 3.2.18 on 2023-04-20 11:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_analysis', '0002_auto_20230420_1443'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fyjhealthfacility',
            name='hub',
            field=models.CharField(max_length=50),
        ),
    ]
