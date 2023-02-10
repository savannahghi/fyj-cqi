# Generated by Django 3.2.5 on 2023-02-09 10:55

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dqa', '0013_auto_20230209_1341'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dataverification',
            name='indicator',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='dqa.indicators'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='dataverification',
            name='quarter_year',
            field=models.ForeignKey(default=2, on_delete=django.db.models.deletion.CASCADE, to='dqa.period'),
            preserve_default=False,
        ),
    ]