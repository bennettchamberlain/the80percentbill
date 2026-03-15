# Contact Lists Documentation

## Overview

Contact lists provide a way to organize recipients (contacts and pledges) into named groups for targeted campaign sending.

## Database Schema

### contact_lists

```sql
CREATE TABLE contact_lists (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_by_id INTEGER NOT NULL REFERENCES email_management_emailuser(id),
    created_at TIMESTAMP NOT NULL
);
```

### contact_list_members

```sql
CREATE TABLE contact_list_members (
    id SERIAL PRIMARY KEY,
    list_id INTEGER NOT NULL REFERENCES contact_lists(id) ON DELETE CASCADE,
    contact_id INTEGER NULL REFERENCES email_management_contact(id) ON DELETE CASCADE,
    pledge_id INTEGER NULL REFERENCES pledge_pledge(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL,
    
    -- Indexes for query performance
    CONSTRAINT contact_list_members_list_contact_uniq UNIQUE (list_id, contact_id),
    CONSTRAINT contact_list_members_list_pledge_uniq UNIQUE (list_id, pledge_id)
);

CREATE INDEX contact_list_members_contact_idx ON contact_list_members(contact_id);
CREATE INDEX contact_list_members_pledge_idx ON contact_list_members(pledge_id);
CREATE INDEX contact_list_members_list_idx ON contact_list_members(list_id);
```

## List Membership Rules

### Mutual Exclusivity Constraint

Each member represents **exactly one recipient** in a list.

A member may reference either:
- **A contact** (`contact_id` is set, `pledge_id` is null)
- **A pledge** (`pledge_id` is set, `contact_id` is null)

**Exactly one** of these fields must be populated.

### Validation

The system enforces this at the model level:

```python
# ✅ Valid: Contact only
ContactListMember(list=my_list, contact=some_contact)

# ✅ Valid: Pledge only
ContactListMember(list=my_list, pledge=some_pledge)

# ❌ Invalid: Both set
ContactListMember(list=my_list, contact=some_contact, pledge=some_pledge)
# Raises: ValidationError("Cannot specify both contact and pledge")

# ❌ Invalid: Neither set
ContactListMember(list=my_list)
# Raises: ValidationError("Either contact or pledge must be specified")
```

## How List Membership Works

When resolving recipients for a campaign:

1. **Iterate through all members** of target lists
2. **Convert each member to a Recipient** instance
   - If member.contact → `Recipient.from_contact(contact)`
   - If member.pledge → `Recipient.from_pledge(pledge)`
3. **Deduplicate** by email address across all lists
4. **Apply subscription filters** (only subscribed recipients)

## List Types

This design allows three types of lists:

### 1. Contact-Only Lists
General mailing lists, imported contacts, newsletter subscribers.

```python
list = ContactList.objects.create(name="Newsletter Subscribers", ...)
for contact in Contact.objects.filter(is_subscribed=True):
    ContactListMember.objects.create(list=list, contact=contact)
```

### 2. Pledge-Only Lists
Campaign-specific targeting for pledge signers.

```python
list = ContactList.objects.create(name="CA-30 Pledges", ...)
for pledge in Pledge.objects.filter(district="CA-30"):
    ContactListMember.objects.create(list=list, pledge=pledge)
```

### 3. Mixed Lists
Both contacts and pledges in the same list.

```python
list = ContactList.objects.create(name="Priority Outreach", ...)
ContactListMember.objects.create(list=list, contact=vip_contact)
ContactListMember.objects.create(list=list, pledge=key_pledge)
```

## Usage Examples

### Creating a List

```python
from email_management.models import ContactList, ContactListMember, EmailUser

user = EmailUser.objects.get(email='admin@example.com')
list = ContactList.objects.create(
    name='My List',
    description='Target audience for campaign',
    created_by=user
)
```

### Adding Members

```python
# Add a contact
ContactListMember.objects.create(list=list, contact=contact_obj)

# Add a pledge
ContactListMember.objects.create(list=list, pledge=pledge_obj)
```

### Getting Recipients

```python
# Get all recipients in a list
recipients = [member.get_recipient() for member in list.members.all()]

# Get count
count = list.member_count()
```

### Preventing Duplicates

The unique_together constraints prevent:
- Same contact in same list multiple times
- Same pledge in same list multiple times

But allow:
- Same email via different paths (contact vs pledge) - will be deduplicated at campaign send time

## Admin Interface

Lists are managed via Django admin with inline member editing:

- Create/edit lists
- Add members (contact or pledge) via inline forms
- View member count
- Search and filter lists

## Future Enhancements

### Phase 2 (Segmentation)
- Dynamic segments based on filters
- Auto-updating lists

### Phase 4 (Recipient Resolution)
- Campaign → Lists → Members → Recipients
- Email deduplication logic
- Subscription filtering

---

**Status**: Phase 2 complete. Lists and members implemented with mutual exclusivity validation.
