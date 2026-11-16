"""Compatibility wrapper: seed the curated 15-film demo catalogue.

Run: python cinema_database_work.py
Recommended: python manage.py seed_cinemago
"""
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()
from django.core.management import call_command

if __name__ == "__main__":
    call_command("seed_cinemago")
