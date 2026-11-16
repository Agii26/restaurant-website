---
paths:
  - "orders/**/*.py"
  - "dashboard/payment_views.py"
---

# Money and payment rules

- Money is `Decimal`, always. `float` is never allowed for amounts (not even for Stripe cents: use `int(amount * 100)` on a Decimal, never float math).
- The server decides prices. Recalculate totals from `MenuItem` and `AddOn` rows at checkout; never trust values stored in the session or sent by the browser.
- "Paid" means Stripe's signed webhook said so. Redirecting a visitor to a success URL proves nothing.
- Make state changes safe to repeat: a webhook can arrive twice. Check the current status before changing it, and use `transaction.atomic`.
- Counters (promo `times_used`) must use `F()` expressions or `select_for_update`, never read-modify-write.
- Store Stripe ids (session, payment intent) on our own records. Never page through Stripe's whole history to find a payment.
- Every refund or cancellation must record who did it and when.
- Never log card data, secrets, or full webhook payloads.
