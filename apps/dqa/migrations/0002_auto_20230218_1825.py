# Generated by Django 3.2.5 on 2023-02-18 15:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cqi', '0001_initial'),
        ('dqa', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='period',
            name='quarter_year',
            field=models.CharField(blank=True, max_length=10),
        ),
        migrations.AlterUniqueTogether(
            name='systemassessment',
            unique_together={('quarter_year', 'description', 'facility_name')},
        ),
    ]
