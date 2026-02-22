"""Verify database connection and do a pledge round-trip test."""

from django.core.management.base import BaseCommand
from django.db import connection

from pledge.models import Pledge


class Command(BaseCommand):
    help = "Verify database connection and pledge count"

    def add_arguments(self, parser):
        parser.add_argument(
            "--test-write",
            action="store_true",
            help="Create a test pledge and verify it appears in the DB",
        )

    def handle(self, *args, **options):
        db = connection.settings_dict
        engine = db["ENGINE"]

        if "postgresql" in engine:
            self.stdout.write(f"Database: Postgres ({db.get('HOST')})")
            with connection.cursor() as c:
                c.execute("SELECT current_database(), current_schema()")
                dbname, schema = c.fetchone()
                self.stdout.write(f"Connected to: database={dbname}, schema={schema}")
        else:
            self.stdout.write(self.style.SUCCESS("Database: SQLite"))

        count = Pledge.objects.count()
        self.stdout.write(f"Current pledge count: {count}")

        if options["test_write"]:
            self.stdout.write("\nCreating test pledge...")
            p = Pledge.objects.create(
                name="DB Verify Test",
                email="verify-test@example.com",
                district="XX-99",
                rep="Test Rep",
            )
            self.stdout.write(self.style.SUCCESS(f"Created pledge id={p.id}"))

            # Verify via ORM (database-agnostic)
            found = Pledge.objects.filter(email="verify-test@example.com").first()
            if found:
                self.stdout.write(self.style.SUCCESS(f"Verified in DB: id={found.id}, {found.name}"))
            else:
                self.stdout.write(self.style.ERROR("Pledge NOT found in DB!"))

            # Clean up
            p.delete()
            self.stdout.write("Test pledge removed.")
