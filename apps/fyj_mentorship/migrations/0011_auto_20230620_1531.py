# Generated by Django 3.2.19 on 2023-06-20 12:31

import crum
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cqi', '0003_auto_20230426_1152'),
        ('fyj_mentorship', '0010_programareas'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='facilitystaffdetails',
            options={'ordering': ['facility_name', 'staff_name'], 'verbose_name_plural': 'Facility staff details'},
        ),
        migrations.CreateModel(
            name='Introduction',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('description', models.TextField()),
                ('drop_down_options', models.CharField(choices=[('', '-'), ('Yes', 'Yes'), ('No', 'No')], max_length=4)),
                ('date_of_interview', models.DateField(blank=True, null=True)),
                ('created_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('facility_name', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cqi.facilities')),
                ('modified_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Introduction',
            },
        ),
    ]
