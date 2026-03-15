"""
Campaign recipient resolution.

When a campaign starts, this module resolves the recipient list and locks it in
as CampaignRecipient records. This prevents segment drift and duplicate sending.
"""
from typing import List, Tuple
from django.db import transaction
from .models import EmailCampaign, CampaignRecipient, Contact
from .recipient import Recipient
from pledge.models import Pledge


def resolve_campaign_recipients(campaign_id: int) -> Tuple[int, int]:
    """
    Resolve and create campaign_recipient records for a campaign.
    
    This function:
    1. Resolves recipients from campaign's segment and/or contact_list
    2. Deduplicates by email address
    3. Creates CampaignRecipient records
    4. Returns (created_count, skipped_count)
    
    Args:
        campaign_id: ID of the campaign to resolve recipients for
        
    Returns:
        tuple: (created_count, skipped_count)
        
    Raises:
        EmailCampaign.DoesNotExist: If campaign not found
        ValueError: If campaign has no targeting (no segment or contact_list)
    """
    try:
        campaign = EmailCampaign.objects.get(id=campaign_id)
    except EmailCampaign.DoesNotExist:
        raise
    
    # Validate campaign has targeting
    if not campaign.segment and not campaign.contact_list:
        raise ValueError(
            f"Campaign {campaign.name} has no segment or contact_list. "
            "At least one must be set."
        )
    
    # Collect all recipients
    recipients = []
    
    # Resolve from segment
    if campaign.segment:
        segment_recipients = campaign.segment.resolve()
        recipients.extend(segment_recipients)
    
    # Resolve from contact list
    if campaign.contact_list:
        list_recipients = _resolve_from_contact_list(campaign.contact_list)
        recipients.extend(list_recipients)
    
    # Deduplicate by email (case-insensitive)
    unique_recipients = _deduplicate_recipients(recipients)
    
    # Create CampaignRecipient records
    created_count = 0
    skipped_count = 0
    
    with transaction.atomic():
        for recipient in unique_recipients:
            # Check if already exists (prevent duplicate resolution)
            exists = CampaignRecipient.objects.filter(
                campaign=campaign,
                contact_id=recipient.source_id if recipient.source_type == 'contact' else None,
                pledge_id=recipient.source_id if recipient.source_type == 'pledge' else None,
            ).exists()
            
            if exists:
                skipped_count += 1
                continue
            
            # Create recipient record
            contact_id = recipient.source_id if recipient.source_type == 'contact' else None
            pledge_id = recipient.source_id if recipient.source_type == 'pledge' else None
            
            CampaignRecipient.objects.create(
                campaign=campaign,
                contact_id=contact_id,
                pledge_id=pledge_id,
                status=CampaignRecipient.STATUS_PENDING
            )
            created_count += 1
    
    return created_count, skipped_count


def _resolve_from_contact_list(contact_list) -> List[Recipient]:
    """
    Resolve recipients from a contact list.
    
    Args:
        contact_list: ContactList instance
        
    Returns:
        List of Recipient instances
    """
    recipients = []
    
    for member in contact_list.members.all():
        recipient = member.get_recipient()
        recipients.append(recipient)
    
    return recipients


def _deduplicate_recipients(recipients: List[Recipient]) -> List[Recipient]:
    """
    Deduplicate recipients by email address (case-insensitive).
    
    If multiple recipients have the same email, keeps the first one.
    
    Args:
        recipients: List of Recipient instances
        
    Returns:
        Deduplicated list of Recipient instances
    """
    seen_emails = set()
    unique = []
    
    for recipient in recipients:
        email_lower = recipient.email.lower()
        if email_lower not in seen_emails:
            unique.append(recipient)
            seen_emails.add(email_lower)
    
    return unique
