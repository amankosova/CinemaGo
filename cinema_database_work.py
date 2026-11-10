"""CinemaGo sample catalogue based on a user-provided kino.kz listing.

Run from the CinemaGo project root:
    python cinema_database_work.py

IMPORTANT: Movie titles, categories, cinema names and addresses are taken from
that listing. Runtime, year, descriptions, hall layouts, dates and ticket prices
are DEMONSTRATION PLACEHOLDERS, not verified real-world listings. No images used.
The script only creates missing records; it does not overwrite or delete data.
"""
import os
from datetime import datetime, time, timedelta
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.db import connection, transaction
from django.db.models import Count, F
from django.utils import timezone
from cinema.models import Genre, Movie, Cinema, Hall, Seat, Showtime

# title, genres as listed. First genre is used because the current Django Movie
# model has only one genre ForeignKey rather than multiple genres per film.
MOVIES = [
    ('Дюна: Часть третья', 'боевик • драма'),
    ('Бажа кинода', 'комедия'),
    ('Заманback 2', 'драма • комедия'),
    ('Бауыр', 'комедия'),
    ('Кот в шляпе', 'мультфильм • фэнтези'),
    ('Шымыр', 'боевик • экшн'),
    ('Қара түйін', 'детектив • триллер'),
    ('Құдірет', 'драма'),
    ('Кит: Во тьме глубин', 'драма • триллер'),
    ('Зверь', 'боевик • драма'),
    ('Остров забвения', 'приключения • комедия'),
    ('Сумерки. Сага. Затмение', 'мелодрама • фэнтези'),
    ('Роллинг Лауд. Дикое веселье', 'комедия'),
    ('Клэйфейс', 'боевик • хоррор'),
    ('Маленькие демоны путешествуют на Запад', 'анимация • комедия'),
    ('Сердце зверя', 'боевик • приключения'),
    ('Барашек Шон и Чудище Лохматое', 'комедия • мультфильм'),
    ('Пункт назначения: Мост №13', 'ужасы • триллер'),
    ('Обитель зла', 'ужасы'),
    ('Жарығым-ай', 'драма'),
    ('Тайный дневник Верити', 'детектив • драма'),
    ('Джордж Майкл: The Faith Tour', 'документальный • музыка'),
    ('Живая книга', 'приключения • фэнтези'),
    ('Цикл зверя', 'мистика • хоррор'),
    ('Синистер. Дом мёртвых', 'ужасы'),
    ('Гнев улья', 'криминал • триллер'),
    ('Сказка о потерянном времени', 'приключения • детский'),
    ('Фьорд', 'драма'),
    ('Последнее проклятие', 'ужасы'),
    ('Зверодвиж', 'анимация • приключения'),
    ('Чудо-Юдо', 'приключения • фэнтези'),
    ('Алан туралы аңыз', 'мультфильм'),
    ('Дитя ветра', 'приключения • фэнтези'),
    ('Чужая мама', 'ужасы'),
    ('До последнего грамма', 'боевик • приключения'),
    ('Street Fighter', 'боевик'),
    ('Подводная братва. На страже рифа', 'приключения • мультфильм'),
    ('Как приручить монстров: Рождественский переполох', 'приключения • мультфильм'),
    ('1+3', 'комедия'),
    ('Приключения мамонтенка. В поисках мамы', 'приключения • мультфильм'),
    ('Мстители: Финал. Расширенная версия', 'боевик • приключения'),
    ('7 қарақшы', 'боевик • приключения'),
    ('Моана', 'боевик • приключения'),
    ('Одиссея', 'боевик • приключения'),
    ('Баден-Баден: Любовный напиток', 'опера'),
    ('Роберт Уилсон: Красота – в загадке', 'документальный • биография'),
    ('Ноймайер: Щелкунчик', 'балет'),
    ('Вишнёвый сад', 'спектакль'),
    ('Великие и брутальные', 'драма • экшн'),
    ('Караваджо: Се человек', 'документальный • искусство'),
    ('Дюна', 'боевик • приключения'),
    ('Махаббат жасқа қарамайды', 'комедия'),
    ('Плетёный муж', 'драма • история'),
    ('Приключения пингвиненка', 'приключения • комедия'),
    ('Рамаяна: Восхождение легенды', 'боевик • приключения'),
    ('Скрудж', 'драма • комедия'),
    ('Инфлюенсер', 'хоррор'),
    ('Психопатка', 'комедия • хоррор'),
    ('История Джин', 'драма • история'),
    ('Театр Ан дер Вин: Норма', 'опера'),
    ('Күлпәш', 'драма'),
]

# Venue, supplied address (Almaty). Theatre excluded because it is not listed
# as a cinema; project currently models cinemas only.
CINEMAS = [
    ('Halyk IMAX Aport Cinema East', 'Кульджинский тракт, 106, молл Aport East, 2 этаж'),
    ('Kinoforum 15 (ТРЦ Forum)', 'ул. Сейфуллина, 617, ТРЦ «Forum Almaty», 5-й этаж'),
    ('Cinemax Dostyk Multiplex', 'Самал-2, д. 111, уг. ул. Жолдасбекова, ТРЦ «Достык Плаза»'),
    ('Lumiera Cinema (ЦУМ)', 'пр. Абылай хана, 62, «Арбат»'),
    ('Kinopark 11 (Есентай) IMAX', 'пр. Аль-Фараби, 77/8, ТЦ «Esentai Mall»'),
    ('Chaplin MEGA Alma-Ata (ул. Розыбакиева)', 'Розыбакиева, 247А, «MEGA Alma-Ata»'),
    ('Chaplin MEGA Park (ул. Макатаева)', 'ул. Макатаева, 127, 3-й этаж'),
    ('Chaplin ADK', 'ул. Сатпаева, 90 (уг. ул. Тлендиева), ТРК «АDК»'),
    ('Kinopark 8 Moskva', 'пр. Абая, уг. пр. Алтынсарина, ТРЦ «MOSKVA Metropolitan»'),
    ('Kinopark 5 Atakent', 'ул. Тимирязева, 42, ТРЦ «Atakent Mall»'),
    ('Kinopark 6 (Спутник)', 'м-н Мамыр-1, 8А, ТРК «Спутник», 3-й этаж'),
    ('Kinoplexx 6 Almaty Mall', 'ул. Жандосова, 83, ТРЦ «Almaty Mall», 3-й этаж'),
    ('Aport Cinema West', 'пр. Райымбека, западное напр., до указателя «Апорт», 2-й этаж'),
    ('Kinopark 4 Globus', 'пр. Абая, 109в, ТРЦ «Globus», 2-й этаж'),
    ('Kinoplexx 5 Maxima', 'пр. Райымбека, 239Г, ТРК «Maxima», 3-й этаж'),
    ('Saryarqa Cinema', 'ул. Алтынсарина, 24, уг. пр. Абая'),
    ('Kinoplexx 12 Alatau Plaza', 'ул. Ырысты 46/4, ТЦ Alatau Plaza'),
    ('Киноцентр Арман (ТРЦ Asia Park Алматы)', 'пр. Райымбека, 514А, уг. ул. Саина'),
    ('Арман 3D (ТРЦ МART, Алматы)', 'ул. Рихарда Зорге, 18 (р-н Алматы 1)'),
    ('Арман 3D (пр. Достык)', 'пр. Достык, 104'),
]

# Exact movie schedules were NOT supplied. Create eight clearly demo-only
# showtimes in four synthetic halls. Prices are example KZT figures.
DEMO_SHOWTIMES = [
    ('Бажа кинода', 0, 18, 30, 2500, 1),
    ('Заманback 2', 1, 19, 0, 2800, 2),
    ('Бауыр', 2, 17, 0, 2400, 3),
    ('Қара түйін', 3, 20, 0, 3000, 4),
    ('Кот в шляпе', 0, 12, 0, 2200, 5),
    ('Шымыр', 1, 16, 30, 2600, 6),
    ('Жарығым-ай', 2, 15, 0, 2300, 7),
    ('Дюна: Часть третья', 3, 21, 0, 3500, 8),
]


def main():
    created = {'genres': 0, 'movies': 0, 'cinemas': 0, 'halls': 0, 'showtimes': 0}
    sample_movie_ids = {}
    demo_halls = []
    with transaction.atomic():
        for title, raw_genres in MOVIES:
            primary_genre = raw_genres.split(' • ')[0]
            genre, new = Genre.objects.get_or_create(
                name_ru=primary_genre,
                defaults={'name_en': primary_genre},
            )
            created['genres'] += int(new)
            movie, new = Movie.objects.get_or_create(
                title_ru=title,
                defaults={
                    'title_en': title,  # not a verified English translation
                    'description_ru': f'Демо-каталог. Жанры из списка: {raw_genres}. Длительность и год не подтверждены.',
                    'description_en': f'Demo catalogue. Source genres: {raw_genres}. Runtime/year are placeholders.',
                    'duration': 100,  # placeholder: source gave no runtime
                    'year': 2026,  # placeholder: source gave no release year
                    'genre': genre,
                }
            )
            created['movies'] += int(new)
            sample_movie_ids[title] = movie

        for name, address in CINEMAS:
            cinema, new = Cinema.objects.get_or_create(
                name=name,
                defaults={'city_en': 'Almaty', 'city_ru': 'Алматы',
                          'address_en': address, 'address_ru': address},
            )
            created['cinemas'] += int(new)
            if len(demo_halls) < 4:
                hall, new = Hall.objects.get_or_create(
                    cinema=cinema, name='Demo Hall 1',
                    defaults={'rows_count': 4, 'seats_per_row': 8},
                )
                created['halls'] += int(new)
                demo_halls.append(hall)

        base = timezone.localdate() + timedelta(days=1)
        for movie_title, hall_index, hour, minute, price, day_offset in DEMO_SHOWTIMES:
            hall = demo_halls[hall_index]
            start = timezone.make_aware(
                datetime.combine(base + timedelta(days=day_offset), time(hour, minute)),
                timezone.get_current_timezone(),
            )
            _, new = Showtime.objects.get_or_create(
                movie=sample_movie_ids[movie_title], hall=hall, starts_at=start,
                defaults={'price': price},
            )
            created['showtimes'] += int(new)

    duplicate_seats = list(Seat.objects.values('hall_id', 'row', 'number')
                           .annotate(n=Count('id')).filter(n__gt=1)[:10])
    incorrect_halls = list(Hall.objects.annotate(actual=Count('seats'))
                            .exclude(actual=F('rows_count') * F('seats_per_row'))
                            .values('id', 'name', 'actual')[:10])
    with connection.cursor() as cursor:
        cursor.execute('PRAGMA foreign_key_check')
        broken_fks = cursor.fetchall()

    lines = [
        'CinemaGo | Movie & Showtime Data Work',
        'SOURCE: film titles, category labels, cinema names and addresses from the user-provided kino.kz catalogue text.',
        'DEMO ONLY: duration=100 min, year=2026, descriptions, demo hall sizes, showtime dates/prices are NOT real listings.',
        'Genres: current Movie model accepts only ONE genre, so the first listed genre is used; all source genres are preserved in the description.',
        '',
        'NEW RECORDS CREATED ON THIS RUN:',
        *[f'  {name}: {count}' for name, count in created.items()],
        '',
        f'DATABASE TOTALS: films={Movie.objects.count()}, cinemas={Cinema.objects.count()}, '
        f'showtimes={Showtime.objects.count()}, halls={Hall.objects.count()}, seats={Seat.objects.count()}',
        '', 'DEMO SHOWTIMES (Movie -> Showtime -> Hall -> Cinema):',
    ]
    for title, *_ in DEMO_SHOWTIMES:
        m = sample_movie_ids[title]
        for s in Showtime.objects.filter(movie=m, hall__in=demo_halls).select_related('hall__cinema'):
            lines.append(f'  {title} | {timezone.localtime(s.starts_at):%Y-%m-%d %H:%M} | '
                         f'{s.price} KZT | {s.hall.name} | {s.hall.cinema.name}')
    lines += ['', 'DATA INTEGRITY CHECKS:',
              f'  Duplicate seat positions within a hall: {len(duplicate_seats)} {duplicate_seats}',
              f'  Hall seat count mismatches: {len(incorrect_halls)} {incorrect_halls}',
              f'  SQLite foreign key violations: {len(broken_fks)} {broken_fks[:10]}']
    passed = not (duplicate_seats or incorrect_halls or broken_fks)
    lines.append('RESULT: ' + ('CHECKS PASSED' if passed else 'REVIEW REQUIRED'))
    report_path = Path(__file__).resolve().parent / 'database_evidence.txt'
    report_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines))
    print('\nEvidence report written to:', report_path)

if __name__ == '__main__':
    main()
