"""Pledge flow: Step 1 (district lookup), Step 2 (sign form), Step 3 (success)."""

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render

from bill.articles import ARTICLES
from core.geo import get_district, get_osm_addresses
from core.sheets import is_duplicate, save_pledge


def index(request):
    """Main pledge view - dispatches to step 1, 2, or 3."""
    step = request.session.get("pledge_step", 1)
    district_info = request.session.get("pledge_district_info")

    if step == 1:
        return _step1(request)
    if step == 2 and district_info:
        return _step2(request)
    if step == 3:
        return _step3(request)
    return _step1(request)


def _step1(request):
    """Step 1: Address lookup and/or manual district entry."""
    district_info = request.session.get("pledge_district_info")
    district_input = request.session.get("pledge_district", "")
    rep_input = request.session.get("pledge_rep", "")
    error = None

    if request.method == "POST":
        action = request.POST.get("action", "")

        if action == "lookup":
            address = request.POST.get("address", "").strip()
            if address:
                district, rep = get_district(address)
                if district and rep:
                    request.session["pledge_district_info"] = (district, rep)
                    request.session["pledge_district"] = district
                    request.session["pledge_rep"] = rep
                    return redirect("pledge:index")
                error = "Could not find congressional district for that address."
            else:
                error = "Please enter an address."

        elif action == "manual" or action == "continue":
            district_input = request.POST.get("district", "").strip()
            rep_input = request.POST.get("rep", "").strip()
            if district_input and rep_input:
                request.session["pledge_district_info"] = (district_input, rep_input)
                request.session["pledge_district"] = district_input
                request.session["pledge_rep"] = rep_input
                request.session["pledge_step"] = 2
                return redirect("pledge:index")
            error = "Please fill in both District Code and Representative Name."

        elif action == "back":
            request.session["pledge_step"] = 1
            request.session.pop("pledge_district_info", None)
            request.session.pop("pledge_district", None)
            request.session.pop("pledge_rep", None)
            return redirect("pledge:index")

    # Count active bills (those that are numbered)
    active_bill_count = sum(1 for article in ARTICLES if len(article) <= 4 or not article[4])
    
    return render(
        request,
        "pledge/step1.html",
        {
            "district_info": district_info,
            "district_input": district_input or (district_info[0] if district_info else ""),
            "rep_input": rep_input or (district_info[1] if district_info else ""),
            "error": error,
            "bill_count": active_bill_count,
        },
    )


def _step2(request):
    """Step 2: Name/email form and pledge submission."""
    district_info = request.session.get("pledge_district_info")
    if not district_info:
        request.session["pledge_step"] = 1
        return redirect("pledge:index")

    district, rep = district_info
    error = None

    if request.method == "POST":
        action = request.POST.get("action", "")
        if action == "back":
            request.session["pledge_step"] = 1
            request.session.pop("pledge_district_info", None)
            request.session.pop("pledge_district", None)
            request.session.pop("pledge_rep", None)
            return redirect("pledge:index")

        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip().lower()

        if not name or not email or "@" not in email:
            error = "Please provide a valid name and email."
        else:
            if is_duplicate(email):
                error = f"'{email}' has already signed."
            else:
                if save_pledge(name, email, district, rep):
                    request.session["pledge_step"] = 3
                    return redirect("pledge:index")
                error = "Unable to save pledge. Please try again."

    return render(
        request,
        "pledge/step2.html",
        {"district": district, "rep": rep, "error": error},
    )


def _step3(request):
    """Step 3: Success confirmation."""
    if request.method == "POST" and request.POST.get("action") == "another":
        request.session.pop("pledge_step", None)
        request.session.pop("pledge_district_info", None)
        request.session.pop("pledge_district", None)
        request.session.pop("pledge_rep", None)
        return redirect("pledge:index")

    return render(request, "pledge/step3.html")


def address_suggestions(request):
    """AJAX: Return address suggestions from OSM for autocomplete."""
    q = request.GET.get("q", "").strip()
    if len(q) < 3:
        return JsonResponse({"suggestions": []})
    results = get_osm_addresses(q)
    suggestions = [r.get("display_name", "") for r in results if r.get("display_name")][:6]
    return JsonResponse({"suggestions": suggestions})


def address_lookup(request):
    """AJAX: Look up district/rep for a selected address."""
    address = request.GET.get("address", "").strip()
    if not address:
        return JsonResponse({"error": "No address provided"}, status=400)
    district, rep = get_district(address)
    if district and rep:
        return JsonResponse({"district": district, "rep": rep})
    return JsonResponse({"error": "Could not find congressional district"}, status=404)
