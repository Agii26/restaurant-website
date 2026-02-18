from django.urls import path
from . import views

app_name = "menu"

urlpatterns = [
    path("", views.menu_page, name="menu"),
    path("dish/<slug:slug>/", views.dish_detail, name="dish_detail"),
]