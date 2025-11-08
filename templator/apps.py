from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class TemplatorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'templator'
    verbose_name = _('Template Manager')
    
    def ready(self):
        """
        Connect signals when the app is ready.
        """
        import templator.signals
