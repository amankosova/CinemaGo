"""Persistent per-user/IP sign-in throttling for the demo site."""
from django.db import models


class LoginAttempt(models.Model):
    key = models.CharField(max_length=64, primary_key=True)
    failed_count = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
