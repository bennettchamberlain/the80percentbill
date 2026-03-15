# Enable Row Level Security on pledge_pledge for Supabase.
# - Django admin connects as postgres (bypasses RLS)
# - anon role: can INSERT (anonymous pledge signing), cannot SELECT (no read of others)
# - authenticated: no policies (cannot read/write pledge data via Supabase API)

from django.db import migrations


def enable_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("ALTER TABLE pledge_pledge ENABLE ROW LEVEL SECURITY;")
        # Grant anon INSERT so Supabase API / anon role can create pledges
        cursor.execute("GRANT INSERT ON pledge_pledge TO anon;")
        # Anonymous users can insert pledges (public sign-up form)
        cursor.execute(
            """
            CREATE POLICY "anon_can_insert_pledges"
            ON pledge_pledge FOR INSERT TO anon
            WITH CHECK (true);
            """
        )
        # No SELECT policy for anon → anon sees zero rows (cannot read others)
        # No policy for authenticated → authenticated sees zero rows
        # postgres (Django admin) bypasses RLS by default


def disable_rls(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            'DROP POLICY IF EXISTS "anon_can_insert_pledges" ON pledge_pledge;'
        )
        cursor.execute("REVOKE INSERT ON pledge_pledge FROM anon;")
        cursor.execute("ALTER TABLE pledge_pledge DISABLE ROW LEVEL SECURITY;")


class Migration(migrations.Migration):

    dependencies = [
        ("pledge", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(enable_rls, disable_rls),
    ]
