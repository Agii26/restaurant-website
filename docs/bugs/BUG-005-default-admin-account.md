# BUG-005: The deploy script creates an `admin` / `admin123` owner account

| Field | Value |
|---|---|
| Severity | Critical |
| Priority | P1 (fix now) |
| Status | Fixed in code (2026-11-17). Automated tests pass; not yet verified on the live site. |
| Found | 2026-11-17, code review, then reproduced with an automated test |
| OWASP 2025 | A02 Security Misconfiguration |
| Verified by running? | Yes: a test reproduced it before the fix. |

## Summary
If the three `DJANGO_SUPERUSER_*` settings are missing, `createsu` silently falls back to the username `admin` and the password `admin123`, and `create_staff_profile` then makes that account the owner. `build.sh` runs both on every deploy.

## Steps to reproduce
1. Run `python manage.py createsu` with none of the three variables set.
2. Look at the users: an `admin` account exists.

## Expected result
No account is created without explicit, strong credentials.

## Actual result
`admin` / `admin123` is created.

## Evidence
`menu/tests/test_createsu.py`: `test_there_is_never_a_default_admin_account` and `test_without_settings_no_account_is_created` failed before the fix.

## Impact
Anyone who guesses the most common admin login could own the restaurant's system, orders, and customer data.

## Fix
No fallback values. Without all three variables the command prints how to set them and creates nothing. The password must pass Django's password validators, so `admin123` is refused even when set on purpose. An existing account is never changed.

## Follow-up
If the old script ever ran on the live site, the account may already exist. See docs/DEPLOYMENT_CHECKLIST.md, step 1.

## Regression tests
`menu/tests/test_createsu.py` (5 tests).
