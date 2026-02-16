from django.contrib import admin
from django.urls import path
from django.http import HttpResponse

def home(request):
    return HttpResponse("""
    <html>
        <head><title>My Restaurant</title></head>
        <body>
            <h1>Welcome to My Restaurant!</h1>
            <p>Website is live on Render! 🎉</p>
            <p><a href="/admin">Go to Admin Panel</a></p>
        </body>
    </html>
    """)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
]