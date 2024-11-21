# Generated by Django 3.2.25 on 2024-11-21 05:34

import crum
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('cqi', '0012_remove_platformupdate_title'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('dqa', '0022_auto_20240623_1737'),
        ('pharmacy', '0060_pharmacyfpmodel_pharmacymalariamodel'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='tablenames',
            options={'verbose_name_plural': 'Table names'},
        ),
        migrations.CreateModel(
            name='PharmacyMalariaQualitativeModel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('date_of_interview', models.DateField(blank=True, null=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('description', models.TextField()),
                ('al_24', models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], default='N/A', max_length=4)),
                ('al_6', models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], default='N/A', max_length=4)),
                ('comments', models.TextField(blank=True, null=True)),
                ('created_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('facility_name', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cqi.facilities')),
                ('model_name', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='pharmacy.tablenames')),
                ('modified_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('quarter_year', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='dqa.period')),
            ],
            options={
                'verbose_name_plural': 'Anti-Malaria',
                'ordering': ['facility_name'],
                'unique_together': {('quarter_year', 'description', 'facility_name', 'date_of_interview')},
            },
        ),
        migrations.CreateModel(
            name='PharmacyFpQualitativeModel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('date_of_interview', models.DateField(blank=True, null=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('description', models.TextField()),
                ('family_planning_rod', models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], default='N/A', max_length=4)),
                ('family_planning_rod2', models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], default='N/A', max_length=4)),
                ('dmpa_im', models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], default='N/A', max_length=4)),
                ('dmpa_sc', models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], default='N/A', max_length=4)),
                ('comments', models.TextField(blank=True, null=True)),
                ('created_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('facility_name', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cqi.facilities')),
                ('model_name', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='pharmacy.tablenames')),
                ('modified_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('quarter_year', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='dqa.period')),
            ],
            options={
                'verbose_name_plural': 'Family planning',
                'ordering': ['facility_name'],
                'unique_together': {('quarter_year', 'description', 'facility_name', 'date_of_interview')},
            },
        ),
    ]
