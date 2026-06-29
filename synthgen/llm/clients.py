"""LLM client factories. Lazy imports so the package loads without the SDKs installed
(e.g. during --dry-run or self-checks)."""

from __future__ import annotations

import os
from functools import lru_cache


@lru_cache(maxsize=8)
def anthropic_sync(key: str):
    import anthropic
    return anthropic.Anthropic(api_key=key)


@lru_cache(maxsize=8)
def anthropic_async(key: str):
    import anthropic
    return anthropic.AsyncAnthropic(api_key=key)


@lru_cache(maxsize=8)
def openai_sync(key: str, base_url: str | None = None):
    from openai import OpenAI
    return OpenAI(api_key=key, base_url=base_url or os.getenv("OPENAI_BASE_URL") or None)


@lru_cache(maxsize=8)
def openai_async(key: str, base_url: str | None = None):
    from openai import AsyncOpenAI
    return AsyncOpenAI(api_key=key, base_url=base_url or os.getenv("OPENAI_BASE_URL") or None)
