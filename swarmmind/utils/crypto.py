"""Fernet symmetric encryption for sensitive data at rest.

The encryption key is sourced from the ``SWARMMIND_ENCRYPTION_KEY`` environment
variable. If unset, a deterministic key is derived from the machine ID so that
data remains decryptable across restarts in single-node deployments. For
production multi-node setups, ``SWARMMIND_ENCRYPTION_KEY`` must be set to a
shared 32-byte base64-encoded Fernet key.
"""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.fernet import Fernet


def _derive_key_from_machine_id() -> bytes:
    """Derive a stable Fernet key from machine-specific ID.

    Used as a fallback when SWARMMIND_ENCRYPTION_KEY is not set.
    """
    machine_id = ""
    for path in ["/etc/machine-id", "/var/lib/dbus/machine-id"]:
        try:
            machine_id = open(path).read().strip()
            break
        except FileNotFoundError:
            continue
    if not machine_id:
        machine_id = os.environ.get("USER", "default") + "@" + os.uname().nodename
    # Fernet key must be 32 bytes base64-encoded (43 chars)
    raw = hashlib.sha256(machine_id.encode()).digest()
    return base64.urlsafe_b64encode(raw)


def _get_fernet_key() -> bytes:
    env_key = os.environ.get("SWARMMIND_ENCRYPTION_KEY", "").strip()
    if env_key:
        # Allow base64-encoded key or raw string (we hash it to 32 bytes)
        try:
            decoded = base64.urlsafe_b64decode(env_key)
            if len(decoded) == 32:
                return base64.urlsafe_b64encode(decoded)
        except Exception:
            pass
        raw = hashlib.sha256(env_key.encode()).digest()
        return base64.urlsafe_b64encode(raw)
    return _derive_key_from_machine_id()


_FERNET = Fernet(_get_fernet_key())


def encrypt(plaintext: str) -> str:
    """Encrypt a string; returns base64-encoded ciphertext."""
    return _FERNET.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt(ciphertext: str) -> str:
    """Decrypt a base64-encoded ciphertext; returns plaintext string."""
    return _FERNET.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
