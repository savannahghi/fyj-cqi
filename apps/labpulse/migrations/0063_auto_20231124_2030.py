# Generated by Django 3.2.22 on 2023-11-24 17:30

import crum
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('labpulse', '0062_rename_date_test_perfomed_drtresults_date_test_performed'),
    ]

    operations = [
        migrations.CreateModel(
            name='DrtPdfFile',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('result', models.FileField(upload_to='drt_files')),
                ('created_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AlterField(
            model_name='drtresults',
            name='result',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='labpulse.drtpdffile'),
        ),
    ]
