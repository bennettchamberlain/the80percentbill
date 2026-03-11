# Email Marketing Admin Portal - The 80% Bill

Email management system for sending marketing emails to users via Brevo SMTP relay.

## Overview

This is an **admin portal** for managing email campaigns, contacts, and sending bulk emails. All contact data and campaign tracking is stored in our database. Brevo is only used as the SMTP relay for actually sending emails.

## Access

- **URL:** http://localhost:8008/email/ (or https://the80percentbill.com/email/ when deployed)
- **Login:** admin@example.com / admin123 (change in production!)

## Setup

```bash
# Set up Brevo SMTP configuration
python manage.py setup_brevo

# This creates:
# - SMTP configuration with Brevo credentials
# - Tests the connection
# - Sets as default configuration
```

## Brevo Credentials

```
SMTP Server: smtp-relay.brevo.com
Port: 587
Login: a473e7001@smtp-brevo.com
Password: x0zDSmTKfNtn7HrR
TLS: Enabled
```

## Features

### 1. Contact Management

**Add contacts via Django admin:**
- Go to `/admin/email_management/contact/`
- Click "Add Contact"
- Fill in email, name, district, state, etc.
- Contacts are auto-subscribed

**Import contacts** (future):
- CSV upload
- API integration
- Pledge form integration

**Track engagement:**
- Emails sent count
- Last email sent date
- Custom data (JSON field for any extra attributes)

### 2. Contact Lists (Segmentation)

**Create lists:**
- Go to `/admin/email_management/contactlist/`
- Name your list (e.g., "NY Residents", "Signed Pledge", "District CA-12")
- Add contacts to the list
- Use lists to target specific campaigns

**Example lists:**
- All subscribers
- By state
- By district
- Pledge signers
- Engaged users (opened recent emails)

### 3. Email Templates

**Create reusable templates:**
- Subject line
- HTML body
- Plain text body
- Define variables

**Template variables:**
- `{{first_name}}` - Contact's first name
- `{{last_name}}` - Contact's last name
- `{{email}}` - Contact's email
- `{{district}}` - Contact's district code
- `{{state}}` - Contact's state
- Any custom field from `custom_data`

**Example template:**
```
Subject: Take Action, {{first_name}}!

Hi {{first_name}},

Your representative in {{district}} needs to hear from you...

Best,
The 80% Bill Team
```

### 4. Email Campaigns

**Create a campaign:**
1. Go to `/admin/email_management/emailcampaign/`
2. Click "Add Email Campaign"
3. Fill in:
   - Name (internal reference)
   - SMTP configuration (select Brevo)
   - Optional: Select a template
   - Subject
   - HTML body and/or plain text body
   - Select contact lists to send to
   - Status: draft/scheduled/sending
   - Optional: Schedule for later

**Send a campaign:**
```python
from email_management.models import EmailCampaign, SMTPConfiguration
from email_management.email_service import EmailSendingService

# Get campaign
campaign = EmailCampaign.objects.get(id=1)

# Get SMTP config
smtp_config = SMTPConfiguration.objects.get(is_default=True)

# Send
service = EmailSendingService(smtp_config)
results = service.send_campaign(campaign)

# Results:
# {'total': 100, 'sent': 95, 'failed': 5}
```

**Campaign statuses:**
- `draft` - Not yet ready to send
- `scheduled` - Will send at scheduled_at time
- `sending` - Currently sending
- `sent` - Completed
- `paused` - Paused mid-send
- `failed` - Failed to send

### 5. Email Logs

**Track every email sent:**
- Recipient
- Subject
- Campaign (if part of one)
- Status: pending/sending/sent/failed/bounced
- Error message (if failed)
- Sent timestamp

**View logs:**
- Go to `/admin/email_management/emaillog/`
- Filter by status, date, recipient
- See exactly what was sent to whom and when

### 6. Sending Service

**The EmailSendingService handles:**
- Connecting to SMTP relay
- Formatting emails (MIME multipart)
- Replacing template variables
- Logging every send
- Error handling
- Contact engagement tracking

**How sending works:**
1. Get contacts from selected lists
2. Filter to only subscribed contacts
3. For each contact:
   - Replace variables in subject/body
   - Send via SMTP
   - Log the send (success or failure)
   - Update contact stats
4. Update campaign stats (sent_count, failed_count)

## Admin Workflow

### Typical Campaign Flow:

1. **Add contacts**
   - Import from CSV or add manually
   - Or automatically from pledge form

2. **Create contact lists**
   - Segment by state, district, or custom criteria
   - Example: "California Residents" list

3. **Create email template**
   - Write subject and body
   - Use variables: {{first_name}}, {{district}}, etc.
   - Save for reuse

4. **Create campaign**
   - Select template (or write custom)
   - Select contact lists to send to
   - Preview: see how many recipients
   - Save as draft

5. **Send campaign**
   - Via admin: change status to "sending"
   - Or via management command/scheduled task
   - Monitor progress in admin

6. **Review logs**
   - Check EmailLog for any failures
   - View engagement stats
   - Adjust future campaigns

## Management Commands

```bash
# Set up Brevo SMTP
python manage.py setup_brevo

# Future commands (to implement):
# python manage.py send_campaign <campaign_id>
# python manage.py import_contacts <csv_file>
# python manage.py sync_pledge_contacts
```

## Data We Track (Not in Brevo)

✅ **Our Database:**
- All contacts with custom fields
- Contact lists/segments
- Email templates
- Campaign details
- Every email sent (logs)
- Engagement stats
- Unsubscribe status

❌ **Brevo:**
- Nothing! Just SMTP relay

## Security Considerations

**Production checklist:**
1. Change admin password
2. Store Brevo credentials in environment variables
3. Use HTTPS for /email/ page
4. Encrypt SMTP password in database
5. Add rate limiting for sends
6. Implement unsubscribe links in all emails
7. Add GDPR compliance features

## Integration with Pledge Form

**Future: Auto-add contacts from pledge:**
```python
# In pledge view
from email_management.models import Contact

def process_pledge(form_data):
    # Save pledge
    pledge = Pledge.objects.create(...)
    
    # Add to contacts
    Contact.objects.get_or_create(
        email=form_data['email'],
        defaults={
            'first_name': form_data.get('name', '').split()[0],
            'district': pledge.district,
            'state': pledge.state,
            'source': 'pledge_form',
            'is_subscribed': True,
        }
    )
```

## Unsubscribe Handling

**Add unsubscribe link to emails:**
```html
<p>
    <a href="https://the80percentbill.com/unsubscribe?email={{email}}">Unsubscribe</a>
</p>
```

**Unsubscribe view** (to implement):
```python
def unsubscribe(request):
    email = request.GET.get('email')
    contact = Contact.objects.get(email=email)
    contact.unsubscribe()  # Sets is_subscribed=False
    return render(request, 'unsubscribe_success.html')
```

## Next Steps

### Phase 1 (Complete) ✅
- Contact management
- SMTP configuration
- Email sending service
- Campaign model
- Email logging
- Brevo integration

### Phase 2 (To Do)
- [ ] Send campaign button in admin
- [ ] Campaign preview
- [ ] CSV contact import
- [ ] Unsubscribe page
- [ ] Email template editor (rich text)

### Phase 3 (Future)
- [ ] Scheduled sending (cron/celery)
- [ ] Auto-import from pledge form
- [ ] Email analytics dashboard
- [ ] A/B testing
- [ ] Deliverability monitoring

## Troubleshooting

### SMTP connection fails
```bash
python manage.py setup_brevo
# Check the connection test output
```

### Emails not sending
1. Check SMTP configuration is active and default
2. Verify contacts are subscribed
3. Check EmailLog for error messages
4. Test SMTP credentials in Brevo dashboard

### Variables not replacing
- Make sure variables are in double braces: `{{first_name}}`
- Check contact has the field populated
- For custom fields, ensure they're in `contact.custom_data`

---

**Ready to send your first campaign!** 📧
