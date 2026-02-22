from django.contrib import admin

from .models import Pledge


@admin.register(Pledge)
class PledgeAdmin(admin.ModelAdmin):
    list_display = ["name", "email", "district", "rep", "timestamp"]
    search_fields = ["name", "email", "district"]
    list_filter = ["district"]
