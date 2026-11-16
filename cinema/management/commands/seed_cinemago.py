import json
from datetime import datetime, time, timedelta
from pathlib import Path
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from cinema.models import Cinema, Genre, Hall, Movie, Showtime

# Data: user-supplied catalogue, not live cinema listings.
# Showtime dates and prices are classroom demonstration values; movie metadata comes from the curated film dataset.
MOVIES = [('Дюна: Часть третья', 'duna3.webp', 'боевик • драма'), ('Бажа кинода', 'bazha_kinoda.webp', 'комедия'), ('Заманback 2', 'zamanback2.webp', 'драма • комедия'), ('Бауыр', 'baur.webp', 'комедия'), ('Кот в шляпе', 'kot_v_sh.webp', 'мультфильм • фэнтези'), ('Шымыр', 'shymyr.webp', 'боевик • экшн'), ('Қара түйін', 'qara_tuyon.webp', 'детектив • триллер'), ('Құдірет', 'qudiret.webp', 'драма'), ('Кит: Во тьме глубин', 'kit.webp', 'драма • триллер'), ('Зверь', 'zver.webp', 'боевик • драма'), ('Остров забвения', 'ostrov_zabv.webp', 'приключения • комедия'), ('Сумерки. Сага. Затмение', 'sumerki.webp', 'мелодрама • фэнтези'), ('Роллинг Лауд. Дикое веселье', 'rolling.webp', 'комедия'), ('Клэйфейс', 'clayface.webp', 'боевик • хоррор'), ('Маленькие демоны путешествуют на Запад', 'little_demons.webp', 'анимация • комедия')]

CINEMAS = [('Halyk IMAX Aport Cinema East', 'Кульджинский тракт, 106, молл Aport East, 2 этаж'), ('Kinoforum 15 (ТРЦ Forum)', 'ул. Сейфуллина, 617, ТРЦ «Forum Almaty», 5-й этаж'), ('Cinemax Dostyk Multiplex', 'Самал-2, д. 111, ТРЦ «Достык Плаза»'), ('Lumiera Cinema (ЦУМ)', 'пр. Абылай хана, 62, «Арбат»')]

class Command(BaseCommand):
    help = "Seed 15 demo films, posters, cinemas, halls and future showtimes. Safe to run repeatedly."

    def handle(self, *args, **kwargs):
        source = Path(settings.BASE_DIR) / "posters"
        target = Path(settings.MEDIA_ROOT) / "posters"
        target.mkdir(parents=True, exist_ok=True)
        for _, filename, _ in MOVIES:
            src = source / filename
            if not src.exists():
                raise FileNotFoundError(f"Missing poster asset: {src}")
            if not (target / filename).exists():
                shutil.copyfile(src, target / filename)

        records = json.loads((Path(settings.BASE_DIR) / 'cinema' / 'data' / 'movies_15_i18n.json').read_text(encoding='utf-8'))
        details = {row['title_ru']: row for row in records}
        with transaction.atomic():
            movie_objects = []
            for title, filename, raw_genres in MOVIES:
                details_row = details[title]
                primary = details_row['genres_localized'][0]
                genre, _ = Genre.objects.get_or_create(
                    name_ru=primary['ru'], defaults={'name_en':primary['en'], 'name_kk':primary['kk']}
                )
                movie, _ = Movie.objects.get_or_create(
                    title_ru=title,
                    defaults={
                        'title_en':details_row['title_en'],
                        'description_ru':details_row['description_ru'],
                        'description_en':details_row['description_en'],
                        'duration':details_row['duration_minutes'],
                        'year':details_row['year'],
                        "genre":genre,
                        "poster":"posters/" + filename,
                    },
                )
                # Update only records selected in the classroom catalogue; no other movies are deleted.
                movie.title_en = details_row['title_en']
                movie.title_kk = details_row['title_kk']
                movie.description_ru = details_row['description_ru']
                movie.description_en = details_row['description_en']
                movie.description_kk = details_row['description_kk']
                movie.duration = details_row['duration_minutes']
                movie.year = details_row['year']
                movie.director = details_row['director']
                movie.main_cast = ', '.join(details_row['main_cast'])
                movie.country = details_row['country']
                movie.age_rating = details_row['age_rating']
                movie.genre = genre
                if not movie.poster:
                    movie.poster = 'posters/' + filename
                movie.save()
                genre_objects = []
                for tag in details_row['genres_localized']:
                    g, _ = Genre.objects.get_or_create(name_ru=tag['ru'], defaults={'name_en':tag['en'], 'name_kk':tag['kk']})
                    # Refresh labels on pre-existing sample genres where names were untranslated.
                    if g.name_en == g.name_ru or not g.name_kk:
                        g.name_en = tag['en']
                        g.name_kk = tag['kk']
                        g.save(update_fields=['name_en', 'name_kk'])
                    genre_objects.append(g)
                movie.genres.set(genre_objects)
                movie_objects.append(movie)

            halls = []
            for name, address in CINEMAS:
                cinema, _ = Cinema.objects.get_or_create(
                    name=name, defaults={"city_ru":"Алматы","city_en":"Almaty", "address_ru":address,"address_en":address}
                )
                hall, _ = Hall.objects.get_or_create(
                    cinema=cinema, name="Demo Hall 1", defaults={"rows_count":4,"seats_per_row":8}
                )
                halls.append(hall)

            # Every one of the 15 films gets two future showtimes.
            # If future demo showtimes for a movie already exist, keep them unchanged.
            base_day = timezone.localdate() + timedelta(days=1)
            new_showtimes = 0
            for i, movie in enumerate(movie_objects):
                if movie.showtimes.filter(starts_at__gt=timezone.now()).exists():
                    continue
                for j in range(2):
                    hall = halls[(i+j)%len(halls)]
                    day = base_day + timedelta(days=(i%7)+j*7)
                    hour = (12, 15, 18, 20)[(i+j)%4]
                    start = timezone.make_aware(
                        datetime.combine(day, time(hour, 0)), timezone.get_current_timezone()
                    )
                    _, created = Showtime.objects.get_or_create(
                        movie=movie, hall=hall, starts_at=start,
                        defaults={"price":2200 + (i%5)*300},
                    )
                    new_showtimes += int(created)

        self.stdout.write(self.style.SUCCESS(
            f"CinemaGo demo ready: catalogue titles={len(MOVIES)}; "
            f"database movies={Movie.objects.count()}, showtimes={Showtime.objects.count()}, "
            f"new showtimes={new_showtimes}."
        ))
        self.stdout.write("Data is for classroom demonstration, not live cinema schedules.")
