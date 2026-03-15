"""
Email sending service using Brevo HTTP API (for Railway compatibility).
Railway blocks SMTP ports, so we use HTTP API instead.
"""
import requests
from django.utils import timezone
from .models import EmailLog


class EmailSendingService:
    """
    Service for sending emails via Brevo HTTP API.
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
        Send a single email via Brevo HTTP API.
        
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
            # Prepare Brevo API request
            url = "https://api.brevo.com/v3/smtp/email"
            
            headers = {
                "accept": "application/json",
                "api-key": self.config.smtp_password,  # Use password field for API key
                "content-type": "application/json"
            }
            
            payload = {
                "sender": {
                    "name": self.config.from_name,
                    "email": sender_email
                },
                "to": [
                    {
                        "email": to_email
                    }
                ],
                "subject": subject,
                "replyTo": {
                    "email": sender_email
                }
            }
            
            # Add bodies
            if html_body:
                payload["htmlContent"] = html_body
            if text_body:
                payload["textContent"] = text_body
            
            # Send via HTTP API
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code in [200, 201]:
                # Success
                log.status = 'sent'
                log.sent_at = timezone.now()
                log.save()
                
                # Update contact email count if provided
                if contact:
                    contact.emails_sent += 1
                    contact.last_email_sent = timezone.now()
                    contact.save()
                
                return log
            else:
                # API error
                error_msg = f"Brevo API error {response.status_code}: {response.text}"
                log.status = 'failed'
                log.error_message = error_msg
                log.save()
                
                return log
                
        except requests.exceptions.Timeout:
            log.status = 'failed'
            log.error_message = 'Request timeout'
            log.save()
            return log
            
        except requests.exceptions.ConnectionError as e:
            log.status = 'failed'
            log.error_message = f'Connection error: {str(e)}'
            log.save()
            return log
            
        except Exception as e:
            log.status = 'failed'
            log.error_message = str(e)
            log.save()
            return log
    
    def test_connection(self):
        """
        Test SMTP connection and authentication.
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            # Test with a simple API request
            url = "https://api.brevo.com/v3/account"
            
            headers = {
                "accept": "application/json",
                "api-key": self.config.smtp_password
            }
            
            response = requests.get(url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                return (True, "✅ Connected successfully to Brevo API")
            else:
                return (False, f"❌ API error: {response.status_code}")
                
        except Exception as e:
            return (False, f"❌ Connection failed: {str(e)}")
