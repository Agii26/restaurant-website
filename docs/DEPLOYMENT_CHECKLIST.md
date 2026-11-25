# Deployment checklist (Render)

Do these in order BEFORE merging the security branch into `main`. Render deploys from `main`, so a merge changes the live site.

## 1. If the old deploy script ever ran on the live site
Before this fix, `createsu` created `admin` / `admin123` whenever the three `DJANGO_SUPERUSER_*` variables were not set. Check the live site's `/admin/` login: if `admin` / `admin123` works, change that password immediately (or delete the account), because it is a full owner account. Fixing the code does not remove an account that already exists in the database.

## 2. Local computer
- Your `.env` needs `DEBUG=True`. The default is now False, and with False the site forces https, which a local server cannot do. Check without showing secrets: `Select-String -Path .env -Pattern '^DEBUG'`
- Compare with `.env.example` for any missing names.
- If `python manage.py runserver` stops with `django_ratelimit.E003`, the login lockout needs a shared cache: set `REDIS_URL` in `.env` to a Redis you can reach. (The same check is why the tests use their own settings file.)

## 3. Render > Environment tab
| Variable | Value |
|---|---|
| `DEBUG` | `False` (or remove it) |
| `SECRET_KEY` | long random string, never reused anywhere else |
| `REDIS_URL` | your Redis address. Without it the login lockout is per server process, which is weaker |
| `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY` | live or test keys, matching each other |
| `STRIPE_WEBHOOK_SECRET` | from the Stripe dashboard. Without it, a customer who pays and closes the tab is not confirmed |
| `DJANGO_SUPERUSER_USERNAME/EMAIL/PASSWORD` | only needed on a brand-new database; password must be strong |
| `HSTS_SECONDS` | leave unset for 3600 (1 hour) at first |

## 4. After deploying, verify
1. `http://` address redirects once to `https://` (no endless redirects, no browser error).
2. Home page, menu, and a test-mode checkout all work.
3. Staff login works. Six wrong passwords for one account show "Too many login attempts".
4. Header check in PowerShell: `curl.exe -I https://YOUR-SITE.onrender.com` should show `Strict-Transport-Security`.

## 5. Raising HSTS slowly
Browsers remember an HSTS setting for as long as it says, so mistakes are hard to undo. Raise `HSTS_SECONDS` one step at a time, a few stable days apart: 3600 (1 hour), 86400 (1 day), 604800 (1 week), 31536000 (1 year).

## 6. If something goes wrong
Render > Deploys > roll back to the previous deploy. Or revert the merge on GitHub.

## Things to know
- If you set a Health Check Path in Render, it may call the site over plain http and get redirected. Tell me and we will exempt that path.
- Rate limiting uses the cache. With `REDIS_URL` set, the project is configured to carry on if Redis is down, which means the lockout silently stops working until Redis returns.
- Django's own `/admin/` login has no lockout yet (see ROADMAP).
