# pozicijos/apps.py
from django.apps import AppConfig

class PozicijosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "pozicijos"

    def ready(self):
        # užregistruojam signalus
        from . import signals  # noqa: F401
