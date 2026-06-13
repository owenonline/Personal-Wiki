from __future__ import annotations

import os
from typing import Any


def build_client() -> Any:
    """Return an Anthropic client.

    Prefers the standard Claude SDK when ``ANTHROPIC_API_KEY`` is set; otherwise
    falls back to Claude Platform on AWS (Anthropic-operated, first-party
    parity) using ``ANTHROPIC_AWS_API_KEY`` as the short-term API key, with
    ``AWS_REGION`` and ``ANTHROPIC_AWS_WORKSPACE_ID`` read from the environment
    by the client. Both clients are used identically (``client.beta.messages``).
    """
    import anthropic

    if os.environ.get("ANTHROPIC_API_KEY"):
        return anthropic.Anthropic()
    aws_key = os.environ.get("ANTHROPIC_AWS_API_KEY")
    if aws_key:
        return anthropic.AnthropicAWS(api_key=aws_key)
    raise RuntimeError(
        "No Anthropic credentials found. Set ANTHROPIC_API_KEY for the standard "
        "API, or ANTHROPIC_AWS_API_KEY + AWS_REGION + ANTHROPIC_AWS_WORKSPACE_ID "
        "for Claude Platform on AWS."
    )
