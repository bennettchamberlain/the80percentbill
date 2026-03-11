from django.urls import path

from . import views

app_name = "reps"

urlpatterns = [
    path("", views.directory, name="directory"),
    path("<str:bioguide_id>/", views.detail, name="detail"),
]
