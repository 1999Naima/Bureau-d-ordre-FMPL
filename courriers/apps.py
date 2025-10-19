from django.apps import AppConfig

class CourriersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'courriers'

    def ready(self):
        import courriers.signals  # ← très important
