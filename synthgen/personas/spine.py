"""Stage 1 — deterministic persona spine. Thin event-emitting wrapper around the lifted
generate_spine logic (synthgen.personas._spine_src). No API, fully reproducible by seed."""

from __future__ import annotations

import json
from pathlib import Path

from . import _spine_src
from ..events import Event, EventBus, EventType


def build(num_personas: int, seed: int, run_dir: Path, bus: EventBus) -> list[dict]:
    """Generate the spine, write personas.json under run_dir, return persona records."""
    bus.emit(Event(EventType.STEP_STARTED, stage="personas",
                   msg=f"spine: {num_personas} personas (seed {seed})"))
    personas, clusters = _spine_src.generate(num_personas, seed)
    out = run_dir / "personas.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"personas": personas}, indent=2, ensure_ascii=False), encoding="utf-8")

    ids = [p["persona_id"] for p in personas]
    assert len(ids) == len(set(ids)), "duplicate persona ids in spine"
    conns = sum(len(p["connections"]) for p in personas)
    bus.emit(Event(EventType.STEP_FINISHED, stage="personas",
                   msg=f"spine written: {len(personas)} personas, {len(clusters)} clusters, {conns} connections",
                   data={"path": str(out)}))
    return personas
