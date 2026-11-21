import secrets
import re
from urllib.parse import parse_qs, urlparse

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import get_language
from django.utils.translation import gettext as gettext_now
from django.utils.translation import gettext_lazy as _


def pick(text_en, text_ru):
    return text_ru if get_language() == "ru" and text_ru else text_en


class Genre(models.Model):
    name_en = models.CharField(_("Name (English)"), max_length=60)
    name_ru = models.CharField(_("Name (Russian)"), max_length=60)
    name_kk = models.CharField("Name (Kazakh)", max_length=60, blank=True, default="")

    class Meta:
        ordering = ["name_en"]

    @property
    def name(self):
        return (self.name_kk or self.name_ru) if get_language() == "kk" else pick(self.name_en, self.name_ru)

    def __str__(self):
        return self.name


class Movie(models.Model):
    title_en = models.CharField(_("Title (English)"), max_length=150)
    title_ru = models.CharField(_("Title (Russian)"), max_length=150)
    description_en = models.TextField(_("Description (English)"))
    description_ru = models.TextField(_("Description (Russian)"))
    title_kk = models.CharField("Title (Kazakh)", max_length=150, blank=True, default="")
    description_kk = models.TextField("Description (Kazakh)", blank=True, default="")
    director = models.CharField("Director", max_length=250, blank=True, default="")
    main_cast = models.TextField("Main cast", blank=True, default="")
    country = models.CharField("Country", max_length=100, blank=True, default="")
    age_rating = models.CharField("Age rating", max_length=10, blank=True, default="")
    genres = models.ManyToManyField(Genre, related_name="movies", blank=True)
    genre = models.ForeignKey(
        Genre, verbose_name=_("Genre"), on_delete=models.SET_NULL, null=True, blank=True
    )
    duration = models.PositiveIntegerField(_("Duration (min)"))
    year = models.PositiveIntegerField(_("Year"))
    poster = models.ImageField(_("Poster"), upload_to="posters/", blank=True)
    trailer_url = models.URLField("Official YouTube trailer", max_length=500, blank=True, default="")

    class Meta:
        ordering = ["title_en"]

    @property
    def trailer_video_id(self):
        """Allow YouTube IDs from known URL formats only, never arbitrary iframe URLs."""
        if not self.trailer_url:
            return ""
        try:
            parsed = urlparse(self.trailer_url)
            hostname = (parsed.hostname or "").lower()
            if parsed.scheme != "https":
                return ""
            if hostname in ("youtu.be", "www.youtu.be"):
                candidate = parsed.path.strip("/").split("/")[0]
            elif hostname in ("youtube.com", "www.youtube.com", "m.youtube.com", "youtube-nocookie.com", "www.youtube-nocookie.com"):
                segments = parsed.path.strip("/").split("/")
                if parsed.path == "/watch":
                    candidate = parse_qs(parsed.query).get("v", [""])[0]
                elif segments[0] in ("embed", "shorts", "live") and len(segments) > 1:
                    candidate = segments[1]
                else:
                    return ""
            else:
                return ""
            return candidate if re.fullmatch(r"[A-Za-z0-9_-]{11}", candidate) else ""
        except (ValueError, IndexError):
            return ""

    @property
    def title(self):
        return (self.title_kk or self.title_ru) if get_language() == "kk" else pick(self.title_en, self.title_ru)

    @property
    def description(self):
        return (self.description_kk or self.description_ru) if get_language() == "kk" else pick(self.description_en, self.description_ru)

    @property
    def genre_names(self):
        return ", ".join(genre.name for genre in self.genres.all()) or (self.genre.name if self.genre else "")

    def __str__(self):
        return self.title


class Cinema(models.Model):
    name = models.CharField(_("Name"), max_length=100)
    city_en = models.CharField(_("City (English)"), max_length=60)
    city_ru = models.CharField(_("City (Russian)"), max_length=60)
    address_en = models.CharField(_("Address (English)"), max_length=200)
    address_ru = models.CharField(_("Address (Russian)"), max_length=200)

    class Meta:
        ordering = ["name"]

    @property
    def city(self):
        return pick(self.city_en, self.city_ru)

    @property
    def address(self):
        return pick(self.address_en, self.address_ru)

    def __str__(self):
        return f"{self.name} ({self.city})"


class Hall(models.Model):
    cinema = models.ForeignKey(
        Cinema, verbose_name=_("Cinema"), on_delete=models.CASCADE, related_name="halls"
    )
    name = models.CharField(_("Hall name"), max_length=60)
    rows_count = models.PositiveIntegerField(
        _("Rows"), validators=[MinValueValidator(1), MaxValueValidator(26)]
    )
    seats_per_row = models.PositiveIntegerField(
        _("Seats in a row"), validators=[MinValueValidator(1), MaxValueValidator(30)]
    )

    class Meta:
        ordering = ["cinema", "name"]

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        with transaction.atomic():
            super().save(*args, **kwargs)
            if is_new:
                Seat.objects.bulk_create(
                    Seat(hall=self, row=r, number=n)
                    for r in range(1, self.rows_count + 1)
                    for n in range(1, self.seats_per_row + 1)
                )

    def __str__(self):
        return f"{self.cinema.name}, {gettext_now('Hall')} {self.name}"


class Seat(models.Model):
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, related_name="seats")
    row = models.PositiveIntegerField()
    number = models.PositiveIntegerField()

    class Meta:
        ordering = ["row", "number"]
        constraints = [
            models.UniqueConstraint(fields=["hall", "row", "number"], name="unique_seat_in_hall")
        ]

    @property
    def label(self):
        return f"{chr(64 + self.row)}{self.number}"

    def __str__(self):
        return self.label


class Showtime(models.Model):
    movie = models.ForeignKey(
        Movie, verbose_name=_("Movie"), on_delete=models.CASCADE, related_name="showtimes"
    )
    hall = models.ForeignKey(
        Hall, verbose_name=_("Hall"), on_delete=models.CASCADE, related_name="showtimes"
    )
    starts_at = models.DateTimeField(_("Starts at"))
    price = models.PositiveIntegerField(_("Price (KZT)"))

    class Meta:
        ordering = ["starts_at"]

    @property
    def cinema(self):
        return self.hall.cinema

    @property
    def is_past(self):
        return self.starts_at <= timezone.now()

    def taken_seat_ids(self):
        expire_reservations()
        return set(self.tickets.filter(status__in=[Ticket.BOOKED, Ticket.PENDING]).values_list("seat_id", flat=True))

    def free_seats_count(self):
        return self.hall.rows_count * self.hall.seats_per_row - len(self.taken_seat_ids())

    def __str__(self):
        return f"{self.movie.title_en} - {self.starts_at:%d.%m.%Y %H:%M}"


def make_ticket_code():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for i in range(6))


class Ticket(models.Model):
    PENDING = "pending"
    BOOKED = "booked"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

    STATUS_CHOICES = [
        (PENDING, "Pending payment"),
        (BOOKED, _("Booked")),
        (CANCELLED, _("Cancelled")),
        (REFUNDED, "Refunded"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tickets"
    )
    reservation = models.ForeignKey("Reservation", null=True, blank=True, on_delete=models.SET_NULL, related_name="tickets")
    showtime = models.ForeignKey(Showtime, on_delete=models.CASCADE, related_name="tickets")
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE, related_name="tickets")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=BOOKED)
    price = models.PositiveIntegerField()
    code = models.CharField(max_length=6, default=make_ticket_code)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["showtime", "seat"],
                condition=Q(status__in=["booked", "pending"]),
                name="one_active_ticket_per_seat",
            )
        ]

    def __str__(self):
        return f"{self.code} - {self.seat.label}"


class Reservation(models.Model):
    """Ten-minute, demo-only payment order; never stores bank card information."""
    import uuid
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reservations')
    showtime = models.ForeignKey(Showtime, on_delete=models.CASCADE, related_name='reservations')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    status = models.CharField(max_length=12, default='pending', choices=[
        ('pending', 'Pending payment'), ('paid', 'Paid (demo)'),
        ('expired', 'Expired'), ('cancelled', 'Cancelled')])
    payment_method = models.CharField(max_length=12, blank=True, choices=[
        ('card', 'Demo card'), ('qr', 'Demo QR')])
    paid_at = models.DateTimeField(null=True, blank=True)

    @property
    def total(self):
        return sum(t.price for t in self.tickets.all())


def expire_reservations():
    """Release expired holds reliably before seat queries and checkout operations."""
    with transaction.atomic():
        ids = list(Reservation.objects.filter(status='pending', expires_at__lte=timezone.now())
                   .values_list('pk', flat=True))
        if ids:
            Ticket.objects.filter(reservation_id__in=ids, status=Ticket.PENDING).update(status=Ticket.CANCELLED)
            Reservation.objects.filter(pk__in=ids, status='pending').update(status='expired')
    return len(ids)
