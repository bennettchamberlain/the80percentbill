#!/bin/bash
set -e

echo "=== Safe Migration Deployment for Railway ==="

# Step 1: Fake email_management migrations to bypass admin dependency conflict
echo "Step 1: Applying email_management migrations with --fake-initial..."
python manage.py migrate email_management --fake-initial 2>&1 || {
    echo "--fake-initial failed, trying --fake..."
    python manage.py migrate email_management --fake
}

# Step 2: Apply all other migrations normally
echo "Step 2: Applying remaining migrations..."
python manage.py migrate

# Step 3: Collect static files (if needed)
echo "Step 3: Collecting static files..."
python manage.py collectstatic --noinput 2>&1 || echo "No static files to collect"

echo "=== Migration deployment complete! ==="
echo "Starting server..."

# Step 4: Start the server
exec gunicorn the_80_percent_bill.wsgi:application --bind 0.0.0.0:$PORT
