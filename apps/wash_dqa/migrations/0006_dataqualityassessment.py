# Generated by Django 3.2.19 on 2023-08-27 13:19

import crum
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('wash_dqa', '0005_auto_20230827_1617'),
    ]

    operations = [
        migrations.CreateModel(
            name='DataQualityAssessment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('description', models.TextField()),
                ('auditor_note', models.CharField(blank=True, max_length=250, null=True)),
                ('dqa_date', models.DateField(blank=True, null=True)),
                ('calculations', models.FloatField(blank=True, null=True)),
                ('number_trained', models.CharField(blank=True, choices=[('Yes', '(2) Yes'), ('No', '(1) No'), ('N/A', '(0) N/A')], max_length=50, null=True)),
                ('number_access_basic_water', models.CharField(blank=True, choices=[('Yes', '(2) Yes'), ('No', '(1) No'), ('N/A', '(0) N/A')], max_length=50, null=True)),
                ('number_access_safe_water', models.CharField(blank=True, choices=[('Yes', '(2) Yes'), ('No', '(1) No'), ('N/A', '(0) N/A')], max_length=50, null=True)),
                ('number_community_open_defecation', models.CharField(blank=True, choices=[('Yes', '(2) Yes'), ('No', '(1) No'), ('N/A', '(0) N/A')], max_length=50, null=True)),
                ('number_access_basic_sanitation', models.CharField(blank=True, choices=[('Yes', '(2) Yes'), ('No', '(1) No'), ('N/A', '(0) N/A')], max_length=50, null=True)),
                ('number_access_safe_sanitation', models.CharField(blank=True, choices=[('Yes', '(2) Yes'), ('No', '(1) No'), ('N/A', '(0) N/A')], max_length=50, null=True)),
                ('number_access_basic_sanitation_institutions', models.CharField(blank=True, choices=[('Yes', '(2) Yes'), ('No', '(1) No'), ('N/A', '(0) N/A')], max_length=50, null=True)),
                ('created_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('model_name', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='wash_dqa.tablenames')),
                ('modified_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('quarter_year', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='wash_dqa.period')),
                ('sub_county_name', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='wash_dqa.subcounties')),
                ('ward_name', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='wash_dqa.ward')),
            ],
            options={
                'verbose_name_plural': 'Data Quality Assessment',
                'ordering': ['ward_name'],
                'unique_together': {('quarter_year', 'description', 'ward_name')},
            },
        ),
    ]