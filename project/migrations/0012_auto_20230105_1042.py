# Generated by Django 3.2.5 on 2023-01-05 07:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('project', '0011_testedchange_data_sources'),
    ]

    operations = [
        migrations.AlterField(
            model_name='testedchange',
            name='comments',
            field=models.CharField(blank=True, max_length=2000, null=True),
        ),
        migrations.AlterField(
            model_name='testedchange',
            name='month_year',
            field=models.DateField(verbose_name='Date'),
        ),
    ]
