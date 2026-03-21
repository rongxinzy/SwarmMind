"""LLM Status Renderer — generates human-readable status summaries on demand."""

import logging

from swarmmind.llm import LLMClient, LLMError
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
        client = LLMClient()
        summary = client.complete(prompt, max_tokens=1024)
        return summary.strip()
    except LLMError as e:
        logger.error("LLM Status Renderer error: %s", e)
        return (
            f"[Status renderer error: {e}] "
            f"Shared context has {len(all_entries)} entries. "
            f"Goal: {goal}"
        )


def generate_conversation_title(user_message: str) -> str:
    """
    Generate a short, descriptive title for a conversation based on the user's first message.
    Uses the LLM to summarize the intent in 3-8 words.
    """
    prompt = f"""<system>
You are a conversation title generator. Given a user's first message in a conversation,
generate a short, descriptive title (3-8 words max) that captures the essence of what they want.

Examples:
- "Show me the Q3 revenue report" -> "Q3 Revenue Report"
- "Review this Python code for bugs" -> "Python Code Review"
- "What's the status of the project?" -> "Project Status Check"
- "Help me debug this API error" -> "API Debugging Help"
</system>

User's first message:
{user_message}

Respond with ONLY the title. No quotes, no explanation. Just the title itself."""

    try:
        client = LLMClient()
        title = client.complete(prompt, max_tokens=32)
        title = title.strip()
        if len(title) > 50:
            title = title[:47] + "..."
        return title
    except Exception as e:
        logger.error("Title generation error: %s", e)
        return user_message[:50] + ("..." if len(user_message) > 50 else "")
