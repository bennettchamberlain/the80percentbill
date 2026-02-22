from django.shortcuts import render


def index(request):
    """Landing page hero section with CTA buttons."""
    return render(request, "home/index.html")
