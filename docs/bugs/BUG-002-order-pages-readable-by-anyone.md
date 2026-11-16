# BUG-002: Anyone can read another customer's order or reservation

| Field | Value |
|---|---|
| Severity | High |
| Priority | P1 (fix now) |
| Status | Fixed in code (2026-11-10). Automated tests pass. |
| Found | 2026-11-08, code review, then reproduced with an automated test |
| OWASP 2025 | A01 Broken Access Control |
| Verified by running? | Yes, all three: order confirmation, reservation confirmation, and order history by typed email. |

## Summary
Confirmation pages are addressed by a guessable number and never check who is asking.

## Steps to reproduce
1. Place an order and note the confirmation URL, `/orders/confirmation/<number>/`.
2. Open that URL in a different browser with no session.
3. The page loads and shows the customer's name and email.
4. Try the numbers before and after it.

## Expected result
Only the person who placed the order (or staff) can see it.

## Actual result
HTTP 200 with the customer's personal details. The same pattern appears in `reservations/views.py` (`confirmation_page`) and in order history, which lists orders for any email typed into `?email=`.

## Evidence
Automated check: a fresh client with no session got 200, and the response contained the name and email.

## Impact
Customer names, emails, and phone numbers can be collected by counting upward.

## Suggested fix
Use the unguessable `order_number` (UUID) in the URL and also require that it belongs to this session or to a signed-in user. Replace order history by email with a link sent to that email.

## Fix
`restaurant_site/access.py` remembers which orders and reservations this browser created; anyone else gets a 404. Order history now lists only this browser's orders and the signed-in customer's own. The "type any email" lookup was removed, and the confirmation page no longer puts the customer's email in a link.

## Follow-up
A customer on a new device can no longer look up orders by email. If that is wanted, add an emailed one-time link.

## Regression tests
`orders/tests/test_access_control.py` (10 tests) and `reservations/tests/test_access_control.py` (3 tests).
