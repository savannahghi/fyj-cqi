# Generated by Django 3.2.25 on 2024-05-18 01:51

import ckeditor.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cqi', '0008_auto_20231216_1755'),
    ]

    operations = [
        migrations.AlterField(
            model_name='county_qi_projects',
            name='problem_background',
            field=ckeditor.fields.RichTextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='hub_qi_projects',
            name='problem_background',
            field=ckeditor.fields.RichTextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='program_qi_projects',
            name='problem_background',
            field=ckeditor.fields.RichTextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='qi_projects',
            name='problem_background',
            field=ckeditor.fields.RichTextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='subcounty_qi_projects',
            name='problem_background',
            field=ckeditor.fields.RichTextField(blank=True, null=True),
        ),
    ]
