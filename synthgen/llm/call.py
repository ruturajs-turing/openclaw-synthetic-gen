"""Event-emitting LLM call wrappers. Every network call emits API_CALL_STARTED then
API_CALL_FINISHED (feeding the dashboard's API side panel) and records cost.

Sync wrappers (call_text) drive persona expansion; async wrappers (acall_text) drive the
task generator's concurrent batches.
"""

from __future__ import annotations

import time

from . import clients
from ..costs import CostModel
from ..events import Event, EventBus, EventType


def _strip_text_anthropic(resp) -> tuple[str, int, int]:
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    u = getattr(resp, "usage", None)
    return text, (getattr(u, "input_tokens", 0) or 0), (getattr(u, "output_tokens", 0) or 0)


def _strip_text_openai(resp) -> tuple[str, int, int]:
    text = resp.choices[0].message.content or ""
    u = getattr(resp, "usage", None)
    return text, (getattr(u, "prompt_tokens", 0) or 0), (getattr(u, "completion_tokens", 0) or 0)


def _emit_start(bus, provider, model, persona_id, kind):
    bus.emit(Event(EventType.API_CALL_STARTED, persona_id=persona_id,
                   data={"provider": provider, "model": model, "kind": kind}))
    return time.perf_counter()


def _emit_finish(bus, costs, provider, model, persona_id, kind, bucket, in_tok, out_tok, t0, error=None):
    usd = 0.0 if error else costs.add_text(model, in_tok, out_tok, bucket)
    bus.emit(Event(EventType.API_CALL_FINISHED, persona_id=persona_id,
                   data={"provider": provider, "model": model, "kind": kind,
                         "latency_ms": round((time.perf_counter() - t0) * 1000),
                         "in_tok": in_tok, "out_tok": out_tok, "usd": round(usd, 5),
                         "error": str(error) if error else None}))
    bus.emit(Event(EventType.COST_UPDATE, data={"spent_usd": round(costs.spent_usd, 4)}))


def call_text(
    bus: EventBus, costs: CostModel, *, provider: str, model: str, system: str, user: str,
    key: str, max_tokens: int = 8192, temperature: float = 0.9,
    persona_id: str | None = None, kind: str = "text", bucket: str = "task",
) -> str:
    t0 = _emit_start(bus, provider, model, persona_id, kind)
    try:
        temp = {} if temperature is None else {"temperature": temperature}
        if provider == "openai":
            resp = clients.openai_sync(key).chat.completions.create(
                model=model, max_tokens=max_tokens, **temp,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            )
            text, in_tok, out_tok = _strip_text_openai(resp)
        else:
            resp = clients.anthropic_sync(key).messages.create(
                model=model, max_tokens=max_tokens, **temp,
                system=system, messages=[{"role": "user", "content": user}],
            )
            text, in_tok, out_tok = _strip_text_anthropic(resp)
    except Exception as e:
        _emit_finish(bus, costs, provider, model, persona_id, kind, bucket, 0, 0, t0, error=e)
        raise
    _emit_finish(bus, costs, provider, model, persona_id, kind, bucket, in_tok, out_tok, t0)
    return text


async def acall_text(
    bus: EventBus, costs: CostModel, *, provider: str, model: str, system: str, user: str,
    key: str, max_tokens: int = 8192, temperature: float = 1.0,
    persona_id: str | None = None, kind: str = "task", bucket: str = "task",
) -> str:
    t0 = _emit_start(bus, provider, model, persona_id, kind)
    try:
        temp = {} if temperature is None else {"temperature": temperature}
        if provider == "openai":
            resp = await clients.openai_async(key).chat.completions.create(
                model=model, max_tokens=max_tokens, **temp,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            )
            text, in_tok, out_tok = _strip_text_openai(resp)
        else:
            resp = await clients.anthropic_async(key).messages.create(
                model=model, max_tokens=max_tokens, **temp,
                system=system, messages=[{"role": "user", "content": user}],
            )
            text, in_tok, out_tok = _strip_text_anthropic(resp)
    except Exception as e:
        _emit_finish(bus, costs, provider, model, persona_id, kind, bucket, 0, 0, t0, error=e)
        raise
    _emit_finish(bus, costs, provider, model, persona_id, kind, bucket, in_tok, out_tok, t0)
    return text
