"""LLM Status Renderer — generates human-readable status summaries on demand."""

import logging

from swarmmind.llm import LLMClient, LLMError
from swarmmind.layered_memory import LayeredMemory
from swarmmind.models import MemoryContext

logger = logging.getLogger(__name__)


def render_status(goal: str, ctx: MemoryContext | None = None, reasoning: bool = False) -> str:
    """
    LLM Status Renderer: given a goal, read all relevant shared context
    and generate a human-readable prose summary.

    Args:
        goal: the supervisor's query.
        ctx: optional memory context to scope reads to specific session/team/project.
             When None, reads all layers — use this when no session context is available
             (e.g., a supervisor checking status without an active conversation).
        reasoning: whether to enable LLM reasoning/thinking mode.

    Phase 1: returns prose summary only.
    Phase 2: LLM decides format (prose / table / Gantt).
    """
    # Read layered memory — ctx=None means all layers, which is correct for
    # a status check that has no session context. Callers that have a ctx
    # (e.g. conversation_id as session_id) should pass it for scoped reads.
    memory = LayeredMemory(agent_id="status_renderer")
    all_entries = memory.read_all(ctx=ctx)

    # Build context string for LLM
    if all_entries:
        context_lines = []
        for entry in all_entries:
            tag_str = ",".join(entry.tags) if entry.tags else "unknown"
            context_lines.append(f"[{entry.key}] ({tag_str}): {entry.value}")
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
[respond_in_language] Detect the language of the text below and respond in that same language.
Text: {goal}
</goal>

<shared_context>
{context_block}
</shared_context>

Respond with ONLY a prose summary. No tables, no bullet lists, no code fences.
Just natural language that a human supervisor can quickly read to understand status."""

    try:
        client = LLMClient()
        summary = client.complete(prompt, max_tokens=1024, reasoning=reasoning)
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
        title = client.complete(prompt, max_tokens=32, reasoning=False)
        title = title.strip()
        if len(title) > 50:
            title = title[:47] + "..."
        return title
    except LLMError as e:
        logger.error("Title generation error: %s", e)
        return user_message[:50] + ("..." if len(user_message) > 50 else "")


def generate_conversation_title_from_exchange(
    user_message: str,
    assistant_message: str,
) -> tuple[str, str]:
    """
    Generate a conversation title from the first complete exchange.

    Returns:
        tuple[title, source], where source is 'llm' or 'fallback'.
    """
    prompt = f"""<system>
You generate titles for chat sessions.

Given the first user message and the assistant's first response, return one concise
title that captures the real intent of the session.

Rules:
- 3 to 8 words when possible
- no quotes
- no punctuation decoration
- no explanation
- prefer concrete task intent over generic labels
</system>

User:
{user_message[:500]}

Assistant:
{assistant_message[:500]}

Respond with ONLY the title."""

    try:
        client = LLMClient()
        title = client.complete(prompt, max_tokens=32, reasoning=False).strip()
        if not title:
            raise LLMError("Empty title response")
        if len(title) > 60:
            title = title[:57] + "..."
        return title, "llm"
    except Exception as e:
        logger.error("Exchange title generation error: %s", e)
        fallback = user_message[:50].strip()
        if len(user_message) > 50:
            fallback += "..."
        return fallback or "New Conversation", "fallback"
