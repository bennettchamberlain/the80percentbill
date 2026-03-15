# Campaign Recipient Resolution Documentation

## Overview

When a campaign starts, we resolve recipients and lock them into `campaign_recipients` table. This prevents segment drift, duplicate sending, and race conditions.

## Database Schema

### campaign_recipients table

```sql
CREATE TABLE campaign_recipients (
    id SERIAL PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES email_campaigns(id) ON DELETE CASCADE,
    contact_id INTEGER NULL REFERENCES email_management_contact(id) ON DELETE CASCADE,
    pledge_id INTEGER NULL REFERENCES pledge_pledge(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    scheduled_for TIMESTAMP NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    sent_at TIMESTAMP NULL,
    failed_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL,
    
    -- Constraints
    UNIQUE (campaign_id, contact_id),
    UNIQUE (campaign_id, pledge_id),
    CHECK (
        (contact_id IS NOT NULL AND pledge_id IS NULL) OR
        (contact_id IS NULL AND pledge_id IS NOT NULL)
    )
);

-- Indexes
CREATE INDEX campaign_recipients_campaign_status_idx ON campaign_recipients(campaign_id, status);
CREATE INDEX campaign_recipients_status_idx ON campaign_recipients(status);
CREATE INDEX campaign_recipients_scheduled_for_idx ON campaign_recipients(scheduled_for);
CREATE INDEX campaign_recipients_contact_idx ON campaign_recipients(contact_id);
CREATE INDEX campaign_recipients_pledge_idx ON campaign_recipients(pledge_id);
```

## Recipient Statuses

### pending
- Initial state after resolution
- Ready to be scheduled
- Waiting for batch processor

### scheduled
- Assigned to a batch
- Has `scheduled_for` timestamp
- Waiting for send time

### sending
- Currently being sent
- Held by send worker
- Prevents duplicate processing

### sent
- Successfully delivered
- Has `sent_at` timestamp
- Terminal success state

### failed
- Send attempt failed
- Has `failed_at` timestamp
- May retry based on policy

### skipped
- Intentionally not sent
- e.g., unsubscribed, invalid email
- Terminal skip state

## Resolution Rules

### Mutual Exclusivity
Each `CampaignRecipient` references **exactly one** source:
- `contact_id` is set, `pledge_id` is null, OR
- `pledge_id` is set, `contact_id` is null

**Never both. Never neither.**

### Deduplication
Recipients are deduplicated by email address (case-insensitive):
1. Collect recipients from segment (if set)
2. Collect recipients from contact_list (if set)
3. Deduplicate by email.lower()
4. Create one CampaignRecipient per unique email

### Preventing Duplicate Resolution
`unique_together` constraints prevent:
- Same contact in same campaign twice
- Same pledge in same campaign twice

If `resolve_campaign_recipients()` runs twice:
- First run: Creates N records
- Second run: Skips N records (already exist)

## Resolution Function

### resolve_campaign_recipients(campaign_id)

Resolves and locks in recipients for a campaign.

```python
from email_management.campaign_resolution import resolve_campaign_recipients

created, skipped = resolve_campaign_recipients(campaign_id)
print(f"Created {created} recipients, skipped {skipped} duplicates")
```

**Process:**
1. Load campaign
2. Validate campaign has targeting (segment or contact_list)
3. Resolve from segment (if set)
4. Resolve from contact_list (if set)
5. Deduplicate by email
6. Create CampaignRecipient records (status=pending)
7. Return (created_count, skipped_count)

**Returns:**
- `tuple`: (created_count, skipped_count)

**Raises:**
- `EmailCampaign.DoesNotExist`: Campaign not found
- `ValueError`: Campaign has no targeting

## Why Lock Recipients?

### Problem 1: Segment Drift
Without locking:
```
T0: Segment resolves to [alice@ex.com, bob@ex.com]
T1: Start sending...
T2: Segment rules change, now resolves to [bob@ex.com, charlie@ex.com]
T3: Continue sending...
Result: Alice doesn't get email (removed), Charlie gets email (added mid-send)
```

With locking:
```
T0: Resolve → Create CampaignRecipient records for alice, bob
T1-T3: Send to locked list (alice, bob)
Result: Consistent send to original resolution
```

### Problem 2: Duplicate Sending
Without locking:
```
T0: Campaign targets contact_list with 1000 members
T1: Worker A starts sending, processes 500
T2: Someone re-runs campaign start
T3: Worker B starts sending same campaign
Result: 500 people get duplicate emails
```

With locking:
```
T0: Resolve once → 1000 CampaignRecipient records
T1-T3: Workers send from locked table, no duplicates possible
```

### Problem 3: Race Conditions
Without locking:
```
T0: Two workers both resolve segment simultaneously
T1: Both start sending to same recipients
Result: Duplicate sends, wasted resources
```

With locking:
```
T0: One resolve call creates records with unique constraints
T1: Second resolve skips (records already exist)
Result: Single send per recipient
```

## Usage Examples

### Example 1: Resolve Segment Campaign

```python
from email_management.models import EmailCampaign
from email_management.campaign_resolution import resolve_campaign_recipients

campaign = EmailCampaign.objects.get(name='CA-30 Outreach')
# Campaign has segment set, no contact_list

created, skipped = resolve_campaign_recipients(campaign.id)
print(f"Resolved {created} recipients from segment")

# Check results
recipients = campaign.recipients.all()
for cr in recipients:
    print(f"  {cr.get_recipient().email} - {cr.status}")
```

### Example 2: Resolve Contact List Campaign

```python
campaign = EmailCampaign.objects.get(name='Newsletter Blast')
# Campaign has contact_list set, no segment

created, skipped = resolve_campaign_recipients(campaign.id)
print(f"Resolved {created} recipients from contact list")
```

### Example 3: Combined Targeting

```python
campaign = EmailCampaign.objects.get(name='Priority Outreach')
# Campaign has BOTH segment AND contact_list

created, skipped = resolve_campaign_recipients(campaign.id)
# Recipients from both sources, deduplicated
print(f"Resolved {created} unique recipients from segment + list")
```

### Example 4: Prevent Duplicate Resolution

```python
# First resolution
created1, skipped1 = resolve_campaign_recipients(campaign.id)
# → (100, 0)

# Second resolution (maybe by accident)
created2, skipped2 = resolve_campaign_recipients(campaign.id)
# → (0, 100) - all skipped, no duplicates created
```

## Integration with Campaign Lifecycle

### When to Resolve

Call `resolve_campaign_recipients()` when:
1. Campaign status changes from `draft` to `scheduled` or `sending`
2. User clicks "Start Campaign" button
3. Scheduler activates a scheduled campaign

**Do NOT resolve:**
- During campaign creation (stay in draft)
- On every campaign edit (resolution is expensive)
- Multiple times (creates duplicates unless carefully handled)

### After Resolution

Once resolved:
```python
campaign = EmailCampaign.objects.get(id=123)

# Check recipient count
total = campaign.recipients.count()
pending = campaign.recipients.filter(status='pending').count()
sent = campaign.recipients.filter(status='sent').count()

print(f"Total: {total}, Pending: {pending}, Sent: {sent}")
```

### Batch Processing (Phase 5)

The batch sender will:
1. Query `campaign.recipients.filter(status='pending')`
2. Batch them (e.g., 50 at a time)
3. Send emails
4. Update status to `sent` or `failed`

## Implementation Status

✅ CampaignRecipient model created
✅ Status enum (6 states)
✅ Mutual exclusivity validation
✅ unique_together constraints
✅ resolve_campaign_recipients() function
✅ Deduplication logic
✅ get_recipient() method

## Not Yet Implemented

⏳ Batch sending (Phase 5)
⏳ Automatic resolution on campaign start (Phase 5)
⏳ Retry logic for failed sends (Phase 5+)
⏳ Scheduled batch assignment (Phase 5)

---

**Status**: Phase 5 complete. Recipient resolution operational. Ready for batch sending implementation.
