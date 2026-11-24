from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class AccountContributionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="profile_owner", email="owner@example.com",
            password="SafePass123!", first_name="Ada", last_name="Lovelace",
        )
        self.client.force_login(self.user)

    def test_tc12_edit_form_is_prefilled_from_current_user(self):
        response = self.client.get(reverse("edit_profile"))
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertEqual(form.instance.pk, self.user.pk)
        self.assertEqual(form["username"].value(), "profile_owner")
        self.assertEqual(form["email"].value(), "owner@example.com")

    def test_tc13_duplicate_username_does_not_change_profile(self):
        User.objects.create_user("taken_name", password="OtherPass123!")
        response = self.client.post(reverse("edit_profile"), {
            "username": "taken_name", "first_name": "Changed",
            "last_name": "Name", "email": "changed@example.com",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("username", response.context["form"].errors)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "profile_owner")
        self.assertEqual(self.user.email, "owner@example.com")
        self.assertEqual(self.user.first_name, "Ada")
        self.assertEqual(self.user.last_name, "Lovelace")

    def test_tc14_blank_email_does_not_change_profile(self):
        response = self.client.post(reverse("edit_profile"), {
            "username": "changed_name", "first_name": "Changed",
            "last_name": "Name", "email": "",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("email", response.context["form"].errors)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "profile_owner")
        self.assertEqual(self.user.email, "owner@example.com")
        self.assertEqual(self.user.first_name, "Ada")
        self.assertEqual(self.user.last_name, "Lovelace")

    def test_tc15_opening_delete_page_does_not_delete_account(self):
        response = self.client.get(reverse("delete_account"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your tickets and reservations will also be deleted.")
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())
