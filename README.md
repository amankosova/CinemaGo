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
