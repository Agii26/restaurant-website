from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from decimal import Decimal
from django_ratelimit.decorators import ratelimit
import stripe

from menu.models import MenuItem
from .cart import Cart
from .models import Order, OrderItem, PromoCode
from .forms import CheckoutForm, AddToCartForm, PromoCodeForm
from .emails import send_customer_confirmation, send_restaurant_notification


stripe.api_key = settings.STRIPE_SECRET_KEY


def add_to_cart(request, item_id):
    menu_item = get_object_or_404(MenuItem, id=item_id, is_available=True)
    cart = Cart(request)

    if request.method == 'POST':
        form = AddToCartForm(request.POST, menu_item=menu_item)
        if form.is_valid():
            addon = form.cleaned_data.get('addon')
            quantity = form.cleaned_data.get('quantity', 1)
            cart.add(menu_item, quantity=quantity, addon=addon)
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

    form = AddToCartForm(menu_item=menu_item)
    return render(request, 'orders/add_to_cart.html', {'form': form, 'item': menu_item})


def cart_view(request):
    cart = Cart(request)
    promo_form = PromoCodeForm()
    promo_discount = Decimal('0')
    promo_code_obj = None

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

    if request.method == 'POST':
        key = request.POST.get('key')
        action = request.POST.get('action')
        if action == 'remove':
            cart.remove(key)
        elif action == 'update':
            qty = int(request.POST.get('quantity', 1))
            cart.update_quantity(key, qty)
        return redirect('orders:cart')

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




@ratelimit(key='ip', rate='10/h', method='POST', block=False)
def checkout_view(request):
    cart = Cart(request)
    if cart.is_empty():
        return redirect('orders:cart')

    # ── Rate limit check ──
    was_limited = getattr(request, 'limited', False)
    if was_limited and request.method == 'POST':
        messages.error(request, 'Too many attempts. Please wait a while before trying again.')
        return redirect('orders:checkout')

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
        # ── Honeypot check ──
        if request.POST.get('website'):
            return redirect('orders:cart')

        form = CheckoutForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user if request.user.is_authenticated else None
            order.subtotal = subtotal
            order.discount_amount = promo_discount
            order.total = total
            order.promo_code = promo_code_obj
            order.status = 'pending'
            order.save()

            for item in cart:
                OrderItem.objects.create(
                    order=order,
                    menu_item=MenuItem.objects.filter(id=item['item_id']).first(),
                    name=item['name'] + (f" + {item['addon_name']}" if item['addon_name'] else ''),
                    price=item['price'],
                    quantity=item['quantity'],
                    item_total=item['total'],
                )

            request.session['pending_order_id'] = order.pk

            try:
                checkout_session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=[{
                        'price_data': {
                            'currency': 'usd',
                            'product_data': {
                                'name': f'Warm Vibe Bistro — Order #{str(order.order_number)[:8].upper()}',
                                'description': f'Pickup at {order.pickup_time.strftime("%b %d, %Y %I:%M %p")}',
                            },
                            'unit_amount': int(total * 100),
                        },
                        'quantity': 1,
                    }],
                    mode='payment',
                    customer_email=order.email,
                    success_url=request.build_absolute_uri('/orders/payment/success/'),
                    cancel_url=request.build_absolute_uri('/orders/payment/cancel/'),
                    metadata={'order_id': str(order.pk)},
                )
                return redirect(checkout_session.url, code=303)

            except stripe.error.StripeError as e:
                order.delete()
                messages.error(request, f'Payment error: {str(e)}. Please try again.')

    else:
        initial = {}
        if request.user.is_authenticated:
            initial = {
                'name': request.user.get_full_name() or request.user.username,
                'email': request.user.email,
            }
        else:
            initial = {
                'name': request.COOKIES.get('guest_name', ''),
                'email': request.COOKIES.get('guest_email', ''),
                'phone': request.COOKIES.get('guest_phone', ''),
            }
        form = CheckoutForm(initial=initial)

    return render(request, 'orders/checkout.html', {
        'form': form,
        'cart': cart,
        'subtotal': subtotal,
        'promo_discount': promo_discount,
        'total': total,
        'promo_code': promo_code_obj,
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
    })


def payment_success(request):
    order_id = request.session.get('pending_order_id')
    if not order_id:
        return redirect('orders:cart')

    try:
        order = Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        return redirect('orders:cart')

    # Confirm the order
    order.status = 'confirmed'
    order.save()

    # Update promo usage
    if order.promo_code:
        order.promo_code.times_used += 1
        order.promo_code.save()
        if 'promo_code' in request.session:
            del request.session['promo_code']

    # Send both emails
    send_customer_confirmation(order)
    send_restaurant_notification(order)

    # Clear cart and session
    cart = Cart(request)
    cart.clear()
    del request.session['pending_order_id']

    # Set autofill cookies and redirect
    response = redirect('orders:order_confirmation', pk=order.pk)
    response.set_cookie('guest_name', order.name, max_age=60*60*24*90)
    response.set_cookie('guest_email', order.email, max_age=60*60*24*90)
    response.set_cookie('guest_phone', order.phone, max_age=60*60*24*90)
    return response


def payment_cancel(request):
    order_id = request.session.get('pending_order_id')
    if order_id:
        try:
            Order.objects.get(pk=order_id, status='pending').delete()
        except Order.DoesNotExist:
            pass
        del request.session['pending_order_id']

    messages.error(request, 'Payment was cancelled. Your cart has been kept — please try again.')
    return redirect('orders:checkout')


@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', None)

    if not webhook_secret:
        return HttpResponse(status=200)

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        order_id = session.get('metadata', {}).get('order_id')
        if order_id:
            try:
                order = Order.objects.get(pk=order_id)
                if order.status == 'pending':
                    order.status = 'confirmed'
                    order.save()
                    send_customer_confirmation(order)
                    send_restaurant_notification(order)
            except Order.DoesNotExist:
                pass

    return HttpResponse(status=200)


def order_confirmation(request, pk):
    order = get_object_or_404(Order, pk=pk)
    return render(request, 'orders/order_confirmation.html', {'order': order})


def order_history(request):
    orders = []
    email_query = request.GET.get('email', '').strip()
    looked_up = False

    if email_query:
        orders = Order.objects.filter(
            email__iexact=email_query,
            status__in=['confirmed', 'preparing', 'ready', 'completed']
        ).prefetch_related('items').order_by('-id')
        looked_up = True
    elif request.user.is_authenticated:
        orders = Order.objects.filter(user=request.user).prefetch_related('items').order_by('-id')

    return render(request, 'orders/order_history.html', {
        'orders': orders,
        'email_query': email_query,
        'looked_up': looked_up,
    })


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