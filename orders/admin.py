from django.contrib import admin
from .models import Order, OrderItem, PromoCode


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('name', 'price', 'quantity', 'item_total')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number_short', 'name', 'status', 'total', 'pickup_time', 'created_at')
    list_filter = ('status', 'created_at')
    list_editable = ('status',)
    search_fields = ('name', 'email', 'phone')
    readonly_fields = ('order_number', 'subtotal', 'discount_amount', 'total', 'created_at', 'updated_at')
    inlines = [OrderItemInline]

    def order_number_short(self, obj):
        return str(obj.order_number)[:8].upper()
    order_number_short.short_description = 'Order #'


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_percent', 'is_active', 'times_used', 'max_uses', 'expires_at')
    list_editable = ('is_active',)