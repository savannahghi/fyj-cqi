# Generated by Django 3.2.19 on 2023-05-16 14:49

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0009_auto_20230516_1748'),
    ]

    operations = [
        migrations.AlterField(
            model_name='registers',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True),
        ),
    ]