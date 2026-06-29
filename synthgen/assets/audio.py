"""Audio generator — OpenAI TTS (gpt-4o-mini-tts). The persona's cached tts_voice keeps a
consistent voice. Note: the current manifest has no 'audio' modality entries, but the
generator + routing exist so audio-modality assets (voicemail, audio-journal) generate when
present. Emits API_CALL events + records audio cost.
"""

from __future__ import annotations

import time
from functools import lru_cache

from .dispatcher import register
from ..manifest.extract import PlannedAsset
from ..config import Settings
from ..costs import CostModel
from ..events import Event, EventBus, EventType


@lru_cache(maxsize=4)
def _client(key: str):
    from openai import OpenAI
    return OpenAI(api_key=key)


def _transcript(pa: PlannedAsset) -> str:
    return (f"This is a synthetic {pa.entry.kind} recording for persona {pa.persona_id}. "
            "All content is fictional test data and contains no real personal information.")


async def _generate(pa: PlannedAsset, settings: Settings, bus: EventBus, costs: CostModel) -> None:
    voice = pa.context.get("tts_voice") or "alloy"
    text = _transcript(pa)
    bus.emit(Event(EventType.API_CALL_STARTED, persona_id=pa.persona_id,
                   data={"provider": "openai", "model": settings.tts_model, "kind": f"audio:{pa.entry.kind}"}))
    t0 = time.perf_counter()
    try:
        resp = _client(settings.openai_key).audio.speech.create(
            model=settings.tts_model, voice=voice, input=text)
        resp.stream_to_file(str(pa.out_path))
    except Exception as e:  # noqa: BLE001
        bus.emit(Event(EventType.API_CALL_FINISHED, persona_id=pa.persona_id,
                       data={"provider": "openai", "model": settings.tts_model,
                             "kind": f"audio:{pa.entry.kind}", "error": str(e),
                             "latency_ms": round((time.perf_counter() - t0) * 1000)}))
        raise
    usd = costs.add_audio(len(text))
    bus.emit(Event(EventType.API_CALL_FINISHED, persona_id=pa.persona_id,
                   data={"provider": "openai", "model": settings.tts_model, "kind": f"audio:{pa.entry.kind}",
                         "latency_ms": round((time.perf_counter() - t0) * 1000), "usd": round(usd, 5)}))
    bus.emit(Event(EventType.COST_UPDATE, data={"spent_usd": round(costs.spent_usd, 4)}))


register("audio")(_generate)
