from django.shortcuts import render, redirect
from django.core.exceptions import ObjectDoesNotExist
from django.utils.http import url_has_allowed_host_and_scheme
from django_ratelimit.decorators import ratelimit
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count
from datetime import timedelta, date

from .forms import StaffLoginForm
from .decorators import staff_required
from orders.models import Order
from reservations.models import Reservation


def _login_attempt_key(group, request):
    """Count login attempts per account name, ignoring capitals and stray spaces."""
    return request.POST.get('username', '').strip().lower()


@ratelimit(key=_login_attempt_key, rate='5/15m', method='POST', block=False)
def staff_login(request):
    """Staff login page."""
    if request.user.is_authenticated:
        try:
            request.user.staff_profile
            return redirect('dashboard:home')
        except ObjectDoesNotExist:
            pass

    if request.method == 'POST':
        if getattr(request, 'limited', False):
            # Refuse BEFORE checking the password, so a blocked guesser learns nothing.
            messages.error(request, 'Too many login attempts for this account. '
                                    'Please wait 15 minutes and try again.')
            return render(request, 'dashboard/login.html', {'form': StaffLoginForm(request)}, status=429)

        form = StaffLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            # Check if user has a staff profile
            try:
                profile = user.staff_profile
                if not profile.is_active:
                    messages.error(request, 'Your account has been deactivated. Contact the owner.')
                    return redirect('dashboard:login')
            except ObjectDoesNotExist:
                messages.error(request, 'You do not have staff access to this dashboard.')
                return redirect('dashboard:login')

            login(request, user)
            # Only follow ?next= when it stays on THIS site. Otherwise a crafted link could send a
            # freshly logged-in staff member to a look-alike phishing page.
            next_url = request.GET.get('next', '')
            if next_url and url_has_allowed_host_and_scheme(
                    next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
                return redirect(next_url)
            return redirect('dashboard:home')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = StaffLoginForm(request)

    return render(request, 'dashboard/login.html', {'form': form})


def staff_logout(request):
    logout(request)
    return redirect('dashboard:login')


@staff_required
def dashboard_home(request):
    """Main dashboard with sales summary and quick stats."""
    today = date.today()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    # ── Orders ──
    all_confirmed = Order.objects.filter(status__in=['confirmed', 'preparing', 'ready', 'completed'])

    today_orders = all_confirmed.filter(created_at__date=today)
    week_orders  = all_confirmed.filter(created_at__date__gte=week_ago)
    month_orders = all_confirmed.filter(created_at__date__gte=month_ago)

    today_revenue = today_orders.aggregate(t=Sum('total'))['t'] or 0
    week_revenue  = week_orders.aggregate(t=Sum('total'))['t'] or 0
    month_revenue = month_orders.aggregate(t=Sum('total'))['t'] or 0

    today_count = today_orders.count()
    week_count  = week_orders.count()
    month_count = month_orders.count()

    # ── Pending actions ──
    pending_orders       = Order.objects.filter(status='pending').count()
    pending_reservations = Reservation.objects.filter(status='pending').count()

    # ── Recent orders (last 8) ──
    recent_orders = Order.objects.filter(
        status__in=['confirmed', 'preparing', 'ready', 'completed', 'pending']
    ).prefetch_related('items').order_by('-created_at')[:8]

    # ── Today's reservations ──
    today_reservations = Reservation.objects.filter(
        date=today
    ).order_by('time')[:6]

    # ── Revenue chart data (last 7 days) ──
    chart_labels = []
    chart_data = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        rev = all_confirmed.filter(created_at__date=d).aggregate(t=Sum('total'))['t'] or 0
        chart_labels.append(d.strftime('%a'))
        chart_data.append(float(rev))

    context = {
        'today_revenue': today_revenue,
        'week_revenue': week_revenue,
        'month_revenue': month_revenue,
        'today_count': today_count,
        'week_count': week_count,
        'month_count': month_count,
        'pending_orders': pending_orders,
        'pending_reservations': pending_reservations,
        'recent_orders': recent_orders,
        'today_reservations': today_reservations,
        'chart_labels': chart_labels,
        'chart_data': chart_data,
        'today': today,
    }
    return render(request, 'dashboard/home.html', context)