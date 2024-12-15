# Generated by Django 3.2.25 on 2024-12-13 09:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('labpulse', '0098_biochemistrytestinglab'),
    ]

    operations = [
        migrations.AddField(
            model_name='biochemistryresult',
            name='testing_lab',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='biochemistry_results', to='labpulse.biochemistrytestinglab'),
        ),
    ]
