"""Pledge storage — uses Django ORM (Supabase Postgres or SQLite)."""

from django.db import IntegrityError

from pledge.models import Pledge


def is_duplicate(email):
    """Return True if the email already exists."""
    email_clean = email.strip().lower()
    return Pledge.objects.filter(email__iexact=email_clean).exists()


def save_pledge(name, email, district, rep_name):
    """Save a pledge to the database. Returns True on success."""
    try:
        Pledge.objects.create(
            name=name.strip(),
            email=email.strip().lower(),
            district=district.strip(),
            rep=rep_name.strip(),
        )
        return True
    except IntegrityError:
        return False
    except Exception:
        return False


def get_pledge_count():
    """Return the total number of pledges."""
    try:
        return Pledge.objects.count()
    except Exception:
        return None
