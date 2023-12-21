# Generated by Django 3.2.22 on 2023-12-20 06:32

import crum
from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('cqi', '0008_auto_20231216_1755'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('labpulse', '0070_alter_drtresults_patient_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='DrtProfile',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('patient_id', models.BigIntegerField(validators=[django.core.validators.MaxValueValidator(9999999999)])),
                ('collection_date', models.DateTimeField()),
                ('sequence_summary', models.CharField(max_length=10)),
                ('haart_class', models.CharField(max_length=50)),
                ('date_received', models.DateTimeField()),
                ('date_reported', models.DateTimeField()),
                ('date_test_performed', models.DateTimeField()),
                ('test_perfomed_by', models.CharField(max_length=50)),
                ('age', models.PositiveIntegerField(blank=True, null=True, validators=[django.core.validators.MaxValueValidator(150)])),
                ('age_unit', models.CharField(blank=True, max_length=20, null=True)),
                ('sex', models.CharField(blank=True, max_length=10, null=True)),
                ('tat_days', models.IntegerField(blank=True, null=True)),
                ('mutation_type', models.CharField(max_length=50)),
                ('mutations', models.CharField(max_length=250)),
                ('county', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cqi.counties')),
                ('created_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('facility_name', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cqi.facilities')),
                ('modified_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('result', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='drt_profile', to='labpulse.drtpdffile')),
                ('sub_county', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cqi.sub_counties')),
            ],
            options={
                'verbose_name_plural': 'DRT Profile',
                'ordering': ['patient_id', 'date_created'],
                'unique_together': {('patient_id', 'collection_date', 'mutation_type')},
            },
        ),
    ]