from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django_ratelimit.decorators import ratelimit
from django_ratelimit.exceptions import Ratelimited
from django.http import Http404
from restaurant_site.access import grant_access, has_access
from .forms import ReservationForm
from .models import Reservation


def get_email(group, request):
    """Extract email from POST data to use as rate limit key."""
    return request.POST.get('email', '').lower().strip()


@ratelimit(key=get_email, rate='5/h', method='POST', block=False)
def reservation_page(request):
    if getattr(request, 'limited', False) and request.method == 'POST':
        messages.error(request, "Too many reservations from this email. Please wait an hour before trying again.")
        return redirect('reservations:reservation')

    form = ReservationForm()

    if request.method == 'POST':
        # Honeypot check
        if request.POST.get('website'):
            return redirect('reservations:reservation')

        form = ReservationForm(request.POST)
        if form.is_valid():
            reservation = form.save()
            grant_access(request, 'reservation', reservation.pk)  # only this browser may reopen it
            messages.success(request, "Your reservation was successfully submitted!")
            return redirect('reservations:confirmation', pk=reservation.pk)

    return render(request, 'reservations/reservation.html', {'form': form})


def confirmation_page(request, pk):
    reservation = get_object_or_404(Reservation, pk=pk)
    if not has_access(request, 'reservation', reservation.pk):
        raise Http404  # 404, not 403: do not reveal that this booking exists
    return render(request, 'reservations/confirmation.html', {'reservation': reservation})