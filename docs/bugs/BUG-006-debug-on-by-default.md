# BUG-006: `DEBUG` is on whenever the environment variable is missing

| Field | Value |
|---|---|
| Severity | High |
| Priority | P1 (fix now) |
| Status | Fixed in code (2026-11-17). Automated tests pass; not yet verified on the live site. |
| Found | 2026-11-17, code review, then reproduced with an automated test |
| OWASP 2025 | A02 Security Misconfiguration |
| Verified by running? | Yes: a test starts the real settings with no DEBUG variable. |

## Summary
`DEBUG = os.environ.get('DEBUG', 'True') == 'True'`: forgetting one variable on the server turns on debug mode.

## Steps to reproduce
1. Load the settings with no `DEBUG` variable set.
2. Read `settings.DEBUG`.

## Expected result
False (safe unless deliberately turned on).

## Actual result
True.

## Evidence
`restaurant_site/tests/test_deploy_settings.py`: `test_debug_is_off_unless_explicitly_turned_on` failed before the fix.

## Impact
Debug mode shows detailed error pages that reveal code and configuration to visitors, and turns off protections meant for production.

## Fix
`DEBUG = env_bool('DEBUG', default=False)`. Local development now needs `DEBUG=True` in `.env` (documented in `.env.example`). The logging level follows the same switch.

## Follow-up
Your local `.env` must contain `DEBUG=True`.

## Regression tests
`DebugDefaultTests` (3 tests).
