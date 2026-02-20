from django.contrib import admin
from .models import Reservation


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('name', 'date', 'time', 'number_of_guests', 'status', 'phone', 'email', 'created_at')
    list_filter = ('status', 'date')
    list_editable = ('status',)
    search_fields = ('name', 'email', 'phone')
    ordering = ('-date', '-time')
    readonly_fields = ('created_at', 'updated_at')