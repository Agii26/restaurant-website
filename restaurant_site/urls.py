from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render
from menu.models import MenuItem


def home(request):
    featured_dishes = MenuItem.objects.filter(
        is_featured=True,
        is_available=True
    ).select_related('category')[:6]
    return render(request, 'home.html', {'featured_dishes': featured_dishes})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('menu/', include('menu.urls')),
    path('reservations/', include('reservations.urls')),
    path('orders/', include('orders.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)