"""Staff login: no redirects to other websites, and no unlimited password guessing."""
from urllib.parse import quote

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from dashboard.models import StaffProfile

PASSWORD = "S3cure-pass-phrase-42"


class StaffLoginSecurityTests(TestCase):
    def setUp(self):
        cache.clear()   # rate-limit counters live in the cache; start every test fresh
        self.login_url = reverse("dashboard:login")
        self.home_url = reverse("dashboard:home")
        for username, role in (("chef", "staff"), ("baker", "staff")):
            user = User.objects.create_user(username, f"{username}@example.com", PASSWORD)
            StaffProfile.objects.create(user=user, role=role)

    def post(self, username="chef", password=PASSWORD, next_url=None):
        url = self.login_url + (f"?next={quote(next_url, safe='')}" if next_url else "")
        return self.client.post(url, {"username": username, "password": password})

    def is_logged_in(self):
        return "_auth_user_id" in self.client.session


class OpenRedirectTests(StaffLoginSecurityTests):
    def test_login_without_next_goes_to_the_dashboard(self):
        self.assertRedirects(self.post(), self.home_url, fetch_redirect_response=False)

    def test_a_safe_next_page_on_this_site_is_honoured(self):
        response = self.post(next_url="/dashboard/orders/")
        self.assertRedirects(response, "/dashboard/orders/", fetch_redirect_response=False)

    def test_next_pointing_at_another_website_is_ignored(self):
        response = self.post(next_url="https://evil.example/phish")
        self.assertRedirects(response, self.home_url, fetch_redirect_response=False)

    def test_protocol_relative_next_is_ignored(self):
        response = self.post(next_url="//evil.example/phish")
        self.assertRedirects(response, self.home_url, fetch_redirect_response=False)

    def test_javascript_next_is_ignored(self):
        response = self.post(next_url="javascript:alert(1)")
        self.assertRedirects(response, self.home_url, fetch_redirect_response=False)


class PasswordGuessingTests(StaffLoginSecurityTests):
    def test_five_wrong_passwords_are_answered_normally(self):
        for _ in range(5):
            response = self.post(password="wrong-guess")
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Invalid username or password")

    def test_the_sixth_attempt_is_blocked(self):
        for _ in range(5):
            self.post(password="wrong-guess")
        response = self.post(password="wrong-guess")
        self.assertEqual(response.status_code, 429)
        self.assertContains(response, "Too many login attempts", status_code=429)

    def test_once_blocked_even_the_correct_password_is_refused(self):
        for _ in range(5):
            self.post(password="wrong-guess")
        response = self.post(password=PASSWORD)
        self.assertEqual(response.status_code, 429)
        self.assertFalse(self.is_logged_in())

    def test_blocking_one_account_does_not_block_another(self):
        for _ in range(6):
            self.post(username="chef", password="wrong-guess")
        response = self.post(username="baker")
        self.assertRedirects(response, self.home_url, fetch_redirect_response=False)
        self.assertTrue(self.is_logged_in())

    def test_username_capitals_do_not_dodge_the_limit(self):
        for name in ("chef", "CHEF", "Chef", "cHeF", "chef "):
            self.post(username=name, password="wrong-guess")
        self.assertEqual(self.post(username="chef", password="wrong-guess").status_code, 429)

    def test_normal_staff_can_log_in(self):
        self.assertRedirects(self.post(), self.home_url, fetch_redirect_response=False)
        self.assertTrue(self.is_logged_in())
