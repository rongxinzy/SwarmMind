"""Configuration for SwarmMind Phase 1."""

import os
from pathlib import Path

# Database
DB_PATH = os.environ.get("SWARMMIND_DB_PATH", "swarmmind.db")

# LLM Provider
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openai")  # "openai" or "anthropic"
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")
LLM_API_KEY = os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL")  # Optional: for proxies like Ollama

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
