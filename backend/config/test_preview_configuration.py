"""Static offline checks for isolated preview and release safety.

No Docker engine, Yahoo requests, local database or secrets needed.
"""

from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


ROOT = Path(settings.BASE_DIR).parent


class PreviewIsolationTests(SimpleTestCase):
    def test_preview_database_is_distinct_from_operators_databases(self):
        compose = (ROOT / "compose.preview.yml").read_text(encoding="utf-8")
        self.assertIn("DB_NAME: marketpulse_preview", compose)
        self.assertIn("POSTGRES_DB: marketpulse_preview", compose)
        self.assertNotIn("DB_NAME: ai_stock_market", compose)
        self.assertNotIn("DB_NAME: marketpulse_restored_test", compose)
        self.assertNotIn("ports: [\"5432:5432\"]", compose)
        self.assertIn('ports: ["127.0.0.1:8088:80"]', compose)

    def test_local_http_login_and_production_configuration_are_separated(self):
        compose = (ROOT / "compose.preview.yml").read_text(encoding="utf-8")
        self.assertIn('DJANGO_DEBUG: "true"', compose)
        self.assertNotIn('DJANGO_DEBUG: "false"', compose)
        deploy_guide = (ROOT / "docs" / "DEPLOYMENT.md").read_text(encoding="utf-8")
        self.assertIn("DJANGO_DEBUG=false", deploy_guide)
        self.assertIn("HTTPS", deploy_guide)

    def test_uploads_not_exposed_by_preview_nginx(self):
        nginx = (ROOT / "frontend" / "deploy" / "nginx.conf").read_text(
            encoding="utf-8"
        )
        self.assertIn("location /media/", nginx)
        self.assertIn("return 404;", nginx)

    def test_preview_secrets_are_gitignored(self):
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("preview.env", gitignore)
