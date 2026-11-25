# BUG-008: Staff login follows any `?next=` address, and a crafted one crashes the page

| Field | Value |
|---|---|
| Severity | High |
| Priority | P1 (fix now) |
| Status | Fixed in code (2026-11-17). Automated tests pass; not yet verified on the live site. |
| Found | 2026-11-17, code review, then reproduced with an automated test |
| OWASP 2025 | A01 Broken Access Control |
| Verified by running? | Yes: both the redirect and the crash were reproduced. |

## Summary
After a successful login the view redirected to whatever `next` contained.

## Steps to reproduce
1. Open the login page with `?next=https://evil.example/phish`.
2. Log in with valid staff credentials.
3. The browser is sent to the other website.
4. With `?next=javascript:alert(1)` the page shows a server error (HTTP 500).

## Expected result
Only addresses on this site are followed; anything else goes to the dashboard.

## Actual result
Redirect to any address; a server error for some inputs.

## Evidence
Three tests failed or errored before the fix (`OpenRedirectTests`).

## Impact
A phishing link that really begins on the restaurant's own login page, so staff trust it, then lands them on a look-alike site.

## Fix
`url_has_allowed_host_and_scheme` decides; anything outside this site goes to the dashboard home. The broad `except Exception` blocks in this view were narrowed to `ObjectDoesNotExist`.

## Regression tests
`OpenRedirectTests` (5 tests).
