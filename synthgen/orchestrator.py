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


def _sample_manifest_counts(minimal: bool = False) -> dict[str, int]:
    """Count modalities in one representative docs-manifest file (per-persona estimate).
    When minimal, count only the curated essential-document kinds."""
    counts = {"image": 0, "document": 0, "audio": 0, "other": 0}
    files = sorted(DOCS_MANIFEST_DIR.glob("P-*.json")) if DOCS_MANIFEST_DIR.exists() else []
    if not files:
        return counts
    try:
        entries = json.loads(files[0].read_text(encoding="utf-8"))
    except Exception:
        return counts
    from .manifest.extract import is_minimal_kind
    for e in entries:
        if minimal and not is_minimal_kind(e.get("kind", "")):
            continue
        m = (e.get("modality") or "").lower()
        counts[m if m in counts else "other"] += 1
    return counts


def estimate(settings: Settings) -> dict:
    minimal = settings.doc_set == "minimal"
    per = _sample_manifest_counts(minimal=minimal)
    n = settings.num_personas
    from .costs import image_price
    est = CostModel.estimate_run(
        num_personas=n,
        tasks_per_persona=settings.tasks_per_persona,
        persona_model=settings.persona_model,
        task_model=settings.task_model,
        n_images=per["image"] * n,
        n_audio=per["audio"] * n,
        n_pdf=per["document"] * n,
        image_usd=image_price(settings.image_model),
    )
    est["per_persona_assets"] = per
    est["doc_set"] = settings.doc_set
    return est


def run(settings: Settings, bus: EventBus, emit_lifecycle: bool = True) -> RunState:
    state = RunState.load_or_init(settings.run_dir)
    if emit_lifecycle:
        bus.emit(Event(EventType.RUN_STARTED, data={"run_id": state.run_id, "dry_run": settings.dry_run}))

    if settings.dry_run:
        est = estimate(settings)
        bus.emit(Event(EventType.COST_UPDATE, msg="dry-run estimate", data=est))
        for stage in STAGES:
            bus.emit(Event(EventType.STAGE_STARTED, stage=stage, msg="(dry-run)"))
            bus.emit(Event(EventType.STAGE_FINISHED, stage=stage, msg="(dry-run, no network)"))
        if emit_lifecycle:
            bus.emit(Event(EventType.RUN_FINISHED, data={"estimated_usd": est["total"]}))
        return state

    # Real run. Every stage is idempotent and skips per-item work that already exists, so the
    # loop always re-enters all stages (cheap, $0 for completed items) — re-running the same
    # run-id self-heals any persona/asset that failed or was added. A stage that raises is
    # logged + checkpointed and stops the run gracefully so a re-run resumes from there.
    costs = CostModel(spent_usd=state.cost_usd_spent)
    ctx: dict = {}  # shared between stages (personas, tasks, plans, mem_state)
    for stage in STAGES:
        bus.emit(Event(EventType.STAGE_STARTED, stage=stage))
        try:
            _run_stage(stage, settings, bus, state, costs, ctx)
        except Exception as e:  # noqa: BLE001
            state.cost_usd_spent = costs.spent_usd
            state.save()
            bus.error(f"stage '{stage}' failed: {type(e).__name__}: {e}", stage=stage)
            if emit_lifecycle:
                bus.emit(Event(EventType.RUN_FINISHED, data={
                    "error": True, "failed_stage": stage, "cost_usd": round(state.cost_usd_spent, 4),
                    "hint": "re-run the same run-id to resume and recover"}))
            return state
        complete = _stage_complete(stage, settings, ctx)
        state.stage_done[stage] = complete
        state.cost_usd_spent = costs.spent_usd
        state.save()
        bus.emit(Event(EventType.STAGE_FINISHED, stage=stage,
                       msg=("complete" if complete else "partial — re-run to backfill")
                            + f" · ${round(costs.spent_usd, 4)} spent"))

    incomplete = [s for s in STAGES if not state.stage_done.get(s)]
    if emit_lifecycle:
        bus.emit(Event(EventType.RUN_FINISHED, data={
            "cost_usd": round(state.cost_usd_spent, 4),
            **({"incomplete_stages": incomplete, "hint": "re-run the same run-id to backfill"} if incomplete else {})}))
    return state


def _completeness_report(settings: Settings) -> dict:
    """Per-persona completeness used to decide whether recovery should run another pass."""
    rd = settings.run_dir
    personas = _load_personas(rd)
    per = []
    for p in personas:
        pid = p["persona_id"]
        d = rd / "personas" / pid
        has_ws = (d / "MEMORY.md").exists()
        f = d / "tasks.json"
        try:
            has_tasks = f.exists() and bool(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            has_tasks = False
        ndocs = len(list((d / "docs").iterdir())) if (d / "docs").is_dir() else 0
        per.append({"persona_id": pid, "workspace": has_ws, "tasks": has_tasks, "n_docs": ndocs})
    n_complete = sum(1 for x in per if x["workspace"] and x["tasks"])
    return {
        "complete": bool(per) and n_complete == len(per),
        "n_personas": len(per), "n_complete": n_complete,
        "personas": per,
        "signature": "|".join(f"{x['persona_id']}:{int(x['workspace'])}{int(x['tasks'])}:{x['n_docs']}" for x in per),
    }


def run_with_recovery(settings: Settings, bus: EventBus, max_passes: int = 3) -> dict:
    """Failsafe wrapper: run the pipeline, then automatically re-run idempotent passes to
    backfill anything that failed (transient LLM/API errors), collecting every error, until
    complete or no further progress. Writes final_report.json + errors.json and emits a final
    RUN_FINISHED carrying the result so the UI can show 'what succeeded / what failed'."""
    state = RunState.load_or_init(settings.run_dir)
    errors: list[dict] = []
    bus.subscribe(lambda ev: errors.append(
        {"ts": ev.ts, "stage": ev.stage, "persona_id": ev.persona_id or ev.data.get("persona_id"),
         "msg": ev.msg}) if ev.type == EventType.ERROR else None)

    bus.emit(Event(EventType.RUN_STARTED, data={"run_id": state.run_id, "recovery": True,
                                                "max_passes": max_passes, "doc_set": settings.doc_set}))
    prev_sig, passes, rep = None, 0, {}
    while passes < max_passes:
        passes += 1
        if passes > 1:
            bus.log(f"recovery pass {passes}/{max_passes} — backfilling failed/missing items")
        state = run(settings, bus, emit_lifecycle=False)
        rep = _completeness_report(settings)
        if rep["complete"] or rep["signature"] == prev_sig:
            break  # done, or no progress between passes (a persistently-failing item)
        prev_sig = rep["signature"]

    report = {
        "run_id": state.run_id, "final": True,
        "complete": rep.get("complete", False),
        "passes": passes,
        "personas": {"total": rep.get("n_personas", 0), "complete": rep.get("n_complete", 0),
                     "failed": [x["persona_id"] for x in rep.get("personas", [])
                                if not (x["workspace"] and x["tasks"])]},
        "errors": errors,
        "n_errors": len(errors),
        "cost_usd": round(state.cost_usd_spent, 4),
    }
    try:
        (settings.run_dir / "final_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        (settings.run_dir / "errors.json").write_text(json.dumps(errors, indent=2), encoding="utf-8")
    except Exception:
        pass
    bus.log(f"FINAL: {'complete ✓' if report['complete'] else 'partial'} · "
            f"{report['personas']['complete']}/{report['personas']['total']} personas · "
            f"{report['n_errors']} errors · {passes} pass(es) · ${report['cost_usd']}")
    bus.emit(Event(EventType.RUN_FINISHED, data=report))
    return report


def _load_personas(run_dir: Path) -> list[dict]:
    f = run_dir / "personas.json"
    return json.loads(f.read_text(encoding="utf-8"))["personas"] if f.exists() else []


def _stage_complete(stage: str, settings: Settings, ctx: dict) -> bool:
    """Per-item completeness so a partial run is marked 'not done' and a re-run backfills it."""
    rd = settings.run_dir
    personas = ctx.get("personas") or _load_personas(rd)
    if not personas:
        return False
    if stage == "personas":
        return all((rd / "personas" / p["persona_id"] / "MEMORY.md").exists() for p in personas)
    if stage == "tasks":
        def _has_tasks(pid):
            f = rd / "personas" / pid / "tasks.json"
            try:
                return f.exists() and bool(json.loads(f.read_text(encoding="utf-8")))
            except Exception:
                return False
        return all(_has_tasks(p["persona_id"]) for p in personas)
    return True  # memory/extract/assets/package are idempotent rewrites/skips


def _run_stage(stage: str, settings: Settings, bus: EventBus, state: RunState,
               costs: CostModel, ctx: dict) -> None:
    if stage == "personas":
        from .personas import spine, expand
        personas = _load_personas(settings.run_dir) or spine.build(
            settings.num_personas, settings.seed, settings.run_dir, bus)
        ctx["personas"] = personas
        # Record the actual seed used (random when unset) so run_manifest is reproducible.
        try:
            meta = json.loads((settings.run_dir / "personas.json").read_text(encoding="utf-8"))
            if meta.get("seed") is not None:
                settings.seed = meta["seed"]
        except Exception:
            pass
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
        minimal = settings.doc_set == "minimal"
        plans: dict = {}
        for p in personas:
            pid = p["persona_id"]
            plan = build_plan(settings.run_dir, p, tasks_map.get(pid, []), mem.get(pid), minimal=minimal)
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
            minimal = settings.doc_set == "minimal"
            plans = {p["persona_id"]: build_plan(settings.run_dir, p, tasks_map.get(p["persona_id"], []),
                                                 mem.get(p["persona_id"]), minimal=minimal) for p in personas}
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
