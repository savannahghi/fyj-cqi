# Generated by Django 3.2.25 on 2024-06-05 07:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dqa', '0015_caretreatment_cqi_gbv_hts_pharmacy_prep_tablenames_tb_vmmc'),
    ]

    operations = [
        migrations.AddField(
            model_name='caretreatment',
            name='denominator',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='caretreatment',
            name='numerator',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='cqi',
            name='denominator',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='cqi',
            name='numerator',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='gbv',
            name='denominator',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='gbv',
            name='numerator',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hts',
            name='denominator',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='hts',
            name='numerator',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='pharmacy',
            name='denominator',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='pharmacy',
            name='numerator',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='prep',
            name='denominator',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='prep',
            name='numerator',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='tb',
            name='denominator',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='tb',
            name='numerator',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='vmmc',
            name='denominator',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='vmmc',
            name='numerator',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
