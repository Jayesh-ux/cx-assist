"""Startup bootstrap: seed the initial admin account from env (if configured)."""
from __future__ import annotations

from app.core.config import settings
from app.core.logging import logger
from app.core.security import hash_password
from app.models.user import User


def bootstrap_admin(db) -> None:
    """Create the platform admin from ADMIN_EMAIL/ADMIN_PASSWORD (idempotent).
    Self-registration only ever creates agents, so this is the sole admin path."""
    if not (settings.admin_email and settings.admin_password):
        logger.info("bootstrap admin: ADMIN_EMAIL/ADMIN_PASSWORD not set, skipping")
        return
    email = settings.admin_email.strip().lower()
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        logger.info("bootstrap admin: %s already present", email)
        return
    admin = User(
        email=email,
        full_name=settings.admin_full_name or "Platform Admin",
        hashed_password=hash_password(settings.admin_password),
        role="admin",
        is_active=True,
    )
    db.add(admin)
    db.commit()
    logger.info("bootstrap admin: seeded %s (role=admin)", email)


def validate_secrets() -> None:
    """Refuse to boot with the insecure default secret key."""
    insecure = ("change-me", "changeme", "secret")
    if (not settings.secret_key) or settings.secret_key.lower() in insecure or "change-me" in settings.secret_key:
        raise RuntimeError(
            "SECRET_KEY must be set to a real random value — refusing to start "
            "with the insecure default. See .env.example."
        )