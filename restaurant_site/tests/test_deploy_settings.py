"""Production-safety checks: the real settings, loaded the way Render loads them.

Each test starts a fresh Python process with a controlled environment, because settings are
read once at start-up. PYTHON_DOTENV_DISABLED stops the developer's own .env file from
changing the answer, so these tests give the same result on every machine.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STRONG_SECRET_KEY = "prod-like-secret-key-" + "aB3dE5gH7jK9mN1pQ3sT5vW7yZ9" * 3

SNAPSHOT_CODE = """
import json
from django.conf import settings
names = ["DEBUG", "SECURE_PROXY_SSL_HEADER", "SECURE_SSL_REDIRECT", "SESSION_COOKIE_SECURE",
         "CSRF_COOKIE_SECURE", "SECURE_HSTS_SECONDS"]
print(json.dumps({name: getattr(settings, name, None) for name in names}))
"""


def clean_environment(**overrides):
    """The current environment minus anything that would leak a developer's setup in."""
    blocked = {"DEBUG", "DATABASE_URL", "REDIS_URL", "DJANGO_SETTINGS_MODULE", "HSTS_SECONDS"}
    env = {key: value for key, value in os.environ.items() if key not in blocked}
    env.update(PYTHON_DOTENV_DISABLED="1", SECRET_KEY=STRONG_SECRET_KEY,
               DJANGO_SETTINGS_MODULE="restaurant_site.settings")
    env.update(overrides)
    return env


def real_settings(**env_overrides):
    """Load restaurant_site.settings in a fresh process and report the values we care about."""
    result = subprocess.run([sys.executable, "-c", SNAPSHOT_CODE], cwd=PROJECT_ROOT,
                            env=clean_environment(**env_overrides),
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


class DebugDefaultTests(SimpleTestCase):
    def test_debug_is_off_unless_explicitly_turned_on(self):
        self.assertIs(real_settings()["DEBUG"], False)   # forgetting the variable must be SAFE

    def test_debug_can_be_turned_on_for_local_development(self):
        self.assertIs(real_settings(DEBUG="True")["DEBUG"], True)

    def test_local_development_is_not_forced_onto_https(self):
        settings = real_settings(DEBUG="True")
        self.assertFalse(settings["SECURE_SSL_REDIRECT"])   # http://localhost:8000 must keep working
        self.assertFalse(settings["SESSION_COOKIE_SECURE"])


class ProductionSettingsTests(SimpleTestCase):
    def test_production_trusts_renders_https_header(self):
        # Render ends HTTPS at its proxy and tells Django via this header. Without it Django
        # thinks every request is plain http and an HTTPS redirect would loop forever.
        self.assertEqual(real_settings(DEBUG="False")["SECURE_PROXY_SSL_HEADER"],
                         ["HTTP_X_FORWARDED_PROTO", "https"])

    def test_production_forces_https_and_secure_cookies(self):
        settings = real_settings(DEBUG="False")
        self.assertTrue(settings["SECURE_SSL_REDIRECT"])
        self.assertTrue(settings["SESSION_COOKIE_SECURE"])
        self.assertTrue(settings["CSRF_COOKIE_SECURE"])
        self.assertGreater(settings["SECURE_HSTS_SECONDS"], 0)

    def test_django_deploy_checkup_reports_no_security_warnings(self):
        result = subprocess.run(
            [sys.executable, "manage.py", "check", "--deploy"], cwd=PROJECT_ROOT,
            env=clean_environment(DEBUG="False", REDIS_URL="redis://localhost:6379/0"),
            capture_output=True, text=True, timeout=60)
        output = result.stdout + result.stderr
        self.assertNotIn("security.W", output, output)   # HSTS, SSL redirect, secure cookies...
        self.assertNotIn("ERRORS:", output, output)
        self.assertEqual(result.returncode, 0, output)
