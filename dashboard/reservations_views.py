from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from datetime import date

from .decorators import staff_required
from orders.models import Order
from reservations.models import Reservation


@staff_required
def reservations_list(request):
    """All reservations with filters and search."""
    reservations = Reservation.objects.order_by('-date', '-time')

    # ── Filters ──
    status_filter = request.GET.get('status', '')
    date_filter   = request.GET.get('date', '')
    search        = request.GET.get('search', '').strip()

    if status_filter:
        reservations = reservations.filter(status=status_filter)

    if date_filter:
        try:
            from datetime import datetime
            d = datetime.strptime(date_filter, '%Y-%m-%d').date()
            reservations = reservations.filter(date=d)
        except ValueError:
            pass

    if search:
        reservations = reservations.filter(
            Q(name__icontains=search) |
            Q(email__icontains=search) |
            Q(phone__icontains=search)
        )

    # ── Counts for tabs ──
    all_res = Reservation.objects.all()
    counts = {
        'all':       all_res.count(),
        'pending':   all_res.filter(status='pending').count(),
        'confirmed': all_res.filter(status='confirmed').count(),
        'cancelled': all_res.filter(status='cancelled').count(),
    }

    # ── Today + upcoming ──
    today = date.today()
    today_count    = all_res.filter(date=today).count()
    upcoming_count = all_res.filter(date__gt=today, status='confirmed').count()

    context = {
        'reservations': reservations,
        'counts': counts,
        'status_filter': status_filter,
        'date_filter': date_filter,
        'search': search,
        'today_count': today_count,
        'upcoming_count': upcoming_count,
        'pending_orders': Order.objects.filter(status='pending').count(),
        'pending_reservations': counts['pending'],
    }
    return render(request, 'dashboard/reservations_list.html', context)


@staff_required
def reservation_detail(request, reservation_id):
    """Full reservation detail with approve/reject/cancel controls."""
    reservation = get_object_or_404(Reservation, id=reservation_id)

    context = {
        'reservation': reservation,
        'pending_orders': Order.objects.filter(status='pending').count(),
        'pending_reservations': Reservation.objects.filter(status='pending').count(),
    }
    return render(request, 'dashboard/reservation_detail.html', context)


@staff_required
def reservation_approve(request, reservation_id):
    """Approve a pending reservation."""
    if request.method != 'POST':
        return redirect('dashboard:reservation_detail', reservation_id=reservation_id)

    reservation = get_object_or_404(Reservation, id=reservation_id)

    if reservation.status != 'pending':
        messages.error(request, 'Only pending reservations can be approved.')
        return redirect('dashboard:reservation_detail', reservation_id=reservation_id)

    reservation.status = 'confirmed'
    reservation.save()
    messages.success(request, f'Reservation for {reservation.name} on {reservation.date} has been approved.')
    return redirect('dashboard:reservation_detail', reservation_id=reservation_id)


@staff_required
def reservation_reject(request, reservation_id):
    """Reject a pending reservation."""
    if request.method != 'POST':
        return redirect('dashboard:reservation_detail', reservation_id=reservation_id)

    reservation = get_object_or_404(Reservation, id=reservation_id)
    reservation.status = 'cancelled'
    reservation.save()
    messages.success(request, f'Reservation for {reservation.name} has been rejected.')
    return redirect('dashboard:reservations_list')


@staff_required
def reservation_cancel(request, reservation_id):
    """Cancel a confirmed reservation."""
    if request.method != 'POST':
        return redirect('dashboard:reservation_detail', reservation_id=reservation_id)

    reservation = get_object_or_404(Reservation, id=reservation_id)
    reservation.status = 'cancelled'
    reservation.save()
    messages.success(request, f'Reservation for {reservation.name} has been cancelled.')
    return redirect('dashboard:reservations_list')


@staff_required
def reservation_add_note(request, reservation_id):
    """Add internal staff note to a reservation."""
    if request.method != 'POST':
        return redirect('dashboard:reservation_detail', reservation_id=reservation_id)

    reservation = get_object_or_404(Reservation, id=reservation_id)
    note = request.POST.get('staff_note', '').strip()

    if note:
        reservation.staff_note = note
        reservation.save()
        messages.success(request, 'Note saved.')
    else:
        messages.error(request, 'Note cannot be empty.')

    return redirect('dashboard:reservation_detail', reservation_id=reservation_id)