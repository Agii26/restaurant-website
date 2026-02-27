from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Sum, Count, Q
from datetime import date, timedelta
import json

from .decorators import staff_required, manager_required
from orders.models import Order, OrderItem


STATUS_FLOW = {
    'pending':   'confirmed',
    'confirmed': 'preparing',
    'preparing': 'ready',
    'ready':     'completed',
}

STATUS_LABELS = {
    'pending':   'Pending',
    'confirmed': 'Confirmed',
    'preparing': 'Preparing',
    'ready':     'Ready',
    'completed': 'Completed',
    'cancelled': 'Cancelled',
}


@staff_required
def orders_list(request):
    """All orders with filters and search."""
    orders = Order.objects.prefetch_related('items').order_by('-created_at')

    # ── Filters ──
    status_filter = request.GET.get('status', '')
    date_filter   = request.GET.get('date', '')
    search        = request.GET.get('search', '').strip()

    if status_filter:
        orders = orders.filter(status=status_filter)

    if date_filter:
        try:
            from datetime import datetime
            d = datetime.strptime(date_filter, '%Y-%m-%d').date()
            orders = orders.filter(created_at__date=d)
        except ValueError:
            pass

    if search:
        orders = orders.filter(
            Q(name__icontains=search) |
            Q(email__icontains=search) |
            Q(order_number__icontains=search)
        )

    # ── Quick counts for filter tabs ──
    all_orders = Order.objects.all()
    counts = {
        'all':       all_orders.count(),
        'pending':   all_orders.filter(status='pending').count(),
        'confirmed': all_orders.filter(status='confirmed').count(),
        'preparing': all_orders.filter(status='preparing').count(),
        'ready':     all_orders.filter(status='ready').count(),
        'completed': all_orders.filter(status='completed').count(),
        'cancelled': all_orders.filter(status='cancelled').count(),
    }

    # ── Today stats ──
    today = date.today()
    today_orders   = all_orders.filter(created_at__date=today)
    today_revenue  = today_orders.filter(
        status__in=['confirmed','preparing','ready','completed']
    ).aggregate(t=Sum('total'))['t'] or 0

    context = {
        'orders': orders,
        'counts': counts,
        'status_filter': status_filter,
        'date_filter': date_filter,
        'search': search,
        'today_revenue': today_revenue,
        'today_count': today_orders.count(),
        'status_choices': STATUS_LABELS,
        'pending_orders': counts['pending'],
        'pending_reservations': 0,
    }
    return render(request, 'dashboard/orders_list.html', context)


@staff_required
def order_detail(request, order_id):
    """Full order detail with status controls."""
    order = get_object_or_404(Order.objects.prefetch_related('items'), id=order_id)
    next_status = STATUS_FLOW.get(order.status)

    context = {
        'order': order,
        'next_status': next_status,
        'next_status_label': STATUS_LABELS.get(next_status, ''),
        'status_labels': STATUS_LABELS,
        'pending_orders': Order.objects.filter(status='pending').count(),
        'pending_reservations': 0,
    }
    return render(request, 'dashboard/order_detail.html', context)


@staff_required
def order_update_status(request, order_id):
    """Advance order to next status."""
    if request.method != 'POST':
        return redirect('dashboard:order_detail', order_id=order_id)

    order = get_object_or_404(Order, id=order_id)
    next_status = STATUS_FLOW.get(order.status)

    if next_status:
        order.status = next_status
        order.save()
        messages.success(request, f'Order #{str(order.order_number)[:8].upper()} marked as {STATUS_LABELS[next_status]}.')
    else:
        messages.error(request, 'Cannot advance this order further.')

    # Return JSON if AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': order.status, 'label': STATUS_LABELS.get(order.status, '')})

    return redirect('dashboard:order_detail', order_id=order_id)


@staff_required
def order_cancel(request, order_id):
    """Cancel an order."""
    if request.method != 'POST':
        return redirect('dashboard:order_detail', order_id=order_id)

    order = get_object_or_404(Order, id=order_id)

    if order.status == 'completed':
        messages.error(request, 'Cannot cancel a completed order.')
        return redirect('dashboard:order_detail', order_id=order_id)

    order.status = 'cancelled'
    order.save()
    messages.success(request, f'Order #{str(order.order_number)[:8].upper()} has been cancelled.')
    return redirect('dashboard:orders_list')


@staff_required
def order_print(request, order_id):
    """Print-friendly receipt view."""
    order = get_object_or_404(Order.objects.prefetch_related('items'), id=order_id)
    return render(request, 'dashboard/order_print.html', {'order': order})