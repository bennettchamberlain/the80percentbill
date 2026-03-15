#!/bin/bash
set -e

echo "=== Direct Database Migration Fix for Railway ==="

# Step 1: Manually mark email_management migrations as applied using raw SQL
echo "Step 1: Marking email_management migrations as applied in database..."

python << 'PYTHON_SCRIPT'
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'the_80_percent_bill.settings')
django.setup()

from django.db import connection
from datetime import datetime

migrations_to_fake = [
    ('pledge', '0003_pledge_contact_pledge_pledge_pled_contact_dba015_idx'),
    ('email_management', '0001_initial'),
    ('email_management', '0002_senderemail'),
    ('email_management', '0003_remove_contactlist_contacts_and_more'),
    ('email_management', '0004_segment'),
    ('email_management', '0005_replace_emailcampaign'),
    ('email_management', '0006_campaignrecipient_and_more'),
    ('email_management', '0007_campaignversion_campaignrecipient_campaign_version_and_more'),
]

with connection.cursor() as cursor:
    # Check if migrations already exist
    cursor.execute(
        "SELECT app, name FROM django_migrations WHERE app = 'email_management'"
    )
    existing = set(cursor.fetchall())
    
    # Insert missing migrations
    now = datetime.now()
    for app, name in migrations_to_fake:
        if (app, name) not in existing:
            print(f"  Inserting: {app}.{name}")
            cursor.execute(
                "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, %s)",
                [app, name, now]
            )
        else:
            print(f"  Already exists: {app}.{name}")

print("✅ All migrations marked as applied")

# Create email_management tables using schema editor
print("\n📦 Creating email_management tables directly...")
from django.db import connection
from django.db.backends.base.schema import BaseDatabaseSchemaEditor

# Import all models
from email_management.models import (
    EmailUser, SMTPConfiguration, EmailTemplate, EmailLog,
    Contact, ContactList, ContactListMember, Segment,
    EmailCampaign, CampaignRecipient, CampaignVersion, SenderEmail
)

with connection.schema_editor() as schema_editor:
    models_to_create = [
        EmailUser, SenderEmail, SMTPConfiguration, Contact, 
        ContactList, ContactListMember, Segment, EmailTemplate,
        EmailCampaign, CampaignRecipient, CampaignVersion, EmailLog
    ]
    
    for model in models_to_create:
        table_name = model._meta.db_table
        # Check if table exists
        with connection.cursor() as cursor:
            cursor.execute(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = '{table_name}'
                );
            """)
            exists = cursor.fetchone()[0]
        
        if not exists:
            print(f"  Creating table: {table_name}")
            schema_editor.create_model(model)
        else:
            print(f"  Table exists: {table_name}")

print("✅ All email_management tables created")
PYTHON_SCRIPT

# Step 2.5: NOW add contact_id column (after email_contacts table exists)
echo "Step 2.5: Adding contact_id column to pledge table..."
python << 'PYTHON_SCRIPT2'
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'the_80_percent_bill.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    # Check if contact_id column exists
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'pledge_pledge' 
        AND column_name = 'contact_id'
    """)
    if cursor.fetchone():
        print("  contact_id column already exists")
    else:
        print("  Adding contact_id column...")
        cursor.execute("""
            ALTER TABLE pledge_pledge 
            ADD COLUMN contact_id INTEGER NULL 
            REFERENCES email_management_contact(id) ON DELETE SET NULL
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS pledge_pled_contact_dba015_idx 
            ON pledge_pledge(contact_id)
        """)
        print("  ✅ contact_id column added with index")
PYTHON_SCRIPT2

# Step 3: Apply all other migrations normally
echo "Step 3: Applying remaining migrations..."
python manage.py migrate

# Step 4: Collect static files
echo "Step 4: Collecting static files..."
python manage.py collectstatic --noinput 2>&1 || echo "No static files to collect"

echo "=== Migration deployment complete! ==="
echo "Starting server..."

# Step 5: Start the server
exec python -m gunicorn the_80_percent_bill.wsgi:application --bind 0.0.0.0:$PORT
