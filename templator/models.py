from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

class TemplateCategory(models.Model):
    """
    Model representing a category for organizing templates.
    """
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = _('Template Category')
        verbose_name_plural = _('Template Categories')
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug']),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        """
        Auto-generate slug from name if not provided.
        """
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Template(models.Model):
    """
    Model representing a template that can be uploaded and used in the OASYS platform.
    """
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=150, unique=True)
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(
        TemplateCategory, 
        on_delete=models.CASCADE,
        related_name='templates'
    )
    zip_file = models.FileField(
        upload_to='template_archives/',
        help_text=_('Upload a ZIP file containing template files.')
    )
    date_uploaded = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    preview_image = models.ImageField(
        upload_to='template_previews/', 
        blank=True, 
        null=True,
        help_text=_('Optional preview image for this template.')
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_templates'
    )
    # Store the extraction path for reference
    extraction_path = models.CharField(max_length=255, blank=True)
    # Store the detected framework (can be set by analyzer)
    detected_framework = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text=_("Framework detected by the analyzer (e.g., django, react, html)")
    )
    
    class Meta:
        verbose_name = _('Template')
        verbose_name_plural = _('Templates')
        ordering = ['-date_uploaded']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
            models.Index(fields=['date_uploaded']),
            models.Index(fields=['category']),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        """
        Auto-generate slug from name if not provided.
        """
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def clean(self):
        """
        Validate that the uploaded file is a ZIP file.
        """
        if self.zip_file and not self.zip_file.name.endswith('.zip'):
            raise ValidationError(_('The uploaded file must be a ZIP archive.'))
