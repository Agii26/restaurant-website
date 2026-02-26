from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def staff_required(view_func):
    """Require user to be logged in and have a StaffProfile."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('dashboard:login')
        try:
            profile = request.user.staff_profile
            if not profile.is_active:
                messages.error(request, 'Your account has been deactivated.')
                return redirect('dashboard:login')
        except Exception:
            messages.error(request, 'You do not have staff access.')
            return redirect('dashboard:login')
        return view_func(request, *args, **kwargs)
    return wrapper


def owner_required(view_func):
    """Require owner role."""
    @wraps(view_func)
    @staff_required
    def wrapper(request, *args, **kwargs):
        if not request.user.staff_profile.is_owner:
            messages.error(request, 'Owner access required.')
            return redirect('dashboard:home')
        return view_func(request, *args, **kwargs)
    return wrapper


def manager_required(view_func):
    """Require manager or owner role."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('dashboard:login')
        try:
            if not request.user.staff_profile.is_manager:
                messages.error(request, 'Manager access required.')
                return redirect('dashboard:home')
        except Exception:
            return redirect('dashboard:login')
        return view_func(request, *args, **kwargs)
    return wrapper