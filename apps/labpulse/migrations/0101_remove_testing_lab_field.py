# Generated by Django 3.2.25 on 2024-12-18 16:12

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('labpulse', '0100_correct_biochemistry_data'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='biochemistryresult',
            name='testing_lab',
        ),
    ]
