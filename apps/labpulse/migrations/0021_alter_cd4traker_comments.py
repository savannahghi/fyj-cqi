# Generated by Django 3.2.19 on 2023-06-15 11:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('labpulse', '0020_alter_cd4traker_age'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cd4traker',
            name='comments',
            field=models.CharField(blank=True, choices=[('Reagents Stock outs', 'Reagents Stock outs'), ('Others', 'Others')], max_length=25, null=True),
        ),
    ]
