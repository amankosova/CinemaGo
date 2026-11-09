from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


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
