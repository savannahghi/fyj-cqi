# Generated by Django 3.2.5 on 2023-02-22 08:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cqi', '0009_auto_20230222_0856'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='sustainmentplan',
            options={'ordering': ['-date_created']},
        ),
        migrations.AddField(
            model_name='subcounty_qi_projects',
            name='triggers',
            field=models.ManyToManyField(blank=True, to='cqi.Trigger'),
        ),
    ]
