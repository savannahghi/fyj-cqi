# Generated by Django 3.2.18 on 2023-04-26 08:52

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('data_analysis', '0004_auto_20230420_1446'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='fyjhealthfacility',
            unique_together={('mfl_code', 'facility')},
        ),
    ]