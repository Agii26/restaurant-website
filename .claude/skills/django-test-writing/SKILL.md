---
name: django-test-writing
description: How to write automated tests in this restaurant project (Django TestCase, session cart, mocking Stripe and email, red-green workflow, file layout). Use when adding or changing tests or when reproducing a bug with a failing test.
---

# Writing tests in this project

## Workflow: red, then green
1. Write the test. Run `python manage.py test <app.module>`. It must FAIL, and for the reason you expect.
2. Only then fix the code. Re-run: it must pass. Then run the whole suite.
3. A bug fix without a test that failed first is not finished.

## File layout
`orders/tests/` and `reservations/tests/` are packages. `menu` and `dashboard` still have an empty `tests.py` stub. Python cannot have both `tests.py` and a `tests/` package, so when you need several files there, DELETE the stub first, then create `tests/__init__.py` and `tests/test_<topic>.py`.

## Use the shared helpers
`orders/tests/base.py` has `OrderFlowTestCase` with `add_to_cart`, `apply_promo`, `start_checkout` (Stripe faked), `make_order` (someone else's order) and `stripe_session` (what Stripe would report). Look at `orders/tests/test_payment_confirmation.py` and `test_access_control.py` for worked examples before writing new ones.

## Never touch the real world
- Stripe: `patch("orders.views.stripe.checkout.Session.create")` and `patch("orders.views.stripe.Webhook.construct_event")`.
- Email: tests use Django's in-memory email backend; read sent mail from `django.core.mail.outbox`.
- Secrets: never read `.env`. Use `override_settings` for any setting a test needs.

## Patterns that are known to work here

```python
import datetime
from unittest.mock import patch, MagicMock
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from menu.models import Category, MenuItem
from orders.models import Order


class CheckoutTests(TestCase):
    def setUp(self):
        category = Category.objects.create(name="Mains")
        self.item = MenuItem.objects.create(category=category, name="Adobo", price="150.00")

    def add_to_cart(self, quantity=2):
        url = reverse("orders:add_to_cart", args=[self.item.id])
        response = self.client.post(url, {"quantity": quantity})   # returns JSON on success
        self.assertEqual(response.json()["cart_subtotal"], "300.00")

    def start_checkout(self):
        self.add_to_cart()
        pickup = (timezone.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
        with patch("orders.views.stripe.checkout.Session.create") as create:
            create.return_value = MagicMock(url="https://stripe.test/pay/abc")
            return self.client.post(reverse("orders:checkout"), {
                "name": "Test Customer", "email": "test@example.com",
                "phone": "+639171234567", "pickup_time": pickup, "order_notes": "",
            })

    def test_checkout_creates_pending_order_and_sends_customer_to_stripe(self):
        response = self.start_checkout()
        self.assertIn(response.status_code, (302, 303))   # see note below
        self.assertEqual(response["Location"], "https://stripe.test/pay/abc")
        self.assertEqual(Order.objects.get().status, "pending")

    @override_settings(STRIPE_WEBHOOK_SECRET="whsec_test")
    def test_signed_webhook_confirms_order(self):
        self.start_checkout()
        order = Order.objects.get()
        event = {"type": "checkout.session.completed",
                 "data": {"object": {"metadata": {"order_id": str(order.pk)}}}}
        with patch("orders.views.stripe.Webhook.construct_event", return_value=event):
            self.client.post(reverse("orders:stripe_webhook"), data="{}",
                             content_type="application/json", HTTP_STRIPE_SIGNATURE="sig")
        order.refresh_from_db()
        self.assertEqual(order.status, "confirmed")
```

## Good to know
- A second visitor with no session: `from django.test import Client; Client().get(...)`. Use it for access-control tests.
- `payment_success` currently sends 2 emails; check `len(mail.outbox)`.
- `manage.py test` uses `restaurant_site/test_settings.py` automatically (in-memory database, in-memory email, dummy Stripe keys), so a forgotten mock can never reach real Stripe.
- Mock Stripe's `Session.retrieve` as `patch("orders.views.stripe.checkout.Session.retrieve", return_value={...})` and signed webhooks as `patch("orders.views.stripe.Webhook.construct_event", ...)`.
- Login lockout counters live in the cache and survive between tests. Call `cache.clear()` in `setUp` of any test that logs in or hits a rate-limited view, or results will depend on test order. Check with `python manage.py test --reverse` and `--shuffle`.
- Settings are read once at start-up, so settings tests run a fresh Python process (see `restaurant_site/tests/test_deploy_settings.py`) with `PYTHON_DOTENV_DISABLED=1` so a developer's own `.env` cannot change the result.
- For a stranger, use a fresh `Client()`: customer pages must return 404 to anyone who did not create the record.
