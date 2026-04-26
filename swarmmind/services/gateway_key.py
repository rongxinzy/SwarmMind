"""Gateway key generation and retrieval.

The gateway key is a random token that DeerFlow uses to authenticate with the
SwarmMind LLM Gateway. It is generated once on first access and persisted in
the database so that DeerFlow can reuse it across restarts.
"""

from __future__ import annotations

import logging
import os
import secrets

from swarmmind.config import API_HOST, API_PORT
from swarmmind.db import session_scope
from swarmmind.db_models import LlmProviderDB

logger = logging.getLogger(__name__)

_GATEWAY_KEY_TABLE = "__gateway_key__"
_GATEWAY_KEY_PROVIDER_ID = "__swarmmind_gateway__"


def get_gateway_key() -> str:
    """Return the current gateway key, creating one if it does not exist."""
    with session_scope() as session:
        # Check if we have a gateway key stored as a special provider row
        provider = session.get(LlmProviderDB, _GATEWAY_KEY_PROVIDER_ID)
        if provider is not None:
            return provider.api_key_encrypted  # This field stores the raw gateway key

        # Generate and persist a new key
        key = "sk-swarmmind-" + secrets.token_urlsafe(32)
        provider = LlmProviderDB(
            provider_id=_GATEWAY_KEY_PROVIDER_ID,
            name=_GATEWAY_KEY_TABLE,
            provider_type="internal",
            api_key_encrypted=key,
            is_enabled=0,
            is_default=0,
        )
        session.add(provider)
        session.commit()
        logger.info("Generated new gateway key")
        return key


def get_gateway_base_url() -> str:
    """Return the base URL for the LLM Gateway."""
    return f"http://{API_HOST}:{API_PORT}/gateway/v1"


def ensure_gateway_key_in_env() -> str:
    """Ensure the gateway key is set in os.environ for DeerFlow config resolution.

    Returns the key.
    """
    key = get_gateway_key()
    os.environ["SWARMMIND_GATEWAY_KEY"] = key
    return key
