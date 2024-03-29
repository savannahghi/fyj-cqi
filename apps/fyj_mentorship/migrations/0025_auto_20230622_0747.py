# Generated by Django 3.2.19 on 2023-06-22 04:47

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cqi', '0003_auto_20230426_1152'),
        ('fyj_mentorship', '0024_auto_20230621_1756'),
    ]

    operations = [
        migrations.AddField(
            model_name='coachingsession',
            name='county',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cqi.counties'),
        ),
        migrations.AddField(
            model_name='coachingsession',
            name='sub_county',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cqi.sub_counties'),
        ),
        migrations.AddField(
            model_name='followup',
            name='county',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cqi.counties'),
        ),
        migrations.AddField(
            model_name='followup',
            name='sub_county',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cqi.sub_counties'),
        ),
        migrations.AddField(
            model_name='identificationgaps',
            name='county',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cqi.counties'),
        ),
        migrations.AddField(
            model_name='identificationgaps',
            name='sub_county',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cqi.sub_counties'),
        ),
        migrations.AddField(
            model_name='introduction',
            name='county',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cqi.counties'),
        ),
        migrations.AddField(
            model_name='introduction',
            name='sub_county',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cqi.sub_counties'),
        ),
        migrations.AddField(
            model_name='preparecoachingsession',
            name='county',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cqi.counties'),
        ),
        migrations.AddField(
            model_name='preparecoachingsession',
            name='sub_county',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='cqi.sub_counties'),
        ),
    ]
