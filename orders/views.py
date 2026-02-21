from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.utils.http import urlencode
from decimal import Decimal
import datetime

from menu.models import MenuItem, AddOn
from .cart import Cart
from .models import Order, OrderItem, PromoCode
from .forms import CheckoutForm, AddToCartForm, PromoCodeForm


def add_to_cart(request, item_id):
    menu_item = get_object_or_404(MenuItem, id=item_id, is_available=True)
    cart = Cart(request)

    if request.method == 'POST':
        form = AddToCartForm(request.POST, menu_item=menu_item)
        if form.is_valid():
            addon = form.cleaned_data.get('addon')
            quantity = form.cleaned_data.get('quantity', 1)
            cart.add(menu_item, quantity=quantity, addon=addon)

            # Build cart items list for response
            cart_items = []
            for item in cart:
                cart_items.append({
                    'key': item['key'],
                    'name': item['name'],
                    'addon_name': item.get('addon_name') or '',
                    'price': str(item['price']),
                    'quantity': item['quantity'],
                    'total': str(item['total']),
                })
            return JsonResponse({
                'success': True,
                'added_item': menu_item.name,
                'cart_count': cart.get_total_items(),
                'cart_subtotal': str(cart.get_subtotal()),
                'cart_items': cart_items,
            })

    # Non-AJAX fallback (direct visit)
    form = AddToCartForm(menu_item=menu_item)
    return render(request, 'orders/add_to_cart.html', {'form': form, 'item': menu_item})

def cart_view(request):
    cart = Cart(request)
    promo_form = PromoCodeForm()
    promo_discount = Decimal('0')
    promo_code_obj = None

    # Handle promo code application
    if request.method == 'POST' and 'promo_code' in request.POST:
        promo_form = PromoCodeForm(request.POST)
        if promo_form.is_valid():
            code = promo_form.cleaned_data['promo_code'].upper()
            try:
                promo = PromoCode.objects.get(code=code)
                if promo.is_valid():
                    request.session['promo_code'] = code
                    messages.success(request, f'Promo code "{code}" applied — {promo.discount_percent}% off!')
                else:
                    messages.error(request, 'This promo code is expired or no longer valid.')
            except PromoCode.DoesNotExist:
                messages.error(request, 'Invalid promo code.')
        return redirect('orders:cart')

    # Handle quantity update / remove
    if request.method == 'POST':
        key = request.POST.get('key')
        action = request.POST.get('action')
        if action == 'remove':
            cart.remove(key)
        elif action == 'update':
            qty = int(request.POST.get('quantity', 1))
            cart.update_quantity(key, qty)
        return redirect('orders:cart')

    # Apply saved promo
    promo_code = request.session.get('promo_code')
    if promo_code:
        try:
            promo_code_obj = PromoCode.objects.get(code=promo_code)
            if promo_code_obj.is_valid():
                promo_discount = (cart.get_subtotal() * promo_code_obj.discount_percent) / 100
        except PromoCode.DoesNotExist:
            del request.session['promo_code']

    subtotal = cart.get_subtotal()
    total = max(subtotal - promo_discount, Decimal('0'))

    return render(request, 'orders/cart.html', {
        'cart': cart,
        'promo_form': promo_form,
        'promo_code': promo_code_obj,
        'promo_discount': promo_discount,
        'subtotal': subtotal,
        'total': total,
    })


def checkout_view(request):
    cart = Cart(request)
    if cart.is_empty():
        return redirect('orders:cart')

    # Require login
    if not request.user.is_authenticated:
        params = urlencode({'next': '/orders/checkout/'})
        return redirect(f'/orders/login/?{params}')

    promo_code_obj = None
    promo_discount = Decimal('0')
    promo_code = request.session.get('promo_code')
    if promo_code:
        try:
            promo_code_obj = PromoCode.objects.get(code=promo_code)
            if promo_code_obj.is_valid():
                promo_discount = (cart.get_subtotal() * promo_code_obj.discount_percent) / 100
        except PromoCode.DoesNotExist:
            pass

    subtotal = cart.get_subtotal()
    total = max(subtotal - promo_discount, Decimal('0'))

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user
            order.subtotal = subtotal
            order.discount_amount = promo_discount
            order.total = total
            order.promo_code = promo_code_obj
            order.save()

            # Save order items
            for item in cart:
                OrderItem.objects.create(
                    order=order,
                    menu_item=MenuItem.objects.filter(id=item['item_id']).first(),
                    name=item['name'] + (f" + {item['addon_name']}" if item['addon_name'] else ''),
                    price=item['price'],
                    quantity=item['quantity'],
                    item_total=item['total'],
                )

            # Update promo usage
            if promo_code_obj:
                promo_code_obj.times_used += 1
                promo_code_obj.save()
                del request.session['promo_code']

            cart.clear()
            return redirect('orders:order_confirmation', pk=order.pk)
    else:
        # Pre-fill name/email/phone from user profile if available
        form = CheckoutForm(initial={
            'name': request.user.get_full_name() or request.user.username,
            'email': request.user.email,
        })

    return render(request, 'orders/checkout.html', {
        'form': form,
        'cart': cart,
        'subtotal': subtotal,
        'promo_discount': promo_discount,
        'total': total,
        'promo_code': promo_code_obj,
    })


def checkout_login(request):
    next_url = request.GET.get('next', '/orders/checkout/')

    if request.user.is_authenticated:
        return redirect(next_url)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'login':
            username = request.POST.get('username')
            password = request.POST.get('password')
            remember = request.POST.get('remember_me')
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                if not remember:
                    request.session.set_expiry(0)
                return redirect(next_url)
            else:
                messages.error(request, 'Invalid username or password.')

        elif action == 'register':
            username = request.POST.get('reg_username')
            email = request.POST.get('reg_email')
            password1 = request.POST.get('reg_password1')
            password2 = request.POST.get('reg_password2')

            if password1 != password2:
                messages.error(request, 'Passwords do not match.')
            elif User.objects.filter(username=username).exists():
                messages.error(request, 'Username already taken.')
            else:
                user = User.objects.create_user(username=username, email=email, password=password1)
                login(request, user)
                return redirect(next_url)

    return render(request, 'orders/checkout_login.html', {'next': next_url})


def order_confirmation(request, pk):
    order = get_object_or_404(Order, pk=pk)
    return render(request, 'orders/order_confirmation.html', {'order': order})


@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items')
    return render(request, 'orders/order_history.html', {'orders': orders})

def cart_count(request):
    cart = Cart(request)
    cart_items = []
    for item in cart:
        cart_items.append({
            'key': item['key'],
            'name': item['name'],
            'addon_name': item.get('addon_name') or '',
            'price': str(item['price']),
            'quantity': item['quantity'],
            'total': str(item['total']),
        })
    return JsonResponse({
        'count': cart.get_total_items(),
        'subtotal': str(cart.get_subtotal()),
        'cart_items': cart_items,
    })