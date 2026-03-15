from django.db import models


class Pledge(models.Model):
    """
    A signed pledge for The 80% Bill.
    
    Pledge-Contact Relationship:
    ---------------------
    • If a pledge has a contact_id, that contact record represents the same person
    • If contact_id is null, the pledge continues to function normally
    • This allows flexible recipient management:
      - Campaigns can target pledges directly
      - Campaigns can target contacts (which may include pledges)
      - No migration of existing pledge logic is required
    
    The contact_id foreign key is nullable to support incremental adoption.
    """

    timestamp = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=255)
    email = models.EmailField()
    district = models.CharField(max_length=50)
    rep = models.CharField(max_length=255)
    
    # Optional reference to unified contact record
    contact = models.ForeignKey(
        'email_management.Contact',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pledges',
        help_text='Optional link to unified contact record'
    )

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["contact"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.email})"
