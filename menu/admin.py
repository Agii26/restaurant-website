from django.contrib import admin
from .models import Category, MenuItem, Tag, AddOn


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name",)


class AddOnInline(admin.TabularInline):
    model = AddOn
    extra = 1
    fields = ("name", "additional_price")


class MenuItemInline(admin.TabularInline):
    model = MenuItem
    extra = 1
    fields = ("name", "price", "is_available", "is_featured")
    show_change_link = True


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "order_position", "is_active")
    list_editable = ("order_position", "is_active")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [MenuItemInline]


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "is_available", "is_featured")
    list_filter = ("category", "is_available", "is_featured", "tags")
    list_editable = ("price", "is_available", "is_featured")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("tags",)
    inlines = [AddOnInline]