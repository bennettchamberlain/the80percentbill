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

# Add contact_id column to pledge table if it doesn't exist
print("\n🔧 Adding contact_id column to pledge table...")
with connection.cursor() as cursor:
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
            REFERENCES email_contacts(id) ON DELETE SET NULL
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS pledge_pled_contact_dba015_idx 
            ON pledge_pledge(contact_id)
        """)
        print("  ✅ contact_id column added with index")
PYTHON_SCRIPT

# Step 2: Create the actual tables (migrations won't run since they're marked as applied)
echo "Step 2: Creating email_management tables..."
python manage.py migrate email_management --run-syncdb 2>&1 || echo "Tables may already exist, continuing..."

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
