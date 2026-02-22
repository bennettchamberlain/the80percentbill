"""Context processors to inject common template variables."""

from django.conf import settings


def site_context(request):
    """Add site-wide variables to all templates."""
    return {
        "donation_link": getattr(settings, "DONATION_LINK", ""),
    }
