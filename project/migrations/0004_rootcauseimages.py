# Generated by Django 3.2.5 on 2023-02-15 10:28

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('project', '0003_delete_rootcauseimages'),
    ]

    operations = [
        migrations.CreateModel(
            name='RootCauseImages',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('root_cause_image', models.ImageField(blank=True, default='images/baseline.png', null=True, upload_to='images')),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('facility', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='project.facilities')),
                ('program', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='project.program')),
                ('program_qi_project', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='project.program_qi_projects')),
                ('qi_project', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='project.qi_projects')),
            ],
            options={
                'verbose_name_plural': "project's images status",
            },
        ),
    ]
