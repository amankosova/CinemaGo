from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from cinema.models import Cinema, Genre, Hall, Movie, Showtime


class PanelPermissionsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.regular_user = user_model.objects.create_user("regular", password="pass12345")
        cls.staff_user = user_model.objects.create_user(
            "staff", password="pass12345", is_staff=True
        )
        cls.genre = Genre.objects.create(name_en="Drama", name_ru="Драма")
        cls.movie = Movie.objects.create(
            title_en="Film", title_ru="Фильм", description_en="Description",
            description_ru="Описание", genre=cls.genre, duration=100, year=2020,
        )
        cls.cinema = Cinema.objects.create(
            name="Cinema", city_en="City", city_ru="Город",
            address_en="Address", address_ru="Адрес",
        )
        cls.hall = Hall.objects.create(
            cinema=cls.cinema, name="1", rows_count=2, seats_per_row=3
        )
        cls.showtime = Showtime.objects.create(
            movie=cls.movie, hall=cls.hall,
            starts_at=timezone.now() + timedelta(days=1), price=1000,
        )

    def payload(self, key, *, edited=False):
        if key == "movies":
            return {
                "title_en": "Edited film" if edited else "New film",
                "title_ru": "Новый фильм", "description_en": "Description",
                "description_ru": "Описание", "genre": self.genre.pk,
                "duration": 110, "year": 2021,
            }
        if key == "cinemas":
            return {
                "name": "Edited cinema" if edited else "New cinema",
                "city_en": "City", "city_ru": "Город",
                "address_en": "Address", "address_ru": "Адрес",
            }
        if key == "halls":
            return {
                "cinema": self.cinema.pk,
                "name": "Edited hall" if edited else "New hall",
                "rows_count": 2, "seats_per_row": 3,
            }
        if key == "genres":
            return {
                "name_en": "Edited genre" if edited else "New genre",
                "name_ru": "Новый жанр",
            }
        return {
            "movie": self.movie.pk, "hall": self.hall.pk,
            "starts_at": timezone.localtime(
                timezone.now() + timedelta(days=2)
            ).strftime("%Y-%m-%dT%H:%M"),
            "price": 1500 if edited else 1200,
        }

    def targets(self):
        return (
            ("movies", Movie, self.movie),
            ("cinemas", Cinema, self.cinema),
            ("halls", Hall, self.hall),
            ("showtimes", Showtime, self.showtime),
            ("genres", Genre, self.genre),
        )

    def identifying_value(self, key, obj):
        field = {
            "movies": "title_en",
            "cinemas": "name",
            "halls": "name",
            "showtimes": "price",
            "genres": "name_en",
        }[key]
        return getattr(obj, field)

    def test_all_panel_pages_require_staff(self):
        urls = [reverse("panel")]
        for key in ("movies", "cinemas", "halls", "showtimes", "genres"):
            urls.extend((reverse("panel_list", args=[key]), reverse("panel_create", args=[key])))
        for key, _model, obj in self.targets():
            urls.extend((
                reverse("panel_edit", args=[key, obj.pk]),
                reverse("panel_delete", args=[key, obj.pk]),
            ))

        for url in urls:
            with self.subTest(url=url, role="anonymous"):
                response = self.client.get(url)
                self.assertRedirects(response, f"{reverse('login')}?next={url}")

        self.client.force_login(self.regular_user)
        for url in urls:
            with self.subTest(url=url, role="regular"):
                self.assertEqual(self.client.get(url).status_code, 403)

        self.client.force_login(self.staff_user)
        for url in urls:
            with self.subTest(url=url, role="staff"):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_anonymous_and_regular_post_requests_cannot_change_catalogue(self):
        for role in (None, self.regular_user):
            self.client.logout()
            if role:
                self.client.force_login(role)
            for key, model, obj in self.targets():
                with self.subTest(role=role, section=key):
                    original_count = model.objects.count()
                    original_value = self.identifying_value(key, obj)
                    requests = (
                        (reverse("panel_create", args=[key]), self.payload(key)),
                        (reverse("panel_edit", args=[key, obj.pk]), self.payload(key, edited=True)),
                        (reverse("panel_delete", args=[key, obj.pk]), {}),
                    )
                    for url, data in requests:
                        response = self.client.post(url, data)
                        if role:
                            self.assertEqual(response.status_code, 403)
                        else:
                            self.assertRedirects(response, f"{reverse('login')}?next={url}")
                    self.assertEqual(model.objects.count(), original_count)
                    obj.refresh_from_db()
                    self.assertEqual(self.identifying_value(key, obj), original_value)

    def test_staff_can_create_edit_and_delete_catalogue_items(self):
        self.client.force_login(self.staff_user)
        for key, model, obj in self.targets():
            with self.subTest(section=key):
                original_count = model.objects.count()
                response = self.client.post(reverse("panel_create", args=[key]), self.payload(key))
                self.assertRedirects(response, reverse("panel_list", args=[key]))
                self.assertEqual(model.objects.count(), original_count + 1)
                new_obj = model.objects.exclude(pk=obj.pk).get()

                response = self.client.post(
                    reverse("panel_edit", args=[key, new_obj.pk]), self.payload(key, edited=True)
                )
                self.assertRedirects(response, reverse("panel_list", args=[key]))
                new_obj.refresh_from_db()
                self.assertEqual(self.identifying_value(key, new_obj), {
                    "movies": "Edited film",
                    "cinemas": "Edited cinema",
                    "halls": "Edited hall",
                    "showtimes": 1500,
                    "genres": "Edited genre",
                }[key])

                response = self.client.post(reverse("panel_delete", args=[key, new_obj.pk]))
                self.assertRedirects(response, reverse("panel_list", args=[key]))
                self.assertEqual(model.objects.count(), original_count)
