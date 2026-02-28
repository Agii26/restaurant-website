from django.db import models


class Reservation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ]

    OCCASION_CHOICES = [
        ('', 'No special occasion'),
        ('birthday', 'Birthday'),
        ('anniversary', 'Anniversary'),
        ('date_night', 'Date Night'),
        ('business', 'Business Dinner'),
        ('celebration', 'Celebration'),
        ('other', 'Other'),
    ]

    # Customer Info
    name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=20)

    # Booking Info
    date = models.DateField()
    time = models.TimeField()
    number_of_guests = models.PositiveIntegerField()
    special_request = models.TextField(blank=True)
    occasion = models.CharField(max_length=20, choices=OCCASION_CHOICES, blank=True)

    # System Fields
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-time']

    def __str__(self):
        return f"{self.name} — {self.date} {self.time} ({self.number_of_guests} guests)"

    def save(self, *args, **kwargs):
        # Auto-confirm small groups (1-4), pending for large groups (5+)
        if not self.pk:  # only on creation
            if self.number_of_guests <= 4:
                self.status = 'confirmed'
            else:
                self.status = 'pending'
        super().save(*args, **kwargs)
    
    staff_note = models.TextField(blank=True, default='')

