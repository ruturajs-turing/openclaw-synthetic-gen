"""Stage 1 — persona spine. Thin event-emitting wrapper around the lifted generate_spine
logic (synthgen.personas._spine_src). No API. Deterministic for a GIVEN seed; when no seed
is provided a fresh random one is drawn each run (so personas differ every time) and the
seed used is recorded in personas.json for reproducibility."""

from __future__ import annotations

import json
import random
from pathlib import Path

from . import _spine_src
from ..events import Event, EventBus, EventType


def build(num_personas: int, seed: int | None, run_dir: Path, bus: EventBus) -> list[dict]:
    """Generate the spine, write personas.json under run_dir, return persona records.
    seed=None => draw a fresh random seed (true per-run variety)."""
    if seed is None:
        seed = random.SystemRandom().randrange(1, 2 ** 31)  # true entropy
    bus.emit(Event(EventType.STEP_STARTED, stage="personas",
                   msg=f"spine: {num_personas} personas (seed {seed})"))
    personas, clusters = _spine_src.generate(num_personas, seed)
    out = run_dir / "personas.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"seed": seed, "personas": personas}, indent=2, ensure_ascii=False), encoding="utf-8")

    ids = [p["persona_id"] for p in personas]
    assert len(ids) == len(set(ids)), "duplicate persona ids in spine"
    conns = sum(len(p["connections"]) for p in personas)
    bus.emit(Event(EventType.STEP_FINISHED, stage="personas",
                   msg=f"spine written: {len(personas)} personas, {len(clusters)} clusters, {conns} connections",
                   data={"path": str(out)}))
    return personas
