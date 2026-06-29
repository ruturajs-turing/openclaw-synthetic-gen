"""Pick the API provider + key from a model id, so persona/task models can be either
Anthropic (claude-*) or OpenAI (gpt-*, o1/o3/o4, chatgpt-*)."""

from __future__ import annotations


def provider_for(model: str) -> str:
    m = (model or "").lower()
    if m.startswith(("gpt", "o1", "o3", "o4", "chatgpt")):
        return "openai"
    return "anthropic"  # claude-* and default


def key_for(settings, model: str) -> str:
    return settings.openai_key if provider_for(model) == "openai" else settings.anthropic_key
