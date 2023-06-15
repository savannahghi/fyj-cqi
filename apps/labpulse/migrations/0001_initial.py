# Generated by Django 3.2.19 on 2023-06-12 20:37

import crum
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('cqi', '0003_auto_20230426_1152'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Cd4TestingLabs',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('testing_lab_name', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='Cd4traker',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('patient_unique_no', models.CharField(max_length=10)),
                ('date_of_collection', models.DateTimeField(auto_now=True)),
                ('cd4_count_results', models.IntegerField(blank=True, null=True)),
                ('serum_crag_results', models.CharField(blank=True, choices=[('Negative', 'Negative'), ('Positive', 'Positive')], max_length=9, null=True)),
                ('date_of_testing', models.DateTimeField(auto_now=True)),
                ('date_dispatched', models.DateTimeField(auto_now_add=True)),
                ('date_updated', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('facility_name', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cqi.facilities')),
                ('modified_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('testing_laboratory', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='labpulse.cd4testinglabs')),
            ],
        ),
    ]