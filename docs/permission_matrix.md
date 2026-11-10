# CinemaGo — Permission Matrix

## 1. Overview

This document describes role-based access permissions in the CinemaGo ticket booking system.

The system distinguishes three user roles:

- **Guest:** A visitor who is not logged in.
- **Registered User:** An authenticated user without staff privileges.
- **Staff/Admin:** An authenticated user with `is_staff=True`.

## 2. Permission Matrix

| Action | Guest | Registered User | Staff/Admin |
|---|:---:|:---:|:---:|
| View movie list page | Yes | Yes | Yes |
| Access admin dashboard | No | No | Yes |
| View movies in admin panel | No | No | Yes |
| Add movie | No | No | Yes |
| Edit movie | No | No | Yes |
| Delete movie | No | No | Yes |
| Add genre | No | No | Yes |
| Edit genre | No | No | Yes |
| Delete genre | No | No | Yes |
| Manage cinemas | No | No | Yes |
| Manage halls | No | No | Yes |
| Manage showtimes | No | No | Yes |

## 3. Permission Implementation

The administrative views use the `@staff_required` decorator.

This decorator performs two checks:

1. The user must be authenticated using Django's `login_required`.
2. The user must have `is_staff=True`.

If the user is not authenticated, Django redirects the user to the configured login URL.

If the user is authenticated but does not have staff privileges, the application returns a 403 Forbidden response.

## 4. Code References

- `cinema/views.py` — public home and movie list views.
- `panel/views.py` — administrative dashboard and management operations.
- `panel/decorators.py` — staff access verification.
- `cinema/models.py` — movie, genre, and booking database models.

## 5. Security Rules

- Guest users cannot access the administrative panel.
- Regular registered users cannot manage movies or genres.
- Staff users can access the administrative management views.
- Administrative create, update, and delete operations are protected by the staff decorator.

## 6. Conclusion

CinemaGo uses Django authentication and staff-based access control to restrict administrative operations.

The permission matrix documents the access rules verified in the reviewed view and decorator code.
