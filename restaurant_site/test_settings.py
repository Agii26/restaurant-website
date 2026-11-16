"""Settings used by `python manage.py test` (manage.py selects this file automatically).

Start from the real settings, then override anything that could touch the outside
world or get in the way of a fast, safe test run.
"""
from .settings import *  # noqa: F401,F403

# Works even when no SECRET_KEY environment variable is set. Never used outside tests.
SECRET_KEY = "test-only-secret-key-never-used-in-production-0123456789"

# Tests always use a throwaway in-memory database, even if DATABASE_URL points at a
# real one on your machine. A test run can never touch real data.
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}

# django-ratelimit refuses to start without a shared cache (Redis). A per-process cache
# is fine for tests, so silence just those two checks (BUG-003). Production still gets them.
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
SILENCED_SYSTEM_CHECKS = ["django_ratelimit.E003", "django_ratelimit.W001"]

# Email goes to an in-memory outbox (django.core.mail.outbox), never to SendGrid.
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Dummy Stripe keys: even if a test forgets to mock Stripe, it cannot reach the real account.
STRIPE_SECRET_KEY = "sk_test_dummy_never_real"
STRIPE_PUBLISHABLE_KEY = "pk_test_dummy_never_real"
STRIPE_WEBHOOK_SECRET = "whsec_test_dummy_never_real"

# Fast password hashing keeps tests quick.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
