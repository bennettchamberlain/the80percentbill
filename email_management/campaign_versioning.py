"""
Campaign versioning system.

Campaigns can be edited while sending. This module handles version creation
and ensures recipients receive the version active when they were sent to.
"""
from django.db import transaction
from django.utils import timezone
from .models import EmailCampaign, CampaignVersion, EmailTemplate


def create_campaign_version(campaign_id: int, notes: str = '', user=None) -> CampaignVersion:
    """
    Create a new version of a campaign.
    
    This captures the current template content as a snapshot. Future sends
    will use this version until another version is created.
    
    Args:
        campaign_id: ID of campaign to version
        notes: Optional notes about what changed
        user: EmailUser who created the version (optional)
        
    Returns:
        CampaignVersion instance
        
    Raises:
        EmailCampaign.DoesNotExist: If campaign not found
    """
    campaign = EmailCampaign.objects.get(id=campaign_id)
    
    # Get current template content
    template = campaign.template
    
    # Create version snapshot
    version = CampaignVersion.objects.create(
        campaign=campaign,
        subject=template.subject,
        html_body=template.body_html,
        plain_body=template.body_text or '',
        created_by=user or campaign.created_by,
        notes=notes
    )
    
    return version


def get_latest_version(campaign_id: int) -> CampaignVersion:
    """
    Get the most recent version of a campaign.
    
    Args:
        campaign_id: ID of campaign
        
    Returns:
        CampaignVersion instance (most recent)
        
    Raises:
        CampaignVersion.DoesNotExist: If no versions exist
    """
    return CampaignVersion.objects.filter(
        campaign_id=campaign_id
    ).order_by('-created_at').first()


def ensure_campaign_has_version(campaign_id: int) -> CampaignVersion:
    """
    Ensure a campaign has at least one version.
    
    If no versions exist, creates the initial version from the template.
    
    Args:
        campaign_id: ID of campaign
        
    Returns:
        CampaignVersion instance (existing or newly created)
    """
    existing = get_latest_version(campaign_id)
    
    if existing:
        return existing
    
    # Create initial version
    return create_campaign_version(
        campaign_id,
        notes='Initial version'
    )


def update_campaign_content(campaign_id: int, subject: str = None, 
                            html_body: str = None, plain_body: str = None,
                            notes: str = '', user=None) -> CampaignVersion:
    """
    Update a campaign's content by creating a new version.
    
    This is the safe way to edit a campaign while it's sending.
    - Recipients already sent keep their original version
    - New sends use the updated content
    
    Args:
        campaign_id: ID of campaign to update
        subject: New subject (optional, keeps current if None)
        html_body: New HTML body (optional, keeps current if None)
        plain_body: New plain body (optional, keeps current if None)
        notes: Description of changes
        user: EmailUser making the update
        
    Returns:
        CampaignVersion instance (new version)
        
    Raises:
        EmailCampaign.DoesNotExist: If campaign not found
    """
    campaign = EmailCampaign.objects.get(id=campaign_id)
    
    # Get current content from latest version or template
    latest_version = get_latest_version(campaign_id)
    
    if latest_version:
        current_subject = latest_version.subject
        current_html = latest_version.html_body
        current_plain = latest_version.plain_body
    else:
        current_subject = campaign.template.subject
        current_html = campaign.template.body_html
        current_plain = campaign.template.body_text or ''
    
    # Use provided values or keep current
    new_subject = subject if subject is not None else current_subject
    new_html = html_body if html_body is not None else current_html
    new_plain = plain_body if plain_body is not None else current_plain
    
    # Create new version
    version = CampaignVersion.objects.create(
        campaign=campaign,
        subject=new_subject,
        html_body=new_html,
        plain_body=new_plain,
        created_by=user or campaign.created_by,
        notes=notes or 'Content updated'
    )
    
    return version


def get_version_stats(campaign_id: int) -> dict:
    """
    Get statistics about campaign versions.
    
    Args:
        campaign_id: ID of campaign
        
    Returns:
        dict with version statistics
    """
    versions = CampaignVersion.objects.filter(campaign_id=campaign_id)
    
    stats = {
        'total_versions': versions.count(),
        'versions': []
    }
    
    for version in versions.order_by('-created_at'):
        stats['versions'].append({
            'id': version.id,
            'version_number': version.version_number,
            'created_at': version.created_at,
            'created_by': version.created_by.email if version.created_by else None,
            'sends_count': version.sends_count,
            'notes': version.notes,
            'subject': version.subject,
        })
    
    return stats


def compare_versions(version1_id: int, version2_id: int) -> dict:
    """
    Compare two campaign versions.
    
    Args:
        version1_id: First version ID
        version2_id: Second version ID
        
    Returns:
        dict with comparison results
    """
    v1 = CampaignVersion.objects.get(id=version1_id)
    v2 = CampaignVersion.objects.get(id=version2_id)
    
    return {
        'version1': {
            'id': v1.id,
            'number': v1.version_number,
            'created_at': v1.created_at,
            'subject': v1.subject,
            'html_body': v1.html_body,
            'plain_body': v1.plain_body,
        },
        'version2': {
            'id': v2.id,
            'number': v2.version_number,
            'created_at': v2.created_at,
            'subject': v2.subject,
            'html_body': v2.html_body,
            'plain_body': v2.plain_body,
        },
        'changes': {
            'subject_changed': v1.subject != v2.subject,
            'html_changed': v1.html_body != v2.html_body,
            'plain_changed': v1.plain_body != v2.plain_body,
        }
    }


def rollback_to_version(campaign_id: int, version_id: int, user=None) -> CampaignVersion:
    """
    Roll back a campaign to a previous version.
    
    Creates a new version with the content from the specified version.
    Does NOT delete the versions in between (keeps full history).
    
    Args:
        campaign_id: ID of campaign
        version_id: ID of version to roll back to
        user: EmailUser performing rollback
        
    Returns:
        CampaignVersion instance (new version with old content)
    """
    old_version = CampaignVersion.objects.get(id=version_id, campaign_id=campaign_id)
    
    # Create new version with old content
    new_version = CampaignVersion.objects.create(
        campaign_id=campaign_id,
        subject=old_version.subject,
        html_body=old_version.html_body,
        plain_body=old_version.plain_body,
        created_by=user,
        notes=f'Rolled back to version {old_version.version_number}'
    )
    
    return new_version
