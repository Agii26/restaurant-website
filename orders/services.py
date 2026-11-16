"""Rules for turning a paid Stripe Checkout Session into a confirmed order.

Two things can tell us a customer paid: Stripe's signed webhook, and the customer's
browser landing on the success page. Either may arrive first, or only one may arrive.
Both go through confirm_order_paid(), which is safe to call any number of times.
"""
import logging

from django.db import transaction
from django.db.models import F

from .emails import send_customer_confirmation, send_restaurant_notification
from .models import Order, PromoCode

logger = logging.getLogger(__name__)


def stripe_session_confirms_payment(stripe_session, order):
    """True only if Stripe says THIS order was paid in full. Never trust the browser."""
    if stripe_session.get("payment_status") != "paid":
        return False

    metadata = stripe_session.get("metadata") or {}
    if str(metadata.get("order_id")) != str(order.pk):
        logger.error("Stripe session is for order %s, not order %s; ignoring.",
                     metadata.get("order_id"), order.pk)
        return False

    expected_cents = int(order.total * 100)
    if stripe_session.get("amount_total") != expected_cents:
        logger.error("Order %s expects %s cents but Stripe reports %s; not confirming.",
                     order.pk, expected_cents, stripe_session.get("amount_total"))
        return False
    return True


def confirm_order_paid(order_id):
    """Mark a pending order as paid, count its promo code, and send the emails.

    Safe to call many times: only the call that actually flips the order from
    'pending' to 'confirmed' does the work. Returns True for that call, else False.
    """
    with transaction.atomic():
        # select_for_update makes two simultaneous calls take turns (PostgreSQL).
        order = Order.objects.select_for_update().filter(pk=order_id).first()
        if order is None or order.status != "pending":
            return False

        order.status = "confirmed"
        order.save(update_fields=["status", "updated_at"])

        if order.promo_code_id:
            # F() lets the database add 1 itself, so two orders cannot overwrite each other.
            PromoCode.objects.filter(pk=order.promo_code_id).update(times_used=F("times_used") + 1)

    # Emails go out after the database change is saved. Both functions log their own failures.
    send_customer_confirmation(order)
    send_restaurant_notification(order)
    return True
