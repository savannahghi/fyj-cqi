# Generated by Django 3.2.19 on 2023-06-15 11:46

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('labpulse', '0021_alter_cd4traker_comments'),
    ]

    operations = [
        migrations.RenameField(
            model_name='cd4traker',
            old_name='comments',
            new_name='reason_for_no_serum_crag',
        ),
    ]
