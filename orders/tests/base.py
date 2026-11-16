"""Shared helpers for order tests: a menu item, a cart, and a way to start checkout."""
import datetime
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from menu.models import Category, MenuItem
from orders.models import Order

STRIPE_SESSION_ID = "cs_test_123"


class OrderFlowTestCase(TestCase):
    """Base class. Never talks to Stripe or SendGrid (see restaurant_site/test_settings.py)."""

    def setUp(self):
        category = Category.objects.create(name="Mains")
        self.item = MenuItem.objects.create(category=category, name="Adobo", price="150.00")

    def add_to_cart(self, client=None, quantity=2):
        client = client or self.client
        response = client.post(reverse("orders:add_to_cart", args=[self.item.id]), {"quantity": quantity})
        self.assertEqual(response.status_code, 200)

    def apply_promo(self, code, client=None):
        (client or self.client).post(reverse("orders:cart"), {"promo_code": code})

    def start_checkout(self, client=None, email="customer@example.com"):
        """Fill the cart, submit checkout. Stripe is faked. Returns (response, order)."""
        client = client or self.client
        self.add_to_cart(client)
        pickup = (timezone.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
        with patch("orders.views.stripe.checkout.Session.create") as create:
            create.return_value = MagicMock(id=STRIPE_SESSION_ID, url="https://stripe.test/pay/abc")
            response = client.post(reverse("orders:checkout"), {
                "name": "Test Customer", "email": email, "phone": "+639171234567",
                "pickup_time": pickup, "order_notes": "",
            })
        return response, Order.objects.latest("id")

    def make_order(self, **overrides):
        """An order created directly in the database, as if some other customer placed it."""
        values = dict(name="Victim Vera", email="vera@example.com", phone="+639170000000",
                      pickup_time=timezone.now() + datetime.timedelta(days=1),
                      status="confirmed", subtotal="300.00", total="300.00")
        values.update(overrides)
        return Order.objects.create(**values)

    @staticmethod
    def stripe_session(order, payment_status="paid", amount_cents=None, order_id=None):
        """What Stripe would report about this order's Checkout Session."""
        return {
            "id": STRIPE_SESSION_ID,
            "payment_status": payment_status,
            "amount_total": int(order.total * 100) if amount_cents is None else amount_cents,
            "metadata": {"order_id": str(order.pk if order_id is None else order_id)},
        }
