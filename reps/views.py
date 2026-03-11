from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from .models import Representative

# All 50 states + DC + territories for the filter dropdown
US_STATES = [
    ("AL", "Alabama"), ("AK", "Alaska"), ("AZ", "Arizona"), ("AR", "Arkansas"),
    ("CA", "California"), ("CO", "Colorado"), ("CT", "Connecticut"), ("DE", "Delaware"),
    ("FL", "Florida"), ("GA", "Georgia"), ("HI", "Hawaii"), ("ID", "Idaho"),
    ("IL", "Illinois"), ("IN", "Indiana"), ("IA", "Iowa"), ("KS", "Kansas"),
    ("KY", "Kentucky"), ("LA", "Louisiana"), ("ME", "Maine"), ("MD", "Maryland"),
    ("MA", "Massachusetts"), ("MI", "Michigan"), ("MN", "Minnesota"), ("MS", "Mississippi"),
    ("MO", "Missouri"), ("MT", "Montana"), ("NE", "Nebraska"), ("NV", "Nevada"),
    ("NH", "New Hampshire"), ("NJ", "New Jersey"), ("NM", "New Mexico"), ("NY", "New York"),
    ("NC", "North Carolina"), ("ND", "North Dakota"), ("OH", "Ohio"), ("OK", "Oklahoma"),
    ("OR", "Oregon"), ("PA", "Pennsylvania"), ("RI", "Rhode Island"), ("SC", "South Carolina"),
    ("SD", "South Dakota"), ("TN", "Tennessee"), ("TX", "Texas"), ("UT", "Utah"),
    ("VT", "Vermont"), ("VA", "Virginia"), ("WA", "Washington"), ("WV", "West Virginia"),
    ("WI", "Wisconsin"), ("WY", "Wyoming"), ("DC", "District of Columbia"),
    ("AS", "American Samoa"), ("GU", "Guam"), ("MP", "Northern Mariana Islands"),
    ("PR", "Puerto Rico"), ("VI", "U.S. Virgin Islands"),
]


def directory(request):
    """List all representatives with search and filters."""
    reps = Representative.objects.filter(in_office=True)

    q = request.GET.get("q", "").strip()
    state = request.GET.get("state", "")
    party = request.GET.get("party", "")
    chamber = request.GET.get("chamber", "")

    if q:
        reps = reps.filter(
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(full_name__icontains=q)
        )
    if state:
        reps = reps.filter(state=state)
    if party:
        reps = reps.filter(party=party)
    if chamber:
        reps = reps.filter(chamber=chamber)

    return render(request, "reps/directory.html", {
        "reps": reps,
        "q": q,
        "state": state,
        "party": party,
        "chamber": chamber,
        "states": US_STATES,
        "total": reps.count(),
    })


def detail(request, bioguide_id):
    """Profile page for a single representative."""
    rep = get_object_or_404(Representative, bioguide_id=bioguide_id)
    positions = rep.bill_positions.all()
    return render(request, "reps/detail.html", {
        "rep": rep,
        "positions": positions,
    })
