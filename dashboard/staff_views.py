from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Q

from .decorators import staff_required, owner_required
from .models import StaffProfile
from orders.models import Order
from reservations.models import Reservation


@staff_required
@owner_required
def staff_list(request):
    """List all staff accounts — owner only."""
    staff = StaffProfile.objects.select_related('user').order_by('role', 'user__first_name')

    context = {
        'staff': staff,
        'total_staff': staff.count(),
        'active_staff': staff.filter(is_active=True).count(),
        'pending_orders': Order.objects.filter(status='pending').count(),
        'pending_reservations': Reservation.objects.filter(status='pending').count(),
    }
    return render(request, 'dashboard/staff_list.html', context)


@staff_required
@owner_required
def staff_add(request):
    """Add a new staff member."""
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name', '').strip()
        username   = request.POST.get('username', '').strip()
        email      = request.POST.get('email', '').strip()
        phone      = request.POST.get('phone', '').strip()
        role       = request.POST.get('role', 'staff')
        password   = request.POST.get('password', '').strip()
        password2  = request.POST.get('password2', '').strip()

        # Validation
        if not username or not password:
            messages.error(request, 'Username and password are required.')
        elif password != password2:
            messages.error(request, 'Passwords do not match.')
        elif len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, f'Username "{username}" is already taken.')
        else:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
            StaffProfile.objects.create(
                user=user,
                role=role,
                phone=phone,
                is_active=True,
            )
            messages.success(request, f'Staff account for {first_name or username} created successfully.')
            return redirect('dashboard:staff_list')

    context = {
        'pending_orders': Order.objects.filter(status='pending').count(),
        'pending_reservations': Reservation.objects.filter(status='pending').count(),
    }
    return render(request, 'dashboard/staff_form.html', context)


@staff_required
@owner_required
def staff_edit(request, staff_id):
    """Edit a staff member's role and info."""
    profile = get_object_or_404(StaffProfile.objects.select_related('user'), id=staff_id)

    # Prevent editing own account here (use profile/settings instead)
    if profile.user == request.user:
        messages.info(request, 'To edit your own account, use the Settings page.')
        return redirect('dashboard:staff_list')

    if request.method == 'POST':
        profile.user.first_name = request.POST.get('first_name', '').strip()
        profile.user.last_name  = request.POST.get('last_name', '').strip()
        profile.user.email      = request.POST.get('email', '').strip()
        profile.phone           = request.POST.get('phone', '').strip()
        profile.role            = request.POST.get('role', 'staff')
        profile.user.save()
        profile.save()
        messages.success(request, f'{profile.user.get_full_name() or profile.user.username} updated.')
        return redirect('dashboard:staff_list')

    context = {
        'profile': profile,
        'editing': True,
        'pending_orders': Order.objects.filter(status='pending').count(),
        'pending_reservations': Reservation.objects.filter(status='pending').count(),
    }
    return render(request, 'dashboard/staff_form.html', context)


@staff_required
@owner_required
def staff_toggle_active(request, staff_id):
    """Activate or deactivate a staff account."""
    if request.method != 'POST':
        return redirect('dashboard:staff_list')

    profile = get_object_or_404(StaffProfile, id=staff_id)

    if profile.user == request.user:
        messages.error(request, 'You cannot deactivate your own account.')
        return redirect('dashboard:staff_list')

    profile.is_active = not profile.is_active
    profile.user.is_active = profile.is_active
    profile.user.save()
    profile.save()

    status = 'activated' if profile.is_active else 'deactivated'
    messages.success(request, f'{profile.user.get_full_name() or profile.user.username} has been {status}.')
    return redirect('dashboard:staff_list')


@staff_required
@owner_required
def staff_reset_password(request, staff_id):
    """Reset a staff member's password."""
    if request.method != 'POST':
        return redirect('dashboard:staff_list')

    profile = get_object_or_404(StaffProfile.objects.select_related('user'), id=staff_id)
    new_password  = request.POST.get('new_password', '').strip()
    new_password2 = request.POST.get('new_password2', '').strip()

    if not new_password:
        messages.error(request, 'Password cannot be empty.')
    elif len(new_password) < 8:
        messages.error(request, 'Password must be at least 8 characters.')
    elif new_password != new_password2:
        messages.error(request, 'Passwords do not match.')
    else:
        profile.user.set_password(new_password)
        profile.user.save()
        messages.success(request, f'Password updated for {profile.user.get_full_name() or profile.user.username}.')

    return redirect('dashboard:staff_list')


@staff_required
@owner_required
def staff_delete(request, staff_id):
    """Delete a staff account entirely."""
    if request.method != 'POST':
        return redirect('dashboard:staff_list')

    profile = get_object_or_404(StaffProfile.objects.select_related('user'), id=staff_id)

    if profile.user == request.user:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('dashboard:staff_list')

    name = profile.user.get_full_name() or profile.user.username
    profile.user.delete()  # Cascades to StaffProfile
    messages.success(request, f'Staff account for {name} has been deleted.')
    return redirect('dashboard:staff_list')