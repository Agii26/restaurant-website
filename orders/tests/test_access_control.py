"""BUG-002: confirmation pages and order history must only show a customer their OWN data."""
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse

from .base import OrderFlowTestCase


class OrderConfirmationAccessTests(OrderFlowTestCase):
    def test_the_customer_who_placed_the_order_can_see_it(self):
        _, order = self.start_checkout()
        response = self.client.get(reverse("orders:order_confirmation", args=[order.pk]))
        self.assertEqual(response.status_code, 200)

    def test_confirmation_page_never_puts_the_customers_email_in_a_link(self):
        _, order = self.start_checkout(email="private@example.com")
        response = self.client.get(reverse("orders:order_confirmation", args=[order.pk]))
        self.assertNotContains(response, "?email=")   # emails in URLs leak into logs and browser history

    def test_a_stranger_cannot_see_someone_elses_order(self):
        _, order = self.start_checkout(email="private@example.com")
        stranger = Client()
        response = stranger.get(reverse("orders:order_confirmation", args=[order.pk]))
        self.assertEqual(response.status_code, 404)   # 404, not 403: do not even confirm it exists
        self.assertNotContains(response, "private@example.com", status_code=404)

    def test_guessing_the_neighbouring_order_number_gets_nothing(self):
        _, mine = self.start_checkout()
        victim = self.make_order()
        response = self.client.get(reverse("orders:order_confirmation", args=[victim.pk]))
        self.assertEqual(response.status_code, 404)

    def test_a_signed_in_customer_can_see_their_own_order_from_any_device(self):
        owner = User.objects.create_user("owner", "owner@example.com", "pw-12345-pw")
        order = self.make_order(user=owner)
        client = Client()
        client.login(username="owner", password="pw-12345-pw")
        self.assertEqual(client.get(reverse("orders:order_confirmation", args=[order.pk])).status_code, 200)

    def test_a_different_signed_in_customer_cannot_see_it(self):
        owner = User.objects.create_user("owner", "owner@example.com", "pw-12345-pw")
        User.objects.create_user("other", "other@example.com", "pw-12345-pw")
        order = self.make_order(user=owner)
        client = Client()
        client.login(username="other", password="pw-12345-pw")
        self.assertEqual(client.get(reverse("orders:order_confirmation", args=[order.pk])).status_code, 404)


class OrderHistoryAccessTests(OrderFlowTestCase):
    def short_number(self, order):
        return str(order.order_number)[:8].upper()

    def test_typing_someone_elses_email_shows_nothing(self):
        victim = self.make_order(email="vera@example.com")
        response = Client().get(reverse("orders:order_history"), {"email": "vera@example.com"})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.short_number(victim))
        self.assertNotContains(response, "Victim Vera")

    def test_history_shows_the_orders_placed_in_this_browser(self):
        _, mine = self.start_checkout()
        mine.status = "confirmed"
        mine.save()
        response = self.client.get(reverse("orders:order_history"))
        self.assertContains(response, self.short_number(mine))

    def test_history_does_not_mix_in_other_customers_orders(self):
        _, mine = self.start_checkout()
        mine.status = "confirmed"
        mine.save()
        victim = self.make_order()
        response = self.client.get(reverse("orders:order_history"))
        self.assertNotContains(response, self.short_number(victim))

    def test_a_signed_in_customer_sees_their_account_orders(self):
        owner = User.objects.create_user("owner", "owner@example.com", "pw-12345-pw")
        order = self.make_order(user=owner)
        client = Client()
        client.login(username="owner", password="pw-12345-pw")
        self.assertContains(client.get(reverse("orders:order_history")), self.short_number(order))
