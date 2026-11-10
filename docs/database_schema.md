# CinemaGo — Database Schema

## 1. Overview

CinemaGo is a web-based cinema ticket booking system developed using Django.

The database contains models for movies, genres, cinemas, halls, seats, showtimes, and tickets.

This document focuses on the Movie and Genre tables.

## 2. Genre Table (Movie Category)

| Field | Data Type | Description |
|---|---|---|
| id | Primary Key | Unique genre identifier |
| name_en | VARCHAR(60) | Genre name in English |
| name_ru | VARCHAR(60) | Genre name in Russian |

## 3. Movie Table

| Field | Data Type | Description |
|---|---|---|
| id | Primary Key | Unique movie identifier |
| title_en | VARCHAR(150) | Movie title in English |
| title_ru | VARCHAR(150) | Movie title in Russian |
| description_en | TEXT | English description |
| description_ru | TEXT | Russian description |
| genre_id | Foreign Key | References Genre |
| duration | Positive Integer | Duration in minutes |
| year | Positive Integer | Release year |
| poster | VARCHAR(100) | Image file path |

## 4. Relationship

One Genre can contain multiple Movies.

Each Movie can belong to one Genre or have no Genre.

Relationship: Genre (1) → Movie (N)

Foreign Key: Movie.genre_id → Genre.id

Deletion behavior: SET_NULL.

## 5. Database Migration

Migration file: cinema/migrations/0001_initial.py

Migration command:

`python manage.py migrate`

Verification command:

`python manage.py showmigrations cinema`

Verified result:

`[X] 0001_initial`

The initial cinema migration was successfully applied to the local database.

## 6. Conclusion

The existing Django models provide the database structure needed to manage movies and movie categories. No duplicate Movie or Category models are required.
