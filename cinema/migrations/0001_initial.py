

import cinema.models
import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Cinema",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100, verbose_name="Name")),
                (
                    "city_en",
                    models.CharField(max_length=60, verbose_name="City (English)"),
                ),
                (
                    "city_ru",
                    models.CharField(max_length=60, verbose_name="City (Russian)"),
                ),
                (
                    "address_en",
                    models.CharField(max_length=200, verbose_name="Address (English)"),
                ),
                (
                    "address_ru",
                    models.CharField(max_length=200, verbose_name="Address (Russian)"),
                ),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Genre",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name_en",
                    models.CharField(max_length=60, verbose_name="Name (English)"),
                ),
                (
                    "name_ru",
                    models.CharField(max_length=60, verbose_name="Name (Russian)"),
                ),
            ],
            options={
                "ordering": ["name_en"],
            },
        ),
        migrations.CreateModel(
            name="Hall",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=60, verbose_name="Hall name")),
                (
                    "rows_count",
                    models.PositiveIntegerField(
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(26),
                        ],
                        verbose_name="Rows",
                    ),
                ),
                (
                    "seats_per_row",
                    models.PositiveIntegerField(
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(30),
                        ],
                        verbose_name="Seats in a row",
                    ),
                ),
                (
                    "cinema",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="halls",
                        to="cinema.cinema",
                        verbose_name="Cinema",
                    ),
                ),
            ],
            options={
                "ordering": ["cinema", "name"],
            },
        ),
        migrations.CreateModel(
            name="Movie",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "title_en",
                    models.CharField(max_length=150, verbose_name="Title (English)"),
                ),
                (
                    "title_ru",
                    models.CharField(max_length=150, verbose_name="Title (Russian)"),
                ),
                (
                    "description_en",
                    models.TextField(verbose_name="Description (English)"),
                ),
                (
                    "description_ru",
                    models.TextField(verbose_name="Description (Russian)"),
                ),
                (
                    "duration",
                    models.PositiveIntegerField(verbose_name="Duration (min)"),
                ),
                ("year", models.PositiveIntegerField(verbose_name="Year")),
                (
                    "poster",
                    models.ImageField(
                        blank=True, upload_to="posters/", verbose_name="Poster"
                    ),
                ),
                (
                    "genre",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="cinema.genre",
                        verbose_name="Genre",
                    ),
                ),
            ],
            options={
                "ordering": ["title_en"],
            },
        ),
        migrations.CreateModel(
            name="Seat",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("row", models.PositiveIntegerField()),
                ("number", models.PositiveIntegerField()),
                (
                    "hall",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="seats",
                        to="cinema.hall",
                    ),
                ),
            ],
            options={
                "ordering": ["row", "number"],
            },
        ),
        migrations.CreateModel(
            name="Showtime",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("starts_at", models.DateTimeField(verbose_name="Starts at")),
                ("price", models.PositiveIntegerField(verbose_name="Price (KZT)")),
                (
                    "hall",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="showtimes",
                        to="cinema.hall",
                        verbose_name="Hall",
                    ),
                ),
                (
                    "movie",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="showtimes",
                        to="cinema.movie",
                        verbose_name="Movie",
                    ),
                ),
            ],
            options={
                "ordering": ["starts_at"],
            },
        ),
        migrations.CreateModel(
            name="Ticket",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("booked", "Booked"), ("cancelled", "Cancelled")],
                        default="booked",
                        max_length=10,
                    ),
                ),
                ("price", models.PositiveIntegerField()),
                (
                    "code",
                    models.CharField(
                        default=cinema.models.make_ticket_code, max_length=6
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "seat",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tickets",
                        to="cinema.seat",
                    ),
                ),
                (
                    "showtime",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tickets",
                        to="cinema.showtime",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tickets",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="seat",
            constraint=models.UniqueConstraint(
                fields=("hall", "row", "number"), name="unique_seat_in_hall"
            ),
        ),
        migrations.AddConstraint(
            model_name="ticket",
            constraint=models.UniqueConstraint(
                condition=models.Q(("status", "booked")),
                fields=("showtime", "seat"),
                name="one_active_ticket_per_seat",
            ),
        ),
    ]
