from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import (
    EmailUser,
    Contact,
    ContactList,
    ContactListMember,
    SMTPConfiguration,
    EmailTemplate,
    EmailCampaign,
    EmailLog,
    SenderEmail,
)


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    """
    Admin interface for contacts/subscribers.
    """
    list_display = [
        'email',
        'first_name',
        'last_name',
        'district',
        'state',
        'is_subscribed_badge',
        'emails_sent',
        'source',
        'created_at',
    ]
    list_filter = ['is_subscribed', 'state', 'source', 'created_at']
    search_fields = ['email', 'first_name', 'last_name', 'district', 'phone']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Contact Information', {
            'fields': ('email', 'first_name', 'last_name', 'phone')
        }),
        ('Location', {
            'fields': ('district', 'state')
        }),
        ('Subscription', {
            'fields': ('is_subscribed', 'unsubscribed_at')
        }),
        ('Engagement Stats', {
            'fields': ('emails_sent', 'emails_opened', 'last_email_sent'),
            'classes': ('collapse',),
        }),
        ('Metadata', {
            'fields': ('source', 'notes', 'custom_data', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ['emails_sent', 'emails_opened', 'last_email_sent', 'created_at', 'updated_at', 'unsubscribed_at']
    
    actions = ['unsubscribe_contacts', 'resubscribe_contacts']
    
    def is_subscribed_badge(self, obj):
        if obj.is_subscribed:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Subscribed</span>'
            )
        return format_html(
            '<span style="color: #999;">✗ Unsubscribed</span>'
        )
    is_subscribed_badge.short_description = 'Status'
    
    def unsubscribe_contacts(self, request, queryset):
        """Bulk unsubscribe action."""
        count = 0
        for contact in queryset:
            if contact.is_subscribed:
                contact.unsubscribe()
                count += 1
        self.message_user(request, f'Unsubscribed {count} contacts.')
    unsubscribe_contacts.short_description = 'Unsubscribe selected contacts'
    
    def resubscribe_contacts(self, request, queryset):
        """Bulk resubscribe action."""
        count = queryset.update(is_subscribed=True, unsubscribed_at=None)
        self.message_user(request, f'Resubscribed {count} contacts.')
    resubscribe_contacts.short_description = 'Resubscribe selected contacts'


class ContactListMemberInline(admin.TabularInline):
    """
    Inline admin for list members.
    """
    model = ContactListMember
    extra = 1
    fields = ['contact', 'pledge', 'created_at']
    readonly_fields = ['created_at']
    autocomplete_fields = ['contact']


@admin.register(ContactList)
class ContactListAdmin(admin.ModelAdmin):
    """
    Admin interface for contact lists/segments.
    """
    list_display = [
        'name',
        'member_count_display',
        'created_by',
        'created_at',
    ]
    list_filter = ['created_at', 'created_by']
    search_fields = ['name', 'description']
    ordering = ['-created_at']
    inlines = [ContactListMemberInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'created_by')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ['created_at']
    
    def member_count_display(self, obj):
        count = obj.member_count()
        return format_html(
            '<span style="color: #666;">{} members</span>',
            count
        )
    member_count_display.short_description = 'Members'


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
        'created_by',
        'status_badge',
        'template',
        'segment',
        'contact_list',
        'start_date',
        'created_at',
    ]
    list_filter = ['status', 'created_at', 'created_by']
    search_fields = ['name', 'description']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'created_by', 'status')
        }),
        ('Configuration', {
            'fields': ('template', 'segment', 'contact_list')
        }),
        ('Sending Controls', {
            'fields': ('daily_send_limit', 'batch_size', 'start_date')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def status_badge(self, obj):
        colors = {
            'draft': '#666',
            'scheduled': 'orange',
            'sending': 'blue',
            'paused': 'purple',
            'completed': 'green',
            'cancelled': 'red',
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#666'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'


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


@admin.register(SenderEmail)
class SenderEmailAdmin(admin.ModelAdmin):
    """
    Admin interface for sender emails.
    """
    list_display = ['email', 'display_name', 'verified_badge', 'active_badge', 'description', 'created_at']
    list_filter = ['is_verified', 'is_active']
    search_fields = ['email', 'display_name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Email Information', {
            'fields': ('email', 'display_name', 'description')
        }),
        ('Status', {
            'fields': ('is_verified', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def verified_badge(self, obj):
        if obj.is_verified:
            return format_html('<span style="color: green; font-weight: bold;">✓ Verified</span>')
        return format_html('<span style="color: orange;">⚠ Not Verified</span>')
    verified_badge.short_description = 'Verified'
    
    def active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">● Active</span>')
        return format_html('<span style="color: #ccc;">○ Inactive</span>')
    active_badge.short_description = 'Status'
