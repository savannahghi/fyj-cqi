# Generated by Django 3.2.19 on 2023-05-20 16:25

import crum
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('dqa', '0013_auto_20230420_1439'),
        ('cqi', '0003_auto_20230426_1152'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('pharmacy', '0026_beginningbalance_expired_expiredunits_expirytracking_negativeadjustment_positiveadjustments_quantity'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkPlan',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('immediate_corrective_actions', models.TextField()),
                ('action_plan', models.TextField()),
                ('responsible_person', models.TextField()),
                ('due_date', models.DateField()),
                ('follow_up_plan', models.TextField()),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('facility_name', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cqi.facilities')),
                ('modified_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('quarter_year', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='dqa.period')),
            ],
        ),
    ]
