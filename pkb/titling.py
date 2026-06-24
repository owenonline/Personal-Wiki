from __future__ import annotations

from typing import Any

# Only the first few turns are needed to name a chat; keep the prompt cheap.
MAX_MESSAGES = 6


def _block_text(content: Any) -> str:
    """Flatten an Anthropic message `content` (list of blocks, or a raw str)
    into plain text, tolerating both SDK objects and plain dicts."""
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for block in content or []:
        text = getattr(block, "text", None)
        if text is None and isinstance(block, dict):
            text = block.get("text")
        if text:
            parts.append(text)
    return "".join(parts)


def generate_chat_title(client: Any, model: str, messages: list[dict]) -> str | None:
    """Ask a lightweight model for a short title for a chat.

    Returns the title string, or ``None`` on any failure (e.g. no messages,
    model unavailable, network error) so the chat simply stays untitled.
    """
    convo = "\n".join(
        f"{m['role']}: {m['content']}"
        for m in messages[:MAX_MESSAGES]
        if m.get("content")
    ).strip()
    if not convo:
        return None
    try:
        resp = client.messages.create(
            model=model,
            max_tokens=24,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Write a concise 3-6 word title for this conversation. "
                        "Reply with only the title — no quotes, no trailing "
                        "punctuation.\n\n" + convo
                    ),
                }
            ],
        )
        title = _block_text(resp.content).strip().strip('"').strip()
        return title[:80] or None
    except Exception:
        return None
