# Campaign Monitoring Documentation

## Overview

Campaign monitoring provides real-time metrics, progress tracking, and detailed recipient information. Essential for understanding campaign performance and troubleshooting issues.

## Computed Metrics

### EmailCampaign Model Properties

All metrics are computed dynamically (not stored) from `campaign_recipients` table.

#### total_recipients
```python
campaign.total_recipients  # Total resolved recipients
```
Count of all CampaignRecipient records.

#### sent_count
```python
campaign.sent_count  # Successfully sent
```
Count where `status = 'sent'`.

#### failed_count
```python
campaign.failed_count  # Permanently failed
```
Count where `status = 'failed'` (after max retries).

#### pending_count
```python
campaign.pending_count  # Not yet sent
```
Count where `status = 'pending'`.

#### skipped_count
```python
campaign.skipped_count  # Intentionally skipped
```
Count where `status = 'skipped'` (e.g., unsubscribed).

#### success_rate
```python
campaign.success_rate  # Percentage (0-100 or None)
```
Formula: `(sent / (sent + failed)) * 100`

Returns `None` if no sends attempted yet.

**Example:**
- Sent: 950
- Failed: 50
- Success rate: 95.0%

#### progress_percentage
```python
campaign.progress_percentage  # Percentage (0-100)
```
Formula: `((sent + failed + skipped) / total) * 100`

Shows overall campaign completion.

**Example:**
- Total: 15,000
- Sent: 10,000
- Failed: 100
- Skipped: 50
- Progress: 67.7%

---

## API Functions

### get_campaign_summary(campaign_id)

Get comprehensive metrics for a campaign.

```python
from email_management.campaign_monitoring import get_campaign_summary

summary = get_campaign_summary(campaign_id=1)
```

**Returns:**
```python
{
    'campaign_id': 1,
    'campaign_name': 'March Fundraiser',
    'status': 'sending',
    'status_display': 'Sending',
    'total_recipients': 15000,
    'sent': 10000,
    'failed': 100,
    'pending': 4900,
    'skipped': 0,
    'success_rate': 99.0,
    'progress_percentage': 67.3,
    'daily_send_limit': 2000,
    'batch_size': 200,
    'created_at': '2026-03-01T00:00:00Z',
    'updated_at': '2026-03-10T15:30:00Z'
}
```

---

### get_all_campaigns_summary(status_filter=None)

Get summary of all campaigns.

```python
from email_management.campaign_monitoring import get_all_campaigns_summary

# All campaigns
all_summaries = get_all_campaigns_summary()

# Only sending campaigns
sending = get_all_campaigns_summary(status_filter='sending')
```

**Returns:** List of campaign summary dicts

---

### get_campaign_recipients(campaign_id, status=None, limit=None, offset=0)

Get paginated list of recipients with details.

```python
from email_management.campaign_monitoring import get_campaign_recipients

# First 100 recipients
recipients = get_campaign_recipients(campaign_id=1, limit=100)

# Only failed recipients
failed = get_campaign_recipients(campaign_id=1, status='failed')

# Pagination (page 2, 50 per page)
page2 = get_campaign_recipients(campaign_id=1, limit=50, offset=50)
```

**Returns:**
```python
{
    'campaign_id': 1,
    'campaign_name': 'March Fundraiser',
    'total': 15000,
    'offset': 0,
    'limit': 100,
    'recipients': [
        {
            'id': 12345,
            'email': 'user@example.com',
            'full_name': 'John Smith',
            'district': 'CA-30',
            'state': 'CA',
            'representative': 'Brad Sherman',
            'status': 'sent',
            'status_display': 'Sent',
            'sent_at': '2026-03-10T10:00:00Z',
            'failed_at': None,
            'attempts': 1,
            'version': 2,
            'version_subject': 'Support our cause'
        },
        # ... more recipients
    ]
}
```

---

### get_campaign_status_breakdown(campaign_id)

Get count of recipients by status.

```python
from email_management.campaign_monitoring import get_campaign_status_breakdown

breakdown = get_campaign_status_breakdown(campaign_id=1)
```

**Returns:**
```python
{
    'campaign_id': 1,
    'campaign_name': 'March Fundraiser',
    'breakdown': {
        'sent': 10000,
        'pending': 4900,
        'failed': 100
    },
    'total': 15000
}
```

---

### get_campaign_version_distribution(campaign_id)

Get count of recipients by version.

```python
from email_management.campaign_monitoring import get_campaign_version_distribution

dist = get_campaign_version_distribution(campaign_id=1)
```

**Returns:**
```python
{
    'campaign_id': 1,
    'campaign_name': 'March Fundraiser',
    'versions': [
        {
            'version_id': 1,
            'version_number': 1,
            'subject': 'Support our cause',
            'count': 5000
        },
        {
            'version_id': 2,
            'version_number': 2,
            'subject': 'URGENT: Support our cause',
            'count': 5000
        }
    ]
}
```

---

### get_campaign_progress_timeline(campaign_id)

Get sends per day over time.

```python
from email_management.campaign_monitoring import get_campaign_progress_timeline

timeline = get_campaign_progress_timeline(campaign_id=1)
```

**Returns:**
```python
{
    'campaign_id': 1,
    'campaign_name': 'March Fundraiser',
    'timeline': {
        '2026-03-01': 2000,
        '2026-03-02': 2000,
        '2026-03-03': 2000,
        '2026-03-04': 1500,
        '2026-03-05': 2000
    }
}
```

Useful for charting campaign velocity.

---

### get_failed_recipients_details(campaign_id)

Get detailed information about failed recipients.

```python
from email_management.campaign_monitoring import get_failed_recipients_details

failed = get_failed_recipients_details(campaign_id=1)
```

**Returns:**
```python
{
    'campaign_id': 1,
    'campaign_name': 'March Fundraiser',
    'failed_count': 100,
    'failed_recipients': [
        {
            'email': 'bounce@example.com',
            'full_name': 'Jane Doe',
            'district': 'CA-12',
            'attempts': 3,
            'failed_at': '2026-03-05T15:00:00Z',
            'error_message': 'SMTP timeout after 3 attempts'
        },
        # ... more failed recipients
    ]
}
```

---

### get_active_campaigns_overview()

Get overview of all active campaigns with estimated completion.

```python
from email_management.campaign_monitoring import get_active_campaigns_overview

active = get_active_campaigns_overview()
```

**Returns:**
```python
[
    {
        'campaign_id': 1,
        'campaign_name': 'March Fundraiser',
        'status': 'sending',
        'total_recipients': 15000,
        'sent': 10000,
        'pending': 4900,
        'success_rate': 99.0,
        'progress_percentage': 67.3,
        'daily_send_limit': 2000,
        'estimated_days_remaining': 2.5
    },
    # ... more active campaigns
]
```

**Estimated completion:**
- Formula: `pending / daily_send_limit`
- Null if unlimited (daily_send_limit = 0)

---

### search_recipients(campaign_id, query, limit=50)

Search for recipients by email, name, or district.

```python
from email_management.campaign_monitoring import search_recipients

# Search for CA-30
results = search_recipients(campaign_id=1, query='CA-30', limit=10)

# Search by email
results = search_recipients(campaign_id=1, query='gmail.com')
```

**Returns:** List of matching recipient dicts

---

## Integration with Email History

The monitoring functions integrate with the existing email history interface:

### Viewing Recipients in History Dashboard

```python
# Get recipients for display
recipients_data = get_campaign_recipients(
    campaign_id=1,
    limit=50,
    offset=0
)

# Render in template
for recipient in recipients_data['recipients']:
    print(f"{recipient['email']} - {recipient['status_display']}")
    print(f"  District: {recipient['district']}")
    print(f"  Sent: {recipient['sent_at']}")
    print(f"  Version: v{recipient['version']}")
```

### Filtering by Status

```python
# Show only failed sends
failed_recipients = get_campaign_recipients(
    campaign_id=1,
    status='failed'
)

# Show successful sends
sent_recipients = get_campaign_recipients(
    campaign_id=1,
    status='sent'
)
```

---

## Example Use Cases

### Dashboard Overview

```python
# Get all active campaigns
active_campaigns = get_active_campaigns_overview()

for campaign in active_campaigns:
    print(f"{campaign['campaign_name']}:")
    print(f"  Progress: {campaign['progress_percentage']:.1f}%")
    print(f"  Success rate: {campaign['success_rate']:.1f}%")
    print(f"  ETA: {campaign['estimated_days_remaining']} days")
```

### Campaign Detail View

```python
# Full metrics
summary = get_campaign_summary(campaign_id=1)

# Status breakdown
breakdown = get_campaign_status_breakdown(campaign_id=1)

# Recent sends
recent = get_campaign_recipients(campaign_id=1, limit=20)

# Version distribution
versions = get_campaign_version_distribution(campaign_id=1)
```

### Troubleshooting Failed Sends

```python
# Get all failed recipients
failed = get_failed_recipients_details(campaign_id=1)

print(f"Failed: {failed['failed_count']}")

# Group by error message
error_counts = {}
for recipient in failed['failed_recipients']:
    error = recipient['error_message']
    error_counts[error] = error_counts.get(error, 0) + 1

print("Error patterns:")
for error, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"  {error}: {count}")
```

### Progress Tracking

```python
# Daily progress chart
timeline = get_campaign_progress_timeline(campaign_id=1)

print("Sends per day:")
for date, count in timeline['timeline'].items():
    print(f"  {date}: {count}")
```

---

## Performance Considerations

### Caching

Metrics are computed on-demand. For high-traffic dashboards, consider caching:

```python
from django.core.cache import cache

def get_cached_summary(campaign_id):
    cache_key = f'campaign_summary_{campaign_id}'
    summary = cache.get(cache_key)
    
    if not summary:
        summary = get_campaign_summary(campaign_id)
        cache.set(cache_key, summary, timeout=60)  # 1 minute
    
    return summary
```

### Pagination

Always use pagination for large recipient lists:

```python
# Good
recipients = get_campaign_recipients(campaign_id=1, limit=50)

# Bad (loads all 15,000)
recipients = get_campaign_recipients(campaign_id=1)
```

### Database Indexes

Existing indexes optimize monitoring queries:
- `campaign_recipients(campaign_id, status)`
- `campaign_recipients(sent_at)`
- `campaign_recipients(campaign_version_id)`

---

## Implementation Status

✅ Campaign metrics properties (total_recipients, sent_count, etc.)
✅ get_metrics_summary() method
✅ get_recipients_list() method
✅ get_campaign_summary()
✅ get_all_campaigns_summary()
✅ get_campaign_recipients() (paginated)
✅ get_campaign_status_breakdown()
✅ get_campaign_version_distribution()
✅ get_campaign_progress_timeline()
✅ get_failed_recipients_details()
✅ get_active_campaigns_overview()
✅ search_recipients()

## Not Yet Implemented

⏳ Web UI dashboard
⏳ Real-time progress charts
⏳ Export to CSV
⏳ Email notifications on completion
⏳ Slack/Discord alerts
⏳ Custom metric alerts (e.g., success rate < 95%)

---

**Status**: Phase 8 complete. Campaign monitoring operational with comprehensive metrics and recipient details.
