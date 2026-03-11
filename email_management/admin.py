from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import (
    EmailUser,
    SMTPConfiguration,
    EmailTemplate,
    EmailCampaign,
    EmailLog,
)


@admin.register(EmailUser)
class EmailUserAdmin(BaseUserAdmin):
    """
    Admin interface for EmailUser model.
    Only superadmins can create/manage email management users.
    """
    list_display = [
        'email',
        'username',
        'first_name',
        'last_name',
        'can_access_email_management_badge',
        'is_staff',
        'is_superuser',
        'created_at',
    ]
    list_filter = [
        'can_access_email_management',
        'is_staff',
        'is_superuser',
        'is_active',
        'created_at',
    ]
    search_fields = ['email', 'username', 'first_name', 'last_name']
    ordering = ['-created_at']
    
    fieldsets = (
        (None, {
            'fields': ('email', 'username', 'password')
        }),
        ('Personal Info', {
            'fields': ('first_name', 'last_name')
        }),
        ('Permissions', {
            'fields': (
                'can_access_email_management',
                'is_active',
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions',
            ),
            'description': 'Control user access to email management and admin areas.'
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email',
                'username',
                'password1',
                'password2',
                'first_name',
                'last_name',
                'can_access_email_management',
                'is_staff',
            ),
        }),
    )
    
    def can_access_email_management_badge(self, obj):
        if obj.can_access_email_management:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Yes</span>'
            )
        return format_html(
            '<span style="color: #ccc;">✗ No</span>'
        )
    can_access_email_management_badge.short_description = 'Email Access'
    
    def save_model(self, request, obj, form, change):
        # If creating a new user, set created_by to current superadmin
        if not change and request.user.is_superuser:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(SMTPConfiguration)
class SMTPConfigurationAdmin(admin.ModelAdmin):
    """
    Admin interface for SMTP configurations.
    """
    list_display = [
        'name',
        'smtp_host',
        'smtp_port',
        'from_email',
        'user_badge',
        'is_active_badge',
        'is_default_badge',
        'created_at',
    ]
    list_filter = ['is_active', 'is_default', 'use_tls', 'use_ssl', 'created_at']
    search_fields = ['name', 'smtp_host', 'from_email', 'smtp_username']
    ordering = ['-is_default', '-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'user', 'is_active', 'is_default')
        }),
        ('SMTP Settings', {
            'fields': (
                'smtp_host',
                'smtp_port',
                'smtp_username',
                'smtp_password',
                'use_tls',
                'use_ssl',
            )
        }),
        ('Email Settings', {
            'fields': ('from_email', 'from_name')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def user_badge(self, obj):
        if obj.user:
            return format_html(
                '<span style="color: #666;">{}</span>',
                obj.user.email
            )
        return format_html(
            '<span style="color: green; font-weight: bold;">Shared</span>'
        )
    user_badge.short_description = 'Owner'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color: green;">●</span>'
            )
        return format_html(
            '<span style="color: #ccc;">○</span>'
        )
    is_active_badge.short_description = 'Active'
    
    def is_default_badge(self, obj):
        if obj.is_default:
            return format_html(
                '<span style="color: blue; font-weight: bold;">⭐ Default</span>'
            )
        return ''
    is_default_badge.short_description = 'Default'


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    """
    Admin interface for email templates.
    """
    list_display = [
        'name',
        'subject',
        'user_badge',
        'is_active_badge',
        'created_at',
    ]
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'subject', 'body_html', 'body_text']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'user', 'is_active')
        }),
        ('Email Content', {
            'fields': ('subject', 'body_html', 'body_text')
        }),
        ('Variables', {
            'fields': ('available_variables',),
            'description': 'Define variables that can be used in this template (e.g., {"name": "Recipient name", "link": "Custom link"})'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def user_badge(self, obj):
        if obj.user:
            return format_html(
                '<span style="color: #666;">{}</span>',
                obj.user.email
            )
        return format_html(
            '<span style="color: green; font-weight: bold;">Shared</span>'
        )
    user_badge.short_description = 'Owner'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color: green;">●</span>'
            )
        return format_html(
            '<span style="color: #ccc;">○</span>'
        )
    is_active_badge.short_description = 'Active'


@admin.register(EmailCampaign)
class EmailCampaignAdmin(admin.ModelAdmin):
    """
    Admin interface for email campaigns.
    """
    list_display = [
        'name',
        'user',
        'status_badge',
        'total_recipients',
        'sent_count',
        'failed_count',
        'progress_badge',
        'created_at',
    ]
    list_filter = ['status', 'created_at', 'user']
    search_fields = ['name', 'subject']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'user', 'status')
        }),
        ('Configuration', {
            'fields': ('smtp_config', 'template')
        }),
        ('Email Content', {
            'fields': ('subject', 'body_html', 'body_text')
        }),
        ('Recipients', {
            'fields': ('recipients', 'total_recipients')
        }),
        ('Statistics', {
            'fields': ('sent_count', 'failed_count')
        }),
        ('Scheduling', {
            'fields': ('scheduled_at', 'sent_at')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ['total_recipients', 'sent_count', 'failed_count', 'created_at', 'updated_at']
    
    def status_badge(self, obj):
        colors = {
            'draft': '#666',
            'scheduled': 'orange',
            'sending': 'blue',
            'sent': 'green',
            'failed': 'red',
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#666'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def progress_badge(self, obj):
        if obj.total_recipients == 0:
            return '-'
        percentage = (obj.sent_count / obj.total_recipients) * 100
        return format_html(
            '<span style="color: {};">{:.1f}%</span>',
            'green' if percentage == 100 else 'orange',
            percentage
        )
    progress_badge.short_description = 'Progress'


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    """
    Admin interface for email logs.
    """
    list_display = [
        'recipient_email',
        'subject_short',
        'campaign_link',
        'user',
        'status_badge',
        'sent_at',
        'created_at',
    ]
    list_filter = ['status', 'created_at', 'user']
    search_fields = ['recipient_email', 'subject', 'error_message']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Email Information', {
            'fields': ('campaign', 'user', 'recipient_email', 'subject')
        }),
        ('Status', {
            'fields': ('status', 'error_message')
        }),
        ('Timestamps', {
            'fields': ('sent_at', 'created_at')
        }),
    )
    
    readonly_fields = ['sent_at', 'created_at']
    
    def subject_short(self, obj):
        if len(obj.subject) > 50:
            return obj.subject[:50] + '...'
        return obj.subject
    subject_short.short_description = 'Subject'
    
    def campaign_link(self, obj):
        if obj.campaign:
            return format_html(
                '<a href="/admin/email_management/emailcampaign/{}/change/">{}</a>',
                obj.campaign.id,
                obj.campaign.name
            )
        return '-'
    campaign_link.short_description = 'Campaign'
    
    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'sent': 'green',
            'failed': 'red',
            'bounced': '#666',
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#666'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
