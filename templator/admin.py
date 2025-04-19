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
    Handles automatic unique slug generation on save.
    """
    list_display = ('name', 'slug', 'category', 'date_uploaded', 'is_active', 'uploaded_by', 'preview_image_tag')
    list_filter = ('is_active', 'category', 'date_uploaded')
    search_fields = ('name', 'description')
    readonly_fields = ('slug', 'date_uploaded', 'extraction_path', 'preview_image_tag', 'detected_framework')
    
    # Base fieldsets (for change form) - keep uploaded_by here (it's made readonly dynamically)
    base_fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'category', 'description')
        }),
        (_('Upload'), {
            'fields': ('zip_file', 'preview_image', 'preview_image_tag', 'is_active')
        }),
        (_('Metadata'), {
            'fields': ('uploaded_by', 'date_uploaded', 'extraction_path', 'detected_framework'),
            'classes': ('collapse',)
        })
    )

    # Define fieldsets for the add_form (including uploaded_by)
    add_fieldsets = (
        (None, {
            # Add uploaded_by here
            'fields': ('name', 'category', 'description', 'uploaded_by') 
        }),
        (_('Upload'), {
            'fields': ('zip_file', 'preview_image', 'is_active') 
        }),
    )

    def get_fieldsets(self, request, obj=None):
        """
        Use add_fieldsets on the add page, base_fieldsets on the change page.
        """
        if not obj: 
            return self.add_fieldsets
        return self.base_fieldsets

    def get_readonly_fields(self, request, obj=None):
        """
        Dynamically set readonly fields. 
        'uploaded_by' is readonly only when editing (obj exists).
        """
        if obj: # Editing an existing object
            # Include 'uploaded_by' in readonly fields for change form
            return ('slug', 'date_uploaded', 'extraction_path', 'preview_image_tag', 'uploaded_by', 'detected_framework')
        else: # Adding a new object
            # Exclude 'uploaded_by' here to make it editable on add form
            # Only fields that are ALWAYS readonly go here
            return ('preview_image_tag',) 
    
    def save_model(self, request, obj, form, change):
        """
        Save the model. Automatic slug generation handled by model.save().
        Automatic uploaded_by assignment is removed.
        """
        super().save_model(request, obj, form, change)
        
        if HAS_ADMIN_LOGGER:
            if change:
                log_admin_change(request.user, obj, f"Template '{obj.name}' was updated")
            else:
                log_admin_addition(request.user, obj, f"Template '{obj.name}' (slug: {obj.slug}) was created by {obj.uploaded_by.username if obj.uploaded_by else 'N/A'}")
    
    def delete_model(self, request, obj):
        """
        Override delete_model to log the action.
        """
        template_name = obj.name
        template_slug = obj.slug # Capture slug for log
        uploader = obj.uploaded_by.username if obj.uploaded_by else 'N/A'
        
        super().delete_model(request, obj)
        
        if HAS_ADMIN_LOGGER:
            log_admin_deletion(request.user, obj, f"Template '{template_name}' (slug: {template_slug}, uploader: {uploader}) was deleted")
    
    def preview_image_tag(self, obj):
        """
        Generate HTML for displaying preview image in admin.
        """
        if obj.preview_image:
            return format_html('<img src="{}" width="150" height="auto" />', obj.preview_image.url)
        return "-"
    preview_image_tag.short_description = _("Preview Image")
