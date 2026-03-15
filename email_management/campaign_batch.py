"""
Campaign batch sending and scheduling.

Processes campaigns with status=sending, respects daily limits and batch sizes,
handles retries, and updates recipient statuses.
"""
import logging
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from typing import List, Tuple
from .models import EmailCampaign, CampaignRecipient, SMTPConfiguration, EmailLog
from .email_service import EmailSendingService

logger = logging.getLogger(__name__)


def process_campaign_batches():
    """
    Main scheduler job - process all active campaigns.
    
    Called periodically (e.g., every 15 minutes) to send campaign batches.
    
    Process:
    1. Find campaigns with status=sending
    2. For each campaign, send up to daily_send_limit emails
    3. Process in batches of batch_size
    4. Update recipient statuses
    5. Mark campaign completed when done
    
    Returns:
        dict: Summary of processing results
    """
    logger.info("Starting campaign batch processor")
    
    # Find active campaigns
    active_campaigns = EmailCampaign.objects.filter(
        status=EmailCampaign.STATUS_SENDING
    )
    
    results = {
        'campaigns_processed': 0,
        'total_sent': 0,
        'total_failed': 0,
        'campaigns_completed': [],
        'errors': [],
    }
    
    for campaign in active_campaigns:
        try:
            sent, failed = process_campaign(campaign)
            results['campaigns_processed'] += 1
            results['total_sent'] += sent
            results['total_failed'] += failed
            
            # Check if campaign is complete
            pending_count = campaign.recipients.filter(
                status=CampaignRecipient.STATUS_PENDING
            ).count()
            
            if pending_count == 0:
                campaign.status = EmailCampaign.STATUS_COMPLETED
                campaign.save()
                results['campaigns_completed'].append(campaign.name)
                logger.info(f"Campaign '{campaign.name}' completed")
            
        except Exception as e:
            error_msg = f"Error processing campaign {campaign.id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            results['errors'].append(error_msg)
    
    logger.info(
        f"Batch processor complete: {results['campaigns_processed']} campaigns, "
        f"{results['total_sent']} sent, {results['total_failed']} failed"
    )
    
    return results


def process_campaign(campaign: EmailCampaign) -> Tuple[int, int]:
    """
    Process a single campaign's pending recipients.
    
    Respects:
    - daily_send_limit (0 = unlimited)
    - batch_size (for rate limiting)
    - start_date (skip if not yet reached)
    
    Args:
        campaign: EmailCampaign instance
        
    Returns:
        tuple: (sent_count, failed_count)
    """
    logger.info(f"Processing campaign: {campaign.name} (ID: {campaign.id})")
    
    # Check start_date
    if campaign.start_date and timezone.now() < campaign.start_date:
        logger.info(f"Campaign {campaign.name} not yet started (start: {campaign.start_date})")
        return 0, 0
    
    # Calculate daily limit remaining
    daily_limit_remaining = get_daily_limit_remaining(campaign)
    
    if daily_limit_remaining == 0:
        logger.info(f"Campaign {campaign.name} reached daily limit")
        return 0, 0
    
    # Get pending recipients (up to daily limit)
    pending_recipients = campaign.recipients.filter(
        status=CampaignRecipient.STATUS_PENDING
    ).order_by('created_at')
    
    if daily_limit_remaining > 0:
        pending_recipients = pending_recipients[:daily_limit_remaining]
    
    if not pending_recipients.exists():
        logger.info(f"No pending recipients for campaign {campaign.name}")
        return 0, 0
    
    # Process in batches
    sent_count = 0
    failed_count = 0
    
    batch_size = campaign.batch_size
    recipient_list = list(pending_recipients)
    
    for i in range(0, len(recipient_list), batch_size):
        batch = recipient_list[i:i + batch_size]
        
        logger.info(
            f"Processing batch {i // batch_size + 1} "
            f"({len(batch)} recipients) for campaign {campaign.name}"
        )
        
        batch_sent, batch_failed = process_batch(campaign, batch)
        sent_count += batch_sent
        failed_count += batch_failed
    
    logger.info(
        f"Campaign {campaign.name} batch complete: "
        f"{sent_count} sent, {failed_count} failed"
    )
    
    return sent_count, failed_count


def process_batch(campaign: EmailCampaign, recipients: List[CampaignRecipient]) -> Tuple[int, int]:
    """
    Process a batch of recipients.
    
    Args:
        campaign: EmailCampaign instance
        recipients: List of CampaignRecipient instances
        
    Returns:
        tuple: (sent_count, failed_count)
    """
    from .campaign_versioning import ensure_campaign_has_version
    
    # Get SMTP configuration (use first available for now)
    smtp_config = SMTPConfiguration.objects.filter(is_active=True).first()
    
    if not smtp_config:
        logger.error("No active SMTP configuration found")
        return 0, len(recipients)
    
    # Ensure campaign has a version (create initial if needed)
    latest_version = ensure_campaign_has_version(campaign.id)
    
    # Initialize email service
    email_service = EmailSendingService(smtp_config)
    
    sent_count = 0
    failed_count = 0
    
    for recipient_record in recipients:
        try:
            # Get recipient data
            recipient = recipient_record.get_recipient()
            
            # Render template with recipient variables (using latest version)
            subject = render_template(latest_version.subject, recipient)
            html_body = render_template(latest_version.html_body, recipient)
            text_body = render_template(latest_version.plain_body, recipient) if latest_version.plain_body else None
            
            # Mark as sending
            recipient_record.status = CampaignRecipient.STATUS_SENDING
            recipient_record.attempts += 1
            # Store which version is being sent
            recipient_record.campaign_version = latest_version
            recipient_record.save()
            
            # Send email
            log = email_service.send_email(
                to_email=recipient.email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
                campaign=campaign,
                user=campaign.created_by,
                contact=recipient_record.contact if recipient_record.contact else None
            )
            
            # Update recipient status based on result
            if log.status == 'sent':
                recipient_record.status = CampaignRecipient.STATUS_SENT
                recipient_record.sent_at = timezone.now()
                sent_count += 1
            else:
                # Check if should retry
                if should_retry(recipient_record):
                    recipient_record.status = CampaignRecipient.STATUS_PENDING
                    logger.info(
                        f"Will retry recipient {recipient.email} "
                        f"(attempt {recipient_record.attempts})"
                    )
                else:
                    recipient_record.status = CampaignRecipient.STATUS_FAILED
                    recipient_record.failed_at = timezone.now()
                    failed_count += 1
                    logger.warning(
                        f"Recipient {recipient.email} failed after "
                        f"{recipient_record.attempts} attempts: {log.error_message}"
                    )
            
            recipient_record.save()
            
        except Exception as e:
            logger.error(f"Error sending to recipient {recipient_record.id}: {str(e)}", exc_info=True)
            
            # Mark as failed
            recipient_record.status = CampaignRecipient.STATUS_FAILED
            recipient_record.failed_at = timezone.now()
            recipient_record.save()
            failed_count += 1
    
    return sent_count, failed_count


def get_daily_limit_remaining(campaign: EmailCampaign) -> int:
    """
    Calculate how many more emails can be sent today for this campaign.
    
    Args:
        campaign: EmailCampaign instance
        
    Returns:
        int: Number of emails remaining (0 = unlimited)
    """
    if campaign.daily_send_limit == 0:
        return -1  # Unlimited (return negative to bypass limit checks)
    
    # Get today's start (midnight)
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Count emails sent today
    sent_today = campaign.recipients.filter(
        status=CampaignRecipient.STATUS_SENT,
        sent_at__gte=today_start
    ).count()
    
    remaining = campaign.daily_send_limit - sent_today
    return max(0, remaining)


def should_retry(recipient_record: CampaignRecipient, max_attempts: int = 3) -> bool:
    """
    Determine if a failed send should be retried.
    
    Args:
        recipient_record: CampaignRecipient instance
        max_attempts: Maximum retry attempts (default: 3)
        
    Returns:
        bool: True if should retry
    """
    return recipient_record.attempts < max_attempts


def render_template(text: str, recipient) -> str:
    """
    Render template text with recipient variables.
    
    Available variables:
    - {{email}}
    - {{first_name}}
    - {{last_name}}
    - {{full_name}}
    - {{display_name}}
    - {{district}}
    - {{state}}
    - {{representative}}
    - Any custom metadata keys
    
    Args:
        text: Template text with {{variables}}
        recipient: Recipient instance
        
    Returns:
        str: Rendered text
    """
    if not text:
        return text
    
    # Standard replacements
    replacements = {
        '{{email}}': recipient.email or '',
        '{{full_name}}': recipient.full_name or '',
        '{{display_name}}': recipient.display_name or '',
    }
    
    # Add metadata variables
    if recipient.metadata:
        for key, value in recipient.metadata.items():
            replacements[f'{{{{{key}}}}}'] = str(value) if value else ''
    
    # Replace all variables
    for var, value in replacements.items():
        text = text.replace(var, value)
    
    return text


def start_campaign(campaign_id: int) -> dict:
    """
    Start a campaign (convenience function for manual starts).
    
    This function:
    1. Validates campaign can start
    2. Resolves recipients if not already done
    3. Changes status to sending
    
    Args:
        campaign_id: ID of campaign to start
        
    Returns:
        dict: Result summary
        
    Raises:
        ValueError: If campaign can't be started
    """
    from .campaign_resolution import resolve_campaign_recipients
    from .campaign_versioning import ensure_campaign_has_version
    
    try:
        campaign = EmailCampaign.objects.get(id=campaign_id)
    except EmailCampaign.DoesNotExist:
        raise ValueError(f"Campaign {campaign_id} not found")
    
    # Validate can start
    if not campaign.can_start():
        raise ValueError(
            f"Campaign {campaign.name} cannot be started. "
            f"Status: {campaign.get_status_display()}"
        )
    
    # Ensure campaign has a version (create initial if needed)
    version = ensure_campaign_has_version(campaign_id)
    logger.info(f"Campaign {campaign.name} using version {version.version_number}")
    
    # Resolve recipients if not done
    recipient_count = campaign.recipients.count()
    if recipient_count == 0:
        created, skipped = resolve_campaign_recipients(campaign_id)
        recipient_count = created
        logger.info(
            f"Resolved {created} recipients for campaign {campaign.name} "
            f"(skipped {skipped} duplicates)"
        )
    
    # Change status to sending
    campaign.status = EmailCampaign.STATUS_SENDING
    campaign.save()
    
    logger.info(f"Started campaign {campaign.name} with {recipient_count} recipients")
    
    return {
        'campaign_id': campaign.id,
        'campaign_name': campaign.name,
        'recipients': recipient_count,
        'daily_limit': campaign.daily_send_limit,
        'batch_size': campaign.batch_size,
        'status': 'sending',
        'version': version.version_number,
    }


def pause_campaign(campaign_id: int) -> dict:
    """
    Pause a running campaign.
    
    Args:
        campaign_id: ID of campaign to pause
        
    Returns:
        dict: Result summary
        
    Raises:
        ValueError: If campaign can't be paused
    """
    try:
        campaign = EmailCampaign.objects.get(id=campaign_id)
    except EmailCampaign.DoesNotExist:
        raise ValueError(f"Campaign {campaign_id} not found")
    
    if not campaign.can_pause():
        raise ValueError(
            f"Campaign {campaign.name} cannot be paused. "
            f"Status: {campaign.get_status_display()}"
        )
    
    campaign.status = EmailCampaign.STATUS_PAUSED
    campaign.save()
    
    logger.info(f"Paused campaign {campaign.name}")
    
    return {
        'campaign_id': campaign.id,
        'campaign_name': campaign.name,
        'status': 'paused',
    }


def resume_campaign(campaign_id: int) -> dict:
    """
    Resume a paused campaign.
    
    Args:
        campaign_id: ID of campaign to resume
        
    Returns:
        dict: Result summary
        
    Raises:
        ValueError: If campaign can't be resumed
    """
    try:
        campaign = EmailCampaign.objects.get(id=campaign_id)
    except EmailCampaign.DoesNotExist:
        raise ValueError(f"Campaign {campaign_id} not found")
    
    if not campaign.can_resume():
        raise ValueError(
            f"Campaign {campaign.name} cannot be resumed. "
            f"Status: {campaign.get_status_display()}"
        )
    
    campaign.status = EmailCampaign.STATUS_SENDING
    campaign.save()
    
    logger.info(f"Resumed campaign {campaign.name}")
    
    return {
        'campaign_id': campaign.id,
        'campaign_name': campaign.name,
        'status': 'sending',
    }


def cancel_campaign(campaign_id: int) -> dict:
    """
    Cancel a campaign permanently.
    
    Args:
        campaign_id: ID of campaign to cancel
        
    Returns:
        dict: Result summary
        
    Raises:
        ValueError: If campaign can't be cancelled
    """
    try:
        campaign = EmailCampaign.objects.get(id=campaign_id)
    except EmailCampaign.DoesNotExist:
        raise ValueError(f"Campaign {campaign_id} not found")
    
    if not campaign.can_cancel():
        raise ValueError(
            f"Campaign {campaign.name} cannot be cancelled. "
            f"Status: {campaign.get_status_display()}"
        )
    
    campaign.status = EmailCampaign.STATUS_CANCELLED
    campaign.save()
    
    logger.info(f"Cancelled campaign {campaign.name}")
    
    # Count stats
    sent = campaign.recipients.filter(status=CampaignRecipient.STATUS_SENT).count()
    pending = campaign.recipients.filter(status=CampaignRecipient.STATUS_PENDING).count()
    
    return {
        'campaign_id': campaign.id,
        'campaign_name': campaign.name,
        'status': 'cancelled',
        'sent_before_cancel': sent,
        'pending_at_cancel': pending,
    }
