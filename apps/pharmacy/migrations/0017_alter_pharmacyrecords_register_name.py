# Generated by Django 3.2.19 on 2023-05-17 06:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0016_alter_pharmacyrecords_currently_in_use'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pharmacyrecords',
            name='register_name',
            field=models.CharField(default=1, max_length=150),
            preserve_default=False,
        ),
    ]
