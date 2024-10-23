# Generated by Django 3.2.25 on 2024-10-22 11:55

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cqi', '0012_remove_platformupdate_title'),
        ('labpulse', '0090_histologyresults_specimen_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='reagentstock',
            name='facility_dispensed_to',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='dispensed_to', to='cqi.facilities'),
        ),
        migrations.AddField(
            model_name='reagentstock',
            name='facility_received_from',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='received_from', to='cqi.facilities'),
        ),
        migrations.AlterField(
            model_name='reagentstock',
            name='beginning_balance',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='reagentstock',
            name='facility_name',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reagent_stock_facility_name', to='cqi.facilities'),
        ),
        migrations.AlterField(
            model_name='reagentstock',
            name='negative_adjustment',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='reagentstock',
            name='positive_adjustments',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='reagentstock',
            name='quantity_expired',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='reagentstock',
            name='quantity_received',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='reagentstock',
            name='quantity_used',
            field=models.PositiveIntegerField(blank=True, default=0),
        ),
    ]
