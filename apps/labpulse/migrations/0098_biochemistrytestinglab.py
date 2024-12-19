# Generated by Django 3.2.25 on 2024-12-13 09:26

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('labpulse', '0097_alter_cd4traker_lab_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='BiochemistryTestingLab',
            fields=[
                ('cd4testinglabs_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='labpulse.cd4testinglabs')),
            ],
            options={
                'verbose_name_plural': 'Biochemistry testing Laboratories',
                'ordering': ['testing_lab_name'],
            },
            bases=('labpulse.cd4testinglabs',),
        ),
    ]