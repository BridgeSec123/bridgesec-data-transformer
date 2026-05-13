"""
Bootstrap management command for zero-downtime migration to multi-tenancy.

Usage:
    python manage.py create_initial_tenant

What it does:
1. Reads current single-tenant values from settings (OKTA_*, MONGO_*, SERVER_URL)
2. Creates one Tenant document with name="default" in the master DB
3. Updates all existing User documents that have no tenant_id to point to this tenant

Run once, BEFORE flipping MULTI_TENANCY_ENABLED=True.
"""
import logging

from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Create the initial default tenant from existing single-tenant settings"

    def handle(self, *args, **options):
        self.stdout.write("Creating initial tenant from current settings...")

        try:
            from core.models.tenant import Tenant
            from core.models.user import User

            # Build default Okta domain from OKTA_API_URL (strip https://)
            okta_api_url = getattr(settings, "OKTA_API_URL", "")
            okta_domain = okta_api_url.replace("https://", "").replace("http://", "").rstrip("/")

            # Check if default tenant already exists
            existing = Tenant.objects(name="default").first()
            if existing:
                self.stdout.write(
                    self.style.WARNING(f"Default tenant already exists (id={existing.id}). Skipping creation.")
                )
                tenant = existing
            else:
                tenant = Tenant(
                    name="default",
                    okta_domain=okta_domain or "default.okta.com",
                    okta_client_id=getattr(settings, "OKTA_CLIENT_ID", ""),
                    okta_client_secret=getattr(settings, "OKTA_SECRET_KEY", ""),
                    okta_issuer=getattr(settings, "OKTA_ISSUER", ""),
                    mongo_uri=getattr(settings, "MONGO_URI", ""),
                    mongo_db_prefix=getattr(settings, "MONGO_DB_NAME", "bridgesec"),
                    terraform_server_url=getattr(settings, "SERVER_URL", "http://localhost:8080"),
                    terraform_state_path="default",
                    service_client_id=getattr(settings, "OKTA_SERVICE_CLIENT_ID", None) or "",
                    service_private_key=getattr(settings, "OKTA_SERVICE_PRIVATE_KEY", None) or "",
                    service_scopes=getattr(settings, "OKTA_SERVICE_SCOPES", None) or "",
                    is_active=True,
                )
                tenant.save()
                self.stdout.write(
                    self.style.SUCCESS(f"Created default tenant with id={tenant.id}")
                )

            # Update existing Users that have no tenant_id
            updated_count = 0
            for user in User.objects(tenant_id=None):
                user.tenant_id = tenant.id
                user.save()
                updated_count += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"Updated {updated_count} user(s) to belong to default tenant."
                )
            )
            self.stdout.write(
                self.style.SUCCESS(
                    "\nDone! You can now set MULTI_TENANCY_ENABLED=True in .env to activate multi-tenancy."
                )
            )

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error creating initial tenant: {e}"))
            logger.exception("create_initial_tenant failed")
            raise
