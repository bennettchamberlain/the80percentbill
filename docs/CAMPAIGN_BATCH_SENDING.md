# Campaign Batch Sending and Scheduling Documentation

## Overview

Campaigns may contain thousands of recipients. The batch sending system processes campaigns gradually, respecting daily limits and batch sizes, with automatic retry logic.

## Architecture

### Daily Limits
Each campaign has a `daily_send_limit`:
- **0** = Unlimited (send as fast as possible)
- **N** = Send max N emails per calendar day

**Example:**
- Campaign: 15,000 recipients
- Daily limit: 2,000
- Result: ~8 days to complete

### Batch Processing
Emails are sent in batches of `batch_size` (default: 50):
- Prevents overwhelming SMTP servers
- Enables better rate limiting
- Allows graceful error recovery

**Example:**
- Daily limit: 2,000
- Batch size: 200
- Result: 10 batches per day

### Retry Logic
Failed sends retry up to 3 times:
- Attempt 1: Initial send
- Attempt 2: Retry (if transient failure)
- Attempt 3: Final retry
- After 3 failures: Mark as failed permanently

## Scheduler Job

### process_campaign_batches()

Main scheduler function, should run periodically (every 15 minutes recommended).

```python
from email_management.campaign_batch import process_campaign_batches

results = process_campaign_batches()
```

**Process:**
1. Find campaigns with status = `sending`
2. For each campaign:
   - Check if start_date reached
   - Calculate daily limit remaining
   - Get pending recipients (up to daily limit)
   - Process in batches
   - Update recipient statuses
3. Mark campaign `completed` when no pending recipients remain

**Returns:**
```python
{
    'campaigns_processed': 2,
    'total_sent': 150,
    'total_failed': 2,
    'campaigns_completed': ['Newsletter March'],
    'errors': []
}
```

### Django Management Command

```bash
python manage.py process_campaigns
```

This command runs the scheduler once. Set up a cron job for periodic execution:

```bash
# Run every 15 minutes
*/15 * * * * cd /path/to/the80percentbill && source venv/bin/activate && python manage.py process_campaigns
```

## Campaign Lifecycle Functions

### start_campaign(campaign_id)

Start a campaign manually.

```python
from email_management.campaign_batch import start_campaign

result = start_campaign(campaign_id=1)
# Returns:
# {
#     'campaign_id': 1,
#     'campaign_name': 'March Fundraiser',
#     'recipients': 15000,
#     'daily_limit': 2000,
#     'batch_size': 200,
#     'status': 'sending'
# }
```

**Process:**
1. Validate campaign can start (status=draft, has targeting)
2. Resolve recipients if not already done
3. Change status to `sending`

**Raises:**
- `ValueError`: If campaign can't be started

### pause_campaign(campaign_id)

Pause a running campaign temporarily.

```python
from email_management.campaign_batch import pause_campaign

result = pause_campaign(campaign_id=1)
# Campaign status → paused
# Batch processor skips paused campaigns
```

### resume_campaign(campaign_id)

Resume a paused campaign.

```python
from email_management.campaign_batch import resume_campaign

result = resume_campaign(campaign_id=1)
# Campaign status → sending
# Will resume on next batch processor run
```

### cancel_campaign(campaign_id)

Cancel a campaign permanently.

```python
from email_management.campaign_batch import cancel_campaign

result = cancel_campaign(campaign_id=1)
# Returns:
# {
#     'campaign_id': 1,
#     'campaign_name': 'March Fundraiser',
#     'status': 'cancelled',
#     'sent_before_cancel': 5000,
#     'pending_at_cancel': 10000
# }
```

## Template Rendering

Templates support variable substitution:

### Available Variables
- `{{email}}` - Recipient email
- `{{full_name}}` - Full name
- `{{display_name}}` - Display name
- `{{district}}` - Congressional district (from metadata)
- `{{state}}` - State (from metadata)
- `{{representative}}` - Representative name (from metadata)
- Any custom metadata keys: `{{custom_field}}`

### Example Template

**Subject:**
```
Action needed in {{district}}
```

**Body:**
```html
<p>Hi {{full_name}},</p>

<p>Your representative in {{district}}, {{representative}}, needs to hear from you.</p>

<p>Email: {{email}}</p>
```

**Rendered for recipient:**
```
Subject: Action needed in CA-30

Hi Bennett Chamberlain,

Your representative in CA-30, Brad Sherman, needs to hear from you.

Email: chamberlain.bennett@gmail.com
```

## Daily Limit Calculation

### get_daily_limit_remaining(campaign)

Returns how many emails can still be sent today.

```python
from email_management.campaign_batch import get_daily_limit_remaining

remaining = get_daily_limit_remaining(campaign)
# Returns:
# - -1 if unlimited (daily_send_limit = 0)
# - N if N emails remaining today
# - 0 if daily limit reached
```

**Logic:**
1. Get today's start (midnight in server timezone)
2. Count recipients with status=sent and sent_at >= today_start
3. Return daily_send_limit - sent_today

**Example:**
```
Campaign daily_send_limit: 2000
Sent today: 1500
Remaining: 500
```

## Retry Logic

### should_retry(recipient_record, max_attempts=3)

Determines if a failed send should be retried.

```python
from email_management.campaign_batch import should_retry

if should_retry(recipient_record):
    # Retry (mark as pending)
else:
    # Give up (mark as failed permanently)
```

**Default behavior:**
- Max attempts: 3
- Retry: attempts < 3
- Give up: attempts >= 3

**Status flow:**
```
pending → sending → [FAIL] → pending (retry)
pending → sending → [FAIL] → pending (retry)
pending → sending → [FAIL] → failed (permanent)
```

## Example Scenarios

### Scenario 1: Large Campaign with Daily Limit

**Setup:**
- Campaign: 15,000 recipients
- Daily limit: 2,000
- Batch size: 200

**Day 1:**
- 00:00: Campaign started (status=sending)
- 00:15: Process 200 (batch 1)
- 00:30: Process 200 (batch 2)
- ...
- 03:00: Process 200 (batch 10) → 2,000 sent
- 03:15: Daily limit reached, stop for today

**Day 2:**
- 00:00: Daily limit resets
- 00:15: Process 200 (batch 11)
- ...
- 03:15: 2,000 more sent (total 4,000)

**Day 8:**
- 00:15: Process last 1,000
- Campaign status → completed

### Scenario 2: Unlimited Campaign (Fast Send)

**Setup:**
- Campaign: 500 recipients
- Daily limit: 0 (unlimited)
- Batch size: 50

**Execution:**
- 00:15: Process 50 (batch 1)
- 00:30: Process 50 (batch 2)
- ...
- 02:30: Process 50 (batch 10) → 500 sent
- Campaign status → completed

### Scenario 3: Retries After Transient Failure

**Recipient record:**
- Email: user@example.com
- Attempts: 0

**Attempt 1 (00:15):**
- Status: pending → sending → failed
- Attempts: 1
- Reason: SMTP timeout
- Action: should_retry() = True → status = pending

**Attempt 2 (00:30):**
- Status: pending → sending → sent ✓
- Attempts: 2

**Result:** Successfully sent after 1 retry

### Scenario 4: Pause/Resume

**Timeline:**
- 00:00: Campaign started, 1000 recipients pending
- 00:15: Send 200 → 800 pending
- 00:30: Send 200 → 600 pending
- **00:45: User pauses campaign**
- 01:00: Batch processor skips (status=paused)
- 01:15: Batch processor skips (status=paused)
- **01:30: User resumes campaign**
- 01:45: Send 200 → 400 pending (resumes from where it left off)

## Implementation Status

✅ Batch processing engine
✅ Daily limit enforcement
✅ Batch size support
✅ Retry logic (max 3 attempts)
✅ Template rendering with variables
✅ Campaign lifecycle functions (start/pause/resume/cancel)
✅ Django management command
✅ Logging and error handling

## Integration Points

### SMTP Configuration
- Uses first active SMTPConfiguration
- Falls back to error if none active
- Supports Brevo or any SMTP server

### Email Logging
- Each send creates EmailLog record
- Tracks success/failure
- Stores error messages

### Recipient Status Tracking
- pending → scheduled → sending → sent/failed
- sent_at and failed_at timestamps
- attempts counter

## Monitoring

### Check Campaign Progress

```python
from email_management.models import EmailCampaign

campaign = EmailCampaign.objects.get(id=1)

# Overall stats
total = campaign.recipients.count()
sent = campaign.recipients.filter(status='sent').count()
failed = campaign.recipients.filter(status='failed').count()
pending = campaign.recipients.filter(status='pending').count()

print(f"Progress: {sent}/{total} sent ({sent/total*100:.1f}%)")
print(f"Failed: {failed}")
print(f"Pending: {pending}")
```

### Check Daily Limit

```python
from email_management.campaign_batch import get_daily_limit_remaining

remaining = get_daily_limit_remaining(campaign)
print(f"Can send {remaining} more emails today")
```

### View Recent Sends

```python
from email_management.models import EmailLog

recent = EmailLog.objects.filter(
    campaign=campaign
).order_by('-created_at')[:10]

for log in recent:
    print(f"{log.recipient_email}: {log.get_status_display()} at {log.sent_at}")
```

## Not Yet Implemented

⏳ Web UI for campaign control (start/pause/resume buttons)
⏳ Real-time progress dashboard
⏳ Scheduled campaigns (start_date enforcement in UI)
⏳ Email preview before send
⏳ A/B testing
⏳ Bounce handling
⏳ Unsubscribe tracking

---

**Status**: Phase 6 complete. Campaign batch sending and scheduling operational. Ready for production use with cron setup.
