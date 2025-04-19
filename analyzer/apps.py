from django.apps import AppConfig


class AnalyzerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'analyzer'
    verbose_name = 'OASYS Template Analyzer'

    def ready(self):
        # Optional: Import signals here if needed
        # try:
        #     import analyzer.signals
        # except ImportError:
        #     pass
        pass
