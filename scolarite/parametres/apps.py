from django.apps import AppConfig
from django.db.models.signals import post_save


class ParametresConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'parametres'

    def ready(self):
        from .middleware import _invalider_a_la_sauvegarde
        post_save.connect(_invalider_a_la_sauvegarde, sender='parametres.Parametres')
