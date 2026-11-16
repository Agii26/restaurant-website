"""BUG-001: an order must only become 'confirmed' when Stripe says it was paid."""
from unittest.mock import patch

import stripe
from django.core import mail
from django.urls import reverse

from orders.models import PromoCode
from .base import OrderFlowTestCase

RETRIEVE = "orders.views.stripe.checkout.Session.retrieve"
CONSTRUCT_EVENT = "orders.views.stripe.Webhook.construct_event"


class SuccessPageTests(OrderFlowTestCase):
    """The page Stripe sends the customer back to. The browser is not trusted."""

    def visit_success_page(self, stripe_session):
        with patch(RETRIEVE, return_value=stripe_session):
            return self.client.get(reverse("orders:payment_success"))

    def test_unpaid_order_stays_pending_when_stripe_says_unpaid(self):
        _, order = self.start_checkout()
        response = self.visit_success_page(self.stripe_session(order, payment_status="unpaid"))
        order.refresh_from_db()
        self.assertEqual(order.status, "pending")
        self.assertEqual(len(mail.outbox), 0)
        self.assertRedirects(response, reverse("orders:cart"), fetch_redirect_response=False)

    def test_order_confirmed_and_emailed_when_stripe_says_paid(self):
        _, order = self.start_checkout()
        response = self.visit_success_page(self.stripe_session(order))
        order.refresh_from_db()
        self.assertEqual(order.status, "confirmed")
        self.assertEqual(len(mail.outbox), 2)  # one to the customer, one to the restaurant
        self.assertRedirects(response, reverse("orders:order_confirmation", args=[order.pk]),
                             fetch_redirect_response=False)

    def test_paid_session_with_the_wrong_amount_is_rejected(self):
        _, order = self.start_checkout()
        self.visit_success_page(self.stripe_session(order, amount_cents=100))
        order.refresh_from_db()
        self.assertEqual(order.status, "pending")

    def test_paid_session_belonging_to_another_order_is_rejected(self):
        _, order = self.start_checkout()
        other = self.make_order(status="pending")
        self.visit_success_page(self.stripe_session(order, order_id=other.pk))
        order.refresh_from_db()
        self.assertEqual(order.status, "pending")

    def test_success_page_without_any_checkout_goes_back_to_cart(self):
        response = self.client.get(reverse("orders:payment_success"))
        self.assertRedirects(response, reverse("orders:cart"), fetch_redirect_response=False)

    def test_checkout_sends_the_customer_to_stripe_with_a_303_redirect(self):  # BUG-004
        response, order = self.start_checkout()
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response["Location"], "https://stripe.test/pay/abc")
        self.assertEqual(order.status, "pending")


class WebhookTests(OrderFlowTestCase):
    """Stripe's signed message. This is the source of truth, even if the customer closes the tab."""

    def post_webhook(self, event):
        with patch(CONSTRUCT_EVENT, return_value=event):
            return self.client.post(reverse("orders:stripe_webhook"), data="{}",
                                    content_type="application/json", HTTP_STRIPE_SIGNATURE="sig")

    @staticmethod
    def completed(session):
        return {"type": "checkout.session.completed", "data": {"object": session}}

    def test_paid_webhook_confirms_and_emails_even_if_customer_never_returns(self):
        _, order = self.start_checkout()
        response = self.post_webhook(self.completed(self.stripe_session(order)))
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, "confirmed")
        self.assertEqual(len(mail.outbox), 2)

    def test_webhook_for_an_unpaid_session_does_not_confirm(self):
        _, order = self.start_checkout()
        self.post_webhook(self.completed(self.stripe_session(order, payment_status="unpaid")))
        order.refresh_from_db()
        self.assertEqual(order.status, "pending")

    def test_delayed_payment_success_event_confirms(self):
        _, order = self.start_checkout()
        event = {"type": "checkout.session.async_payment_succeeded",
                 "data": {"object": self.stripe_session(order)}}
        self.post_webhook(event)
        order.refresh_from_db()
        self.assertEqual(order.status, "confirmed")

    def test_bad_signature_is_rejected(self):
        with patch(CONSTRUCT_EVENT, side_effect=stripe.error.SignatureVerificationError("bad", "sig")):
            response = self.client.post(reverse("orders:stripe_webhook"), data="{}",
                                        content_type="application/json", HTTP_STRIPE_SIGNATURE="sig")
        self.assertEqual(response.status_code, 400)

    def test_webhook_for_unknown_order_is_ignored_politely(self):
        _, order = self.start_checkout()
        response = self.post_webhook(self.completed(self.stripe_session(order, order_id=999999)))
        self.assertEqual(response.status_code, 200)

    def test_webhook_only_accepts_post(self):
        self.assertEqual(self.client.get(reverse("orders:stripe_webhook")).status_code, 405)


class ConfirmedExactlyOnceTests(OrderFlowTestCase):
    """The webhook and the success page can both arrive, in either order. Only one may act."""

    def test_webhook_then_success_page_counts_promo_and_emails_once(self):
        PromoCode.objects.create(code="SAVE10", discount_percent=10, max_uses=100)
        self.apply_promo("SAVE10")
        _, order = self.start_checkout()   # fills the cart (2 x 150.00) in the same browser session
        self.assertEqual(str(order.total), "270.00")
        paid = self.stripe_session(order)

        event = {"type": "checkout.session.completed", "data": {"object": paid}}
        with patch(CONSTRUCT_EVENT, return_value=event):
            self.client.post(reverse("orders:stripe_webhook"), data="{}",
                             content_type="application/json", HTTP_STRIPE_SIGNATURE="sig")
        with patch(RETRIEVE, return_value=paid):
            self.client.get(reverse("orders:payment_success"))

        order.refresh_from_db()
        self.assertEqual(order.status, "confirmed")
        self.assertEqual(PromoCode.objects.get(code="SAVE10").times_used, 1)
        self.assertEqual(len(mail.outbox), 2)

    def test_success_page_then_webhook_counts_promo_and_emails_once(self):
        PromoCode.objects.create(code="SAVE10", discount_percent=10, max_uses=100)
        self.apply_promo("SAVE10")
        _, order = self.start_checkout()
        paid = self.stripe_session(order)

        with patch(RETRIEVE, return_value=paid):
            self.client.get(reverse("orders:payment_success"))
        event = {"type": "checkout.session.completed", "data": {"object": paid}}
        with patch(CONSTRUCT_EVENT, return_value=event):
            self.client.post(reverse("orders:stripe_webhook"), data="{}",
                             content_type="application/json", HTTP_STRIPE_SIGNATURE="sig")

        self.assertEqual(PromoCode.objects.get(code="SAVE10").times_used, 1)
        self.assertEqual(len(mail.outbox), 2)
