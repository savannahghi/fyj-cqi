# Generated by Django 3.2.19 on 2023-06-20 10:15

import crum
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('fyj_mentorship', '0003_alter_fyjstaffdetails_hub'),
    ]

    operations = [
        migrations.CreateModel(
            name='FacilityStaffCarders',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('carder', models.CharField(blank=True, max_length=250, null=True, unique=True)),
                ('created_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Facility staff carders',
                'ordering': ['carder'],
            },
        ),
    ]
