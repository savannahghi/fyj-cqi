# Generated by Django 3.2.22 on 2023-11-24 18:49

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('labpulse', '0063_auto_20231124_2030'),
    ]

    operations = [
        migrations.AlterField(
            model_name='drtresults',
            name='result',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='drt_results', to='labpulse.drtpdffile'),
        ),
    ]
