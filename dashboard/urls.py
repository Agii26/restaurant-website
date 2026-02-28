from django.urls import path
from . import views
from . import orders_views
from . import reservations_views
from . import menu_views

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
]