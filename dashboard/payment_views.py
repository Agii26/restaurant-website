from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.core.paginator import Paginator
from django.http import HttpResponse
from datetime import date, timedelta
import csv
import stripe
from django.conf import settings

from .decorators import staff_required, manager_required
from orders.models import Order
from reservations.models import Reservation

stripe.api_key = settings.STRIPE_SECRET_KEY


def _get_payment_status(order):
    """Return payment status label based on order status."""
    if order.status == 'cancelled':
        return 'refunded_or_cancelled'
    if order.status == 'pending':
        return 'pending'
    return 'paid'


@staff_required
@manager_required
def payments_list(request):
    """All transactions with filters, search, pagination."""
    search      = request.GET.get('search', '').strip()
    status_f    = request.GET.get('status', '')
    date_filter = request.GET.get('date', '')
    page        = request.GET.get('page', 1)

    orders = Order.objects.prefetch_related('items').order_by('-created_at')

    if search:
        orders = orders.filter(
            Q(name__icontains=search) |
            Q(email__icontains=search) |
            Q(order_number__icontains=search)
        )

    if status_f == 'paid':
        orders = orders.filter(status__in=['confirmed', 'preparing', 'ready', 'completed'])
    elif status_f == 'pending':
        orders = orders.filter(status='pending')
    elif status_f == 'cancelled':
        orders = orders.filter(status='cancelled')

    if date_filter:
        try:
            from datetime import datetime
            d = datetime.strptime(date_filter, '%Y-%m-%d').date()
            orders = orders.filter(created_at__date=d)
        except ValueError:
            pass

    # ── Revenue stats ──
    today      = date.today()
    week_ago   = today - timedelta(days=7)
    month_ago  = today - timedelta(days=30)

    confirmed = Order.objects.filter(status__in=['confirmed', 'preparing', 'ready', 'completed'])
    today_rev  = confirmed.filter(created_at__date=today).aggregate(t=Sum('total'))['t'] or 0
    week_rev   = confirmed.filter(created_at__date__gte=week_ago).aggregate(t=Sum('total'))['t'] or 0
    month_rev  = confirmed.filter(created_at__date__gte=month_ago).aggregate(t=Sum('total'))['t'] or 0
    total_rev  = confirmed.aggregate(t=Sum('total'))['t'] or 0
    total_txns = confirmed.count()

    # ── Pagination ──
    paginator = Paginator(orders, 25)
    orders_page = paginator.get_page(page)

    context = {
        'orders': orders_page,
        'paginator': paginator,
        'search': search,
        'status_f': status_f,
        'date_filter': date_filter,
        'today_rev': today_rev,
        'week_rev': week_rev,
        'month_rev': month_rev,
        'total_rev': total_rev,
        'total_txns': total_txns,
        'pending_orders': Order.objects.filter(status='pending').count(),
        'pending_reservations': Reservation.objects.filter(status='pending').count(),
    }
    return render(request, 'dashboard/payments_list.html', context)


@staff_required
@manager_required
def payment_detail(request, order_id):
    """Payment detail with Stripe info and refund option."""
    order = get_object_or_404(Order.objects.prefetch_related('items'), id=order_id)

    stripe_session = None
    stripe_charge  = None
    stripe_error   = None

    # Try to fetch Stripe session
    try:
        sessions = stripe.checkout.Session.list(limit=100)
        for s in sessions.auto_paging_iter():
            if s.metadata.get('order_id') == str(order.id):
                stripe_session = s
                # Fetch charge if payment intent exists
                if s.payment_intent:
                    pi = stripe.PaymentIntent.retrieve(s.payment_intent)
                    if pi.latest_charge:
                        stripe_charge = stripe.Charge.retrieve(pi.latest_charge)
                break
    except stripe.error.StripeError as e:
        stripe_error = str(e)

    context = {
        'order': order,
        'stripe_session': stripe_session,
        'stripe_charge': stripe_charge,
        'stripe_error': stripe_error,
        'stripe_amount': stripe_charge.amount_captured / 100 if stripe_charge else None,
        'payment_status': _get_payment_status(order),
        'pending_orders': Order.objects.filter(status='pending').count(),
        'pending_reservations': Reservation.objects.filter(status='pending').count(),
    }
    return render(request, 'dashboard/payment_detail.html', context)


@staff_required
@manager_required
def payment_refund(request, order_id):
    """Initiate a Stripe refund for an order."""
    if request.method != 'POST':
        return redirect('dashboard:payment_detail', order_id=order_id)

    order = get_object_or_404(Order, id=order_id)
    refund_type = request.POST.get('refund_type', 'full')
    amount_str  = request.POST.get('amount', '').strip()

    try:
        # Find Stripe charge
        sessions = stripe.checkout.Session.list(limit=100)
        stripe_charge = None

        for s in sessions.auto_paging_iter():
            if s.metadata.get('order_id') == str(order.id):
                if s.payment_intent:
                    pi = stripe.PaymentIntent.retrieve(s.payment_intent)
                    if pi.latest_charge:
                        stripe_charge = stripe.Charge.retrieve(pi.latest_charge)
                break

        if not stripe_charge:
            messages.error(request, 'Could not find Stripe charge for this order.')
            return redirect('dashboard:payment_detail', order_id=order_id)

        refund_params = {'charge': stripe_charge.id}

        if refund_type == 'partial' and amount_str:
            try:
                amount_cents = int(float(amount_str) * 100)
                refund_params['amount'] = amount_cents
            except ValueError:
                messages.error(request, 'Invalid refund amount.')
                return redirect('dashboard:payment_detail', order_id=order_id)

        refund = stripe.Refund.create(**refund_params)

        if refund.status == 'succeeded':
            order.status = 'cancelled'
            order.save()
            messages.success(request, f'Refund of ${float(refund.amount)/100:.2f} processed successfully.')
        else:
            messages.error(request, f'Refund status: {refund.status}. Check your Stripe dashboard.')

    except stripe.error.StripeError as e:
        messages.error(request, f'Stripe error: {str(e)}')

    return redirect('dashboard:payment_detail', order_id=order_id)


@staff_required
@manager_required
def payments_export_csv(request):
    """Export all confirmed transactions to CSV."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="transactions_{date.today()}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Order #', 'Date', 'Customer', 'Email', 'Phone', 'Items', 'Total', 'Status', 'Pickup Time'])

    orders = Order.objects.filter(
        status__in=['confirmed', 'preparing', 'ready', 'completed', 'cancelled']
    ).prefetch_related('items').order_by('-created_at')

    # Apply same filters as list view
    search      = request.GET.get('search', '').strip()
    date_filter = request.GET.get('date', '')

    if search:
        orders = orders.filter(Q(name__icontains=search) | Q(email__icontains=search))

    if date_filter:
        try:
            from datetime import datetime
            d = datetime.strptime(date_filter, '%Y-%m-%d').date()
            orders = orders.filter(created_at__date=d)
        except ValueError:
            pass

    for order in orders:
        writer.writerow([
            str(order.order_number)[:8].upper(),
            order.created_at.strftime('%Y-%m-%d %H:%M'),
            order.name,
            order.email,
            order.phone,
            order.items.count(),
            order.total,
            order.get_status_display(),
            order.pickup_time.strftime('%Y-%m-%d %H:%M') if order.pickup_time else '',
        ])

    return response