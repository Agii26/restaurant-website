from menu.models import MenuItem, AddOn
from decimal import Decimal


CART_SESSION_KEY = 'cart'


class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(CART_SESSION_KEY)
        if not cart:
            cart = self.session[CART_SESSION_KEY] = {}
        self.cart = cart

    def _get_item_key(self, item_id, addon_id=None):
        return f"{item_id}_addon_{addon_id}" if addon_id else str(item_id)

    def add(self, menu_item, quantity=1, addon=None):
        key = self._get_item_key(menu_item.id, addon.id if addon else None)
        price = menu_item.price + (addon.additional_price if addon else Decimal('0'))

        if key in self.cart:
            self.cart[key]['quantity'] += quantity
        else:
            self.cart[key] = {
                'item_id': menu_item.id,
                'addon_id': addon.id if addon else None,
                'name': menu_item.name,
                'addon_name': addon.name if addon else None,
                'price': str(price),
                'quantity': quantity,
            }
        self.save()

    def remove(self, key):
        if key in self.cart:
            del self.cart[key]
            self.save()

    def update_quantity(self, key, quantity):
        if key in self.cart:
            if quantity <= 0:
                self.remove(key)
            else:
                self.cart[key]['quantity'] = quantity
                self.save()

    def save(self):
        self.session.modified = True

    def clear(self):
        self.session[CART_SESSION_KEY] = {}
        self.session.modified = True

    def __iter__(self):
        for key, item in self.cart.items():
            item = item.copy()
            item['key'] = key
            item['price'] = Decimal(item['price'])
            item['total'] = item['price'] * item['quantity']
            yield item

    def get_subtotal(self):
        return sum(Decimal(item['price']) * item['quantity'] for item in self.cart.values())

    def get_total_items(self):
        return sum(item['quantity'] for item in self.cart.values())

    def is_empty(self):
        return len(self.cart) == 0