import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Creates the first superuser from environment variables, if it does not exist yet'

    def handle(self, *args, **options):
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', '').strip()
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', '').strip()
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', '')

        # No fallback values: a default account like admin / admin123 is a gift to attackers.
        if not (username and email and password):
            self.stdout.write(self.style.WARNING(
                'Skipping superuser creation. To create one, set DJANGO_SUPERUSER_USERNAME, '
                'DJANGO_SUPERUSER_EMAIL and DJANGO_SUPERUSER_PASSWORD.'))
            return

        User = get_user_model()
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'Superuser "{username}" already exists.'))
            return

        try:
            validate_password(password)  # rejects short, common (like admin123) and all-number passwords
        except ValidationError as exc:
            raise CommandError('DJANGO_SUPERUSER_PASSWORD is too weak: ' + ' '.join(exc.messages))

        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f'Superuser "{username}" created successfully!'))
