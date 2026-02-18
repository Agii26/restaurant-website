from django.db import models
from django.utils.text import slugify


class Tag(models.Model):
    TAG_CHOICES = [
        ('spicy', '🌶 Spicy'),
        ('vegan', '🌱 Vegan'),
        ('bestseller', '⭐ Bestseller'),
        ('new', '🆕 New'),
    ]
    name = models.CharField(max_length=50, choices=TAG_CHOICES, unique=True)

    def __str__(self):
        return self.get_name_display()


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    order_position = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["order_position", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="items")
    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to="menu_images/", blank=True, null=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name="items")
    is_available = models.BooleanField(default=True, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} — ${self.price}"

    def get_base_price(self):
        return self.price


class AddOn(models.Model):
    dish = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name="addons")
    name = models.CharField(max_length=100)
    additional_price = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.dish.name} — {self.name} (+${self.additional_price})"