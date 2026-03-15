# Campaign Core Structure Documentation

## Overview

Email campaigns provide the core structure for sending targeted messages to recipients. Campaigns reference templates (read-only) and target recipients via segments or contact lists.

## Database Schema

### email_campaigns table

```sql
CREATE TABLE email_campaigns (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    template_id INTEGER NOT NULL REFERENCES email_management_emailtemplate(id) ON DELETE PROTECT,
    segment_id INTEGER NULL REFERENCES segments(id) ON DELETE SET NULL,
    contact_list_id INTEGER NULL REFERENCES contact_lists(id) ON DELETE SET NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    daily_send_limit INTEGER NOT NULL DEFAULT 1000,
    batch_size INTEGER NOT NULL DEFAULT 50,
    start_date TIMESTAMP NULL,
    created_by_id INTEGER NOT NULL REFERENCES email_management_emailuser(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE INDEX email_campaigns_status_idx ON email_campaigns(status);
CREATE INDEX email_campaigns_start_date_idx ON email_campaigns(start_date);
CREATE INDEX email_campaigns_created_at_idx ON email_campaigns(created_at DESC);
```

## Campaign Fields

### Basic Information
- **name**: Campaign display name
- **description**: Optional campaign notes/purpose

### Configuration
- **template_id**: Reference to email template (required, protected)
  - Templates are read-only from campaign perspective
  - Deleting a template is blocked if campaigns reference it
  - Template changes don't affect sent emails

### Recipient Targeting
- **segment_id**: Target via dynamic segment (nullable)
- **contact_list_id**: Target via static list (nullable)
- At least one of `segment_id` or `contact_list_id` should be set
- Both can be set to combine targeting methods

### Sending Controls
- **daily_send_limit**: Max emails per day (default: 1000, 0 = unlimited)
- **batch_size**: Emails per batch (default: 50)
- **start_date**: When to begin sending (null = immediate when started)

### Status & Lifecycle
- **status**: Current campaign state (see statuses below)
- **created_by_id**: User who created the campaign
- **created_at**, **updated_at**: Timestamps

## Campaign Statuses

### draft
- Initial state when created
- Campaign can be edited freely
- Recipients not yet resolved
- Can transition to: scheduled, sending (if immediate)

### scheduled  
- Campaign queued for future sending
- Waiting for start_date to arrive
- Can still be edited
- Can transition to: sending, draft, cancelled

### sending
- Actively processing batches
- Sending emails to resolved recipients
- Cannot be edited
- Can transition to: paused, completed, cancelled

### paused
- Temporarily stopped mid-send
- Can resume where it left off
- Cannot be edited
- Can transition to: sending, cancelled

### completed
- All emails sent successfully
- Terminal state (cannot change)
- Statistics finalized

### cancelled
- Campaign permanently stopped
- Terminal state (cannot change)
- May have partial sends

## Campaign Methods

### State Checks

**can_edit() → bool**
- Returns True if campaign can be modified
- Editable states: draft, scheduled

**can_start() → bool**
- Returns True if campaign can be started
- Requires: status=draft AND (segment OR contact_list)

**can_pause() → bool**
- Returns True if campaign can be paused
- Pausable states: sending

**can_resume() → bool**
- Returns True if campaign can be resumed
- Resumable states: paused

**can_cancel() → bool**
- Returns True if campaign can be cancelled
- Cancellable states: draft, scheduled, sending, paused

## Recipient Targeting Rules

### Via Segment Only
```python
campaign = EmailCampaign.objects.create(
    name='CA-30 Outreach',
    segment=ca30_segment,
    contact_list=None,
    ...
)
# Recipients resolved from segment filters
```

### Via Contact List Only
```python
campaign = EmailCampaign.objects.create(
    name='Newsletter Blast',
    segment=None,
    contact_list=newsletter_list,
    ...
)
# Recipients from list members
```

### Combined Targeting
```python
campaign = EmailCampaign.objects.create(
    name='Priority California',
    segment=california_segment,
    contact_list=priority_list,
    ...
)
# Recipients from BOTH segment AND list (deduplicated)
```

## Template Relationship

Campaigns **reference** templates, they don't copy them:

- Template FK uses `on_delete=PROTECT`
- Cannot delete a template if campaigns reference it
- Template changes don't affect previously sent emails
- Campaign stores reference, not content

This differs from some systems that copy template content at campaign creation time.

## Sending Controls

### Daily Send Limit
- Prevents overwhelming mail servers
- Enforced at batch scheduler level (Phase 5)
- `0` = unlimited
- Example: 1000 emails/day with batch_size=50 = 20 batches

### Batch Size
- How many emails to send in one operation
- Smaller batches = better rate limiting
- Larger batches = faster completion
- Typical range: 25-100

### Start Date
- When to begin sending
- `null` = start immediately when status changes to "sending"
- Future date = schedule for later
- Scheduler (Phase 5) monitors this field

## Usage Examples

### Create Draft Campaign

```python
from email_management.models import EmailCampaign, EmailUser, EmailTemplate, Segment

campaign = EmailCampaign.objects.create(
    name='March Fundraiser',
    description='Monthly fundraising email to all constituents',
    template=EmailTemplate.objects.get(name='fundraiser-template'),
    segment=Segment.objects.get(name='All Active Subscribers'),
    daily_send_limit=2000,
    batch_size=50,
    created_by=EmailUser.objects.get(email='admin@example.com')
)
# Status: draft
# Can edit, can start
```

### Schedule Campaign

```python
from django.utils import timezone
from datetime import timedelta

campaign.start_date = timezone.now() + timedelta(days=3)
campaign.status = EmailCampaign.STATUS_SCHEDULED
campaign.save()
# Will begin sending in 3 days
```

### Check Campaign State

```python
if campaign.can_start():
    print("Ready to send!")
    print(f"Targeting: {campaign.segment or campaign.contact_list}")
    print(f"Batch size: {campaign.batch_size}")
    print(f"Daily limit: {campaign.daily_send_limit}")
```

## Implementation Status

✅ EmailCampaign model created
✅ Status enum with 6 states
✅ Template reference (PROTECT)
✅ Segment and contact_list targeting
✅ Daily limit and batch size controls
✅ State check methods
✅ Indexes on status, start_date, created_at

## Not Yet Implemented

⏳ Recipient resolution logic (Phase 4)
⏳ Batch sending engine (Phase 5)
⏳ Status transitions/state machine (Phase 5)
⏳ Campaign statistics tracking (Phase 5+)
⏳ Scheduling system (Phase 5)

---

**Status**: Phase 4 Step 1 complete. Campaign core structure operational. Ready for recipient resolution implementation.
