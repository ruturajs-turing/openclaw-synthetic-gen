"""Write the top-level run_manifest.json — the index of the whole run."""

from __future__ import annotations

import json
from pathlib import Path

from .. import SYNTHETIC_BANNER, __version__
from ..config import Settings
from ..state import RunState


def write(run_dir: Path, settings: Settings, state: RunState, per_persona: list[dict]) -> Path:
    manifest = {
        "synthgen_version": __version__,
        "run_id": state.run_id,
        "synthetic": True,
        "banner": SYNTHETIC_BANNER,
        "config": {
            "num_personas": settings.num_personas,
            "tasks_per_persona": settings.tasks_per_persona,
            "seed": settings.seed,
            "persona_model": settings.persona_model,
            "task_model": settings.task_model,
            "embedding_model": settings.embedding_model,
            "image_model": settings.image_model,
            "tts_model": settings.tts_model,
            "max_assets": settings.max_assets,
            "budget_usd": settings.budget_usd,
        },
        "totals": {
            "personas": len(per_persona),
            "tasks": sum(p.get("n_tasks", 0) for p in per_persona),
            "assets": sum(p.get("n_assets", 0) for p in per_persona),
            "cost_usd": round(state.cost_usd_spent, 4),
        },
        "personas": per_persona,
    }
    out = run_dir / "run_manifest.json"
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return out
