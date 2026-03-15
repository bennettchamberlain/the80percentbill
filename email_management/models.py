from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


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


class Contact(models.Model):
    """
    Contacts/subscribers for email campaigns.
    This is where we manage our own contact list.
    """
    email = models.EmailField(unique=True, verbose_name='Email Address', db_index=True)
    first_name = models.CharField(max_length=255, blank=True, verbose_name='First Name')
    last_name = models.CharField(max_length=255, blank=True, verbose_name='Last Name')
    
    # Custom fields
    phone = models.CharField(max_length=50, blank=True, verbose_name='Phone')
    district = models.CharField(max_length=10, blank=True, verbose_name='District Code')
    state = models.CharField(max_length=50, blank=True, verbose_name='State')
    
    # Subscription status
    is_subscribed = models.BooleanField(default=True, verbose_name='Subscribed')
    unsubscribed_at = models.DateTimeField(null=True, blank=True, verbose_name='Unsubscribed At')
    
    # Engagement tracking
    emails_sent = models.IntegerField(default=0, verbose_name='Emails Sent')
    emails_opened = models.IntegerField(default=0, verbose_name='Emails Opened')
    last_email_sent = models.DateTimeField(null=True, blank=True, verbose_name='Last Email Sent')
    
    # Metadata
    source = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Source',
        help_text='How this contact was added (e.g., pledge form, import, manual)'
    )
    notes = models.TextField(blank=True, verbose_name='Notes')
    custom_data = models.JSONField(default=dict, blank=True, verbose_name='Custom Data')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Contact'
        verbose_name_plural = 'Contacts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['is_subscribed']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        if self.first_name or self.last_name:
            return f"{self.first_name} {self.last_name} <{self.email}>".strip()
        return self.email
    
    def unsubscribe(self):
        """Unsubscribe this contact."""
        self.is_subscribed = False
        self.unsubscribed_at = timezone.now()
        self.save()


class ContactList(models.Model):
    """
    Named lists for organizing recipients.
    
    Lists provide a way to group recipients (contacts and/or pledges)
    for targeted campaign sending.
    """
    name = models.CharField(max_length=255, verbose_name='List Name')
    description = models.TextField(blank=True, verbose_name='Description')
    created_by = models.ForeignKey(
        EmailUser,
        on_delete=models.CASCADE,
        related_name='created_lists',
        verbose_name='Created By'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'contact_lists'
        verbose_name = 'Contact List'
        verbose_name_plural = 'Contact Lists'
        ordering = ['-created_at']
        
    def __str__(self):
        return self.name
    
    def member_count(self):
        """Return total number of members in this list."""
        return self.members.count()


class ContactListMember(models.Model):
    """
    Membership record linking lists to recipients.
    
    How list membership works:
    ---------------------------
    Each member represents ONE recipient in a list.
    
    A member may reference either:
    • A contact (contact_id is set, pledge_id is null)
    • A pledge (pledge_id is set, contact_id is null)
    
    Exactly one of these fields must be populated.
    
    This design allows lists to contain:
    - Only contacts (general mailing list)
    - Only pledges (campaign-specific)
    - Mixed audiences (both contacts and pledges)
    
    When resolving recipients for a campaign, the system will:
    1. Iterate through all members of target lists
    2. Convert each member to a Recipient instance
    3. Deduplicate by email address
    4. Apply subscription filters
    """
    list = models.ForeignKey(
        ContactList,
        on_delete=models.CASCADE,
        related_name='members'
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='list_memberships'
    )
    pledge = models.ForeignKey(
        'pledge.Pledge',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='list_memberships'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'contact_list_members'
        indexes = [
            models.Index(fields=['contact']),
            models.Index(fields=['pledge']),
            models.Index(fields=['list']),
        ]
        # Prevent duplicate memberships
        unique_together = [
            ['list', 'contact'],
            ['list', 'pledge'],
        ]
    
    def clean(self):
        """
        Validate that exactly one of contact_id or pledge_id is set.
        
        This enforces the mutual exclusivity constraint:
        - Both null: Invalid (no recipient)
        - Both set: Invalid (ambiguous recipient)
        - One set: Valid
        """
        from django.core.exceptions import ValidationError
        
        has_contact = self.contact_id is not None
        has_pledge = self.pledge_id is not None
        
        if not has_contact and not has_pledge:
            raise ValidationError(
                'Either contact or pledge must be specified.'
            )
        
        if has_contact and has_pledge:
            raise ValidationError(
                'Cannot specify both contact and pledge. Choose one.'
            )
    
    def save(self, *args, **kwargs):
        """Override save to run validation."""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def get_recipient(self):
        """
        Return a Recipient instance for this member.
        
        Returns:
            Recipient instance (from email_management.recipient)
        """
        from email_management.recipient import Recipient
        
        if self.contact:
            return Recipient.from_contact(self.contact)
        elif self.pledge:
            return Recipient.from_pledge(self.pledge)
        else:
            raise ValueError('Member has no contact or pledge')


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
        help_text='Variables that can be used in this template (e.g., {"first_name": "Recipient first name"})'
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
    Email campaigns for targeted messaging.
    
    Campaigns reference templates (read-only) and target recipients via
    either segments or contact lists (or both).
    
    Campaign lifecycle:
    1. draft → user creates and configures
    2. scheduled → queued for sending at start_date
    3. sending → actively processing batches
    4. completed → all sends finished
    5. paused → temporarily stopped (can resume)
    6. cancelled → permanently stopped
    """
    
    # Status choices
    STATUS_DRAFT = 'draft'
    STATUS_SCHEDULED = 'scheduled'
    STATUS_SENDING = 'sending'
    STATUS_PAUSED = 'paused'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'
    
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_SCHEDULED, 'Scheduled'),
        (STATUS_SENDING, 'Sending'),
        (STATUS_PAUSED, 'Paused'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]
    
    # Basic info
    name = models.CharField(max_length=255, verbose_name='Campaign Name')
    description = models.TextField(blank=True, verbose_name='Description')
    
    # Template reference (read-only)
    template = models.ForeignKey(
        EmailTemplate,
        on_delete=models.PROTECT,
        related_name='campaigns',
        verbose_name='Email Template',
        help_text='Template is referenced, not copied. Changes to template do not affect sent emails.'
    )
    
    # Recipient targeting (at least one must be set)
    segment = models.ForeignKey(
        'Segment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='campaigns',
        verbose_name='Segment',
        help_text='Target recipients via segment filters'
    )
    contact_list = models.ForeignKey(
        ContactList,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='campaigns',
        verbose_name='Contact List',
        help_text='Target recipients via contact list'
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        verbose_name='Status',
        db_index=True
    )
    
    # Sending controls
    daily_send_limit = models.IntegerField(
        default=1000,
        verbose_name='Daily Send Limit',
        help_text='Maximum emails to send per day (0 = unlimited)'
    )
    batch_size = models.IntegerField(
        default=50,
        verbose_name='Batch Size',
        help_text='Number of emails to send in each batch'
    )
    
    # Scheduling
    start_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Start Date',
        help_text='When to begin sending (null = send immediately when started)'
    )
    
    # Ownership
    created_by = models.ForeignKey(
        EmailUser,
        on_delete=models.CASCADE,
        related_name='created_campaigns',
        verbose_name='Created By'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'email_campaigns'
        verbose_name = 'Email Campaign'
        verbose_name_plural = 'Email Campaigns'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['start_date']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
    
    def can_edit(self):
        """Check if campaign can be edited."""
        return self.status in [self.STATUS_DRAFT, self.STATUS_SCHEDULED]
    
    def can_start(self):
        """Check if campaign can be started."""
        return self.status == self.STATUS_DRAFT and (self.segment or self.contact_list)
    
    def can_pause(self):
        """Check if campaign can be paused."""
        return self.status == self.STATUS_SENDING
    
    def can_resume(self):
        """Check if campaign can be resumed."""
        return self.status == self.STATUS_PAUSED
    
    def can_cancel(self):
        """Check if campaign can be cancelled."""
        return self.status in [self.STATUS_DRAFT, self.STATUS_SCHEDULED, self.STATUS_SENDING, self.STATUS_PAUSED]
    
    # Progress tracking metrics
    
    @property
    def total_recipients(self):
        """Total number of recipients resolved for this campaign."""
        return self.recipients.count()
    
    @property
    def sent_count(self):
        """Number of recipients successfully sent."""
        return self.recipients.filter(status=CampaignRecipient.STATUS_SENT).count()
    
    @property
    def failed_count(self):
        """Number of recipients that failed permanently."""
        return self.recipients.filter(status=CampaignRecipient.STATUS_FAILED).count()
    
    @property
    def pending_count(self):
        """Number of recipients not yet sent."""
        return self.recipients.filter(status=CampaignRecipient.STATUS_PENDING).count()
    
    @property
    def skipped_count(self):
        """Number of recipients intentionally skipped."""
        return self.recipients.filter(status=CampaignRecipient.STATUS_SKIPPED).count()
    
    @property
    def success_rate(self):
        """
        Success rate as percentage (sent / (sent + failed) * 100).
        Returns None if no sends attempted yet.
        """
        total_attempted = self.sent_count + self.failed_count
        if total_attempted == 0:
            return None
        return (self.sent_count / total_attempted) * 100
    
    @property
    def progress_percentage(self):
        """
        Campaign progress as percentage ((sent + failed + skipped) / total * 100).
        Returns 0 if no recipients.
        """
        total = self.total_recipients
        if total == 0:
            return 0
        completed = self.sent_count + self.failed_count + self.skipped_count
        return (completed / total) * 100
    
    def get_metrics_summary(self):
        """
        Get comprehensive campaign metrics.
        
        Returns:
            dict with all campaign metrics
        """
        return {
            'campaign_id': self.id,
            'campaign_name': self.name,
            'status': self.status,
            'status_display': self.get_status_display(),
            'total_recipients': self.total_recipients,
            'sent': self.sent_count,
            'failed': self.failed_count,
            'pending': self.pending_count,
            'skipped': self.skipped_count,
            'success_rate': self.success_rate,
            'progress_percentage': self.progress_percentage,
            'daily_send_limit': self.daily_send_limit,
            'batch_size': self.batch_size,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }
    
    def get_recipients_list(self, status=None, limit=None):
        """
        Get list of recipients with details.
        
        Args:
            status: Filter by recipient status (optional)
            limit: Maximum number to return (optional)
            
        Returns:
            list of dicts with recipient details
        """
        queryset = self.recipients.select_related('contact', 'pledge', 'campaign_version')
        
        if status:
            queryset = queryset.filter(status=status)
        
        queryset = queryset.order_by('-sent_at', 'created_at')
        
        if limit:
            queryset = queryset[:limit]
        
        recipients_list = []
        for recipient_record in queryset:
            recipient = recipient_record.get_recipient()
            
            recipients_list.append({
                'id': recipient_record.id,
                'email': recipient.email,
                'full_name': recipient.full_name,
                'district': recipient.metadata.get('district'),
                'state': recipient.metadata.get('state'),
                'status': recipient_record.status,
                'status_display': recipient_record.get_status_display(),
                'sent_at': recipient_record.sent_at,
                'failed_at': recipient_record.failed_at,
                'attempts': recipient_record.attempts,
                'version': recipient_record.campaign_version.version_number if recipient_record.campaign_version else None,
            })
        
        return recipients_list


class EmailLog(models.Model):
    """
    Log of individual email sends.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sending', 'Sending'),
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
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name='email_logs',
        verbose_name='Contact'
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
        return f"{self.recipient_email} - {self.get_status_display()}"


class SenderEmail(models.Model):
    """
    Approved sender email addresses for campaigns.
    """
    email = models.EmailField(unique=True, verbose_name='Sender Email')
    display_name = models.CharField(max_length=100, default='The 80% Bill', verbose_name='Display Name')
    is_verified = models.BooleanField(
        default=False,
        verbose_name='Verified',
        help_text="Verified in email provider (Brevo, etc.)"
    )
    is_active = models.BooleanField(default=True, verbose_name='Active')
    description = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Description',
        help_text="e.g., 'General inquiries', 'Newsletter', 'Support'"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Sender Email'
        verbose_name_plural = 'Sender Emails'
        ordering = ['-is_verified', 'email']
    
    def __str__(self):
        status = "✓" if self.is_verified else "⚠"
        return f"{status} {self.email} ({self.display_name})"



class Segment(models.Model):
    """
    Reusable audience segments based on recipient attributes.
    
    Segments define filter rules that resolve to a set of recipients.
    This enables targeted campaign messaging based on attributes like
    congressional district, representative, or engagement metrics.
    
    The definition field contains filter rules in JSONB format:
    {
        "conditions": [
            {
                "field": "congressional_district",
                "operator": "=",
                "value": "CA-12"
            },
            {
                "field": "representative",
                "operator": "contains",
                "value": "Pelosi"
            }
        ],
        "match": "all"  # or "any"
    }
    
    Supported fields:
    - congressional_district (from contact.district or pledge.district)
    - representative (from pledge.rep or contact metadata)
    - state (from contact.state)
    - is_subscribed (from contact.is_subscribed)
    - source (from contact.source)
    - Any field in contact.custom_data or pledge metadata
    
    Supported operators:
    - = (equals)
    - != (not equals)
    - contains (substring match)
    - in (value in list)
    - > < >= <= (numeric/date comparison)
    """
    name = models.CharField(max_length=255, verbose_name='Segment Name')
    description = models.TextField(blank=True, verbose_name='Description')
    definition = models.JSONField(
        default=dict,
        verbose_name='Filter Definition',
        help_text='JSON filter rules for segment matching'
    )
    created_by = models.ForeignKey(
        EmailUser,
        on_delete=models.CASCADE,
        related_name='created_segments',
        verbose_name='Created By'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'segments'
        verbose_name = 'Segment'
        verbose_name_plural = 'Segments'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def resolve(self):
        """
        Resolve this segment to a set of recipients.
        
        Returns:
            list: List of Recipient instances matching the segment filters
        """
        from .segment_resolver import resolve_segment
        return resolve_segment(self.id)


class CampaignRecipient(models.Model):
    """
    Locked-in recipient list for a campaign.
    
    When a campaign starts, we resolve recipients and create records here.
    This prevents:
    - Segment drift (segment rules changing mid-campaign)
    - Duplicate sending (same person getting email twice)
    - Race conditions (concurrent resolution)
    
    Each record represents ONE send attempt to ONE recipient.
    
    Rules:
    - Exactly one of contact_id or pledge_id must be set
    - Once created, these records are immutable (except status updates)
    - Status tracks the send lifecycle
    """
    
    # Status choices
    STATUS_PENDING = 'pending'
    STATUS_SCHEDULED = 'scheduled'
    STATUS_SENDING = 'sending'
    STATUS_SENT = 'sent'
    STATUS_FAILED = 'failed'
    STATUS_SKIPPED = 'skipped'
    
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_SCHEDULED, 'Scheduled'),
        (STATUS_SENDING, 'Sending'),
        (STATUS_SENT, 'Sent'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_SKIPPED, 'Skipped'),
    ]
    
    # Campaign reference
    campaign = models.ForeignKey(
        EmailCampaign,
        on_delete=models.CASCADE,
        related_name='recipients',
        verbose_name='Campaign'
    )
    
    # Recipient reference (exactly one must be set)
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='campaign_sends',
        verbose_name='Contact'
    )
    pledge = models.ForeignKey(
        'pledge.Pledge',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='campaign_sends',
        verbose_name='Pledge'
    )
    
    # Version tracking
    campaign_version = models.ForeignKey(
        'CampaignVersion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='campaign_sends',
        verbose_name='Campaign Version',
        help_text='The version of campaign content sent to this recipient'
    )
    
    # Send tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
        verbose_name='Status'
    )
    scheduled_for = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name='Scheduled For',
        help_text='When this recipient is scheduled to receive the email'
    )
    attempts = models.IntegerField(
        default=0,
        verbose_name='Attempts',
        help_text='Number of send attempts'
    )
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Sent At'
    )
    failed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Failed At'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'campaign_recipients'
        verbose_name = 'Campaign Recipient'
        verbose_name_plural = 'Campaign Recipients'
        indexes = [
            models.Index(fields=['campaign', 'status']),
            models.Index(fields=['status']),
            models.Index(fields=['scheduled_for']),
            models.Index(fields=['contact']),
            models.Index(fields=['pledge']),
        ]
        # Prevent duplicate recipients in same campaign
        unique_together = [
            ['campaign', 'contact'],
            ['campaign', 'pledge'],
        ]
    
    def clean(self):
        """Validate that exactly one of contact or pledge is set."""
        from django.core.exceptions import ValidationError
        
        has_contact = self.contact_id is not None
        has_pledge = self.pledge_id is not None
        
        if not has_contact and not has_pledge:
            raise ValidationError(
                'Either contact or pledge must be specified.'
            )
        
        if has_contact and has_pledge:
            raise ValidationError(
                'Cannot specify both contact and pledge. Choose one.'
            )
    
    def save(self, *args, **kwargs):
        """Override save to run validation."""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def get_recipient(self):
        """
        Return a Recipient instance for this campaign recipient.
        
        Returns:
            Recipient instance
        """
        from .recipient import Recipient
        
        if self.contact:
            return Recipient.from_contact(self.contact)
        elif self.pledge:
            return Recipient.from_pledge(self.pledge)
        else:
            raise ValueError('Campaign recipient has no contact or pledge')
    
    def __str__(self):
        email = self.contact.email if self.contact else self.pledge.email if self.pledge else 'unknown'
        return f"{self.campaign.name} → {email} ({self.get_status_display()})"


class CampaignVersion(models.Model):
    """
    Campaign content version history.
    
    When a campaign is edited while sending, we create a new version.
    This ensures:
    - Recipients already sent keep their original version
    - New sends use the updated version
    - No double sending or content inconsistency
    
    Each version captures the email content at a point in time.
    """
    
    # Campaign reference
    campaign = models.ForeignKey(
        EmailCampaign,
        on_delete=models.CASCADE,
        related_name='versions',
        verbose_name='Campaign'
    )
    
    # Email content (snapshot of template at this moment)
    subject = models.CharField(
        max_length=255,
        verbose_name='Subject'
    )
    html_body = models.TextField(
        verbose_name='HTML Body'
    )
    plain_body = models.TextField(
        blank=True,
        verbose_name='Plain Text Body',
        help_text='Fallback for email clients that do not support HTML'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        EmailUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='campaign_versions',
        verbose_name='Created By',
        help_text='User who created this version'
    )
    notes = models.TextField(
        blank=True,
        verbose_name='Version Notes',
        help_text='Optional notes about what changed in this version'
    )
    
    class Meta:
        db_table = 'campaign_versions'
        verbose_name = 'Campaign Version'
        verbose_name_plural = 'Campaign Versions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['campaign', '-created_at']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.campaign.name} v{self.version_number} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
    
    @property
    def version_number(self):
        """
        Calculate this version's number (1-indexed).
        
        Returns:
            int: Version number (1 = first version, 2 = second, etc.)
        """
        # Count versions created before or at same time as this one
        count = CampaignVersion.objects.filter(
            campaign=self.campaign,
            created_at__lte=self.created_at
        ).count()
        return count
    
    @property
    def sends_count(self):
        """
        Count how many recipients were sent using this version.
        
        Returns:
            int: Number of CampaignRecipient records using this version
        """
        return self.campaign_sends.count()
    
    def get_content_preview(self, max_length=100):
        """
        Get a preview of the email content.
        
        Args:
            max_length: Maximum length of preview
            
        Returns:
            str: Truncated HTML body
        """
        import re
        # Strip HTML tags for preview
        text = re.sub('<[^<]+?>', '', self.html_body)
        if len(text) > max_length:
            return text[:max_length] + '...'
        return text
