# BUG-001: An order is confirmed without any payment

| Field | Value |
|---|---|
| Severity | Critical |
| Priority | P1 (fix now) |
| Status | Fixed in code (2026-11-10). Automated tests pass; not yet tried against Stripe test mode in a real browser. |
| Found | 2026-11-08, code review, then reproduced with an automated test |
| OWASP 2025 | A06 Insecure Design |
| Verified by running? | Yes, in a test with Stripe mocked. Not yet tried against Stripe test mode in a browser. |

## Summary
A customer can get a confirmed order, and the restaurant gets the notification email, without ever paying.

## Steps to reproduce
1. Add a dish to the cart and submit the checkout form. The site creates a pending order and redirects to Stripe.
2. On the Stripe page, do NOT pay. In the same browser, open `/orders/payment/success/`.
3. The order is now "confirmed" and 2 emails have been sent (customer and restaurant).

## Expected result
The order stays "pending" until Stripe's signed webhook reports a completed payment.

## Actual result
`payment_success` only checks that the session holds a pending order id, then marks it confirmed and sends emails.

## Evidence
Automated check: after the steps above, `Order.status == "confirmed"` and `len(mail.outbox) == 2`.

## Impact
Free food. The restaurant prepares orders nobody paid for.

## Suggested fix
Confirm only from the signed webhook (or by retrieving the Stripe session and checking `payment_status == "paid"`). Make the success page read-only. Send emails and count promo use from the same single confirmation path, so a customer who closes the tab early is still handled.

## Fix
`orders/services.py` now holds `confirm_order_paid()` (safe to call repeatedly) and `stripe_session_confirms_payment()` (paid, right order, right amount). `payment_success` asks Stripe directly; the webhook uses the same two functions and now also sends the emails and counts the promo, so a customer who closes the tab is still handled.

## Regression tests
`orders/tests/test_payment_confirmation.py`: `SuccessPageTests`, `WebhookTests`, `ConfirmedExactlyOnceTests` (13 tests).
