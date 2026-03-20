"""LLM Status Renderer — generates human-readable status summaries on demand."""

import json
import logging
import os

import httpx

from swarmmind.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_PROVIDER
from swarmmind.shared_memory import SharedMemory

logger = logging.getLogger(__name__)


def render_status(goal: str) -> str:
    """
    LLM Status Renderer: given a goal, read all relevant shared context
    and generate a human-readable prose summary.

    Phase 1: returns prose summary only.
    Phase 2: LLM decides format (prose / table / Gantt).
    """
    # Read all shared memory for context
    memory = SharedMemory(agent_id="status_renderer")
    all_entries = memory.read_all()

    # Build context string for LLM
    if all_entries:
        context_lines = [
            f"[{entry['key']}] ({entry.get('domain_tags', 'unknown')}): {entry['value']}"
            for entry in all_entries
        ]
        context_block = "\n".join(context_lines)
    else:
        context_block = "(No shared context yet. The team has not accumulated any memory.)"

    prompt = f"""<system>
You are the SwarmMind Status Renderer. Your job is to synthesize a human-readable
status report from the team's accumulated context.

Given a goal and the current shared context, produce a clear, concise prose summary
that answers: "What is the current status of this project/goal?"

Keep it informative but not overly long. Highlight what's been done, what's in
progress, and what might be missing.
</system>

<goal>
{goal}
</goal>

<shared_context>
{context_block}
</shared_context>

Respond with ONLY a prose summary. No tables, no bullet lists, no code fences.
Just natural language that a human supervisor can quickly read to understand status."""

    try:
        if LLM_PROVIDER == "anthropic":
            summary = _call_anthropic(prompt)
        else:
            summary = _call_openai(prompt)
        return summary.strip()
    except Exception as e:
        logger.error("LLM Status Renderer error: %s", e)
        return (
            f"[Status renderer error: {e}] "
            f"Shared context has {len(all_entries)} entries. "
            f"Goal: {goal}"
        )


def _call_openai(prompt: str) -> str:
    api_key = LLM_API_KEY or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    base_url = LLM_BASE_URL or "https://api.openai.com/v1"
    url = f"{base_url.rstrip('/')}/chat/completions"

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024,
        "temperature": 0.4,
    }

    with httpx.Client(timeout=60.0) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


def _call_anthropic(prompt: str) -> str:
    api_key = LLM_API_KEY or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    base_url = LLM_BASE_URL or "https://api.anthropic.com/v1"
    url = f"{base_url.rstrip('/')}/messages"

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    payload = {
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024,
    }

    with httpx.Client(timeout=60.0) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]
