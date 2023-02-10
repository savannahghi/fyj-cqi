# Generated by Django 3.2.5 on 2023-02-09 06:31

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dqa', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dataverification',
            name='field_1',
            field=models.CharField(max_length=100, validators=[django.core.validators.RegexValidator('^\\d+$')]),
        ),
        migrations.AlterField(
            model_name='dataverification',
            name='field_10',
            field=models.CharField(max_length=100, validators=[django.core.validators.RegexValidator('^\\d+$')]),
        ),
        migrations.AlterField(
            model_name='dataverification',
            name='field_11',
            field=models.CharField(max_length=100, validators=[django.core.validators.RegexValidator('^\\d+$')]),
        ),
        migrations.AlterField(
            model_name='dataverification',
            name='field_12',
            field=models.CharField(max_length=100, validators=[django.core.validators.RegexValidator('^\\d+$')]),
        ),
        migrations.AlterField(
            model_name='dataverification',
            name='field_13',
            field=models.CharField(max_length=100, validators=[django.core.validators.RegexValidator('^\\d+$')]),
        ),
        migrations.AlterField(
            model_name='dataverification',
            name='field_2',
            field=models.CharField(max_length=100, validators=[django.core.validators.RegexValidator('^\\d+$')]),
        ),
        migrations.AlterField(
            model_name='dataverification',
            name='field_3',
            field=models.CharField(max_length=100, validators=[django.core.validators.RegexValidator('^\\d+$')]),
        ),
        migrations.AlterField(
            model_name='dataverification',
            name='field_4',
            field=models.CharField(max_length=100, validators=[django.core.validators.RegexValidator('^\\d+$')]),
        ),
        migrations.AlterField(
            model_name='dataverification',
            name='field_5',
            field=models.CharField(max_length=100, validators=[django.core.validators.RegexValidator('^\\d+$')]),
        ),
        migrations.AlterField(
            model_name='dataverification',
            name='field_6',
            field=models.CharField(max_length=100, validators=[django.core.validators.RegexValidator('^\\d+$')]),
        ),
        migrations.AlterField(
            model_name='dataverification',
            name='field_7',
            field=models.CharField(max_length=100, validators=[django.core.validators.RegexValidator('^\\d+$')]),
        ),
        migrations.AlterField(
            model_name='dataverification',
            name='field_8',
            field=models.CharField(max_length=100, validators=[django.core.validators.RegexValidator('^\\d+$')]),
        ),
        migrations.AlterField(
            model_name='dataverification',
            name='field_9',
            field=models.CharField(max_length=100, validators=[django.core.validators.RegexValidator('^\\d+$')]),
        ),
    ]