"""Local password and bearer-token helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

TOKEN_PREFIX = "swm_"  # noqa: S105 - public token prefix, not a token value.
PASSWORD_SCHEME = "pbkdf2_sha256"  # noqa: S105 - password hash scheme name, not a password.
PASSWORD_ITERATIONS = 260_000


def normalize_email(email: str) -> str:
    """Normalize user emails for identity lookup."""
    return email.strip().lower()


def hash_password(password: str) -> str:
    """Hash a password with PBKDF2-HMAC-SHA256."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    salt_b64 = base64.urlsafe_b64encode(salt).decode("ascii").rstrip("=")
    digest_b64 = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return f"{PASSWORD_SCHEME}${PASSWORD_ITERATIONS}${salt_b64}${digest_b64}"


def verify_password(password: str, stored_hash: str | None) -> bool:
    """Verify a password against the stored PBKDF2 hash."""
    if not stored_hash:
        return False
    try:
        scheme, iterations_text, salt_b64, digest_b64 = stored_hash.split("$", 3)
        if scheme != PASSWORD_SCHEME:
            return False
        iterations = int(iterations_text)
        salt = _urlsafe_b64decode(salt_b64)
        expected = _urlsafe_b64decode(digest_b64)
    except (ValueError, TypeError):
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected)


def generate_api_token() -> str:
    """Generate a high-entropy API token."""
    return TOKEN_PREFIX + secrets.token_urlsafe(32)


def hash_api_token(token: str) -> str:
    """Hash an API token for storage and lookup."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _urlsafe_b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
