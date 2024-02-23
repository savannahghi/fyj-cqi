# Generated by Django 3.2.22 on 2024-02-23 07:54

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cqi', '0008_auto_20231216_1755'),
        ('labpulse', '0079_biochemistryresult_age'),
    ]

    operations = [
        migrations.AddField(
            model_name='biochemistryresult',
            name='county',
            field=models.ForeignKey(default='', on_delete=django.db.models.deletion.CASCADE, related_name='counties', to='cqi.counties'),
        ),
        migrations.AddField(
            model_name='biochemistryresult',
            name='facility',
            field=models.ForeignKey(default='', on_delete=django.db.models.deletion.CASCADE, related_name='facilities', to='cqi.facilities'),
        ),
        migrations.AddField(
            model_name='biochemistryresult',
            name='sub_county',
            field=models.ForeignKey(default='', on_delete=django.db.models.deletion.CASCADE, related_name='subcounties', to='cqi.sub_counties'),
        ),
    ]
