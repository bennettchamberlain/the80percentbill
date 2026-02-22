from django.shortcuts import render

from .articles import ARTICLES


def index(request):
    """Display all 20 bill articles."""
    return render(request, "bill/index.html", {"articles": ARTICLES})
