"""Stage 1b — LLM expansion of spines into workspace trees. Reuses the lifted builder
functions (persona_brief, prompts, write_workspace) but routes the LLM call through the
event-emitting synthgen.llm layer for progress + cost tracking.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import _builders
from ._prompts import SYSTEM_PROMPT, build_life_pack_prompt
from ._prompts.artifact_prompts import schema_as_text
from ..costs import CostModel
from ..events import Event, EventBus, EventType
from ..config import Settings


def _expand_one(p: dict, id_to_name: dict, all_personas: dict, settings: Settings,
                bus: EventBus, costs: CostModel, attempts: int = 3) -> dict:
    pid = p["persona_id"]
    brief = _builders.persona_brief(p, id_to_name)
    user = build_life_pack_prompt(brief, schema_as_text())
    import time
    last_err: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            raw = call_text_for_expand(settings, bus, costs, pid, user)
            pack = _builders.parse_json_object(raw)
            _builders.write_workspace(settings.run_dir, p, pack, all_personas)
            return pack
        except json.JSONDecodeError as e:
            # LLMs occasionally emit malformed JSON — retry (next attempt usually parses).
            last_err = e
            dbg = settings.run_dir / "_failed"
            dbg.mkdir(parents=True, exist_ok=True)
            try:
                (dbg / f"{pid}.attempt{attempt}.raw.txt").write_text(raw, encoding="utf-8")
            except Exception:
                pass
            bus.emit(Event(EventType.LOG, persona_id=pid, stage="personas",
                           msg=f"{pid}: invalid JSON from model (attempt {attempt}/{attempts}), retrying"))
        except Exception as e:  # noqa: BLE001  (rate limit / API / network — transient)
            last_err = e
            bus.emit(Event(EventType.LOG, persona_id=pid, stage="personas",
                           msg=f"{pid}: expand error {type(e).__name__} (attempt {attempt}/{attempts}), retrying"))
        if attempt < attempts:
            time.sleep(min(2 ** attempt, 8))
    raise last_err  # type: ignore[misc]


def call_text_for_expand(settings, bus, costs, pid, user) -> str:
    from ..llm.call import call_text
    from ..llm.route import provider_for, key_for
    model = settings.persona_model
    return call_text(
        bus, costs,
        provider=provider_for(model), model=model,
        system=SYSTEM_PROMPT, user=user, key=key_for(settings, model),
        max_tokens=8192, temperature=0.9,
        persona_id=pid, kind="persona_expand", bucket="persona",
    )


def expand_all(personas: list[dict], settings: Settings, bus: EventBus, costs: CostModel,
               done: set[str] | None = None) -> dict[str, dict]:
    """Expand each persona's workspace. Skips persona_ids already in `done` (resume).
    Sequential for now (persona expand is not the throughput bottleneck); concurrency knob
    is reserved for the task stage. Returns {persona_id: life_pack}.
    """
    done = done or set()
    all_personas = {p["persona_id"]: p for p in personas}
    id_to_name = {pid: p.get("full_name", pid) for pid, p in all_personas.items()}
    packs: dict[str, dict] = {}
    for p in personas:
        pid = p["persona_id"]
        if pid in done or (settings.run_dir / "personas" / pid / "MEMORY.md").exists():
            bus.emit(Event(EventType.LOG, persona_id=pid, stage="personas", msg=f"{pid}: workspace exists, skip"))
            continue
        try:
            packs[pid] = _expand_one(p, id_to_name, all_personas, settings, bus, costs)
            bus.emit(Event(EventType.PERSONA_GENERATED, persona_id=pid, stage="personas",
                           msg=f"{pid} expanded"))
        except Exception as e:  # noqa: BLE001
            bus.error(f"{pid} expand failed: {type(e).__name__}: {e}", persona_id=pid)
    return packs
