# Generated by Django 3.2.19 on 2023-09-11 16:43

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('labpulse', '0056_auto_20230911_1920'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='enabledisablecommodities',
            options={'verbose_name_plural': 'Enable Disable Commodities'},
        ),
        migrations.RenameField(
            model_name='enabledisablecommodities',
            old_name='allow_commodities_use',
            new_name='disable_commodities_use',
        ),
    ]
