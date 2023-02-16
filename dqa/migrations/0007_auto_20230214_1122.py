# Generated by Django 3.2.5 on 2023-02-14 08:22

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('project', '0001_initial'),
        ('dqa', '0006_dqaworkplan_quarter_year'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dqaworkplan',
            name='facility_name',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='project.facilities'),
        ),
        migrations.AlterField(
            model_name='dqaworkplan',
            name='quarter_year',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='dqa.period'),
        ),
    ]
