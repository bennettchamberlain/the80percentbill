# Pledge-Contact Relationship Documentation

## Overview

The system uses two separate tables to represent email recipients:

1. **contacts** - General-purpose recipient table
2. **pledges** - Specific to The 80% Bill campaign

## Relationship Design

```
pledges
├── id
├── email
├── name
├── district
├── rep
├── timestamp
└── contact_id (nullable FK → contacts)

contacts  
├── id
├── email
├── first_name
├── last_name
├── metadata (JSONB)
├── created_at
└── updated_at
```

## The Rule

**If a pledge has a `contact_id`:**
- That contact record represents the same person
- The contact is the "canonical" recipient record
- Campaigns can use either the pledge or the contact

**If a pledge has `contact_id = NULL`:**
- The pledge continues to function independently
- No contact record exists (yet)
- Campaigns can still target the pledge directly

## Why This Design?

1. **Incremental adoption** - No need to migrate all pledges immediately
2. **Flexibility** - Campaigns can target:
   - All contacts (general mailing list)
   - Only pledges (campaign-specific)
   - Mixed audiences
3. **Data integrity** - Both tables remain independent
4. **No breaking changes** - Existing pledge logic continues to work

## Recipient Abstraction

The `Recipient` class provides a unified interface:

```python
from email_management.recipient import Recipient

# From a contact
recipient = Recipient.from_contact(contact_obj)

# From a pledge
recipient = Recipient.from_pledge(pledge_obj)

# Both provide:
recipient.email
recipient.full_name
recipient.display_name
recipient.metadata
```

Campaign systems operate on `Recipient` instances, not directly on pledges/contacts.

## Future Migration Path

When ready to unify records:

1. Create contact for each pledge without one
2. Set `pledge.contact_id` to link them
3. Campaigns automatically benefit from unified targeting

No code changes required - the relationship already exists.

## SQL Schema

### contacts (email_management_contact)
```sql
CREATE TABLE email_management_contact (
    id SERIAL PRIMARY KEY,
    email VARCHAR(254) UNIQUE NOT NULL,
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    -- (additional fields: phone, district, state, subscription, tracking, etc.)
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE INDEX ON email_management_contact(email);
CREATE INDEX ON email_management_contact(created_at DESC);
```

### pledges
```sql
CREATE TABLE pledge_pledge (
    id SERIAL PRIMARY KEY,
    email VARCHAR(254) NOT NULL,
    name VARCHAR(255) NOT NULL,
    district VARCHAR(50) NOT NULL,
    rep VARCHAR(255) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    contact_id INTEGER NULL REFERENCES email_management_contact(id) ON DELETE SET NULL
);

CREATE INDEX ON pledge_pledge(email);
CREATE INDEX ON pledge_pledge(contact_id);
```

## Examples

### Example 1: Pledge without contact
```python
pledge = Pledge.objects.get(email='user@example.com')
# pledge.contact_id = None
# Campaigns can still send to pledge.email
```

### Example 2: Pledge with contact
```python
pledge = Pledge.objects.get(email='user@example.com')
# pledge.contact_id = 123
contact = pledge.contact
# Campaigns use contact.email (same as pledge.email)
```

### Example 3: Contact without pledge
```python
contact = Contact.objects.get(email='imported@example.com')
# No pledge exists
# Campaigns send to general mailing list
```

## Implementation Status

✅ Database schema updated
✅ Pledge.contact FK added (nullable)
✅ Recipient abstraction created
✅ Migration applied successfully
⏳ Contact-pledge linking logic (future phase)
⏳ Campaign resolution logic (future phase)

---

**Next steps**: Build segmentation and campaign resolution to use this foundation.
