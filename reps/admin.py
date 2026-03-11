from django.contrib import admin

from .models import BillPosition, Representative


@admin.register(Representative)
class RepresentativeAdmin(admin.ModelAdmin):
    list_display = ["full_name", "party", "state", "chamber", "in_office"]
    list_filter = ["party", "chamber", "state", "in_office"]
    search_fields = ["first_name", "last_name", "full_name", "bioguide_id", "state", "narrative"]
    readonly_fields = ["last_updated", "narrative_updated", "narrative_sources"]


@admin.register(BillPosition)
class BillPositionAdmin(admin.ModelAdmin):
    list_display = ["representative", "bill_article", "bill_title", "position"]
    list_filter = ["position", "bill_article"]
    search_fields = ["representative__last_name", "bill_title"]
    raw_id_fields = ["representative"]
