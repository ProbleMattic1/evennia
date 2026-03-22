"""
Docker/PostgreSQL settings override.

When running Evennia in Docker with PostgreSQL (e.g. via docker-compose),
set the POSTGRES_HOST environment variable. This file will then override
DATABASES to use PostgreSQL instead of SQLite.

Environment variables used:
  POSTGRES_HOST   - Database host (e.g. "postgres" for docker-compose service)
  POSTGRES_DB     - Database name (default: evennia)
  POSTGRES_USER   - Database user (default: evennia)
  POSTGRES_PASSWORD - Database password
  POSTGRES_PORT   - Database port (default: 5432)

See: https://www.evennia.com/docs/latest/Setup/Installation-Docker.html
"""

import os

if os.getenv("POSTGRES_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "evennia"),
            "USER": os.getenv("POSTGRES_USER", "evennia"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", "password"),
            "HOST": os.getenv("POSTGRES_HOST", "postgres"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
        }
    }
