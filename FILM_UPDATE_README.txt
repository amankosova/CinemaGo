CinemaGo film metadata update — 15 films, RU/EN/KZ descriptions.

Run in a NEW folder or back up your working project and db.sqlite3 before applying changes.
1. py -m venv .venv
2. .\.venv\Scripts\Activate.ps1
3. python -m pip install -r requirements.txt
4. python manage.py migrate
5. python manage.py seed_cinemago
6. python manage.py check
7. python manage.py test
8. python manage.py runserver

If updating an existing CinemaGo checkout: merge files carefully; do not overwrite your db.sqlite3.
The migration 0002 adds fields and genre many-to-many associations. It does not delete tickets, users, or showtimes.
Seed refreshes curated fields for the 15 matching titles and keeps unrelated movies, showtimes, user data untouched.
Only film metadata is authored in three languages. The whole website UI still needs translation and a language switcher.
English/Kazakh summaries are paraphrased translations; movie data should be reviewed before publication.
