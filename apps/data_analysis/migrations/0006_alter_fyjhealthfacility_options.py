# Generated by Django 3.2.22 on 2024-02-12 09:49

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('data_analysis', '0005_alter_fyjhealthfacility_unique_together'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='fyjhealthfacility',
            options={'ordering': ['facility']},
        ),
    ]