"""Import current legislators from the unitedstates/congress-legislators YAML dataset."""

from pathlib import Path

import yaml
from django.core.management.base import BaseCommand

from reps.models import Representative


class Command(BaseCommand):
    help = "Import current legislators from congress-legislators YAML files"

    def add_arguments(self, parser):
        parser.add_argument(
            "--data-dir",
            required=True,
            help="Path to local clone of github.com/unitedstates/congress-legislators",
        )

    def handle(self, *args, **options):
        data_dir = Path(options["data_dir"])
        current_file = data_dir / "legislators-current.yaml"
        social_file = data_dir / "legislators-social-media.yaml"

        if not current_file.exists():
            self.stderr.write(self.style.ERROR(f"File not found: {current_file}"))
            return

        with open(current_file) as f:
            legislators = yaml.safe_load(f)

        # Build social media lookup keyed by bioguide_id
        social_lookup = {}
        if social_file.exists():
            with open(social_file) as f:
                social_data = yaml.safe_load(f)
            for entry in social_data:
                bio_id = entry.get("id", {}).get("bioguide")
                if bio_id:
                    social_lookup[bio_id] = entry.get("social", {})

        party_map = {"Democrat": "D", "Republican": "R", "Independent": "I"}
        chamber_map = {"rep": "house", "sen": "senate"}
        created = 0
        updated = 0
        seen_ids = set()

        for leg in legislators:
            ids = leg.get("id", {})
            bioguide_id = ids.get("bioguide")
            if not bioguide_id:
                continue

            name = leg.get("name", {})
            # Use the most recent term
            terms = leg.get("terms", [])
            if not terms:
                continue
            term = terms[-1]

            party_raw = term.get("party", "")
            party = party_map.get(party_raw)
            if party is None:
                self.stderr.write(self.style.WARNING(
                    f"Unknown party '{party_raw}' for {bioguide_id}, defaulting to Independent"
                ))
                party = "I"

            chamber = chamber_map.get(term.get("type", ""), "house")

            district = term.get("district")

            social = social_lookup.get(bioguide_id, {})

            fec_ids = ids.get("fec", [])
            if isinstance(fec_ids, str):
                fec_ids = [fec_ids]

            defaults = {
                "first_name": name.get("first", ""),
                "last_name": name.get("last", ""),
                "full_name": name.get("official_full", f"{name.get('first', '')} {name.get('last', '')}"),
                "party": party,
                "state": term.get("state", ""),
                "district": district,
                "chamber": chamber,
                "in_office": True,
                "term_start": term.get("start"),
                "term_end": term.get("end"),
                "seniority": None,
                "official_website": term.get("url", ""),
                "phone": term.get("phone", ""),
                "office_address": term.get("address", ""),
                "contact_form_url": term.get("contact_form", ""),
                "twitter": social.get("twitter", ""),
                "facebook": social.get("facebook", ""),
                "youtube": social.get("youtube", "") or social.get("youtube_id", ""),
                "instagram": social.get("instagram", ""),
                "opensecrets_id": ids.get("opensecrets", ""),
                "fec_ids": fec_ids,
                "govtrack_id": str(ids.get("govtrack", "")),
                "votesmart_id": str(ids.get("votesmart", "") or ""),
            }

            seen_ids.add(bioguide_id)
            _, was_created = Representative.objects.update_or_create(
                bioguide_id=bioguide_id,
                defaults=defaults,
            )
            if was_created:
                created += 1
            else:
                updated += 1

        # Mark any previously-imported legislators who are no longer current
        departed = Representative.objects.filter(in_office=True).exclude(
            bioguide_id__in=seen_ids
        ).update(in_office=False)

        self.stdout.write(
            self.style.SUCCESS(
                f"Done: {created} created, {updated} updated, {departed} marked departed "
                f"({created + updated} total current)"
            )
        )
