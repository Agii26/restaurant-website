"""Remember which records THIS browser created, so only it can open them again.

Confirmation pages are addressed by a guessable number (/orders/confirmation/12/).
Knowing the number must never be enough to see someone's name, email and phone.
So when a customer places an order or books a table we note the id in their own
session, and the page checks for it. Anyone else gets a 404 (not 403: we do not
even confirm that the record exists).
"""

SESSION_KEY = "owned_records"
MAX_REMEMBERED = 50  # per kind; keeps the session small


def grant_access(request, kind, pk):
    """Record that this browser created the `kind` record (e.g. 'order') with this pk."""
    owned = dict(request.session.get(SESSION_KEY, {}))
    ids = [i for i in owned.get(kind, []) if i != pk] + [pk]
    owned[kind] = ids[-MAX_REMEMBERED:]
    request.session[SESSION_KEY] = owned  # reassign so Django notices the change


def remembered_ids(request, kind):
    """All ids of this kind that this browser created."""
    return list(request.session.get(SESSION_KEY, {}).get(kind, []))


def has_access(request, kind, pk):
    return pk in remembered_ids(request, kind)
