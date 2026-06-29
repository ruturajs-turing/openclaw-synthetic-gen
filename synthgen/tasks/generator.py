"""Stage 2 — privacy task generation. Reimplements the per-persona batch loop so it emits
synthgen events and routes API calls through the event-emitting LLM layer, while preserving
the source pipeline's two load-bearing mechanisms EXACTLY:

  * Backpropagation: `previously_generated = all_tasks[-25:]` fed into the next batch's
    user prompt for story continuity (task_generator.py:77).
  * Embedding dedup gate: EmbeddingStore.check_batch -> flag -> regen up to N attempts
    with a novelty hint (task_generator.py:106-158).

The heavy logic (HTG system/user prompts, response parser, gemini-embedding LanceDB store)
is the vendored _kit, untouched.
"""

from __future__ import annotations

import asyncio
import json
import math
from pathlib import Path

from ._kit_bootstrap import ensure_kit_on_path
from .adapter import to_task_persona
from ..config import Settings
from ..costs import CostModel
from ..events import Event, EventBus, EventType

BATCH_SIZE = 5


def _make_embed_store(settings: Settings):
    ensure_kit_on_path()
    from embedding_store import EmbeddingStore
    return EmbeddingStore(
        db_path=str(settings.run_dir / "task_embeddings_db"),
        api_key=settings.gemini_key,
        model=settings.embedding_model,
        threshold=settings.similarity_threshold,
    )


async def _call_once(bus, costs, settings, pid, system_prompt, user_prompt) -> list[dict]:
    """One model call -> parsed tasks, with light retry. Returns [] on persistent failure."""
    ensure_kit_on_path()
    from response_parser import parse_tasks_response
    from ..llm.call import acall_text

    for attempt in range(1, settings.max_regen_attempts + 1):
        try:
            text = await acall_text(
                bus, costs, provider="anthropic", model=settings.task_model,
                system=system_prompt, user=user_prompt, key=settings.anthropic_key,
                max_tokens=16384, temperature=None, persona_id=pid, kind="task", bucket="task",
            )
            tasks = parse_tasks_response(text)
            if tasks:
                return tasks
            bus.log(f"{pid}: parse returned 0 tasks (attempt {attempt})", persona_id=pid)
        except Exception as e:  # noqa: BLE001
            bus.error(f"{pid}: task call failed: {type(e).__name__}: {e} (attempt {attempt})", persona_id=pid)
            if attempt == settings.max_regen_attempts:
                return []
            await asyncio.sleep(2 ** attempt)
    return []


async def generate_for_persona(persona: dict, settings: Settings, bus: EventBus,
                               costs: CostModel, embed_store, start_seq: int = 1) -> list[dict]:
    ensure_kit_on_path()
    from prompts.system_prompt import get_system_prompt
    from prompts.user_prompt import build_user_prompt

    pid = persona["persona_id"]
    persona_num = int(pid.split("-")[-1])
    n = settings.tasks_per_persona
    num_batches = max(1, math.ceil(n / BATCH_SIZE))
    system_prompt = get_system_prompt(start_seq=start_seq)

    all_tasks: list[dict] = []
    for batch_num in range(1, num_batches + 1):
        previously_generated = all_tasks[-25:] if all_tasks else []   # backprop (exact)
        user_prompt = build_user_prompt(
            persona, batch_num, previously_generated, persona_num,
            start_seq=start_seq, persona_assets=None,
        )
        tasks = await _call_once(bus, costs, settings, pid, system_prompt, user_prompt)

        # Embedding similarity gate + regen loop (preserved from task_generator.py).
        if embed_store and tasks:
            accepted, flagged = embed_store.check_batch(tasks)
            if flagged:
                bus.emit(Event(EventType.DEDUP_FLAGGED, persona_id=pid,
                               msg=f"batch {batch_num}: {len(flagged)} too similar, regenerating",
                               data={"flagged": [t.get("task_id", "?") for t in flagged]}))
                for attempt in range(1, settings.max_regen_attempts + 1):
                    novelty_hint = (
                        "\n\nIMPORTANT: The following task IDs were too similar to existing "
                        "tasks and must be regenerated with DIFFERENT themes, domains, and "
                        "scenarios. Avoid: "
                        + "; ".join(t.get("_flagged_reason", "") for t in flagged)
                    )
                    regen_tasks = await _call_once(bus, costs, settings, pid, system_prompt,
                                                   user_prompt + novelty_hint)
                    if not regen_tasks:
                        break
                    regen_accepted, still_flagged = embed_store.check_batch(regen_tasks)
                    accepted.extend(regen_accepted)
                    if not still_flagged:
                        bus.log(f"{pid} batch {batch_num}: regen attempt {attempt} succeeded", persona_id=pid)
                        break
                    flagged = still_flagged
            embed_store.store_batch(accepted)
            tasks = accepted

        all_tasks.extend(tasks)
        bus.emit(Event(EventType.TASK_BATCH_GENERATED, persona_id=pid,
                       msg=f"batch {batch_num}/{num_batches} -> {len(tasks)} tasks (total {len(all_tasks)})",
                       data={"batch": batch_num, "n": len(tasks)}))

    all_tasks = all_tasks[:n]  # ponytail: model emits 5/batch; truncate to requested count

    out_dir = settings.run_dir / "personas" / pid
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "tasks.json").write_text(json.dumps(all_tasks, indent=2, ensure_ascii=False), encoding="utf-8")
    return all_tasks


async def generate_all(personas: list[dict], settings: Settings, bus: EventBus,
                       costs: CostModel, done: set[str] | None = None) -> dict[str, list[dict]]:
    """Generate tasks for every persona, bounded concurrency. Returns {persona_id: tasks}.
    Skips personas already in `done` (resume) or with a complete tasks.json on disk.
    """
    done = done or set()
    embed_store = _make_embed_store(settings) if settings.gemini_key else None
    if embed_store is None:
        bus.log("no Gemini key: embedding dedup disabled for this run")

    sem = asyncio.Semaphore(max(1, settings.concurrency))
    results: dict[str, list[dict]] = {}

    async def _one(p: dict):
        pid = p["persona_id"]
        existing = settings.run_dir / "personas" / pid / "tasks.json"
        if pid in done or existing.exists():
            try:
                prev = json.loads(existing.read_text(encoding="utf-8"))
                if prev:  # non-empty => genuinely complete; empty file = failed run, retry
                    results[pid] = prev
                    bus.log(f"{pid}: tasks exist ({len(prev)}), skip", persona_id=pid)
                    return
            except (json.JSONDecodeError, OSError):
                pass
        async with sem:
            tp = to_task_persona(settings.run_dir, p)
            results[pid] = await generate_for_persona(tp, settings, bus, costs, embed_store)

    await asyncio.gather(*(_one(p) for p in personas), return_exceptions=False)
    return results
