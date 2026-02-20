from django.shortcuts import render, redirect
from .forms import ReservationForm
from .models import Reservation


def reservation_page(request):
    form = ReservationForm()

    if request.method == 'POST':
        form = ReservationForm(request.POST)
        if form.is_valid():
            reservation = form.save()
            return redirect('reservations:confirmation', pk=reservation.pk)

    return render(request, 'reservations/reservation.html', {'form': form})


def confirmation_page(request, pk):
    reservation = Reservation.objects.get(pk=pk)
    return render(request, 'reservations/confirmation.html', {'reservation': reservation})