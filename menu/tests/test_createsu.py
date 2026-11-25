"""The deploy script runs `createsu` on every deploy. It must never invent a default admin."""
import os
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

STRONG = "Correct-horse-battery-staple-91"


class CreateSuperuserCommandTests(TestCase):
    def run_createsu(self, **env):
        clean = {k: v for k, v in os.environ.items() if not k.startswith("DJANGO_SUPERUSER_")}
        clean.update(env)
        out = StringIO()
        with patch.dict(os.environ, clean, clear=True):
            call_command("createsu", stdout=out)
        return out.getvalue()

    def test_without_settings_no_account_is_created(self):
        output = self.run_createsu()
        self.assertEqual(User.objects.count(), 0)
        self.assertIn("DJANGO_SUPERUSER_PASSWORD", output)   # tells the owner what to set

    def test_there_is_never_a_default_admin_account(self):
        self.run_createsu()
        self.assertFalse(User.objects.filter(username="admin").exists())

    def test_all_three_settings_create_the_superuser(self):
        self.run_createsu(DJANGO_SUPERUSER_USERNAME="owner", DJANGO_SUPERUSER_EMAIL="owner@example.com",
                          DJANGO_SUPERUSER_PASSWORD=STRONG)
        user = User.objects.get(username="owner")
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.check_password(STRONG))

    def test_the_old_default_password_is_refused_even_when_set_on_purpose(self):
        with self.assertRaises(CommandError):
            self.run_createsu(DJANGO_SUPERUSER_USERNAME="owner", DJANGO_SUPERUSER_EMAIL="owner@example.com",
                              DJANGO_SUPERUSER_PASSWORD="admin123")
        self.assertEqual(User.objects.count(), 0)

    def test_an_existing_account_is_left_alone(self):
        User.objects.create_superuser("owner", "owner@example.com", "the-original-password-77")
        self.run_createsu(DJANGO_SUPERUSER_USERNAME="owner", DJANGO_SUPERUSER_EMAIL="owner@example.com",
                          DJANGO_SUPERUSER_PASSWORD=STRONG)
        self.assertEqual(User.objects.filter(username="owner").count(), 1)
        self.assertTrue(User.objects.get(username="owner").check_password("the-original-password-77"))
