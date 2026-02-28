from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum, Count, Q, Max
from django.core.paginator import Paginator
from datetime import date

from .decorators import staff_required, manager_required
from orders.models import Order
from reservations.models import Reservation


@staff_required
def customers_list(request):
    """All unique customers aggregated by email."""
    search = request.GET.get('search', '').strip()
    sort   = request.GET.get('sort', '-last_order')
    page   = request.GET.get('page', 1)

    # Aggregate orders by email
    customers_qs = Order.objects.filter(
        status__in=['confirmed', 'preparing', 'ready', 'completed']
    ).values('email').annotate(
        name=Max('name'),
        phone=Max('phone'),
        total_spent=Sum('total'),
        order_count=Count('id'),
        last_order=Max('created_at'),
    )

    if search:
        customers_qs = customers_qs.filter(
            Q(email__icontains=search) |
            Q(name__icontains=search)
        )

    # Sorting
    sort_map = {
        '-last_order': '-last_order',
        'last_order':  'last_order',
        '-total_spent': '-total_spent',
        'total_spent':  'total_spent',
        '-order_count': '-order_count',
        'name':         'name',
    }
    customers_qs = customers_qs.order_by(sort_map.get(sort, '-last_order'))

    # Pagination
    paginator = Paginator(customers_qs, 20)
    customers_page = paginator.get_page(page)

    # Summary stats
    total_customers  = customers_qs.count()
    total_revenue    = customers_qs.aggregate(t=Sum('total_spent'))['t'] or 0
    repeat_customers = customers_qs.filter(order_count__gt=1).count()

    context = {
        'customers': customers_page,
        'paginator': paginator,
        'search': search,
        'sort': sort,
        'total_customers': total_customers,
        'total_revenue': total_revenue,
        'repeat_customers': repeat_customers,
        'pending_orders': Order.objects.filter(status='pending').count(),
        'pending_reservations': Reservation.objects.filter(status='pending').count(),
    }
    return render(request, 'dashboard/customers_list.html', context)


@staff_required
def customer_detail(request, email):
    """Full customer profile — orders + reservations."""
    # Get all orders for this email
    orders = Order.objects.filter(
        email__iexact=email
    ).prefetch_related('items').order_by('-created_at')

    # Get all reservations for this email
    reservations = Reservation.objects.filter(
        email__iexact=email
    ).order_by('-date', '-time')

    if not orders.exists() and not reservations.exists():
        messages.error(request, f'No customer found with email {email}.')
        return redirect('dashboard:customers_list')

    # Aggregate stats
    confirmed_orders = orders.filter(status__in=['confirmed', 'preparing', 'ready', 'completed'])
    total_spent  = confirmed_orders.aggregate(t=Sum('total'))['t'] or 0
    order_count  = confirmed_orders.count()
    first_order  = confirmed_orders.order_by('created_at').first()
    latest_order = confirmed_orders.order_by('-created_at').first()

    # Get name and phone from latest order
    latest = orders.first()
    customer_name  = latest.name if latest else email
    customer_phone = latest.phone if latest else '—'

    # Check if blocked
    from .models import BlockedCustomer
    is_blocked = BlockedCustomer.objects.filter(email__iexact=email).exists()

    context = {
        'email': email,
        'customer_name': customer_name,
        'customer_phone': customer_phone,
        'orders': orders,
        'reservations': reservations,
        'total_spent': total_spent,
        'order_count': order_count,
        'first_order': first_order,
        'latest_order': latest_order,
        'is_blocked': is_blocked,
        'pending_orders': Order.objects.filter(status='pending').count(),
        'pending_reservations': Reservation.objects.filter(status='pending').count(),
    }
    return render(request, 'dashboard/customer_detail.html', context)


@staff_required
@manager_required
def customer_block(request, email):
    """Block a customer by email."""
    if request.method != 'POST':
        return redirect('dashboard:customer_detail', email=email)

    from .models import BlockedCustomer
    reason = request.POST.get('reason', '').strip()

    blocked, created = BlockedCustomer.objects.get_or_create(
        email__iexact=email,
        defaults={'email': email, 'reason': reason}
    )
    if created:
        messages.success(request, f'{email} has been blocked.')
    else:
        messages.info(request, f'{email} is already blocked.')

    return redirect('dashboard:customer_detail', email=email)


@staff_required
@manager_required
def customer_unblock(request, email):
    """Unblock a customer."""
    if request.method != 'POST':
        return redirect('dashboard:customer_detail', email=email)

    from .models import BlockedCustomer
    BlockedCustomer.objects.filter(email__iexact=email).delete()
    messages.success(request, f'{email} has been unblocked.')
    return redirect('dashboard:customer_detail', email=email)