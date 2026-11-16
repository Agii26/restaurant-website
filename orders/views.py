import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.db.models import Q
from django.contrib import messages
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from decimal import Decimal
from django_ratelimit.decorators import ratelimit
import stripe

from dashboard.models import BlockedCustomer
from menu.models import MenuItem
from .cart import Cart
from .models import Order, OrderItem, PromoCode
from .forms import CheckoutForm, AddToCartForm, PromoCodeForm
from .services import confirm_order_paid, stripe_session_confirms_payment
from restaurant_site.access import grant_access, has_access, remembered_ids

logger = logging.getLogger(__name__)


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





def checkout_view(request):
    cart = Cart(request)
    if cart.is_empty():
        return redirect('orders:cart')

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
            email = form.cleaned_data['email']  # ← email is now defined

            # ── Blocked customer check ──
            if BlockedCustomer.objects.filter(email__iexact=email).exists():
                messages.error(request, 'Unable to process your order.')
                return redirect('orders:checkout')
            
            order = form.save(commit=False)
            order.user = request.user if request.user.is_authenticated else None
            order.subtotal = subtotal
            order.discount_amount = promo_discount
            order.total = total
            order.promo_code = promo_code_obj
            order.status = 'pending'
            order.save()
            grant_access(request, 'order', order.pk)  # only this browser may reopen it

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
                request.session['pending_stripe_session_id'] = checkout_session.id
                return HttpResponseRedirect(checkout_session.url, status=303)  # BUG-004: redirect() ignored code=

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


def _stripe_says_paid(request, order):
    """Ask Stripe directly whether this browser's checkout session was paid."""
    session_id = request.session.get('pending_stripe_session_id')
    if not session_id:
        return False
    try:
        stripe_session = stripe.checkout.Session.retrieve(session_id)
    except stripe.error.StripeError:
        logger.exception("Could not ask Stripe about session %s", session_id)
        return False
    return stripe_session_confirms_payment(stripe_session, order)


def payment_success(request):
    order_id = request.session.get('pending_order_id')
    if not order_id:
        return redirect('orders:cart')

    order = Order.objects.filter(pk=order_id).first()
    if order is None:
        return redirect('orders:cart')

    if order.status == 'pending':
        # BUG-001: reaching this URL proves nothing, so ask Stripe. If the webhook already
        # confirmed the order the status is no longer 'pending' and we skip straight ahead.
        if not _stripe_says_paid(request, order):
            messages.warning(request, "We haven't received confirmation of your payment yet. "
                                      "If your card was charged, your order will be confirmed "
                                      "automatically within a minute. Otherwise please try again.")
            return redirect('orders:cart')
        confirm_order_paid(order.pk)  # safe even if the webhook is doing the same thing right now

    # Payment is settled: clear the cart and the checkout bookkeeping.
    Cart(request).clear()
    for key in ('pending_order_id', 'pending_stripe_session_id', 'promo_code'):
        request.session.pop(key, None)

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
    request.session.pop('pending_stripe_session_id', None)

    messages.error(request, 'Payment was cancelled. Your cart has been kept — please try again.')
    return redirect('orders:checkout')


# Stripe sends one of these when a card payment succeeds (or a delayed payment finally does).
PAID_EVENT_TYPES = ('checkout.session.completed', 'checkout.session.async_payment_succeeded')


@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', None)

    if not webhook_secret:
        logger.warning('Stripe webhook called but STRIPE_WEBHOOK_SECRET is not set; ignoring it.')
        return HttpResponse(status=200)

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    if event['type'] in PAID_EVENT_TYPES:
        stripe_session = event['data']['object']
        order_id = (stripe_session.get('metadata') or {}).get('order_id')
        order = Order.objects.filter(pk=order_id).first() if str(order_id).isdigit() else None
        # Only confirm when Stripe says THIS order was paid in full. Unknown orders are ignored
        # (still answer 200, otherwise Stripe keeps retrying a message we will never accept).
        if order and stripe_session_confirms_payment(stripe_session, order):
            confirm_order_paid(order.pk)

    return HttpResponse(status=200)


def _can_view_order(request, order):
    """BUG-002: only the browser that placed the order, or its signed-in owner."""
    if has_access(request, 'order', order.pk):
        return True
    return request.user.is_authenticated and order.user_id == request.user.id


def order_confirmation(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if not _can_view_order(request, order):
        raise Http404  # 404, not 403: do not reveal that this order exists
    return render(request, 'orders/order_confirmation.html', {'order': order})


def order_history(request):
    """Orders placed from this browser, plus the signed-in customer's own orders."""
    mine = Q(pk__in=remembered_ids(request, 'order'))
    if request.user.is_authenticated:
        mine |= Q(user=request.user)
    orders = (Order.objects
              .filter(mine, status__in=['confirmed', 'preparing', 'ready', 'completed'])
              .prefetch_related('items')
              .order_by('-id'))
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