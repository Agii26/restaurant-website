from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('cart/', views.cart_view, name='cart'),
    path('cart/count/', views.cart_count, name='cart_count'),
    path('add/<int:item_id>/', views.add_to_cart, name='add_to_cart'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('payment/cancel/', views.payment_cancel, name='payment_cancel'),
    path('webhook/', views.stripe_webhook, name='stripe_webhook'),
    path('confirmation/<int:pk>/', views.order_confirmation, name='order_confirmation'),
    path('history/', views.order_history, name='order_history'),
]