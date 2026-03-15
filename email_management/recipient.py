"""
Recipient abstraction for campaign system.

A Recipient represents any email recipient and provides a unified interface
for working with both pledges and contacts.
"""
from typing import Optional, Dict, Any


class Recipient:
    """
    Abstraction over pledge and contact records.
    
    Campaign systems operate on this abstraction, allowing them to target:
    - Contacts directly
    - Pledges (with or without linked contacts)
    - Mixed audiences
    
    This abstraction provides a consistent interface regardless of the
    underlying record type.
    """
    
    def __init__(self, source_type: str, source_id: int, email: str,
                 first_name: str = '', last_name: str = '', metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize a recipient.
        
        Args:
            source_type: 'contact' or 'pledge'
            source_id: ID of the source record
            email: Email address
            first_name: First name
            last_name: Last name
            metadata: Additional data (district, rep, etc.)
        """
        self.source_type = source_type
        self.source_id = source_id
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.metadata = metadata or {}
    
    @property
    def full_name(self) -> str:
        """Return full name or empty string."""
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def display_name(self) -> str:
        """Return name for display (full name or email)."""
        return self.full_name or self.email
    
    @classmethod
    def from_contact(cls, contact) -> 'Recipient':
        """
        Create a Recipient from a Contact model instance.
        
        Args:
            contact: Contact model instance
            
        Returns:
            Recipient instance
        """
        return cls(
            source_type='contact',
            source_id=contact.id,
            email=contact.email,
            first_name=contact.first_name,
            last_name=contact.last_name,
            metadata={
                'district': contact.district,
                'state': contact.state,
                'phone': contact.phone,
                'source': contact.source,
                'is_subscribed': contact.is_subscribed,
                **contact.custom_data
            }
        )
    
    @classmethod
    def from_pledge(cls, pledge) -> 'Recipient':
        """
        Create a Recipient from a Pledge model instance.
        
        Args:
            pledge: Pledge model instance
            
        Returns:
            Recipient instance
        """
        # Parse name from pledge
        name_parts = pledge.name.strip().split(' ', 1)
        first_name = name_parts[0] if len(name_parts) > 0 else ''
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        return cls(
            source_type='pledge',
            source_id=pledge.id,
            email=pledge.email,
            first_name=first_name,
            last_name=last_name,
            metadata={
                'district': pledge.district,
                'representative': pledge.rep,
                'pledge_timestamp': pledge.timestamp.isoformat() if pledge.timestamp else None,
                'has_contact': pledge.contact_id is not None,
                'contact_id': pledge.contact_id
            }
        )
    
    def __repr__(self) -> str:
        return f"<Recipient({self.source_type}:{self.source_id}) {self.display_name} <{self.email}>>"
    
    def __str__(self) -> str:
        return f"{self.display_name} <{self.email}>"
