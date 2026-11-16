# BUG-004: `redirect(url, code=303)` returns 302

| Field | Value |
|---|---|
| Severity | Low |
| Priority | P3 (backlog) |
| Status | Fixed (2026-11-10) |
| Found | 2026-11-08, a test expected 303 and got 302 |
| Verified by running? | Yes |

## Summary
The checkout code asks for a 303 redirect to Stripe, but Django's `redirect()` shortcut has no `code` argument, so it is silently ignored.

## Steps to reproduce
POST a valid checkout form (Stripe mocked) and read the response status.

## Expected result
303 See Other, as the code intends.

## Actual result
302 Found. Browsers still follow it correctly, so customers see no problem today.

## Suggested fix
Return `HttpResponseRedirect` with status 303 explicitly, or accept 302 and remove the misleading argument.

## Fix
The checkout now returns `HttpResponseRedirect(url, status=303)`.

## Regression test
`SuccessPageTests.test_checkout_sends_the_customer_to_stripe_with_a_303_redirect`.
