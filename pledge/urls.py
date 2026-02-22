from django.urls import path

from . import views

app_name = "pledge"

urlpatterns = [
    path("", views.index, name="index"),
    path("api/address-suggestions/", views.address_suggestions, name="address_suggestions"),
    path("api/address-lookup/", views.address_lookup, name="address_lookup"),
]
