from django.urls import path
from . import views
from . import orders_views

app_name = 'dashboard'

urlpatterns = [
    # ── Core ──
    path('', views.dashboard_home, name='home'),
    path('login/', views.staff_login, name='login'),
    path('logout/', views.staff_logout, name='logout'),

    # ── Orders ──
    path('orders/', orders_views.orders_list, name='orders_list'),
    path('orders/<int:order_id>/', orders_views.order_detail, name='order_detail'),
    path('orders/<int:order_id>/status/', orders_views.order_update_status, name='order_update_status'),
    path('orders/<int:order_id>/cancel/', orders_views.order_cancel, name='order_cancel'),
    path('orders/<int:order_id>/print/', orders_views.order_print, name='order_print'),
]