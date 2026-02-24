from django.core.mail import EmailMultiAlternatives
from django.conf import settings
import os


def _open_template(filename):
    """Read an email HTML template from the orders/email_templates directory."""
    template_dir = os.path.join(os.path.dirname(__file__), 'email_templates')
    path = os.path.join(template_dir, filename)
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def _build_order_items_html(order):
    """Build items table rows HTML for emails."""
    rows = ''
    for item in order.items.all():
        rows += f'''
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:2px;">
          <tr>
            <td style="padding:10px 0;font-size:14px;color:#1a1816;border-bottom:1px solid #e8dcc8;">
              {item.quantity}&times; {item.name}
            </td>
            <td style="padding:10px 0;text-align:right;font-size:14px;color:#1a1816;border-bottom:1px solid #e8dcc8;white-space:nowrap;">
              &#8369;{item.item_total}
            </td>
          </tr>
        </table>
        '''
    return rows


def _build_discount_row_html(order):
    """Build discount row if promo was applied."""
    if order.discount_amount and order.discount_amount > 0:
        return f'''
        <tr>
          <td style="padding:6px 0;font-size:13px;color:#4a7c59;">Discount</td>
          <td style="padding:6px 0;text-align:right;font-size:13px;color:#4a7c59;">&#8722;&#8369;{order.discount_amount}</td>
        </tr>
        '''
    return ''


def send_customer_confirmation(order):
    """Send branded confirmation email to the customer."""
    subject = f'Order Confirmed — #{str(order.order_number)[:8].upper()} | Warm Vibe Bistro'

    order_number = str(order.order_number)[:8].upper()
    pickup_time = order.pickup_time.strftime('%B %d, %Y at %I:%M %p')
    order_items_html = _build_order_items_html(order)
    discount_row_html = _build_discount_row_html(order)

    # Plain text fallback
    plain_items = '\n'.join([
        f'  {item.quantity}x {item.name} — P{item.item_total}'
        for item in order.items.all()
    ])
    plain_text = f"""
Hi {order.name},

Your order has been confirmed and paid!

Order Number: #{order_number}
Pickup Time: {pickup_time}

Items:
{plain_items}

Total: P{order.total}

Please bring this email or your order number when you pick up.

Warm Vibe Bistro
123 Bistro Lane, Makati City, Metro Manila
    """.strip()

    # Build HTML using simple replacement — avoids .format() conflicts with template braces
    html = _open_template('order_confirmation.html')
    html = html.replace('{{ order_number }}', order_number)
    html = html.replace('{{ name }}', order.name)
    html = html.replace('{{ pickup_time }}', pickup_time)
    html = html.replace('{{ order_items_html }}', order_items_html)
    html = html.replace('{{ discount_row_html }}', discount_row_html)
    html = html.replace('{{ total }}', str(order.total))

    msg = EmailMultiAlternatives(
        subject=subject,
        body=plain_text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[order.email],
    )
    msg.attach_alternative(html, 'text/html')
    msg.send(fail_silently=True)


def send_restaurant_notification(order):
    """Send new order alert to the restaurant."""
    order_number = str(order.order_number)[:8].upper()
    pickup_time = order.pickup_time.strftime('%B %d, %Y at %I:%M %p')
    order_items_html = _build_order_items_html(order)
    order_notes = order.order_notes or ''

    subject = f'New Order #{order_number} — P{order.total} — Pickup: {order.pickup_time.strftime("%b %d %I:%M %p")}'

    # Plain text fallback
    plain_items = '\n'.join([
        f'  {item.quantity}x {item.name} — P{item.item_total}'
        for item in order.items.all()
    ])
    plain_text = f"""
NEW ORDER — #{order_number}

Customer: {order.name}
Email: {order.email}
Phone: {order.phone}
Pickup: {pickup_time}
Notes: {order_notes or 'None'}

Items:
{plain_items}

Total: P{order.total}
Payment: Confirmed via Stripe
    """.strip()

    # Build notes row separately to avoid conditional logic in template
    notes_row_html = ''
    if order_notes:
        notes_row_html = f'''
        <tr>
          <td style="padding:6px 0;font-size:13px;color:#7a6f62;vertical-align:top;">Notes</td>
          <td style="padding:6px 0;font-size:14px;color:#1a1816;">{order_notes}</td>
        </tr>
        '''

    # Build HTML using simple replacement — no .format() to avoid brace conflicts
    html = _open_template('restaurant_notification.html')
    html = html.replace('{{ order_number }}', order_number)
    html = html.replace('{{ name }}', order.name)
    html = html.replace('{{ email }}', order.email)
    html = html.replace('{{ phone }}', order.phone)
    html = html.replace('{{ pickup_time }}', pickup_time)
    html = html.replace('{{ order_notes_row }}', notes_row_html)
    html = html.replace('{{ order_items_html }}', order_items_html)
    html = html.replace('{{ total }}', str(order.total))

    msg = EmailMultiAlternatives(
        subject=subject,
        body=plain_text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[settings.RESTAURANT_EMAIL],
    )
    msg.attach_alternative(html, 'text/html')
    msg.send(fail_silently=True)