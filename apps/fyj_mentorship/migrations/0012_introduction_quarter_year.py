# Generated by Django 3.2.19 on 2023-06-20 15:39

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dqa', '0013_auto_20230420_1439'),
        ('fyj_mentorship', '0011_auto_20230620_1531'),
    ]

    operations = [
        migrations.AddField(
            model_name='introduction',
            name='quarter_year',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='dqa.period'),
        ),
    ]