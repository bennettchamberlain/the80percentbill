from django.db import models


class Representative(models.Model):
    """A current member of Congress (House or Senate)."""

    PARTY_CHOICES = [
        ("D", "Democrat"),
        ("R", "Republican"),
        ("I", "Independent"),
    ]
    CHAMBER_CHOICES = [
        ("house", "House"),
        ("senate", "Senate"),
    ]

    # Core identity
    bioguide_id = models.CharField(max_length=10, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    full_name = models.CharField(max_length=200)
    party = models.CharField(max_length=1, choices=PARTY_CHOICES)
    state = models.CharField(max_length=2)
    district = models.PositiveSmallIntegerField(null=True, blank=True)
    chamber = models.CharField(max_length=6, choices=CHAMBER_CHOICES)
    in_office = models.BooleanField(default=True)

    # Term info
    term_start = models.DateField(null=True, blank=True)
    term_end = models.DateField(null=True, blank=True)
    next_election = models.CharField(max_length=4, blank=True, default="")
    seniority = models.PositiveSmallIntegerField(null=True, blank=True)

    # Contact
    official_website = models.URLField(blank=True, default="")
    phone = models.CharField(max_length=20, blank=True, default="")
    office_address = models.CharField(max_length=300, blank=True, default="")
    contact_form_url = models.URLField(blank=True, default="")

    # Social media
    twitter = models.CharField(max_length=100, blank=True, default="")
    facebook = models.CharField(max_length=100, blank=True, default="")
    youtube = models.CharField(max_length=100, blank=True, default="")
    instagram = models.CharField(max_length=100, blank=True, default="")

    # Cross-reference IDs for other data sources
    opensecrets_id = models.CharField(max_length=20, blank=True, default="")
    fec_ids = models.JSONField(default=list, blank=True)
    govtrack_id = models.CharField(max_length=20, blank=True, default="")
    votesmart_id = models.CharField(max_length=20, blank=True, default="")

    # 80% Bill alignment
    alignment_score = models.PositiveSmallIntegerField(null=True, blank=True)

    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["state", "last_name"]

    def __str__(self):
        return f"{self.title} {self.full_name} ({self.party}-{self.state})"

    @property
    def photo_url(self):
        return f"https://theunitedstates.io/images/congress/225x275/{self.bioguide_id}.jpg"

    @property
    def district_display(self):
        if self.chamber == "senate":
            return f"{self.state} (Senate)"
        if self.district == 0:
            return f"{self.state}-At Large"
        return f"{self.state}-{self.district}"

    @property
    def title(self):
        return "Sen." if self.chamber == "senate" else "Rep."

    @property
    def opensecrets_url(self):
        if self.opensecrets_id:
            return f"https://www.opensecrets.org/members-of-congress/summary?cid={self.opensecrets_id}"
        return ""

    @property
    def congress_gov_url(self):
        return f"https://www.congress.gov/member/{self.bioguide_id}"


class BillPosition(models.Model):
    """Tracks a representative's stance on one of the 20 bill articles."""

    POSITION_CHOICES = [
        ("sponsor", "Sponsor"),
        ("cosponsor", "Cosponsor"),
        ("voted_yes", "Voted Yes"),
        ("voted_no", "Voted No"),
        ("no_position", "No Position"),
    ]

    representative = models.ForeignKey(
        Representative,
        on_delete=models.CASCADE,
        related_name="bill_positions",
    )
    bill_article = models.PositiveSmallIntegerField()
    bill_title = models.CharField(max_length=200)
    position = models.CharField(max_length=15, choices=POSITION_CHOICES, default="no_position")
    source_url = models.URLField(blank=True, default="")
    last_checked = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ["representative", "bill_article"]
        ordering = ["bill_article"]

    def __str__(self):
        return f"{self.representative.last_name} - Art. {self.bill_article}: {self.position}"
