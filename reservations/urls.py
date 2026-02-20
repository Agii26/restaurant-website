from django.urls import path
from . import views

app_name = 'reservations'

urlpatterns = [
    path('', views.reservation_page, name='reservation'),
    path('confirmation/<int:pk>/', views.confirmation_page, name='confirmation'),
]