"""
Campaign monitoring and metrics.

Provides functions for tracking campaign progress, viewing recipient details,
and generating reports.
"""
from django.db.models import Count, Q, Avg, F
from django.utils import timezone
from datetime import timedelta
from typing import List, Dict, Optional
from .models import EmailCampaign, CampaignRecipient


def get_campaign_summary(campaign_id: int) -> dict:
    """
    Get comprehensive metrics summary for a campaign.
    
    Args:
        campaign_id: ID of campaign
        
    Returns:
        dict with all campaign metrics and progress
        
    Raises:
        EmailCampaign.DoesNotExist: If campaign not found
    """
    campaign = EmailCampaign.objects.get(id=campaign_id)
    
    return campaign.get_metrics_summary()


def get_all_campaigns_summary(status_filter: str = None) -> List[dict]:
    """
    Get summary of all campaigns.
    
    Args:
        status_filter: Optional status to filter by (e.g., 'sending')
        
    Returns:
        list of campaign summary dicts
    """
    queryset = EmailCampaign.objects.all()
    
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    summaries = []
    for campaign in queryset.order_by('-created_at'):
        summaries.append(campaign.get_metrics_summary())
    
    return summaries


def get_campaign_recipients(campaign_id: int, status: str = None, 
                           limit: int = None, offset: int = 0) -> dict:
    """
    Get paginated list of campaign recipients with details.
    
    Args:
        campaign_id: ID of campaign
        status: Filter by status (optional)
        limit: Number of results per page (default: 50)
        offset: Starting position (for pagination)
        
    Returns:
        dict with recipients list and pagination info
    """
    campaign = EmailCampaign.objects.get(id=campaign_id)
    
    queryset = campaign.recipients.select_related('contact', 'pledge', 'campaign_version')
    
    if status:
        queryset = queryset.filter(status=status)
    
    total_count = queryset.count()
    
    queryset = queryset.order_by('-sent_at', 'created_at')
    
    if limit:
        queryset = queryset[offset:offset + limit]
    
    recipients = []
    for recipient_record in queryset:
        recipient = recipient_record.get_recipient()
        
        recipients.append({
            'id': recipient_record.id,
            'email': recipient.email,
            'full_name': recipient.full_name,
            'district': recipient.metadata.get('district'),
            'state': recipient.metadata.get('state'),
            'representative': recipient.metadata.get('representative'),
            'status': recipient_record.status,
            'status_display': recipient_record.get_status_display(),
            'sent_at': recipient_record.sent_at,
            'failed_at': recipient_record.failed_at,
            'attempts': recipient_record.attempts,
            'version': recipient_record.campaign_version.version_number if recipient_record.campaign_version else None,
            'version_subject': recipient_record.campaign_version.subject if recipient_record.campaign_version else None,
        })
    
    return {
        'campaign_id': campaign_id,
        'campaign_name': campaign.name,
        'total': total_count,
        'offset': offset,
        'limit': limit or total_count,
        'recipients': recipients,
    }


def get_campaign_progress_timeline(campaign_id: int) -> dict:
    """
    Get campaign progress over time (sends per day).
    
    Args:
        campaign_id: ID of campaign
        
    Returns:
        dict with daily send counts
    """
    campaign = EmailCampaign.objects.get(id=campaign_id)
    
    # Get all sent recipients grouped by date
    sent_recipients = campaign.recipients.filter(
        status=CampaignRecipient.STATUS_SENT,
        sent_at__isnull=False
    ).extra(
        select={'date': 'DATE(sent_at)'}
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')
    
    timeline = {}
    for entry in sent_recipients:
        date_str = entry['date'].strftime('%Y-%m-%d')
        timeline[date_str] = entry['count']
    
    return {
        'campaign_id': campaign_id,
        'campaign_name': campaign.name,
        'timeline': timeline,
    }


def get_campaign_status_breakdown(campaign_id: int) -> dict:
    """
    Get count of recipients by status.
    
    Args:
        campaign_id: ID of campaign
        
    Returns:
        dict with counts per status
    """
    campaign = EmailCampaign.objects.get(id=campaign_id)
    
    breakdown = campaign.recipients.values('status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    status_counts = {}
    for entry in breakdown:
        status_counts[entry['status']] = entry['count']
    
    return {
        'campaign_id': campaign_id,
        'campaign_name': campaign.name,
        'breakdown': status_counts,
        'total': campaign.total_recipients,
    }


def get_campaign_version_distribution(campaign_id: int) -> dict:
    """
    Get count of recipients by version.
    
    Shows how many recipients received each version of the campaign.
    
    Args:
        campaign_id: ID of campaign
        
    Returns:
        dict with counts per version
    """
    campaign = EmailCampaign.objects.get(id=campaign_id)
    
    distribution = campaign.recipients.filter(
        campaign_version__isnull=False
    ).values(
        'campaign_version__id',
        'campaign_version__subject',
        version_number=F('campaign_version__id')  # Placeholder, will calculate
    ).annotate(
        count=Count('id')
    ).order_by('campaign_version__created_at')
    
    versions = []
    for entry in distribution:
        version_id = entry['campaign_version__id']
        from .models import CampaignVersion
        version = CampaignVersion.objects.get(id=version_id)
        
        versions.append({
            'version_id': version_id,
            'version_number': version.version_number,
            'subject': entry['campaign_version__subject'],
            'count': entry['count'],
        })
    
    return {
        'campaign_id': campaign_id,
        'campaign_name': campaign.name,
        'versions': versions,
    }


def get_failed_recipients_details(campaign_id: int) -> dict:
    """
    Get detailed information about failed recipients.
    
    Args:
        campaign_id: ID of campaign
        
    Returns:
        dict with failed recipient details and error patterns
    """
    campaign = EmailCampaign.objects.get(id=campaign_id)
    
    failed_recipients = campaign.recipients.filter(
        status=CampaignRecipient.STATUS_FAILED
    ).select_related('contact', 'pledge')
    
    failed_list = []
    for recipient_record in failed_recipients:
        recipient = recipient_record.get_recipient()
        
        # Try to get error message from EmailLog
        from .models import EmailLog
        last_log = EmailLog.objects.filter(
            campaign=campaign,
            recipient_email=recipient.email
        ).order_by('-created_at').first()
        
        error_message = last_log.error_message if last_log and last_log.error_message else 'Unknown error'
        
        failed_list.append({
            'email': recipient.email,
            'full_name': recipient.full_name,
            'district': recipient.metadata.get('district'),
            'attempts': recipient_record.attempts,
            'failed_at': recipient_record.failed_at,
            'error_message': error_message,
        })
    
    return {
        'campaign_id': campaign_id,
        'campaign_name': campaign.name,
        'failed_count': len(failed_list),
        'failed_recipients': failed_list,
    }


def get_active_campaigns_overview() -> List[dict]:
    """
    Get overview of all active (sending) campaigns.
    
    Returns:
        list of active campaign summaries with progress
    """
    active_campaigns = EmailCampaign.objects.filter(
        status=EmailCampaign.STATUS_SENDING
    ).order_by('-updated_at')
    
    overview = []
    for campaign in active_campaigns:
        metrics = campaign.get_metrics_summary()
        
        # Add estimated completion time
        if campaign.daily_send_limit > 0 and metrics['pending'] > 0:
            days_remaining = metrics['pending'] / campaign.daily_send_limit
            metrics['estimated_days_remaining'] = round(days_remaining, 1)
        else:
            metrics['estimated_days_remaining'] = None
        
        overview.append(metrics)
    
    return overview


def search_recipients(campaign_id: int, query: str, limit: int = 50) -> List[dict]:
    """
    Search for recipients by email, name, or district.
    
    Args:
        campaign_id: ID of campaign
        query: Search query string
        limit: Maximum results
        
    Returns:
        list of matching recipients
    """
    campaign = EmailCampaign.objects.get(id=campaign_id)
    
    # Search in recipients
    recipients_queryset = campaign.recipients.select_related('contact', 'pledge')
    
    matching_recipients = []
    for recipient_record in recipients_queryset[:limit * 2]:  # Get more to filter
        recipient = recipient_record.get_recipient()
        
        # Check if query matches email, name, or district
        query_lower = query.lower()
        if (query_lower in recipient.email.lower() or
            query_lower in recipient.full_name.lower() or
            (recipient.metadata.get('district') and query_lower in recipient.metadata.get('district', '').lower())):
            
            matching_recipients.append({
                'email': recipient.email,
                'full_name': recipient.full_name,
                'district': recipient.metadata.get('district'),
                'status': recipient_record.status,
                'status_display': recipient_record.get_status_display(),
                'sent_at': recipient_record.sent_at,
            })
            
            if len(matching_recipients) >= limit:
                break
    
    return matching_recipients


def get_campaign_failures_timeline(campaign_id: int) -> dict:
    """
    Get campaign failures over time (failed per day).
    
    Args:
        campaign_id: ID of campaign
        
    Returns:
        dict with daily failure counts
    """
    campaign = EmailCampaign.objects.get(id=campaign_id)
    
    # Get all failed recipients grouped by date
    failed_recipients = campaign.recipients.filter(
        status=CampaignRecipient.STATUS_FAILED,
        failed_at__isnull=False
    ).extra(
        select={'date': 'DATE(failed_at)'}
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')
    
    timeline = {}
    for entry in failed_recipients:
        date_str = entry['date'].strftime('%Y-%m-%d')
        timeline[date_str] = entry['count']
    
    return {
        'campaign_id': campaign_id,
        'campaign_name': campaign.name,
        'timeline': timeline,
    }
