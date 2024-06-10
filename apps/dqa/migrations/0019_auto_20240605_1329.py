# Generated by Django 3.2.25 on 2024-06-05 10:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dqa', '0018_auto_20240605_1051'),
    ]

    operations = [
        migrations.AddField(
            model_name='caretreatment',
            name='indicator_performance',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='cqi',
            name='indicator_performance',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='gbv',
            name='indicator_performance',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hts',
            name='indicator_performance',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='pharmacy',
            name='indicator_performance',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='prep',
            name='indicator_performance',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='tb',
            name='indicator_performance',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='vmmc',
            name='indicator_performance',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='caretreatment',
            name='dropdown_option',
            field=models.CharField(blank=True, choices=[('Yes', 'Yes - completely'), ('Partly', 'Partly'), ('No', 'No - not at all'), ('N/A', 'N/A')], max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='cqi',
            name='dropdown_option',
            field=models.CharField(blank=True, choices=[('Yes', 'Yes - completely'), ('Partly', 'Partly'), ('No', 'No - not at all'), ('N/A', 'N/A')], max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='gbv',
            name='dropdown_option',
            field=models.CharField(blank=True, choices=[('Yes', 'Yes - completely'), ('Partly', 'Partly'), ('No', 'No - not at all'), ('N/A', 'N/A')], max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='hts',
            name='dropdown_option',
            field=models.CharField(blank=True, choices=[('Yes', 'Yes - completely'), ('Partly', 'Partly'), ('No', 'No - not at all'), ('N/A', 'N/A')], max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='pharmacy',
            name='dropdown_option',
            field=models.CharField(blank=True, choices=[('Yes', 'Yes - completely'), ('Partly', 'Partly'), ('No', 'No - not at all'), ('N/A', 'N/A')], max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='prep',
            name='dropdown_option',
            field=models.CharField(blank=True, choices=[('Yes', 'Yes - completely'), ('Partly', 'Partly'), ('No', 'No - not at all'), ('N/A', 'N/A')], max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='tb',
            name='dropdown_option',
            field=models.CharField(blank=True, choices=[('Yes', 'Yes - completely'), ('Partly', 'Partly'), ('No', 'No - not at all'), ('N/A', 'N/A')], max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='vmmc',
            name='dropdown_option',
            field=models.CharField(blank=True, choices=[('Yes', 'Yes - completely'), ('Partly', 'Partly'), ('No', 'No - not at all'), ('N/A', 'N/A')], max_length=50, null=True),
        ),
    ]
