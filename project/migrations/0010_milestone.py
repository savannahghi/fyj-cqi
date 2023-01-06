# Generated by Django 3.2.5 on 2023-01-05 06:36

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('project', '0009_auto_20230105_0832'),
    ]

    operations = [
        migrations.CreateModel(
            name='Milestone',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Milestone name')),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('description', models.TextField()),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_by', models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('facility', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='project.facilities')),
                ('qi_project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='project.qi_projects')),
            ],
        ),
    ]
