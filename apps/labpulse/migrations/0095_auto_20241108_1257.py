# Generated by Django 3.2.25 on 2024-11-08 09:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('labpulse', '0094_auto_20241106_1149'),
    ]

    operations = [
        migrations.AddField(
            model_name='cd4traker',
            name='reason_for_no_tb_lam',
            field=models.CharField(blank=True, choices=[('Reagents Stock outs', 'Reagents Stock outs'), ('On TB Rx', 'On TB Rx'), ('Others', 'Others')], max_length=30, null=True),
        ),
        migrations.AlterField(
            model_name='cd4traker',
            name='reason_for_no_serum_crag',
            field=models.CharField(blank=True, choices=[('Reagents Stock outs', 'Reagents Stock outs'), ('On cryptococcal meningitis Rx', 'On cryptococcal meningitis Rx'), ('Others', 'Others')], max_length=30, null=True),
        ),
        migrations.AlterField(
            model_name='cd4traker',
            name='testing_type',
            field=models.CharField(choices=[('All', 'All tests'), ('TB LAM Only', 'TB LAM Only'), ('ScrAg Only', 'ScrAg Only'), ('TB LAM & ScrAg', 'TB LAM & ScrAg')], default='All', max_length=20),
        ),
    ]
