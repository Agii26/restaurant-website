from django.urls import path
from . import views
from . import orders_views
from . import reservations_views
from . import menu_views
from . import customer_views
from . import payment_views
from . import staff_views

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

    # ── Reservations ──
    path('reservations/', reservations_views.reservations_list, name='reservations_list'),
    path('reservations/<int:reservation_id>/', reservations_views.reservation_detail, name='reservation_detail'),
    path('reservations/<int:reservation_id>/approve/', reservations_views.reservation_approve, name='reservation_approve'),
    path('reservations/<int:reservation_id>/reject/', reservations_views.reservation_reject, name='reservation_reject'),
    path('reservations/<int:reservation_id>/cancel/', reservations_views.reservation_cancel, name='reservation_cancel'),
    path('reservations/<int:reservation_id>/note/', reservations_views.reservation_add_note, name='reservation_add_note'),

    # ── Menu ──
    path('menu/', menu_views.menu_list, name='menu_list'),
    path('menu/add/', menu_views.menu_item_add, name='menu_item_add'),
    path('menu/<int:item_id>/edit/', menu_views.menu_item_edit, name='menu_item_edit'),
    path('menu/<int:item_id>/delete/', menu_views.menu_item_delete, name='menu_item_delete'),
    path('menu/<int:item_id>/toggle/', menu_views.menu_item_toggle, name='menu_item_toggle'),
    path('menu/import/', menu_views.menu_csv_import, name='menu_csv_import'),
    path('menu/import/template/', menu_views.menu_csv_template, name='menu_csv_template'),
    path('menu/categories/', menu_views.categories_list, name='categories_list'),

    # ── Customers ──
    path('customers/', customer_views.customers_list, name='customers_list'),
    path('customers/<str:email>/', customer_views.customer_detail, name='customer_detail'),
    path('customers/<str:email>/block/', customer_views.customer_block, name='customer_block'),
    path('customers/<str:email>/unblock/', customer_views.customer_unblock, name='customer_unblock'),

    # ── Payments ──
    path('payments/', payment_views.payments_list, name='payments_list'),
    path('payments/export/', payment_views.payments_export_csv, name='payments_export_csv'),
    path('payments/<int:order_id>/', payment_views.payment_detail, name='payment_detail'),
    path('payments/<int:order_id>/refund/', payment_views.payment_refund, name='payment_refund'),

    # ── Staff ──
    path('staff/', staff_views.staff_list, name='staff_list'),
    path('staff/add/', staff_views.staff_add, name='staff_add'),
    path('staff/<int:staff_id>/edit/', staff_views.staff_edit, name='staff_edit'),
    path('staff/<int:staff_id>/toggle/', staff_views.staff_toggle_active, name='staff_toggle_active'),
    path('staff/<int:staff_id>/password/', staff_views.staff_reset_password, name='staff_reset_password'),
    path('staff/<int:staff_id>/delete/', staff_views.staff_delete, name='staff_delete'),
]