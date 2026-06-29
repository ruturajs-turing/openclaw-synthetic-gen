"""Sequences the six pipeline stages and owns the run checkpoint.

P0: stage bodies are stubs that emit events; the dry-run path produces a real cost
estimate (text costs computed precisely; asset counts read from a representative
docs-manifest so the full-manifest image estimate is honest). Later phases replace each
stub with the lifted/new implementation.
"""

from __future__ import annotations

import json
from pathlib import Path

from .config import DOCS_MANIFEST_DIR, Settings
from .costs import CostModel
from .events import Event, EventBus, EventType
from .state import RunState

STAGES = ["personas", "tasks", "memory", "extract", "assets", "package"]


def _sample_manifest_counts() -> dict[str, int]:
    """Count modalities in one representative docs-manifest file (per-persona estimate)."""
    counts = {"image": 0, "document": 0, "audio": 0, "other": 0}
    files = sorted(DOCS_MANIFEST_DIR.glob("P-*.json")) if DOCS_MANIFEST_DIR.exists() else []
    if not files:
        return counts
    try:
        entries = json.loads(files[0].read_text(encoding="utf-8"))
    except Exception:
        return counts
    for e in entries:
        m = (e.get("modality") or "").lower()
        counts[m if m in counts else "other"] += 1
    return counts


def estimate(settings: Settings) -> dict:
    per = _sample_manifest_counts()
    n = settings.num_personas
    est = CostModel.estimate_run(
        num_personas=n,
        tasks_per_persona=settings.tasks_per_persona,
        persona_model=settings.persona_model,
        task_model=settings.task_model,
        n_images=per["image"] * n,
        n_audio=per["audio"] * n,
        n_pdf=per["document"] * n,
    )
    est["per_persona_assets"] = per
    return est


def run(settings: Settings, bus: EventBus) -> RunState:
    state = RunState.load_or_init(settings.run_dir)
    bus.emit(Event(EventType.RUN_STARTED, data={"run_id": state.run_id, "dry_run": settings.dry_run}))

    if settings.dry_run:
        est = estimate(settings)
        bus.emit(Event(EventType.COST_UPDATE, msg="dry-run estimate", data=est))
        # Walk stages so the UI/event stream looks identical to a real run.
        for stage in STAGES:
            bus.emit(Event(EventType.STAGE_STARTED, stage=stage, msg="(dry-run)"))
            bus.emit(Event(EventType.STAGE_FINISHED, stage=stage, msg="(dry-run, no network)"))
        bus.emit(Event(EventType.RUN_FINISHED, data={"estimated_usd": est["total"]}))
        return state

    # Real run: implemented incrementally across phases P1–P6.
    costs = CostModel(spent_usd=state.cost_usd_spent)
    ctx: dict = {}  # shared between stages (personas, packs, tasks, plans)
    for stage in STAGES:
        bus.emit(Event(EventType.STAGE_STARTED, stage=stage))
        if state.stage_done.get(stage):
            bus.emit(Event(EventType.STAGE_FINISHED, stage=stage, msg="already done (resumed)"))
            _rehydrate_stage(stage, settings, ctx)
            continue
        _run_stage(stage, settings, bus, state, costs, ctx)
        state.stage_done[stage] = True
        state.cost_usd_spent = costs.spent_usd
        state.save()
        bus.emit(Event(EventType.STAGE_FINISHED, stage=stage, msg=f"${round(costs.spent_usd, 4)} spent so far"))

    bus.emit(Event(EventType.RUN_FINISHED, data={"cost_usd": round(state.cost_usd_spent, 4)}))
    return state


def _load_personas(run_dir: Path) -> list[dict]:
    f = run_dir / "personas.json"
    return json.loads(f.read_text(encoding="utf-8"))["personas"] if f.exists() else []


def _rehydrate_stage(stage: str, settings: Settings, ctx: dict) -> None:
    """On resume, repopulate ctx that a completed stage would have produced."""
    if stage == "personas" and "personas" not in ctx:
        ctx["personas"] = _load_personas(settings.run_dir)
    elif stage == "tasks" and "tasks" not in ctx:
        tasks_map: dict = {}
        for p in ctx.get("personas") or _load_personas(settings.run_dir):
            f = settings.run_dir / "personas" / p["persona_id"] / "tasks.json"
            if f.exists():
                tasks_map[p["persona_id"]] = json.loads(f.read_text(encoding="utf-8"))
        ctx["tasks"] = tasks_map


def _run_stage(stage: str, settings: Settings, bus: EventBus, state: RunState,
               costs: CostModel, ctx: dict) -> None:
    if stage == "personas":
        from .personas import spine, expand
        personas = _load_personas(settings.run_dir) or spine.build(
            settings.num_personas, settings.seed, settings.run_dir, bus)
        ctx["personas"] = personas
        expand.expand_all(personas, settings, bus, costs, done=state.personas_done)
        # Mark done only if the workspace actually landed (failed expands retry on resume).
        for p in personas:
            if (settings.run_dir / "personas" / p["persona_id"] / "MEMORY.md").exists():
                state.personas_done.add(p["persona_id"])
        if not state.personas_done:
            raise RuntimeError("persona expansion produced no workspaces (check model id / API key)")
        return

    if stage == "tasks":
        import asyncio
        from .tasks.generator import generate_all
        personas = ctx.get("personas") or _load_personas(settings.run_dir)
        ctx["personas"] = personas
        tasks_map = asyncio.run(generate_all(personas, settings, bus, costs, done=state.tasks_done))
        ctx["tasks"] = tasks_map
        for pid, tlist in tasks_map.items():
            if tlist:
                state.tasks_done.add(pid)
        return

    if stage == "memory":
        from .memory.builder import build_all
        personas = ctx.get("personas") or _load_personas(settings.run_dir)
        tasks_map = ctx.get("tasks") or {}
        ctx["mem_state"] = build_all(settings.run_dir, personas, tasks_map, bus)
        return

    if stage == "extract":
        from .manifest.extract import build_plan, write_pii_index
        personas = ctx.get("personas") or _load_personas(settings.run_dir)
        tasks_map = ctx.get("tasks") or {}
        mem = ctx.get("mem_state") or {}
        plans: dict = {}
        for p in personas:
            pid = p["persona_id"]
            plan = build_plan(settings.run_dir, p, tasks_map.get(pid, []), mem.get(pid))
            write_pii_index(settings.run_dir, pid, plan)
            plans[pid] = plan
            bus.emit(Event(EventType.STEP_FINISHED, stage="extract", persona_id=pid,
                           msg=f"{pid}: {len(plan)} assets planned, pii_index written"))
        ctx["plans"] = plans
        return

    if stage == "assets":
        import asyncio
        from .assets import register_all
        from .assets.dispatcher import dispatch
        register_all()
        plans = ctx.get("plans")
        if not plans:
            from .manifest.extract import build_plan
            personas = ctx.get("personas") or _load_personas(settings.run_dir)
            mem = ctx.get("mem_state") or {}
            tasks_map = ctx.get("tasks") or {}
            plans = {p["persona_id"]: build_plan(settings.run_dir, p, tasks_map.get(p["persona_id"], []),
                                                 mem.get(p["persona_id"])) for p in personas}
        flat = [pa for pid in plans for pa in plans[pid]]
        asyncio.run(dispatch(flat, settings, bus, costs, state))
        return

    if stage == "package":
        from .packaging.packager import package_all
        from .packaging.run_index import write as write_index
        personas = ctx.get("personas") or _load_personas(settings.run_dir)
        tasks_map = ctx.get("tasks") or {}
        per_persona = package_all(settings.run_dir, personas, tasks_map, bus)
        state.cost_usd_spent = costs.spent_usd
        out = write_index(settings.run_dir, settings, state, per_persona)
        bus.log(f"run manifest written: {out}", stage="package")
        return

    bus.log(f"stage '{stage}' not yet implemented (skeleton)", stage=stage)
