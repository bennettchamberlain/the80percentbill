"""
Segment resolution engine.

Resolves segments to sets of recipients based on filter definitions.
Supports filtering against both pledge and contact fields, with special
handling for congressional_district as a first-class attribute.
"""
from typing import List
from .models import Segment, Contact, ContactListMember
from .recipient import Recipient
from pledge.models import Pledge


def resolve_segment(segment_id: int) -> List[Recipient]:
    """
    Resolve a segment to a set of recipients.
    
    This function evaluates the segment's filter definition against
    all contacts and pledges, returning recipients that match the criteria.
    
    Args:
        segment_id: ID of the segment to resolve
        
    Returns:
        List of Recipient instances matching the segment filters
        
    Example segment definition:
        {
            "conditions": [
                {
                    "field": "congressional_district",
                    "operator": "=",
                    "value": "CA-12"
                }
            ],
            "match": "all"  # or "any"
        }
    
    Supported fields:
        - congressional_district: From contact.district or pledge.district
        - representative: From pledge.rep
        - state: From contact.state
        - is_subscribed: From contact.is_subscribed
        - source: From contact.source
        - Custom fields from contact.custom_data
    
    Supported operators:
        - =: Equals
        - !=: Not equals
        - contains: Substring match (case-insensitive)
        - in: Value in list
        - >, <, >=, <=: Numeric/date comparison
    """
    try:
        segment = Segment.objects.get(id=segment_id)
    except Segment.DoesNotExist:
        return []
    
    definition = segment.definition
    conditions = definition.get('conditions', [])
    match_mode = definition.get('match', 'all')  # 'all' or 'any'
    
    if not conditions:
        # No conditions = match nothing (safer than matching everything)
        return []
    
    recipients = []
    seen_emails = set()
    
    # Resolve from contacts
    contacts = Contact.objects.all()
    for contact in contacts:
        recipient = Recipient.from_contact(contact)
        if _matches_conditions(recipient, conditions, match_mode):
            if recipient.email.lower() not in seen_emails:
                recipients.append(recipient)
                seen_emails.add(recipient.email.lower())
    
    # Resolve from pledges (that don't have a linked contact to avoid duplicates)
    pledges = Pledge.objects.filter(contact__isnull=True)
    for pledge in pledges:
        recipient = Recipient.from_pledge(pledge)
        if _matches_conditions(recipient, conditions, match_mode):
            if recipient.email.lower() not in seen_emails:
                recipients.append(recipient)
                seen_emails.add(recipient.email.lower())
    
    return recipients


def _matches_conditions(recipient: Recipient, conditions: list, match_mode: str) -> bool:
    """
    Check if a recipient matches the filter conditions.
    
    Args:
        recipient: Recipient instance to check
        conditions: List of condition dicts
        match_mode: 'all' (AND) or 'any' (OR)
        
    Returns:
        True if recipient matches, False otherwise
    """
    results = []
    
    for condition in conditions:
        field = condition.get('field')
        operator = condition.get('operator')
        value = condition.get('value')
        
        # Map field names to recipient attributes
        if field == 'congressional_district':
            actual_value = recipient.metadata.get('district', '')
        elif field == 'representative':
            actual_value = recipient.metadata.get('representative', '')
        elif field == 'state':
            actual_value = recipient.metadata.get('state', '')
        elif field == 'is_subscribed':
            actual_value = recipient.metadata.get('is_subscribed', True)
        elif field == 'source':
            actual_value = recipient.metadata.get('source', '')
        else:
            # Try to get from metadata
            actual_value = recipient.metadata.get(field)
        
        # Evaluate condition
        match = _evaluate_condition(actual_value, operator, value)
        results.append(match)
    
    # Apply match mode
    if match_mode == 'any':
        return any(results)
    else:  # 'all' (default)
        return all(results)


def _evaluate_condition(actual_value, operator: str, expected_value) -> bool:
    """
    Evaluate a single condition.
    
    Args:
        actual_value: The recipient's value for this field
        operator: Comparison operator
        expected_value: The value to compare against
        
    Returns:
        True if condition matches, False otherwise
    """
    if actual_value is None:
        return operator == '!=' or operator == 'not in'
    
    if operator == '=':
        return str(actual_value).lower() == str(expected_value).lower()
    
    elif operator == '!=':
        return str(actual_value).lower() != str(expected_value).lower()
    
    elif operator == 'contains':
        return str(expected_value).lower() in str(actual_value).lower()
    
    elif operator == 'in':
        if not isinstance(expected_value, list):
            expected_value = [expected_value]
        return actual_value in expected_value
    
    elif operator == 'not in':
        if not isinstance(expected_value, list):
            expected_value = [expected_value]
        return actual_value not in expected_value
    
    elif operator == '>':
        try:
            return float(actual_value) > float(expected_value)
        except (ValueError, TypeError):
            return False
    
    elif operator == '<':
        try:
            return float(actual_value) < float(expected_value)
        except (ValueError, TypeError):
            return False
    
    elif operator == '>=':
        try:
            return float(actual_value) >= float(expected_value)
        except (ValueError, TypeError):
            return False
    
    elif operator == '<=':
        try:
            return float(actual_value) <= float(expected_value)
        except (ValueError, TypeError):
            return False
    
    # Unknown operator
    return False
