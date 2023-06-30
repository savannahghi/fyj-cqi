# Generated by Django 3.2.19 on 2023-06-21 08:04

import crum
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('cqi', '0003_auto_20230426_1152'),
        ('pharmacy', '0050_alter_workplan_pharmacy_records'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('fyj_mentorship', '0018_auto_20230621_0727'),
    ]

    operations = [
        migrations.CreateModel(
            name='MentorshipWorkPlan',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('action_plan', models.TextField()),
                ('complete_date', models.DateField()),
                ('follow_up_plan', models.TextField()),
                ('progress', models.FloatField(blank=True, null=True)),
                ('coaching_session', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='fyj_mentorship.coachingsession')),
                ('created_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('facility_name', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cqi.facilities')),
                ('follow_up', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='fyj_mentorship.followup')),
                ('identification_gaps', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='fyj_mentorship.identificationgaps')),
                ('introduction', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='fyj_mentorship.introduction')),
                ('model_name', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='pharmacy.tablenames')),
                ('modified_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('prepare_coaching_session', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='fyj_mentorship.preparecoachingsession')),
            ],
            options={
                'verbose_name_plural': 'Work Plan',
                'ordering': ['facility_name'],
            },
        ),
    ]
