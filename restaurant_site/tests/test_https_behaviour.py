"""What actually happens to a request in production, behind Render's HTTPS proxy.

The settings tests prove the values are right; these prove the BEHAVIOUR is right, in
particular that the HTTPS redirect cannot loop.
"""
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from dashboard.models import StaffProfile

PRODUCTION = dict(
    DEBUG=False,
    SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"),
    SECURE_SSL_REDIRECT=True,
    SESSION_COOKIE_SECURE=True,
    CSRF_COOKIE_SECURE=True,
    SECURE_HSTS_SECONDS=3600,
    SECURE_HSTS_INCLUDE_SUBDOMAINS=True,
)


@override_settings(**PRODUCTION)
class BehindRendersProxyTests(TestCase):
    def setUp(self):
        cache.clear()   # login lockout counters live in the cache; do not inherit another test's

    def test_a_request_the_proxy_marked_https_is_served_not_redirected(self):
        response = self.client.get(reverse("menu:menu"), HTTP_X_FORWARDED_PROTO="https")
        self.assertEqual(response.status_code, 200)   # no redirect loop

    def test_a_request_that_really_arrived_over_http_is_sent_to_https(self):
        response = self.client.get(reverse("menu:menu"))
        self.assertEqual(response.status_code, 301)
        self.assertTrue(response["Location"].startswith("https://"))

    def test_https_responses_tell_browsers_to_stay_on_https(self):
        response = self.client.get(reverse("menu:menu"), HTTP_X_FORWARDED_PROTO="https")
        self.assertIn("max-age=3600", response["Strict-Transport-Security"])

    def test_login_cookies_are_marked_secure(self):
        user = User.objects.create_user("chef", "chef@example.com", "S3cure-pass-phrase-42")
        StaffProfile.objects.create(user=user, role="staff")
        response = self.client.post(reverse("dashboard:login"),
                                    {"username": "chef", "password": "S3cure-pass-phrase-42"},
                                    HTTP_X_FORWARDED_PROTO="https")
        self.assertEqual(response.status_code, 302)   # logged in, not bounced to https again
        self.assertTrue(response.cookies["sessionid"]["secure"])   # login session cookie
        self.assertTrue(response.cookies["csrftoken"]["secure"])   # rotated at login
