from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('cart/', views.cart_view, name='cart'),
    path('add/<int:item_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/count/', views.cart_count, name='cart_count'),
    path('checkout/', views.checkout_view, name='checkout'),
    path('login/', views.checkout_login, name='checkout_login'),
    path('confirmation/<int:pk>/', views.order_confirmation, name='order_confirmation'),
    path('history/', views.order_history, name='order_history'),
]