
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import LoginAttempt


class ProfileTests(TestCase):

    def test_guest_redirected_to_login(self):
        response = self.client.get(reverse("profile"))
        self.assertRedirects(
            response,
            "/accounts/login/?next=/accounts/profile/"
        )

    def test_logged_in_user_sees_own_profile(self):
        user = User.objects.create_user(
            username="student",
            email="student@example.com",
            password="SafePass123!"
        )
        self.client.force_login(user)

        response = self.client.get(reverse("profile"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "student@example.com")
        self.assertContains(response, "student")

    def test_registration_creates_user(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "newstudent",
                "email": "new@example.com",
                "password1": "SecurePass123!",
                "password2": "SecurePass123!"
            }
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            User.objects.filter(username="newstudent").exists()
        )


class ProfileEditTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="profileuser",
            email="old@example.com",
            password="SafePass123!"
        )

    def test_guest_cannot_edit_profile(self):
        response = self.client.get(reverse("edit_profile"))

        self.assertEqual(response.status_code, 302)

    def test_user_can_edit_profile(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("edit_profile"),
            {
                "username": "updateduser",
                "first_name": "New",
                "last_name": "Name",
                "email": "new@example.com"
            }
        )

        self.assertRedirects(response, reverse("profile"))

        self.user.refresh_from_db()

        self.assertEqual(self.user.username, "updateduser")
        self.assertEqual(self.user.first_name, "New")
        self.assertEqual(self.user.last_name, "Name")
        self.assertEqual(self.user.email, "new@example.com")

    def test_invalid_email_does_not_update_profile(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("edit_profile"),
            {
                "username": "changeduser",
                "first_name": "New",
                "last_name": "Name",
                "email": "invalid-email"
            }
        )

        self.assertEqual(response.status_code, 200)

        self.user.refresh_from_db()

        self.assertEqual(self.user.username, "profileuser")
        self.assertEqual(self.user.email, "old@example.com")


class DeleteAccountTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="deleteuser",
            password="SafePass123!"
        )

    def test_guest_cannot_open_delete_page(self):
        response = self.client.get(reverse("delete_account"))

        self.assertEqual(response.status_code, 302)

    def test_wrong_password_does_not_delete_account(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("delete_account"),
            {"password": "WrongPassword123!"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            User.objects.filter(pk=self.user.pk).exists()
        )

    def test_correct_password_deletes_account(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("delete_account"),
            {"password": "SafePass123!"}
        )

        self.assertRedirects(response, reverse("home"))
        self.assertFalse(
            User.objects.filter(pk=self.user.pk).exists()
        )

    def test_admin_account_cannot_be_deleted(self):
        self.user.is_staff = True
        self.user.save()

        self.client.force_login(self.user)

        response = self.client.post(
            reverse("delete_account"),
            {"password": "SafePass123!"}
        )

        self.assertRedirects(response, reverse("profile"))
        self.assertTrue(
            User.objects.filter(pk=self.user.pk).exists()
        )


class LoginLockoutTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            "loginviewer",
            password="SecurePassword123!"
        )

    def test_five_failed_passwords_lock_login_for_five_minutes(self):
        for _ in range(4):
            response = self.client.post(
                reverse("login"),
                {
                    "username": "loginviewer",
                    "password": "wrong-password"
                }
            )
            self.assertEqual(response.status_code, 200)

        response = self.client.post(
            reverse("login"),
            {
                "username": "loginviewer",
                "password": "wrong-password"
            }
        )

        self.assertEqual(response.status_code, 429)
        self.assertContains(
            response,
            "Too many failed attempts",
            status_code=429
        )
        self.assertEqual(
            LoginAttempt.objects.get().failed_count,
            5
        )

        response = self.client.post(
            reverse("login"),
            {
                "username": "loginviewer",
                "password": "SecurePassword123!"
            }
        )

        self.assertEqual(response.status_code, 429)

    def test_expired_lock_allows_correct_password(self):
        for _ in range(5):
            self.client.post(
                reverse("login"),
                {
                    "username": "loginviewer",
                    "password": "wrong-password"
                }
            )

        lock = LoginAttempt.objects.get()
        lock.locked_until = timezone.now() - timedelta(seconds=1)
        lock.save()

        response = self.client.post(
            reverse("login"),
            {
                "username": "loginviewer",
                "password": "SecurePassword123!"
            }
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(LoginAttempt.objects.exists())

    def test_login_message_is_localized(self):
        for code, snippet in [
            ("ru", "Неверное имя"),
            ("kk", "құпиясөз"),
            ("en", "Incorrect username"),
        ]:
            self.client.cookies[
                settings.LANGUAGE_COOKIE_NAME
            ] = code

            response = self.client.post(
                reverse("login"),
                {
                    "username": "loginviewer",
                    "password": "wrong-password"
                }
            )

            self.assertEqual(
                response.wsgi_request.LANGUAGE_CODE,
                code
            )
            self.assertContains(response, snippet)


class PasswordHashingTests(TestCase):

    def test_password_is_stored_as_pbkdf2_hash(self):
        user = User.objects.create_user(
            "hashcheck",
            password="SecurePassword123!"
        )

        self.assertNotEqual(
            user.password,
            "SecurePassword123!"
        )
        self.assertTrue(
            user.password.startswith("pbkdf2_sha256$")
        )
        self.assertTrue(
            user.check_password("SecurePassword123!")
        )
