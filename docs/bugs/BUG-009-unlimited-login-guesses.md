# BUG-009: Staff login allows unlimited password guesses

| Field | Value |
|---|---|
| Severity | High |
| Priority | P1 (fix now) |
| Status | Fixed in code (2026-11-17). Automated tests pass; not yet verified on the live site. |
| Found | 2026-11-17, code review, then reproduced with an automated test |
| OWASP 2025 | A07 Authentication Failures |
| Verified by running? | Yes: a test made six wrong guesses and was never blocked. |

## Summary
There was no limit on failed login attempts.

## Steps to reproduce
Submit the login form with a wrong password many times in a row.

## Expected result
After a few attempts the account is locked for a while.

## Actual result
Never blocked.

## Evidence
`test_the_sixth_attempt_is_blocked` and two others failed before the fix.

## Impact
An attacker can try thousands of passwords against a staff or owner account.

## Fix
5 attempts per account name per 15 minutes (ignoring capitals and spaces). When blocked, even the correct password is refused (HTTP 429) without being checked. One blocked account does not block another.

## Follow-up
Limits by visitor address for promo codes and checkout need the visitor's real IP behind Render's proxy, so they are a later step. Django's own `/admin/` login has no lockout yet. The lockout needs a shared cache (`REDIS_URL`) to work across server processes.

## Regression tests
`PasswordGuessingTests` (6 tests).
