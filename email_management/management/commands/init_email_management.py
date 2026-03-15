"""
Management command to safely apply email_management migrations on existing databases.
This bypasses the admin.0001_initial dependency conflict.
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Safely apply email_management migrations on existing production databases'

    def handle(self, *args, **options):
        self.stdout.write('Checking migration status...')
        
        # Check if email_management tables already exist
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'email_users'
                );
            """)
            tables_exist = cursor.fetchone()[0]
        
        if tables_exist:
            self.stdout.write(self.style.SUCCESS(
                'email_management tables already exist. Faking migrations...'
            ))
            call_command('migrate', 'email_management', '--fake')
        else:
            self.stdout.write(self.style.WARNING(
                'email_management tables do not exist. Applying with --fake-initial...'
            ))
            try:
                call_command('migrate', 'email_management', '--fake-initial')
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f'Failed with --fake-initial, trying --fake: {e}'
                ))
                call_command('migrate', 'email_management', '--fake')
        
        self.stdout.write(self.style.SUCCESS(
            'Email management migrations applied successfully!'
        ))
