# Generated by Django 3.2.5 on 2023-01-16 09:51

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('project', '0024_remove_lesson_learned_goals_and_objectives'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='lesson_learned',
            name='problem_or_opportunity',
        ),
    ]