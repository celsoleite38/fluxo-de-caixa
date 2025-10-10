from django.apps import AppConfig

class ColaboradorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'colaborador'
    
    def ready(self):
        import colaborador.signals