# Generated by Django 3.2.22 on 2023-11-14 08:49

import crum
from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('cqi', '0007_alter_facilities_fyj_facilities'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('labpulse', '0058_rename_disable_commodities_use_enabledisablecommodities_use_commodities'),
    ]

    operations = [
        migrations.CreateModel(
            name='DrtResults',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('patient_id', models.IntegerField(validators=[django.core.validators.MaxValueValidator(9999999999)])),
                ('result', models.FileField(upload_to='drt_results')),
                ('collection_date', models.DateTimeField()),
                ('county', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cqi.counties')),
                ('created_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('facility_name', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cqi.facilities')),
                ('modified_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('sub_county', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cqi.sub_counties')),
            ],
            options={
                'ordering': ['patient_id', 'date_created'],
            },
        ),
        migrations.CreateModel(
            name='BiochemistryResult',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('sample_id', models.CharField(max_length=50)),
                ('patient_id', models.CharField(max_length=10)),
                ('test', models.CharField(max_length=100)),
                ('full_name', models.CharField(max_length=255)),
                ('result', models.FloatField()),
                ('low_limit', models.FloatField()),
                ('high_limit', models.FloatField()),
                ('units', models.CharField(max_length=20)),
                ('reference_class', models.CharField(max_length=100)),
                ('collection_date', models.DateField()),
                ('result_time', models.DateTimeField()),
                ('mfl_code', models.IntegerField()),
                ('results_interpretation', models.CharField(max_length=255)),
                ('number_of_samples', models.IntegerField()),
                ('created_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Biochemistry Result',
                'verbose_name_plural': 'Biochemistry Results',
                'ordering': ['patient_id', 'collection_date'],
                'unique_together': {('sample_id', 'patient_id', 'test', 'collection_date', 'result')},
            },
        ),
    ]