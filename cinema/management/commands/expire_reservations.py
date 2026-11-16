from django.core.management.base import BaseCommand
from cinema.models import expire_reservations

class Command(BaseCommand):
    help = 'Release expired pending cinema reservations (run once per minute in production).'
    def handle(self, *args, **options):
        self.stdout.write(f'Expired reservations released: {expire_reservations()}')
