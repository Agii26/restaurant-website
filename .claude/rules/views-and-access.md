---
paths:
  - "**/views.py"
  - "dashboard/*_views.py"
---

# View and access-control rules

- A view that takes an id, pk, or email must check the requester may see that record (owner of the order, or the right staff role). Sequential ids are guessable.
- Every `dashboard` view needs `@staff_required`; add `@manager_required` or `@owner_required` for sensitive pages.
- State-changing actions accept POST only, and every form has `{% csrf_token %}`.
- Redirecting to a user-supplied `next` URL requires `url_has_allowed_host_and_scheme`.
- Prefer a Django `ModelForm` over reading `request.POST` by hand.
- Catch specific exceptions. Never show exception text to users; log it instead.
- List pages must be paginated.
