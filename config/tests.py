import os
import runpy
from pathlib import Path
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings


class ProductionSettingsTests(SimpleTestCase):
    def load_settings(self, environment):
        with patch.dict(os.environ, environment, clear=True):
            return runpy.run_path(str(Path(__file__).with_name("settings.py")))

    def test_production_requires_a_secret_key_by_default(self):
        with self.assertRaisesMessage(ImproperlyConfigured, "DJANGO_SECRET_KEY is required"):
            self.load_settings({})

    def test_production_reads_environment_and_enables_https(self):
        settings = self.load_settings({
            "DJANGO_SECRET_KEY": "test-configuration-value",
            "DJANGO_ALLOWED_HOSTS": "backend.example.com, localhost, ",
        })

        self.assertFalse(settings["DEBUG"])
        self.assertEqual(settings["SECRET_KEY"], "test-configuration-value")
        self.assertEqual(settings["ALLOWED_HOSTS"], ["backend.example.com", "localhost"])
        self.assertTrue(settings["SECURE_SSL_REDIRECT"])
        self.assertTrue(settings["SESSION_COOKIE_SECURE"])
        self.assertTrue(settings["CSRF_COOKIE_SECURE"])

    def test_local_debug_mode_can_start_without_a_secret(self):
        settings = self.load_settings({"DJANGO_DEBUG": "true"})

        self.assertTrue(settings["DEBUG"])
        self.assertTrue(settings["SECRET_KEY"])
        self.assertFalse(settings["SECURE_SSL_REDIRECT"])

    @override_settings(SECURE_SSL_REDIRECT=True, ALLOWED_HOSTS=["backend.example.com"])
    def test_production_redirects_http_to_https(self):
        response = self.client.get("/api/health/", HTTP_HOST="backend.example.com")

        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], "https://backend.example.com/api/health/")
