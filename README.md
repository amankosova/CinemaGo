# CinemaGo — combined demo project (15 films)

This archive combines the **new Django/SQLite project** with the compatible catalogue,
filters, showtime/seat-selection and booking screens. The old `cineseat` architecture
was reviewed as a reference; its models and service code were **not** blindly copied,
because it uses incompatible Customer/Event/Booking tables.

## Start from scratch (Windows / VS Code)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py seed_cinemago
python manage.py check
python manage.py test
python manage.py runserver
```

Open http://127.0.0.1:8000/movies/ and select a movie with future showtimes.
To create an account use `/accounts/register/`. For the team management panel,
create a LOCAL staff/admin account using `python manage.py createsuperuser` and visit `/panel/`.

**Do not unzip this onto your existing working directory.** Use a fresh folder and
copy any personal changes consciously. The archive does NOT contain anyone's
local `db.sqlite3`, `.git`, `.venv`, or credentials.

## Posters

All **15 user-supplied `.webp`** files are in `posters/` (separate folder).
The `seed_cinemago` management command copies them into `media/posters/` and links
them with `Movie.poster`. The media folder is generated locally and excluded from Git.
Run the command again to replenish missing poster copies; it does not delete data.

## Content and limitations

- Movie titles and listed genres come from the provided catalogue; cinema names and
  addresses are sample catalogue text. **Year 2026, duration 100 minutes, ticket
  prices, halls and times are placeholders.**
- There are 15 seeded catalogue titles. If an existing SQLite DB contains old titles,
  `seed_cinemago` does NOT delete them. Seed a fresh DB for exactly 15.
- The `Movie` data model supports one primary genre, not multiple tags.
- User flow: catalogue/search/sort/filter → movie details → showtime → seat map →
  booking confirmation → saved ticket → My Tickets/cancellation.
- Booking is a learning/demo flow. No real payments, QR issuance, timer-based payment,
  live ticket inventory API, or production-ready concurrency guarantees are included.
  The previous `cineseat` implementation of mock payments/hold expiration was not
  transplanted, as its data schema differs.
- Django password hashing and login/logout are built-in. Login-attempt throttling
  is not included; this is not ready for internet deployment.
- Source image assets were provided by the user. Ensure you have rights to distribute
  the posters outside the classroom.

## Verification

We validated Python syntax and archive asset completeness. A Django end-to-end
run could not be completed in this build environment because Django dependencies
were unavailable; execute the commands above and check actual results locally.

# CinemaGo — Movie Ticket Booking System

CinemaGo is a web-based cinema ticket booking application designed to streamline the process of browsing movies, selecting showtimes, choosing seats, and reserving tickets. Built with **Django** and **SQLite**, the platform features a dedicated Admin Panel for catalogue management and a role-based access control matrix to ensure secure interactions.

---

##  Key Features & Functional Modules

### 1. Authentication & User Profile
- **User Registration & Authentication:** Secure login and logout functionality for users.
- **Role Permissions:** Distinct permissions for Guests, Registered Users, and System Administrators.
- **Profile Management:** View registered user profile information (Username, Email).

### 2. Movie Catalogue & Showtimes
- **Movie Browsing & Search:** Filter and search movies by title or genre with interactive details (posters, ratings, descriptions).
- **Showtimes & Schedules:** Browse upcoming session dates, screening times, and assigned cinema halls.

### 3. Seat Selection & Booking System
- **Interactive Seat Map:** Real-time seat availability preview per showtime.
- **Ticket Reservation:** Booking confirmation for authenticated users.
- **Booking History:** Personal history view for active and past movie reservations with cancellation support.

### 4. Admin Management (CRUD)
- **Catalogue Control:** System Admins can add, update, or remove movies.
- **Schedule Management:** Full CRUD operations for showtimes and cinema hall assignments.
- **User Administration:** View registered users and manage access roles.

---

## Project Architecture & Roles

The system development adheres to the **Five Main Project Areas**:

1. **Systems Analysis & Requirements:** Defined 21 Functional Requirements (FR-01 to FR-21), Use-Case Diagram (UC-01 to UC-10), and Business Rules.
2. **Data & Database:** Designed relational schema (`Users`, `Movies`, `Showtimes`, `Halls`, `Bookings`) with SQLite.
3. **Application & Development:** Clean Django MVT architecture with modular apps (`accounts`, `cinema`, `panel`).
4. **Architecture & Security:** Enforced Role-Based Access Control (RBAC) via custom authentication and decorators.
5. **Testing, Analytics & Integration:** Unit testing suite, integration test scenarios, and user acceptance criteria verification.
