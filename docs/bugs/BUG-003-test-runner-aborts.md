# BUG-003: `python manage.py test` aborts on a fresh machine

| Field | Value |
|---|---|
| Severity | Medium |
| Priority | P1 (blocks all automated testing) |
| Status | Fixed (2026-11-10) |
| Found | 2026-11-08, while setting up the project |
| Verified by running? | Yes |

## Summary
The test runner stops before running anything because a system check fails.

## Steps to reproduce
1. Fresh clone, install requirements, set `SECRET_KEY` and `DEBUG=True`, leave `REDIS_URL` unset.
2. Run `python manage.py test`.

## Expected result
Tests run.

## Actual result
`Found 0 test(s).` then `SystemCheckError ... django_ratelimit.E003: cache backend LocMemCache is not a shared cache`. Exit code 2.

## Impact
Nobody can run tests without Redis. It also means rate limiting is not shared between server processes when no shared cache is configured (this part is from the library's own message, not yet tested).

## Suggested fix
Add a separate test settings module that silences this check or sets a test cache. Configure a shared cache for production.

## Fix
`restaurant_site/test_settings.py` (selected automatically by `manage.py test`): in-memory database, in-memory email, dummy Stripe keys, and only the two rate-limit checks silenced. Production settings are unchanged.

## Regression test
`python manage.py test` with no environment variables set now starts and runs.
