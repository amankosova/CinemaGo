from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Cinema, Hall, Movie, Showtime, Ticket


class BookingTests(TestCase):
    def setUp(self):
        movie = Movie.objects.create(
            title_en="Film", title_ru="Фильм", description_en="d", description_ru="о", duration=100, year=2020
        )
        cinema = Cinema.objects.create(name="C", city_en="A", city_ru="А", address_en="a", address_ru="а")
        hall = Hall.objects.create(cinema=cinema, name="1", rows_count=2, seats_per_row=3)
        self.showtime = Showtime.objects.create(
            movie=movie, hall=hall, starts_at=timezone.now() + timedelta(days=1), price=1000
        )
        self.seats = list(hall.seats.all())
        self.alice = User.objects.create_user("alice", password="pass12345")
        self.bob = User.objects.create_user("bob", password="pass12345")

    def book(self, user, *seats):
        self.client.force_login(user)
        url = reverse("booking_create", args=[self.showtime.pk])
        return self.client.post(url, {"seats": [s.id for s in seats]})

    def test_seat_cannot_be_booked_twice(self):
        self.book(self.alice, self.seats[0], self.seats[1])
        self.book(self.bob, self.seats[1], self.seats[2])
        self.assertEqual(Ticket.objects.count(), 2)

    def test_cancel_frees_the_seat(self):
        self.book(self.alice, self.seats[0])
        ticket = Ticket.objects.get()
        self.client.post(reverse("ticket_cancel", args=[ticket.pk]))
        self.book(self.bob, self.seats[0])
        self.assertEqual(Ticket.objects.filter(status=Ticket.BOOKED).count(), 1)

    def test_panel_is_for_staff_only(self):
        self.assertEqual(self.client.get(reverse("panel")).status_code, 302)
        self.client.force_login(self.alice)
        self.assertEqual(self.client.get(reverse("panel")).status_code, 403)
        self.alice.is_staff = True
        self.alice.save()
        self.assertEqual(self.client.get(reverse("panel")).status_code, 200)
