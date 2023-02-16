# Generated by Django 3.2.5 on 2023-02-14 07:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('project', '0001_initial'),
        ('dqa', '0004_alter_dqaworkplan_individuals_responsible'),
    ]

    operations = [
        migrations.AddField(
            model_name='dqaworkplan',
            name='facility_name',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='project.facilities'),
            preserve_default=False,
        ),
    ]