from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='home'),
    path('login/', views.staff_login, name='login'),
    path('logout/', views.staff_logout, name='logout'),
]