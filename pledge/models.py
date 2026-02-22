from django.db import models


class Pledge(models.Model):
    """A signed pledge for The 80% Bill."""

    timestamp = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=255)
    email = models.EmailField()
    district = models.CharField(max_length=50)
    rep = models.CharField(max_length=255)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["email"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.email})"
