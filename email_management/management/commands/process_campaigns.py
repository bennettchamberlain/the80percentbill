"""
Django management command to process campaign batches.

Usage:
    python manage.py process_campaigns

This command should be run periodically (e.g., every 15 minutes via cron).
"""
from django.core.management.base import BaseCommand
from email_management.campaign_batch import process_campaign_batches


class Command(BaseCommand):
    help = 'Process pending campaign batches'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending',
        )
    
    def handle(self, *args, **options):
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No emails will be sent')
            )
            # TODO: Implement dry-run mode
            return
        
        self.stdout.write('Starting campaign batch processor...')
        
        results = process_campaign_batches()
        
        # Display results
        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Batch processing complete!\n"
                f"   Campaigns processed: {results['campaigns_processed']}\n"
                f"   Emails sent: {results['total_sent']}\n"
                f"   Emails failed: {results['total_failed']}\n"
            )
        )
        
        if results['campaigns_completed']:
            self.stdout.write(
                self.style.SUCCESS(
                    f"   Campaigns completed: {', '.join(results['campaigns_completed'])}"
                )
            )
        
        if results['errors']:
            self.stdout.write(
                self.style.ERROR(
                    f"\n❌ Errors encountered:\n"
                )
            )
            for error in results['errors']:
                self.stdout.write(f"   - {error}")
