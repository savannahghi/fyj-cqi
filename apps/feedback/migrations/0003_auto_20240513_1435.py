# Generated by Django 3.2.25 on 2024-05-13 11:35

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('feedback', '0002_auto_20240513_1310'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='feedback',
            options={'ordering': ['app__name'], 'verbose_name_plural': 'User feedback'},
        ),
        migrations.RenameField(
            model_name='feedback',
            old_name='description',
            new_name='user_feedback',
        ),
    ]
