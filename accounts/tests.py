from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import translation
from django.conf import settings


class ProfileTests(TestCase):
    def test_guest_redirected_to_login(self):
        response = self.client.get(reverse("profile"))
        self.assertRedirects(response, "/accounts/login/?next=/accounts/profile/")

    def test_logged_in_user_sees_own_profile(self):
        user = User.objects.create_user(username="student", email="student@example.com", password="SafePass123!")
        self.client.force_login(user)
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "student@example.com")
        self.assertContains(response, "student")

    def test_registration_creates_user(self):
        response = self.client.post(reverse("register"), {"username": "newstudent", "email": "new@example.com", "password1": "SecurePass123!", "password2": "SecurePass123!"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username="newstudent").exists())


class LoginLockoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('loginviewer', password='SecurePassword123!')

    def test_five_failed_passwords_lock_login_for_five_minutes(self):
        from .models import LoginAttempt
        for _ in range(4):
            self.assertEqual(self.client.post(reverse('login'), {'username':'loginviewer','password':'wrong-password'}).status_code, 200)
        response = self.client.post(reverse('login'), {'username':'loginviewer','password':'wrong-password'})
        self.assertEqual(response.status_code, 429)
        self.assertContains(response, 'Too many failed attempts', status_code=429)
        self.assertEqual(LoginAttempt.objects.get().failed_count, 5)
        self.assertEqual(self.client.post(reverse('login'), {'username':'loginviewer','password':'SecurePassword123!'}).status_code, 429)

    def test_expired_lock_allows_correct_password(self):
        from django.utils import timezone
        from datetime import timedelta
        from .models import LoginAttempt
        for _ in range(5):
            self.client.post(reverse('login'), {'username':'loginviewer','password':'wrong-password'})
        lock = LoginAttempt.objects.get()
        lock.locked_until = timezone.now() - timedelta(seconds=1)
        lock.save()
        response = self.client.post(reverse('login'), {'username':'loginviewer','password':'SecurePassword123!'})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(LoginAttempt.objects.exists())

    
    
    def test_login_message_is_localized(self):
        for code, snippet in [
            ("ru", "Неверное имя"),
            ("kk", "құпиясөз"),
            ("en", "Incorrect username"),
        ]:
            self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = code

            response = self.client.post(
                reverse("login"),
                {
                    "username": "loginviewer",
                    "password": "wrong-password",
                },
            )

            self.assertEqual(
                response.wsgi_request.LANGUAGE_CODE,
                code,
            )
            self.assertContains(response, snippet)

class PasswordHashingTests(TestCase):
    def test_password_is_stored_as_pbkdf2_hash(self):
        user = User.objects.create_user("hashcheck", password="SecurePassword123!")
        self.assertNotEqual(user.password, "SecurePassword123!")
        self.assertTrue(user.password.startswith("pbkdf2_sha256$"))
        self.assertTrue(user.check_password("SecurePassword123!"))