# Roadmap: fixing the restaurant system (started Nov 2026)

Status labels: **Verified** = reproduced by running it. **Read** = seen in the code, not yet proven by a test.

## Step 1: Agent workspace (done)
- [x] CLAUDE.md, permissions, 2 hooks, 3 subagents, 2 skills, 2 rules (see docs/AGENT_SETUP.md)

## Step 2: Safety-net tests, then Tier 1 fixes (security and money)
Done so far (27 automated tests, all passing):
- [x] Test settings so `manage.py test` runs (BUG-003)
- [x] Unpaid order confirmed by visiting the success URL (BUG-001)
- [x] Order, reservation and order-history pages readable by anyone (BUG-002), all three verified by running
- [x] Checkout redirect code ignored (BUG-004)
Still to do in Step 2:
- [ ] `createsu` falls back to admin / admin123; `DEBUG` defaults to True. Read.
- [ ] HTTPS settings: `check --deploy` reports missing HSTS, SSL redirect, secure session and CSRF cookies, weak SECRET_KEY. Verified.
- [ ] Open redirect on staff login `next=`; no rate limit on login, promo, or checkout. Read.
- [ ] Customer name and notes pasted unescaped into emails to the restaurant. Read.
- [ ] Refunds scan the whole Stripe history; no audit record of who refunded; float money. Read.

## Step 3: Tier 2 correctness fixes
- [ ] Time zone: site is UTC, customers type local time. Read.
- [ ] Reservation form's earliest date frozen at server start; no hours, capacity, or reservation emails. Read.
- [ ] Promo code can exceed max uses under simultaneous orders. Read.
- [ ] Prices and availability not rechecked at checkout; quantity update has no cap. Read.
- [ ] Abandoned pending orders pile up. Read.
- [ ] Duplicate dish names crash the add form; CSV import accepts negative prices. Read.
- [ ] `redirect(url, code=303)` returns 302 (BUG-004). Verified.

## Step 4: Professional tooling
- [ ] GitHub Actions running tests on every push
- [ ] ruff (lint + format), pre-commit, pip-audit, coverage
- [ ] requirements.txt re-saved as UTF-8; CDN scripts pinned
- [ ] Email provider: `django-anymail` warns it dropped official SendGrid support. Verified (warning), impact to be researched.
- [ ] Background email sending, error monitoring, health check

## Step 5: Study guide and QA pack
- [ ] Interview study guide (rebuild-from-scratch walkthrough, Q&A, cheat sheet)
- [ ] Test plan, test cases, bug log, Playwright browser tests
