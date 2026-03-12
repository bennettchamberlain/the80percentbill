"""
Email sending service using SMTP relay (Brevo or any SMTP server).
Handles actual email sending with proper error handling and logging.
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from django.utils import timezone
from .models import EmailLog, Contact


class EmailSendingService:
    """
    Service for sending emails via SMTP relay.
    """
    
    def __init__(self, smtp_config):
        """
        Initialize with an SMTP configuration.
        
        Args:
            smtp_config: SMTPConfiguration instance
        """
        self.config = smtp_config
    
    def send_email(self, to_email, subject, html_body=None, text_body=None, 
                   campaign=None, user=None, contact=None, from_email=None):
        """
        Send a single email.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML body (optional)
            text_body: Plain text body (optional)
            campaign: EmailCampaign instance (optional)
            user: EmailUser who is sending (optional)
            contact: Contact instance (optional)
            from_email: Override sender email (optional, defaults to SMTP config)
        
        Returns:
            EmailLog instance
        """
        # Use provided from_email or default to SMTP config
        sender_email = from_email or self.config.from_email
        
        # Create log entry
        log = EmailLog.objects.create(
            campaign=campaign,
            contact=contact,
            user=user,
            recipient_email=to_email,
            subject=subject,
            status='sending'
        )
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = formataddr((self.config.from_name, sender_email))
            msg['To'] = to_email
            msg['Reply-To'] = sender_email
            
            # Add headers to improve deliverability and inbox placement
            msg['X-Mailer'] = 'The 80% Bill Email System'
            msg['X-Priority'] = '3'  # Normal priority
            msg['List-Unsubscribe'] = f'<mailto:{sender_email}?subject=unsubscribe>'
            
            # Important: Add Message-ID for threading and legitimacy
            import time
            import random
            msg['Message-ID'] = f'<{int(time.time())}.{random.randint(1000,9999)}@the80percentbill.com>'
            
            # Add bodies (plain text first, then HTML for better spam score)
            if text_body:
                msg.attach(MIMEText(text_body, 'plain'))
            if html_body:
                msg.attach(MIMEText(html_body, 'html'))
            
            # Connect and send
            if self.config.use_ssl:
                server = smtplib.SMTP_SSL(self.config.smtp_host, self.config.smtp_port)
            else:
                server = smtplib.SMTP(self.config.smtp_host, self.config.smtp_port)
                if self.config.use_tls:
                    server.starttls()
            
            # Login
            server.login(self.config.smtp_username, self.config.smtp_password)
            
            # Send
            server.send_message(msg)
            server.quit()
            
            # Update log
            log.status = 'sent'
            log.sent_at = timezone.now()
            log.save()
            
            # Update contact stats
            if contact:
                contact.emails_sent += 1
                contact.last_email_sent = timezone.now()
                contact.save()
            
            return log
            
        except Exception as e:
            # Log failure
            log.status = 'failed'
            log.error_message = str(e)
            log.save()
            
            return log
    
    def send_campaign(self, campaign):
        """
        Send an entire campaign to all recipients.
        
        Args:
            campaign: EmailCampaign instance
        
        Returns:
            dict with results
        """
        from .models import EmailCampaign
        
        # Mark as sending
        campaign.status = 'sending'
        campaign.started_at = timezone.now()
        campaign.save()
        
        # Get all contacts from selected lists
        contacts = Contact.objects.filter(
            lists__in=campaign.contact_lists.all(),
            is_subscribed=True
        ).distinct()
        
        campaign.total_recipients = contacts.count()
        campaign.save()
        
        sent = 0
        failed = 0
        
        for contact in contacts:
            # Replace variables in subject and body
            subject = self._replace_variables(campaign.subject, contact)
            html_body = self._replace_variables(campaign.body_html, contact) if campaign.body_html else None
            text_body = self._replace_variables(campaign.body_text, contact) if campaign.body_text else None
            
            # Send email
            log = self.send_email(
                to_email=contact.email,
                subject=subject,
                html_body=html_body,
                text_body=text_body,
                campaign=campaign,
                user=campaign.user,
                contact=contact
            )
            
            if log.status == 'sent':
                sent += 1
            else:
                failed += 1
            
            # Update campaign stats
            campaign.sent_count = sent
            campaign.failed_count = failed
            campaign.save()
        
        # Mark as completed
        campaign.status = 'sent'
        campaign.completed_at = timezone.now()
        campaign.save()
        
        return {
            'total': campaign.total_recipients,
            'sent': sent,
            'failed': failed,
        }
    
    def _replace_variables(self, text, contact):
        """
        Replace template variables with contact data.
        
        Available variables:
        - {{first_name}}
        - {{last_name}}
        - {{email}}
        - {{district}}
        - {{state}}
        - Any custom_data keys
        
        Args:
            text: Text with variables
            contact: Contact instance
        
        Returns:
            Text with variables replaced
        """
        if not text:
            return text
        
        # Standard variables
        replacements = {
            '{{first_name}}': contact.first_name or '',
            '{{last_name}}': contact.last_name or '',
            '{{email}}': contact.email or '',
            '{{district}}': contact.district or '',
            '{{state}}': contact.state or '',
        }
        
        # Custom data variables
        if contact.custom_data:
            for key, value in contact.custom_data.items():
                replacements[f'{{{{{key}}}}}'] = str(value)
        
        # Replace
        for var, value in replacements.items():
            text = text.replace(var, value)
        
        return text
    
    def test_connection(self):
        """
        Test SMTP connection.
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            if self.config.use_ssl:
                server = smtplib.SMTP_SSL(self.config.smtp_host, self.config.smtp_port, timeout=10)
            else:
                server = smtplib.SMTP(self.config.smtp_host, self.config.smtp_port, timeout=10)
                if self.config.use_tls:
                    server.starttls()
            
            server.login(self.config.smtp_username, self.config.smtp_password)
            server.quit()
            
            return (True, 'Connection successful!')
            
        except Exception as e:
            return (False, f'Connection failed: {str(e)}')
