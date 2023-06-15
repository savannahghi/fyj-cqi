# Generated by Django 3.2.19 on 2023-05-16 14:51

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0011_auto_20230516_1750'),
    ]

    operations = [
        migrations.CreateModel(
            name='Registers',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('register_name', models.CharField(choices=[('Malaria', 'Malaria Commodities DAR (MoH 645)'), ('ARV DAR', 'ARV Daily Activity Register (DAR) (MOH 367A)/WebADT'), ('F-MAPS', 'ARV F-MAPS (MOH 729B)'), ('DADR-Anti TB register', 'DADR-Anti TB register'), ('FP', 'Family Planning Commodities Daily Activity Register (DAR) (MOH 512)'), ('delivery notes', 'Delivery notes file')], max_length=250)),
            ],
        ),
        migrations.AddField(
            model_name='pharmacyrecords',
            name='register_name',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='pharmacy.registers'),
        ),
    ]