from django.apps import AppConfig


class ProjectConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.cqi'

    # def ready(self):
    #     import apps.cqi.signals
