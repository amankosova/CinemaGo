from django.core.management.base import BaseCommand
from cinema.models import Movie
from .seed_cinemago import TRAILER_URLS


class Command(BaseCommand):
    help = "Attach 15 user-supplied YouTube trailers to existing catalogue films without changing other records."

    def handle(self, *args, **kwargs):
        updated, missing = 0, []
        for title, url in TRAILER_URLS.items():
            count = Movie.objects.filter(title_ru=title).update(trailer_url=url)
            updated += count
            if not count:
                missing.append(title)
        self.stdout.write(self.style.SUCCESS(f"Trailer links updated for {updated} film(s)."))
        if missing:
            self.stdout.write(self.style.WARNING("Not found (run seed_cinemago only if needed): " + ", ".join(missing)))
