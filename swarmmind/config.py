"""Configuration for SwarmMind.

MVP still reads model/provider defaults from environment, but DeerFlow runtime
config bundles are now materialized explicitly by ``swarmmind.runtime`` instead
of relying on cwd-based ``config.yaml`` discovery.
"""

import os

from dotenv import load_dotenv

# Load .env file if present (override system env vars so .env takes precedence)
load_dotenv(override=True)

# Database
DB_PATH = os.environ.get("SWARMMIND_DB_PATH", "swarmmind.db")

# LLM Provider
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openai")  # "openai" or "anthropic"
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")
LLM_API_KEY = os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
LLM_BASE_URL = os.environ.get("ANTHROPIC_BASE_URL") or os.environ.get(
    "LLM_BASE_URL"
)  # Alibaba DashScope or custom proxy

# Action proposal timeout in seconds
ACTION_TIMEOUT_SECONDS = int(os.environ.get("ACTION_TIMEOUT_SECONDS", "300"))  # 5 minutes

# Supervisor API
API_HOST = os.environ.get("SWARMMIND_API_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("SWARMMIND_API_PORT", "8000"))

# Agent polling interval (seconds)
AGENT_POLL_INTERVAL = int(os.environ.get("AGENT_POLL_INTERVAL", "5"))

# Shared memory retry config
MEMORY_MAX_RETRIES = 3
MEMORY_RETRY_DELAY_MS = 100

# Layered memory TTL config
MEMORY_DEFAULT_L1_TTL_SECONDS = 86400  # 24 hours
MEMORY_MAX_TTL_SECONDS = 604800  # 7 days

# L4 USER_SOUL write authorization — only these agents may write to L4
SOUL_WRITER_AGENT_IDS = {"soul_writer"}

# DeerFlow runtime env overrides
DEER_FLOW_CONFIG_PATH = os.environ.get("DEER_FLOW_CONFIG_PATH", None)
DEER_FLOW_HOME = os.environ.get("DEER_FLOW_HOME", None)
DEER_FLOW_EXTENSIONS_CONFIG_PATH = os.environ.get("DEER_FLOW_EXTENSIONS_CONFIG_PATH", None)
DEER_FLOW_SKILLS_PATH = os.environ.get("DEER_FLOW_SKILLS_PATH", None)

# Disable TitleMiddleware in main thread (we generate title in isolated session)
# This prevents title LLM calls from appearing in the user-facing message stream
try:
    from deerflow.config.title_config import TitleConfig, set_title_config

    set_title_config(TitleConfig(enabled=False))
except ImportError:
    pass  # deerflow not installed
