# Campaign Versioning Documentation

## Overview

Campaigns can be edited while sending. Campaign versioning ensures:
- Recipients already sent keep their original version
- New sends use the updated version
- No double sending or content inconsistency
- Complete audit trail of all changes

## Problem Statement

**Without versioning:**
```
T0: Campaign starts, subject = "Original Subject"
T1: 1000 emails sent with "Original Subject"
T2: Campaign edited, subject = "Updated Subject"
T3: 1000 more emails sent with "Updated Subject"
Result: Inconsistent experience, no record of what each recipient received
```

**With versioning:**
```
T0: Campaign starts, creates v1 (subject = "Original Subject")
T1: 1000 emails sent, recipients tied to v1
T2: Campaign edited, creates v2 (subject = "Updated Subject")
T3: 1000 more emails sent, recipients tied to v2
Result: Each recipient knows which version they received, full audit trail
```

## Database Schema

### campaign_versions table

```sql
CREATE TABLE campaign_versions (
    id SERIAL PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES email_campaigns(id) ON DELETE CASCADE,
    subject VARCHAR(255) NOT NULL,
    html_body TEXT NOT NULL,
    plain_body TEXT,
    created_at TIMESTAMP NOT NULL,
    created_by_id INTEGER NULL REFERENCES email_management_emailuser(id) ON DELETE SET NULL,
    notes TEXT
);

CREATE INDEX campaign_versions_campaign_created_idx ON campaign_versions(campaign_id, created_at DESC);
CREATE INDEX campaign_versions_created_idx ON campaign_versions(created_at);
```

### campaign_recipients.campaign_version_id

```sql
ALTER TABLE campaign_recipients ADD COLUMN campaign_version_id INTEGER NULL
    REFERENCES campaign_versions(id) ON DELETE SET NULL;
```

**Field behavior:**
- `NULL` = Not yet sent (no version assigned)
- `<id>` = Sent with specific version

## Version Lifecycle

### 1. Campaign Creation
Campaign is created in draft status. **No version yet.**

### 2. Campaign Start
```python
start_campaign(campaign_id)
```
- Creates initial version (v1) from template
- Campaign status → sending
- Recipients resolved (if not done)

### 3. Batch Sending
```python
process_campaign_batches()
```
- Gets latest version
- Sends to pending recipients
- Assigns `campaign_version_id` when sent

### 4. Campaign Edit (While Sending)
```python
update_campaign_content(
    campaign_id,
    subject='New subject',
    notes='Updated for better engagement'
)
```
- Creates new version (v2)
- **Does NOT affect already-sent recipients**
- Future sends use v2

### 5. More Sending
Next batch processing:
- Gets latest version (v2)
- Sends to remaining pending recipients
- Assigns v2 to those recipients

### 6. Audit & Comparison
```python
get_version_stats(campaign_id)
compare_versions(v1_id, v2_id)
```
- See how many recipients got each version
- Compare content between versions

## API Reference

### create_campaign_version(campaign_id, notes='', user=None)

Create a new version from current template.

```python
from email_management.campaign_versioning import create_campaign_version

version = create_campaign_version(
    campaign_id=1,
    notes='Updated call-to-action'
)
print(f"Created v{version.version_number}")
```

**Returns:** CampaignVersion instance

---

### get_latest_version(campaign_id)

Get the most recent version.

```python
from email_management.campaign_versioning import get_latest_version

latest = get_latest_version(campaign_id=1)
print(f"Latest: v{latest.version_number} - {latest.subject}")
```

**Returns:** CampaignVersion instance (most recent) or None

---

### ensure_campaign_has_version(campaign_id)

Ensure campaign has at least one version (creates if needed).

```python
from email_management.campaign_versioning import ensure_campaign_has_version

version = ensure_campaign_has_version(campaign_id=1)
# Always returns a version (creates initial if none exist)
```

**Returns:** CampaignVersion instance

---

### update_campaign_content(campaign_id, subject=None, html_body=None, plain_body=None, notes='', user=None)

Safe way to edit a campaign (creates new version).

```python
from email_management.campaign_versioning import update_campaign_content

new_version = update_campaign_content(
    campaign_id=1,
    subject='UPDATED: Support our cause',
    notes='Made subject more urgent'
)
print(f"Created v{new_version.version_number}")
```

**Behavior:**
- Omitted fields keep current values
- Creates new version immediately
- Future sends use new version
- Past sends unchanged

**Returns:** CampaignVersion instance (new)

---

### get_version_stats(campaign_id)

Get statistics about all versions.

```python
from email_management.campaign_versioning import get_version_stats

stats = get_version_stats(campaign_id=1)
print(f"Total versions: {stats['total_versions']}")

for v in stats['versions']:
    print(f"v{v['version_number']}: {v['subject']} ({v['sends_count']} sends)")
```

**Returns:**
```python
{
    'total_versions': 3,
    'versions': [
        {
            'id': 3,
            'version_number': 3,
            'created_at': '2026-03-15T08:00:00Z',
            'created_by': 'user@example.com',
            'sends_count': 5000,
            'notes': 'Final urgency update',
            'subject': 'URGENT: Support our cause'
        },
        # ... older versions
    ]
}
```

---

### compare_versions(version1_id, version2_id)

Compare two versions.

```python
from email_management.campaign_versioning import compare_versions

diff = compare_versions(v1_id=1, v2_id=2)

if diff['changes']['subject_changed']:
    print(f"Subject changed:")
    print(f"  v1: {diff['version1']['subject']}")
    print(f"  v2: {diff['version2']['subject']}")
```

**Returns:**
```python
{
    'version1': {
        'id': 1,
        'number': 1,
        'subject': 'Original',
        'html_body': '...',
        'plain_body': '...'
    },
    'version2': {
        'id': 2,
        'number': 2,
        'subject': 'Updated',
        'html_body': '...',
        'plain_body': '...'
    },
    'changes': {
        'subject_changed': True,
        'html_changed': False,
        'plain_changed': False
    }
}
```

---

### rollback_to_version(campaign_id, version_id, user=None)

Roll back to a previous version.

```python
from email_management.campaign_versioning import rollback_to_version

new_version = rollback_to_version(
    campaign_id=1,
    version_id=1,  # Roll back to v1
    user=user
)
print(f"Rolled back. Created v{new_version.version_number} with v1 content")
```

**Behavior:**
- Creates NEW version with old content
- Does NOT delete intervening versions (keeps history)
- Future sends use rolled-back content

**Returns:** CampaignVersion instance (new version with old content)

---

## Integration with Batch Sending

The batch processor automatically handles versioning:

```python
def process_batch(campaign, recipients):
    # Get latest version
    latest_version = ensure_campaign_has_version(campaign.id)
    
    for recipient_record in recipients:
        # Render using latest version
        subject = render_template(latest_version.subject, recipient)
        html_body = render_template(latest_version.html_body, recipient)
        
        # Send email
        email_service.send_email(...)
        
        # Store which version was sent
        recipient_record.campaign_version = latest_version
        recipient_record.status = 'sent'
        recipient_record.save()
```

**Key points:**
- Version fetched ONCE per batch (all recipients in batch get same version)
- Version assigned when status changes to 'sent'
- Recipients retain version reference forever

## Example Scenarios

### Scenario 1: Edit Before Any Sends

**Timeline:**
- Campaign created (draft)
- User edits subject
- Campaign started

**Behavior:**
- start_campaign() creates v1 with edited content
- All recipients get v1
- No wasted versions

---

### Scenario 2: Edit Mid-Campaign

**Timeline:**
- Campaign started → v1 created
- 5000/15000 sent with v1
- User edits subject → v2 created
- 10000 more sent with v2

**Result:**
```sql
SELECT campaign_version_id, COUNT(*) 
FROM campaign_recipients 
WHERE campaign_id = 1 
GROUP BY campaign_version_id;

campaign_version_id | count
--------------------|-------
1                   | 5000
2                   | 10000
```

---

### Scenario 3: Multiple Edits

**Timeline:**
- Day 1: Start → v1 (2000 sent)
- Day 2: Edit → v2 (2000 sent)
- Day 3: Edit → v3 (2000 sent)
- Day 4: Edit → v4 (2000 sent)

**Result:**
- Each recipient tied to specific version
- Full audit trail
- Can see evolution of campaign

---

### Scenario 4: Rollback After Bad Edit

**Timeline:**
- v1: "Support our cause" (5000 sent)
- v2: "URGENT!!!" (1000 sent) ← Typo!
- rollback_to_version(v1) → v3: "Support our cause" (9000 sent)

**Result:**
- v1: 5000 sends
- v2: 1000 sends (with typo)
- v3: 9000 sends (corrected)
- History preserved, v2 not deleted

---

## Audit & Reporting

### View All Versions for Campaign

```python
versions = CampaignVersion.objects.filter(campaign_id=1).order_by('created_at')

for v in versions:
    print(f"v{v.version_number} - {v.created_at}")
    print(f"  Subject: {v.subject}")
    print(f"  Sends: {v.sends_count}")
    print(f"  Notes: {v.notes}")
```

### View Recipients by Version

```python
from email_management.models import CampaignRecipient

# Get all recipients who got v2
v2_recipients = CampaignRecipient.objects.filter(
    campaign_id=1,
    campaign_version_id=2,
    status='sent'
)

for r in v2_recipients:
    recipient = r.get_recipient()
    print(f"{recipient.email} received v2 at {r.sent_at}")
```

### Version Distribution

```python
from django.db.models import Count

distribution = CampaignRecipient.objects.filter(
    campaign_id=1,
    status='sent'
).values('campaign_version__version_number').annotate(
    count=Count('id')
)

for entry in distribution:
    print(f"v{entry['campaign_version__version_number']}: {entry['count']} recipients")
```

## Model Properties

### CampaignVersion.version_number

```python
version = CampaignVersion.objects.get(id=1)
print(version.version_number)  # 1, 2, 3, etc.
```

Calculated property (not stored). Counts versions created before/at this one.

### CampaignVersion.sends_count

```python
version = CampaignVersion.objects.get(id=1)
print(version.sends_count)  # Number of recipients sent with this version
```

Counts CampaignRecipient records with campaign_version_id = this version.

### CampaignVersion.get_content_preview(max_length=100)

```python
version = CampaignVersion.objects.get(id=1)
preview = version.get_content_preview(max_length=50)
print(preview)  # "Hi {{full_name}}, we need your support..."
```

Strips HTML tags, truncates to max_length.

## Implementation Status

✅ CampaignVersion model
✅ campaign_recipients.campaign_version_id field
✅ Version creation logic
✅ Version selection during sending
✅ Update campaign content (creates new version)
✅ Ensure campaign has version
✅ Get latest version
✅ Version stats
✅ Compare versions
✅ Rollback to previous version
✅ Integration with batch sender

## Not Yet Implemented

⏳ Web UI for version management
⏳ Visual diff viewer (HTML comparison)
⏳ Version approval workflow
⏳ Version scheduling (send v2 starting Monday)
⏳ A/B testing (50% get v1, 50% get v2)

---

**Status**: Phase 7 complete. Campaign versioning operational. Safe to edit campaigns while sending.
