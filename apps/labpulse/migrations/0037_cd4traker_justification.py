# Generated by Django 3.2.19 on 2023-06-29 05:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('labpulse', '0036_auto_20230620_1116'),
    ]

    operations = [
        migrations.AddField(
            model_name='cd4traker',
            name='justification',
            field=models.CharField(blank=True, choices=[('Negative', 'Negative'), ('Positive', 'Positive')], max_length=9, null=True),
        ),
    ]
