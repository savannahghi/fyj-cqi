# Generated by Django 3.2.5 on 2023-02-22 10:04

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cqi', '0015_auto_20230222_1259'),
    ]

    operations = [
        migrations.AddField(
            model_name='baseline',
            name='county_qi_project',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cqi.county_qi_projects'),
        ),
        migrations.AddField(
            model_name='baseline',
            name='hub_qi_project',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cqi.hub_qi_projects'),
        ),
        migrations.AddField(
            model_name='baseline',
            name='subcounty_qi_project',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cqi.subcounty_qi_projects'),
        ),
    ]
