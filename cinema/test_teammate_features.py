from datetime import timedelta
from urllib.parse import quote

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Cinema, Hall, Movie, Reservation, Showtime, Ticket


class LocalizationContributionTests(TestCase):
    def setUp(self):
        self.movie = Movie.objects.create(
            title_en="English title", title_ru="Русское название",
            title_kk="Қазақша атау", description_en="English story",
            description_ru="Русская история", description_kk="Қазақша оқиға",
            duration=90, year=2026,
        )

    def test_tc01_russian_movie_detail_uses_localized_content(self):
        url = reverse("movie_detail", args=[self.movie.pk])
        self.client.post(reverse("set_language"), {"language": "ru", "next": url})
        response = self.client.get(url)
        self.assertContains(response, "Русское название")
        self.assertContains(response, "Русская история")
        self.assertNotContains(response, "English story")

    def test_tc02_kazakh_movie_detail_uses_localized_content(self):
        url = reverse("movie_detail", args=[self.movie.pk])
        self.client.post(reverse("set_language"), {"language": "kk", "next": url})
        response = self.client.get(url)
        self.assertContains(response, "Қазақша атау")
        self.assertContains(response, "Қазақша оқиға")
        self.assertNotContains(response, "Русская история")

    def test_tc03_missing_kazakh_movie_fields_fall_back_to_russian(self):
        self.movie.title_kk = ""
        self.movie.description_kk = ""
        self.movie.save(update_fields=["title_kk", "description_kk"])
        url = reverse("movie_detail", args=[self.movie.pk])
        self.client.post(reverse("set_language"), {"language": "kk", "next": url})
        response = self.client.get(url)
        self.assertContains(response, "Русское название")
        self.assertContains(response, "Русская история")


class TrailerContributionTests(TestCase):
    def setUp(self):
        self.movie = Movie.objects.create(
            title_en="Trailer film", title_ru="Трейлер",
            description_en="Story", description_ru="История",
            duration=90, year=2026,
        )

    def test_tc04_watch_url_renders_trailer_dialog(self):
        self.movie.trailer_url = "https://www.youtube.com/watch?v=AbC_123-xyz&t=12"
        self.movie.save(update_fields=["trailer_url"])
        response = self.client.get(reverse("movie_detail", args=[self.movie.pk]))
        self.assertContains(response, 'data-youtube-id="AbC_123-xyz"')
        self.assertContains(response, "https://www.youtube.com/watch?v=AbC_123-xyz")

    def test_tc05_short_youtube_url_extracts_video_id(self):
        self.movie.trailer_url = "https://youtu.be/AbC_123-xyz?si=share"
        self.assertEqual(self.movie.trailer_video_id, "AbC_123-xyz")

    def test_tc06_lookalike_youtube_host_is_rejected(self):
        self.movie.trailer_url = "https://youtube.com.evil.example/watch?v=AbC_123-xyz"
        self.assertEqual(self.movie.trailer_video_id, "")
        self.movie.save(update_fields=["trailer_url"])
        response = self.client.get(reverse("movie_detail", args=[self.movie.pk]))
        self.assertNotContains(response, 'id="movie-trailer-dialog"')

    def test_tc07_invalid_video_id_is_rejected(self):
        self.movie.trailer_url = "https://www.youtube.com/watch?v=too-short"
        self.assertEqual(self.movie.trailer_video_id, "")
        self.movie.save(update_fields=["trailer_url"])
        response = self.client.get(reverse("movie_detail", args=[self.movie.pk]))
        self.assertNotContains(response, 'data-trailer-open')


class CinemaLocationContributionTests(TestCase):
    def setUp(self):
        self.cinema = Cinema.objects.create(
            name="Central", city_en="Almaty", city_ru="Алматы",
            address_en="12 Abay Ave", address_ru="Абая 12",
        )

    def test_tc08_2gis_link_encodes_english_address(self):
        response = self.client.get(reverse("home"))
        self.assertContains(
            response, f"https://2gis.kz/almaty/search/{quote(self.cinema.address_en)}"
        )
        self.assertContains(response, 'rel="noopener noreferrer"')

    def test_tc09_2gis_link_uses_russian_address_in_russian_locale(self):
        self.client.post(reverse("set_language"), {"language": "ru", "next": reverse("home")})
        response = self.client.get(reverse("home"))
        self.assertContains(
            response, f"https://2gis.kz/almaty/search/{quote(self.cinema.address_ru)}"
        )
        self.assertContains(response, "Алматы · Абая 12")


class RefundContributionTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("refund_owner", password="SafePass123!")
        self.other = User.objects.create_user("other_viewer", password="SafePass123!")
        movie = Movie.objects.create(
            title_en="Film", title_ru="Фильм", description_en="Story",
            description_ru="История", duration=100, year=2026,
        )
        cinema = Cinema.objects.create(
            name="Central", city_en="Almaty", city_ru="Алматы",
            address_en="Abay", address_ru="Абая",
        )
        hall = Hall.objects.create(cinema=cinema, name="One", rows_count=1, seats_per_row=2)
        showtime = Showtime.objects.create(
            movie=movie, hall=hall, starts_at=timezone.now() + timedelta(days=1), price=2000,
        )
        self.order = Reservation.objects.create(
            user=self.owner, showtime=showtime, status="paid",
            expires_at=timezone.now() + timedelta(minutes=10), payment_method="card",
            paid_at=timezone.now(),
        )
        self.ticket = Ticket.objects.create(
            user=self.owner, reservation=self.order, showtime=showtime,
            seat=hall.seats.first(), status=Ticket.BOOKED, price=2000,
        )

    def test_tc10_repeated_refund_request_keeps_ticket_refunded(self):
        self.client.force_login(self.owner)
        url = reverse("ticket_refund", args=[self.ticket.pk])
        self.assertRedirects(self.client.post(url), reverse("my_tickets"))
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.REFUNDED)
        self.assertRedirects(self.client.post(url), reverse("my_tickets"))
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.REFUNDED)
        self.assertEqual(self.order.tickets.count(), 1)

    def test_tc11_other_user_cannot_refund_ticket(self):
        self.client.force_login(self.other)
        response = self.client.post(reverse("ticket_refund", args=[self.ticket.pk]))
        self.assertEqual(response.status_code, 404)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.BOOKED)
