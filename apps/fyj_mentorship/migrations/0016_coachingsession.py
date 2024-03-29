# Generated by Django 3.2.19 on 2023-06-21 03:23

import crum
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('dqa', '0013_auto_20230420_1439'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cqi', '0003_auto_20230426_1152'),
        ('fyj_mentorship', '0015_preparecoachingsession'),
    ]

    operations = [
        migrations.CreateModel(
            name='CoachingSession',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('description', models.TextField()),
                ('drop_down_options', models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No')], max_length=4)),
                ('date_of_interview', models.DateField(blank=True, null=True)),
                ('comments', models.CharField(blank=True, max_length=600, null=True)),
                ('created_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('facility_name', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cqi.facilities')),
                ('modified_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('quarter_year', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='dqa.period')),
            ],
            options={
                'verbose_name_plural': 'Coaching session',
            },
        ),
    ]
