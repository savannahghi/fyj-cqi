# Generated by Django 3.2.18 on 2023-04-20 11:39

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='FYJHealthFacility',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mfl_code', models.CharField(max_length=20)),
                ('county', models.CharField(max_length=50)),
                ('health_subcounty', models.CharField(max_length=50)),
                ('subcounty', models.CharField(max_length=50)),
                ('ward', models.CharField(max_length=50)),
                ('facility', models.CharField(max_length=100)),
                ('datim_mfl', models.CharField(max_length=20)),
                ('m_and_e_mentor', models.CharField(max_length=100)),
                ('m_and_e_assistant', models.CharField(max_length=100)),
                ('care_and_treatment', models.BooleanField()),
                ('hts', models.BooleanField()),
                ('vmmc', models.BooleanField()),
                ('key_pop', models.BooleanField()),
                ('hub', models.CharField(max_length=5)),
                ('facility_type', models.CharField(max_length=50)),
                ('category', models.CharField(max_length=10)),
                ('emr', models.BooleanField()),
            ],
        ),
    ]