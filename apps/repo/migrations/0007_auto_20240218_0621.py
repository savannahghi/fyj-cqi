# Generated by Django 3.2.22 on 2024-02-18 03:21

import crum
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('repo', '0006_auto_20240217_1538'),
    ]

    operations = [
        migrations.CreateModel(
            name='Conference',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=250)),
                ('created_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('modified_by', models.ForeignKey(blank=True, default=crum.get_current_user, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Conferences',
                'ordering': ['name'],
                'unique_together': {('name',)},
            },
        ),
        migrations.AddField(
            model_name='manuscript',
            name='conference',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='repo.conference'),
        ),
    ]
