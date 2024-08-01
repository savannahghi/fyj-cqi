# Generated by Django 3.2.25 on 2024-07-29 10:54

import crum
from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cqi', '0010_auto_20240518_0542'),
        ('labpulse', '0083_auto_20240729_1353'),
    ]

    operations = [
        migrations.CreateModel(
            name='HistologyPdfFile',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('result', models.FileField(upload_to='histology_files')),
                ('created_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'HISTOLOGY PDF Results',
            },
        ),
        migrations.CreateModel(
            name='HistologyResults',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('patient_id', models.BigIntegerField(validators=[django.core.validators.MaxValueValidator(9999999999)])),
                ('collection_date', models.DateTimeField()),
                ('date_reported', models.DateTimeField()),
                ('date_test_performed', models.DateTimeField()),
                ('authorization_date', models.DateTimeField()),
                ('test_performed_by', models.CharField(max_length=50)),
                ('reported_by', models.CharField(max_length=50)),
                ('lab_name', models.CharField(blank=True, max_length=250, null=True)),
                ('lab_phone', models.CharField(blank=True, max_length=250, null=True)),
                ('lab_email', models.CharField(blank=True, max_length=250, null=True)),
                ('lab_post_address', models.CharField(blank=True, max_length=250, null=True)),
                ('clinical_summary', models.CharField(blank=True, max_length=250, null=True)),
                ('referring_doctor', models.CharField(blank=True, max_length=500, null=True)),
                ('microscopy', models.CharField(blank=True, max_length=2500, null=True)),
                ('diagnosis', models.CharField(blank=True, max_length=2500, null=True)),
                ('gross_description', models.CharField(blank=True, max_length=2500, null=True)),
                ('comments', models.CharField(blank=True, max_length=2500, null=True)),
                ('age', models.PositiveIntegerField(blank=True, null=True, validators=[django.core.validators.MaxValueValidator(150)])),
                ('sex', models.CharField(blank=True, max_length=10, null=True)),
                ('tat_days', models.IntegerField(blank=True, null=True)),
                ('county', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cqi.counties')),
                ('created_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('facility_name', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cqi.facilities')),
                ('modified_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('result', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='histology_results', to='labpulse.histologypdffile')),
                ('sub_county', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cqi.sub_counties')),
            ],
            options={
                'verbose_name_plural': 'Histology Results',
                'ordering': ['patient_id', 'date_created'],
                'unique_together': {('patient_id', 'collection_date')},
            },
        ),
    ]