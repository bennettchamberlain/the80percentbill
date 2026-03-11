from django.contrib.auth.models import AbstractUser
from django.db import models


class EmailUser(AbstractUser):
    """
    Custom user model for email management system.
    Only users created by superadmin can access the email management page.
    """
    # Use email as the primary identifier
    email = models.EmailField(unique=True, verbose_name='Email Address')
    
    # Additional fields
    can_access_email_management = models.BooleanField(
        default=False,
        verbose_name='Can Access Email Management',
        help_text='Designates whether this user can access the email management system.'
    )
    created_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_users',
        verbose_name='Created By',
        help_text='The superadmin who created this user.'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Override username requirement - we'll use email instead
    username = models.CharField(max_length=150, unique=True, blank=True)
    
    class Meta:
        verbose_name = 'Email Management User'
        verbose_name_plural = 'Email Management Users'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.email
    
    def save(self, *args, **kwargs):
        # Auto-generate username from email if not provided
        if not self.username:
            self.username = self.email.split('@')[0]
            # Ensure uniqueness
            base_username = self.username
            counter = 1
            while EmailUser.objects.filter(username=self.username).exclude(pk=self.pk).exists():
                self.username = f"{base_username}{counter}"
                counter += 1
        super().save(*args, **kwargs)


class SMTPConfiguration(models.Model):
    """
    SMTP configuration for sending emails.
    Can be shared or user-specific.
    """
    name = models.CharField(
        max_length=255,
        verbose_name='Configuration Name',
        help_text='Descriptive name for this SMTP configuration'
    )
    user = models.ForeignKey(
        EmailUser,
        on_delete=models.CASCADE,
        related_name='smtp_configs',
        null=True,
        blank=True,
        verbose_name='Owner',
        help_text='Leave blank for shared configuration'
    )
    
    # SMTP Settings
    smtp_host = models.CharField(max_length=255, verbose_name='SMTP Host')
    smtp_port = models.IntegerField(default=587, verbose_name='SMTP Port')
    smtp_username = models.CharField(max_length=255, verbose_name='SMTP Username')
    smtp_password = models.CharField(
        max_length=255,
        verbose_name='SMTP Password',
        help_text='Will be encrypted in production'
    )
    use_tls = models.BooleanField(default=True, verbose_name='Use TLS')
    use_ssl = models.BooleanField(default=False, verbose_name='Use SSL')
    
    # Email settings
    from_email = models.EmailField(verbose_name='From Email')
    from_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='From Name',
        help_text='Display name for sender'
    )
    
    # Metadata
    is_active = models.BooleanField(default=True, verbose_name='Active')
    is_default = models.BooleanField(
        default=False,
        verbose_name='Default Configuration',
        help_text='Use this configuration by default'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'SMTP Configuration'
        verbose_name_plural = 'SMTP Configurations'
        ordering = ['-is_default', '-created_at']
    
    def __str__(self):
        owner = f" ({self.user.email})" if self.user else " (Shared)"
        return f"{self.name}{owner}"


class EmailTemplate(models.Model):
    """
    Reusable email templates.
    """
    name = models.CharField(max_length=255, verbose_name='Template Name')
    user = models.ForeignKey(
        EmailUser,
        on_delete=models.CASCADE,
        related_name='email_templates',
        null=True,
        blank=True,
        verbose_name='Owner',
        help_text='Leave blank for shared template'
    )
    
    subject = models.CharField(max_length=255, verbose_name='Email Subject')
    body_html = models.TextField(verbose_name='HTML Body', blank=True)
    body_text = models.TextField(verbose_name='Plain Text Body', blank=True)
    
    # Variables that can be used in template (JSON)
    available_variables = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Available Variables',
        help_text='Variables that can be used in this template (e.g., {{name}}, {{link}})'
    )
    
    is_active = models.BooleanField(default=True, verbose_name='Active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Email Template'
        verbose_name_plural = 'Email Templates'
        ordering = ['-created_at']
    
    def __str__(self):
        owner = f" ({self.user.email})" if self.user else " (Shared)"
        return f"{self.name}{owner}"


class EmailCampaign(models.Model):
    """
    Email campaigns / sends.
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('sending', 'Sending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]
    
    name = models.CharField(max_length=255, verbose_name='Campaign Name')
    user = models.ForeignKey(
        EmailUser,
        on_delete=models.CASCADE,
        related_name='campaigns',
        verbose_name='Created By'
    )
    smtp_config = models.ForeignKey(
        SMTPConfiguration,
        on_delete=models.PROTECT,
        related_name='campaigns',
        verbose_name='SMTP Configuration'
    )
    template = models.ForeignKey(
        EmailTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='campaigns',
        verbose_name='Email Template'
    )
    
    subject = models.CharField(max_length=255, verbose_name='Email Subject')
    body_html = models.TextField(verbose_name='HTML Body', blank=True)
    body_text = models.TextField(verbose_name='Plain Text Body', blank=True)
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='Status'
    )
    
    # Recipients (stored as JSON array of email addresses)
    recipients = models.JSONField(
        default=list,
        verbose_name='Recipients',
        help_text='List of recipient email addresses'
    )
    
    # Statistics
    total_recipients = models.IntegerField(default=0, verbose_name='Total Recipients')
    sent_count = models.IntegerField(default=0, verbose_name='Sent Count')
    failed_count = models.IntegerField(default=0, verbose_name='Failed Count')
    
    # Scheduling
    scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Scheduled Send Time'
    )
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Actually Sent At'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Email Campaign'
        verbose_name_plural = 'Email Campaigns'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.status}"


class EmailLog(models.Model):
    """
    Log of individual email sends.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('bounced', 'Bounced'),
    ]
    
    campaign = models.ForeignKey(
        EmailCampaign,
        on_delete=models.CASCADE,
        related_name='logs',
        null=True,
        blank=True,
        verbose_name='Campaign'
    )
    user = models.ForeignKey(
        EmailUser,
        on_delete=models.CASCADE,
        related_name='email_logs',
        verbose_name='Sent By'
    )
    
    recipient_email = models.EmailField(verbose_name='Recipient')
    subject = models.CharField(max_length=255, verbose_name='Subject')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Status'
    )
    
    error_message = models.TextField(
        blank=True,
        verbose_name='Error Message',
        help_text='Error details if send failed'
    )
    
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='Sent At')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Email Log'
        verbose_name_plural = 'Email Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['recipient_email']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.recipient_email} - {self.status}"
