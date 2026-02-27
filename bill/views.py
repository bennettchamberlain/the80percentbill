from django.shortcuts import render

from .articles import ARTICLES, VETERANS_BILL_NOTE

def index(request):
    """Display all 20 bill articles."""
    context = {
        "articles": ARTICLES,
        "veterans_note": VETERANS_BILL_NOTE
    }
    return render(request, "bill/index.html", context)