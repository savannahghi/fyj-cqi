# Generated by Django 3.2.5 on 2023-01-29 08:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('project', '0037_auto_20230129_0924'),
    ]

    operations = [
        migrations.AlterField(
            model_name='qi_team_members',
            name='impact',
            field=models.TextField(default='Null'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='qi_team_members',
            name='notes',
            field=models.TextField(default=1),
            preserve_default=False,
        ),
    ]
