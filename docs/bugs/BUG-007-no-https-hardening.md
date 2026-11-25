# BUG-007: HTTPS and cookie hardening settings are missing

| Field | Value |
|---|---|
| Severity | Medium |
| Priority | P2 (this sprint) |
| Status | Fixed in code (2026-11-17). Automated tests pass; not yet verified on the live site. |
| Found | 2026-11-17, code review, then reproduced with an automated test |
| OWASP 2025 | A02 Security Misconfiguration |
| Verified by running? | Yes: Django's own `check --deploy` listed four warnings. |

## Summary
No HTTPS redirect, no HSTS, and the session and CSRF cookies are not marked Secure. Render's proxy header was also not configured, so Django could not tell which requests were really https.

## Steps to reproduce
Run `python manage.py check --deploy` with production-like settings.

## Expected result
No security warnings.

## Actual result
security.W004 (HSTS), W008 (SSL redirect), W012 (session cookie), W016 (CSRF cookie).

## Evidence
`test_django_deploy_checkup_reports_no_security_warnings` failed before the fix. Render's own support confirms it ends HTTPS at its proxy and forwards `X-Forwarded-Proto`.

## Impact
Cookies, including the staff login session, could travel over plain http and be intercepted on shared Wi-Fi.

## Fix
Under `if not DEBUG`: trust Render's `X-Forwarded-Proto` header, redirect to https, mark cookies Secure, and send HSTS starting at 1 hour. The HSTS preload warning is deliberately silenced with a comment explaining why.

## Follow-up
Raise `HSTS_SECONDS` in steps (docs/DEPLOYMENT_CHECKLIST.md).

## Regression tests
`ProductionSettingsTests` (3) and `BehindRendersProxyTests` (4, which also prove the redirect cannot loop).
