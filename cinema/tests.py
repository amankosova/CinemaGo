from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone, translation

from .models import Cinema, Hall, Movie, Showtime, Ticket, Reservation


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

    def hold(self, user, *seats):
        self.client.force_login(user)
        response = self.client.post(reverse('booking_confirm', args=[self.showtime.pk]),
                                    {'seats':[s.id for s in seats]})
        return response

    def pay(self, reservation, method='card'):
        return self.client.post(reverse('booking_create', args=[self.showtime.pk]),
                                {'reservation':str(reservation.pk),'payment_method':method})

    def test_seat_cannot_be_booked_twice(self):
        self.assertEqual(self.hold(self.alice,self.seats[0],self.seats[1]).status_code,302)
        self.assertEqual(self.hold(self.bob,self.seats[1],self.seats[2]).status_code,302)
        self.assertEqual(Ticket.objects.filter(status=Ticket.PENDING).count(),2)

    def test_cancel_frees_the_seat(self):
        self.hold(self.alice,self.seats[0]);order=Reservation.objects.get()
        self.pay(order)
        ticket=Ticket.objects.get()
        self.client.post(reverse('ticket_cancel',args=[ticket.pk]))
        self.hold(self.bob,self.seats[0])
        self.assertEqual(Ticket.objects.filter(status=Ticket.PENDING).count(),1)

    def test_timer_expiration_releases_seats(self):
        self.hold(self.alice,self.seats[0]); order=Reservation.objects.get()
        order.expires_at=timezone.now()-timedelta(seconds=1);order.save()
        self.hold(self.bob,self.seats[0])
        order.refresh_from_db()
        self.assertEqual(order.status,'expired')
        self.assertEqual(Ticket.objects.filter(status=Ticket.PENDING).count(),1)

    def test_checkout_card_and_qr(self):
        for idx,method in enumerate(['card','qr']):
            self.hold(self.alice,self.seats[idx]);order=Reservation.objects.filter(status='pending').latest('created_at')
            page=self.client.get(reverse('checkout', args=[order.pk]))
            self.assertContains(page,'checkout-clock')
            self.assertContains(page,'Demo')
            self.pay(order,method);order.refresh_from_db()
            self.assertEqual(order.status,'paid')
            self.assertEqual(order.payment_method,method)
        self.assertEqual(Ticket.objects.filter(status=Ticket.BOOKED).count(),2)

    def test_unpaid_hold_does_not_become_paid_after_timeout(self):
        self.hold(self.alice,self.seats[0]);order=Reservation.objects.get()
        order.expires_at=timezone.now()-timedelta(seconds=1);order.save()
        self.pay(order);order.refresh_from_db()
        self.assertEqual(order.status,'expired')
        self.assertEqual(Ticket.objects.filter(status=Ticket.BOOKED).count(),0)

    def test_user_cannot_access_another_users_checkout(self):
        self.hold(self.alice,self.seats[0]);order=Reservation.objects.get()
        self.client.force_login(self.bob)
        self.assertEqual(self.client.get(reverse('checkout',args=[order.pk])).status_code,404)
        self.assertEqual(self.pay(order).status_code,404)

    def test_panel_is_for_staff_only(self):
        self.assertEqual(self.client.get(reverse("panel")).status_code, 302)
        self.client.force_login(self.alice)
        self.assertEqual(self.client.get(reverse("panel")).status_code, 403)
        self.alice.is_staff = True
        self.alice.save()
        self.assertEqual(self.client.get(reverse("panel")).status_code, 403)
        self.alice.is_superuser = True
        self.alice.save()
        self.assertEqual(self.client.get(reverse("panel")).status_code, 200)


    def test_qr_image_requires_owner_and_paid_ticket(self):
        self.hold(self.alice,self.seats[0]); order=Reservation.objects.get()
        ticket=Ticket.objects.get()
        self.assertEqual(self.client.get(reverse('ticket_qr',args=[ticket.pk])).status_code,404)
        self.pay(order)
        response=self.client.get(reverse('ticket_qr',args=[ticket.pk]))
        self.assertEqual(response.status_code,200)
        self.assertEqual(response['Content-Type'],'image/png')
        self.assertTrue(response.content.startswith(b'\x89PNG'))
        self.client.force_login(self.bob)
        self.assertEqual(self.client.get(reverse('ticket_qr',args=[ticket.pk])).status_code,404)

    def test_cancelled_ticket_qr_is_not_available(self):
        self.hold(self.alice,self.seats[0]); order=Reservation.objects.get()
        self.pay(order); ticket=Ticket.objects.get()
        self.client.post(reverse('ticket_cancel',args=[ticket.pk]))
        self.assertEqual(self.client.get(reverse('ticket_qr',args=[ticket.pk])).status_code,404)



class CatalogueAndSeatScreenTests(TestCase):
    def setUp(self):
        self.movie = Movie.objects.create(title_en="Test", title_ru="Тест", description_en="Demo", description_ru="Demo", duration=100, year=2026)
        self.cinema = Cinema.objects.create(name="Demo", city_en="Almaty", city_ru="Алматы", address_en="Demo", address_ru="Demo")
        self.hall = Hall.objects.create(cinema=self.cinema, name="1", rows_count=2, seats_per_row=3)
        self.showtime = Showtime.objects.create(movie=self.movie, hall=self.hall, starts_at=timezone.now()+timedelta(days=1), price=2200)

    def test_movie_catalogue_and_details(self):
        with translation.override("en"):
            response = self.client.get(reverse("movie_list"))
            self.assertContains(response, "Test")
        response = self.client.get(reverse("movie_detail", args=[self.movie.pk]))
        self.assertContains(response, "Demo")

    def test_seat_screen_requires_login(self):
        response = self.client.get(reverse("seat_select", args=[self.showtime.pk]))
        self.assertEqual(response.status_code, 302)

    def test_seat_screen_has_positions(self):
        self.client.force_login(User.objects.create_user("viewer", password="demo-password-123"))
        response = self.client.get(reverse("seat_select", args=[self.showtime.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A1")

    def test_genre_filter_and_sort(self):
        response = self.client.get(reverse("movie_list"), {"q":"Тест", "sort":"title_desc"})
        self.assertContains(response, "Тест")

class HeaderAndLanguageTests(TestCase):
    def setUp(self):
        self.viewer = User.objects.create_user('normal_viewer', password='safe-test-pass-012')
        self.admin = User.objects.create_superuser('site_admin', 'admin@example.com', 'safe-test-pass-012')

    def test_header_shows_admin_only_to_superuser(self):
        self.client.force_login(self.viewer)
        response = self.client.get(reverse('home'))
        self.assertContains(response, reverse('my_tickets'))
        self.assertNotContains(response, reverse('panel'))
        self.client.force_login(self.admin)
        response = self.client.get(reverse('home'))
        self.assertContains(response, reverse('panel'))

    def test_languages_have_working_switcher_endpoint(self):
        from django.utils.translation import get_language
        self.client.post(reverse('set_language'), {'language':'kk', 'next':reverse('home')})
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'Сіздің орныңыз сізді күтуде.')
        self.client.post(reverse('set_language'), {'language':'ru', 'next':reverse('home')})
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'Твоё место ждёт тебя.')
        self.client.post(reverse('set_language'), {'language':'en', 'next':reverse('home')})
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'Your seat is waiting.')

    def test_profile_contains_my_tickets_and_admin_for_superuser(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('profile'))
        self.assertContains(response, reverse('my_tickets'))
        self.assertContains(response, reverse('panel'))

    def test_preview_in_catalogue(self):
        Movie.objects.create(title_en='Film One', title_ru='Фильм один',
            description_en='Story summary', description_ru='Описание фильма',
            director='Director X', duration=95, year=2026)
        response = self.client.get(reverse('movie_list'))
        self.assertContains(response, 'movie-preview')
        self.assertContains(response, 'Director X')


class DurationSortAndFilterTests(TestCase):
    def setUp(self):
        self.short = Movie.objects.create(title_en='Short', title_ru='Короткий',
            description_en='A', description_ru='А', duration=85, year=2025)
        self.long = Movie.objects.create(title_en='Long', title_ru='Длинный',
            description_en='B', description_ru='Б', duration=155, year=2026)

    def test_duration_sorting_ascending(self):
        response = self.client.get(reverse('movie_list'), {'sort': 'duration_short'})
        self.assertEqual([m.pk for m in response.context['movies']], [self.short.pk, self.long.pk])

    def test_duration_sorting_descending(self):
        response = self.client.get(reverse('movie_list'), {'sort': 'duration_long'})
        self.assertEqual([m.pk for m in response.context['movies']], [self.long.pk, self.short.pk])

    def test_year_filter_removed_from_catalogue_form(self):
        response = self.client.get(reverse('movie_list'))
        self.assertNotContains(response, '<select name="year">', html=False)
        self.assertContains(response, 'value="year_new"')

