# Generated by Django 3.2.5 on 2023-02-09 11:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dqa', '0016_dataverification_date_created'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataverification',
            name='date_modified',
            field=models.DateTimeField(auto_now=True),
        ),
    ]