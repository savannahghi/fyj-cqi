# Generated by Django 3.2.19 on 2023-07-05 06:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('labpulse', '0042_alter_cd4traker_date_dispatched'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='cd4traker',
            options={'ordering': ['-date_dispatched'], 'permissions': [('view_show_results', 'Can view show results'), ('view_choose_testing_lab', 'Can view choose testing lab'), ('view_add_cd4_count', 'Can view add CD4 count'), ('view_add_retrospective_cd4_count', 'Can view add retrospective CD4 count'), ('view_update_cd4_results', 'Can view update CD4 results')], 'verbose_name_plural': 'CD4 count tracker'},
        ),
    ]
