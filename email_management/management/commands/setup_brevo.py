"""
Django management command to set up Brevo SMTP configuration.
"""
from django.core.management.base import BaseCommand
from email_management.models import SMTPConfiguration


class Command(BaseCommand):
    help = 'Set up Brevo SMTP configuration for The 80% Bill'
    
    def handle(self, *args, **options):
        # Brevo credentials
        smtp_config, created = SMTPConfiguration.objects.get_or_create(
            name='Brevo SMTP',
            defaults={
                'smtp_host': 'smtp-relay.brevo.com',
                'smtp_port': 587,
                'smtp_username': 'a473e7001@smtp-brevo.com',
                'smtp_password': 'x0zDSmTKfNtn7HrR',
                'use_tls': True,
                'use_ssl': False,
                'from_email': 'noreply@the80percentbill.com',  # Change this to your actual sender email
                'from_name': 'The 80% Bill',
                'is_active': True,
                'is_default': True,
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS('✓ Successfully created Brevo SMTP configuration')
            )
        else:
            self.stdout.write(
                self.style.WARNING('Brevo SMTP configuration already exists')
            )
        
        # Test connection
        from email_management.email_service import EmailSendingService
        
        service = EmailSendingService(smtp_config)
        success, message = service.test_connection()
        
        if success:
            self.stdout.write(
                self.style.SUCCESS(f'✓ {message}')
            )
        else:
            self.stdout.write(
                self.style.ERROR(f'✗ {message}')
            )
