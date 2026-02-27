from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from dashboard.models import StaffProfile

class Command(BaseCommand):
    help = 'Create StaffProfile for existing superusers'

    def handle(self, *args, **kwargs):
        superusers = User.objects.filter(is_superuser=True)
        for user in superusers:
            profile, created = StaffProfile.objects.get_or_create(
                user=user,
                defaults={'role': 'owner'}
            )
            if created:
                self.stdout.write(f'Created StaffProfile for {user.username}')
            else:
                self.stdout.write(f'StaffProfile already exists for {user.username}')
