from django.shortcuts import render, get_object_or_404
from .models import Category, MenuItem


def menu_page(request):
    categories = Category.objects.filter(is_active=True).prefetch_related(
        "items__tags", "items__addons"
    )
    return render(request, "menu/menu.html", {"categories": categories})


def dish_detail(request, slug):
    dish = get_object_or_404(MenuItem, slug=slug, is_available=True)
    return render(request, "menu/dish_detail.html", {"dish": dish})