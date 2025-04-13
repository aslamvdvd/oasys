from django.contrib import admin
from django.utils.html import format_html
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import Template, TemplateCategory

# Import the admin logger
try:
    from log_service.admin_logger import log_admin_addition, log_admin_change, log_admin_deletion
    HAS_ADMIN_LOGGER = True
except ImportError:
    HAS_ADMIN_LOGGER = False

@admin.register(TemplateCategory)
class TemplateCategoryAdmin(admin.ModelAdmin):
    """
    Admin interface for TemplateCategory model.
    """
    list_display = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'description')
    ordering = ('name',)
    
    def save_model(self, request, obj, form, change):
        """
        Override save_model to log the action.
        """
        super().save_model(request, obj, form, change)
        
        if HAS_ADMIN_LOGGER:
            if change:
                log_admin_change(request.user, obj, f"Category '{obj.name}' was updated")
            else:
                log_admin_addition(request.user, obj, f"Category '{obj.name}' was created")
    
    def delete_model(self, request, obj):
        """
        Override delete_model to log the action.
        """
        category_name = obj.name
        
        super().delete_model(request, obj)
        
        if HAS_ADMIN_LOGGER:
            log_admin_deletion(request.user, obj, f"Category '{category_name}' was deleted")

@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    """
    Admin interface for Template model.
    """
    list_display = ('name', 'category', 'date_uploaded', 'is_active', 'uploaded_by', 'preview_image_tag')
    list_filter = ('is_active', 'category', 'date_uploaded')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('date_uploaded', 'extraction_path', 'preview_image_tag')
    
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'category', 'description')
        }),
        (_('Upload'), {
            'fields': ('zip_file', 'preview_image', 'preview_image_tag', 'is_active')
        }),
        (_('Metadata'), {
            'fields': ('uploaded_by', 'date_uploaded', 'extraction_path'),
            'classes': ('collapse',)
        })
    )
    
    def save_model(self, request, obj, form, change):
        """
        Override save_model to set the uploaded_by field to the current user and log the action.
        """
        if not change:  # If this is a new object
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)
        
        if HAS_ADMIN_LOGGER:
            if change:
                log_admin_change(request.user, obj, f"Template '{obj.name}' was updated")
            else:
                log_admin_addition(request.user, obj, f"Template '{obj.name}' was created")
    
    def delete_model(self, request, obj):
        """
        Override delete_model to log the action.
        """
        template_name = obj.name
        
        super().delete_model(request, obj)
        
        if HAS_ADMIN_LOGGER:
            log_admin_deletion(request.user, obj, f"Template '{template_name}' was deleted")
    
    def preview_image_tag(self, obj):
        """
        Generate HTML for displaying preview image in admin.
        """
        if obj.preview_image:
            return format_html('<img src="{}" width="150" height="auto" />', obj.preview_image.url)
        return "-"
    preview_image_tag.short_description = _("Preview Image")
