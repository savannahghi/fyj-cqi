# Generated by Django 3.2.5 on 2022-12-22 07:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('project', '0018_archiveproject'),
    ]

    operations = [
        migrations.AlterField(
            model_name='archiveproject',
            name='archive_project',
            field=models.BooleanField(default=True),
        ),
    ]
