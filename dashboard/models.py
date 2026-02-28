from django.db import models
from django.contrib.auth.models import User


class StaffProfile(models.Model):
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('manager', 'Manager'),
        ('staff', 'Staff'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='staff')
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.get_full_name() or self.user.username} ({self.get_role_display()})'

    @property
    def is_owner(self):
        return self.role == 'owner'

    @property
    def is_manager(self):
        return self.role in ('owner', 'manager')

    @property
    def can_manage_menu(self):
        return self.role in ('owner', 'manager')

    @property
    def can_manage_staff(self):
        return self.role == 'owner'

    @property
    def can_view_payments(self):
        return self.role in ('owner', 'manager')


class BlockedCustomer(models.Model):
    email = models.EmailField(unique=True)
    reason = models.TextField(blank=True)
    blocked_at = models.DateTimeField(auto_now_add=True)
    blocked_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='blocked_customers'
    )

    def __str__(self):
        return f'Blocked: {self.email}'

    class Meta:
        ordering = ['-blocked_at']