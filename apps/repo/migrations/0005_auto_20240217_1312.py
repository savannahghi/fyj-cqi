# Generated by Django 3.2.22 on 2024-02-17 10:12

import ckeditor.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('repo', '0004_alter_manuscript_abstract'),
    ]

    operations = [
        migrations.AlterField(
            model_name='manuscript',
            name='conclusion',
            field=ckeditor.fields.RichTextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='manuscript',
            name='findings',
            field=ckeditor.fields.RichTextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='manuscript',
            name='indicators',
            field=ckeditor.fields.RichTextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='manuscript',
            name='keywords',
            field=ckeditor.fields.RichTextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='manuscript',
            name='methodology',
            field=ckeditor.fields.RichTextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='manuscript',
            name='results',
            field=ckeditor.fields.RichTextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='manuscript',
            name='title',
            field=ckeditor.fields.RichTextField(blank=True, null=True),
        ),
    ]