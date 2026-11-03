"""ASGI config for the BugResolutionPortal project."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bug_portal.settings")

application = get_asgi_application()
