# Generated by Django 3.2.25 on 2024-06-05 07:13

import crum
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cqi', '0010_auto_20240518_0542'),
        ('dqa', '0014_auto_20230828_0926'),
    ]

    operations = [
        migrations.CreateModel(
            name='TableNames',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('model_name', models.CharField(blank=True, max_length=25, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Vmmc',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('description', models.TextField()),
                ('dropdown_option', models.CharField(blank=True, choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], max_length=50, null=True)),
                ('verification', models.TextField()),
                ('dqa_date', models.DateField(blank=True, null=True)),
                ('calculations', models.FloatField(blank=True, null=True)),
                ('created_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('facility_name', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cqi.facilities')),
                ('modified_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('quarter_year', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='dqa.period')),
            ],
            options={
                'verbose_name_plural': 'VMMC',
            },
        ),
        migrations.CreateModel(
            name='Tb',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('description', models.TextField()),
                ('dropdown_option', models.CharField(blank=True, choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], max_length=50, null=True)),
                ('verification', models.TextField()),
                ('dqa_date', models.DateField(blank=True, null=True)),
                ('calculations', models.FloatField(blank=True, null=True)),
                ('created_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('facility_name', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cqi.facilities')),
                ('modified_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('quarter_year', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='dqa.period')),
            ],
            options={
                'verbose_name_plural': 'TB',
            },
        ),
        migrations.CreateModel(
            name='Prep',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('description', models.TextField()),
                ('dropdown_option', models.CharField(blank=True, choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], max_length=50, null=True)),
                ('verification', models.TextField()),
                ('dqa_date', models.DateField(blank=True, null=True)),
                ('calculations', models.FloatField(blank=True, null=True)),
                ('created_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('facility_name', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cqi.facilities')),
                ('modified_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('quarter_year', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='dqa.period')),
            ],
            options={
                'verbose_name_plural': 'PrEP',
            },
        ),
        migrations.CreateModel(
            name='Pharmacy',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('description', models.TextField()),
                ('dropdown_option', models.CharField(blank=True, choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], max_length=50, null=True)),
                ('verification', models.TextField()),
                ('dqa_date', models.DateField(blank=True, null=True)),
                ('calculations', models.FloatField(blank=True, null=True)),
                ('created_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('facility_name', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cqi.facilities')),
                ('modified_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('quarter_year', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='dqa.period')),
            ],
            options={
                'verbose_name_plural': 'Pharmacy',
            },
        ),
        migrations.CreateModel(
            name='Hts',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('description', models.TextField()),
                ('dropdown_option', models.CharField(blank=True, choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], max_length=50, null=True)),
                ('verification', models.TextField()),
                ('dqa_date', models.DateField(blank=True, null=True)),
                ('calculations', models.FloatField(blank=True, null=True)),
                ('created_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('facility_name', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cqi.facilities')),
                ('modified_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('quarter_year', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='dqa.period')),
            ],
            options={
                'verbose_name_plural': 'HTS',
            },
        ),
        migrations.CreateModel(
            name='Gbv',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('description', models.TextField()),
                ('dropdown_option', models.CharField(blank=True, choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], max_length=50, null=True)),
                ('verification', models.TextField()),
                ('dqa_date', models.DateField(blank=True, null=True)),
                ('calculations', models.FloatField(blank=True, null=True)),
                ('created_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('facility_name', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cqi.facilities')),
                ('modified_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('quarter_year', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='dqa.period')),
            ],
            options={
                'verbose_name_plural': 'GBV',
            },
        ),
        migrations.CreateModel(
            name='Cqi',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('description', models.TextField()),
                ('dropdown_option', models.CharField(blank=True, choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], max_length=50, null=True)),
                ('verification', models.TextField()),
                ('dqa_date', models.DateField(blank=True, null=True)),
                ('calculations', models.FloatField(blank=True, null=True)),
                ('created_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('facility_name', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cqi.facilities')),
                ('modified_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('quarter_year', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='dqa.period')),
            ],
            options={
                'verbose_name_plural': 'CQI',
            },
        ),
        migrations.CreateModel(
            name='CareTreatment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('description', models.TextField()),
                ('dropdown_option', models.CharField(blank=True, choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No'), ('N/A', 'N/A')], max_length=50, null=True)),
                ('verification', models.TextField()),
                ('dqa_date', models.DateField(blank=True, null=True)),
                ('calculations', models.FloatField(blank=True, null=True)),
                ('created_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('facility_name', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cqi.facilities')),
                ('modified_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('quarter_year', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='dqa.period')),
            ],
            options={
                'verbose_name_plural': 'Care and Treatment',
            },
        ),
    ]
