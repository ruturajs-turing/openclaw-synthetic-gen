"""Console entrypoint. argparse + interactive prompts; subscribes a console listener.

The full rich.Live dashboard lands in P7; until then a plain console listener prints the
event stream so dry-runs and tiny real runs are observable.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rich.console import Console

from .config import Settings, load_keys
from .events import Event, EventBus, EventType
from . import orchestrator

console = Console()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="synthgen", description="Unified synthetic data pipeline")
    p.add_argument("--personas", dest="num_personas", type=int, help="number of personas to generate")
    p.add_argument("--tasks", dest="tasks_per_persona", type=int, help="tasks per persona")
    p.add_argument("--seed", type=int, default=None, help="deterministic spine seed")
    p.add_argument("--run-dir", dest="run_dir", default=None, help="output directory (resumable)")
    p.add_argument("--concurrency", type=int, default=None, help="text-generation concurrency")
    p.add_argument("--asset-concurrency", dest="asset_concurrency", type=int, default=None)
    p.add_argument("--max-assets", dest="max_assets", type=int, default=None, help="cap total assets this run")
    p.add_argument("--budget-usd", dest="budget_usd", type=float, default=None, help="hard dollar ceiling")
    p.add_argument("--persona-model", dest="persona_model", default=None)
    p.add_argument("--task-model", dest="task_model", default=None)
    p.add_argument("--image-model", dest="image_model", default=None)
    p.add_argument("--tts-model", dest="tts_model", default=None)
    p.add_argument("--minimal", action="store_true",
                   help="generate only the curated essential documents (IDs, finance, health, personal) instead of the full manifest")
    p.add_argument("--dry-run", dest="dry_run", action="store_true", help="estimate cost, make no API calls")
    p.add_argument("--recovery-passes", dest="recovery_passes", type=int, default=3,
                   help="max auto-recovery passes to backfill failed items (default 3)")
    p.add_argument("--no-recovery", dest="no_recovery", action="store_true",
                   help="disable auto-recovery (single pass only)")
    p.add_argument("--plain", action="store_true", help="plain log output instead of the live dashboard")
    p.add_argument("--yes", "-y", action="store_true", help="skip interactive confirmation")
    return p


def console_listener(ev: Event) -> None:
    t = ev.type
    if t == EventType.COST_UPDATE:
        d = ev.data
        if "total" not in d:
            return  # per-call running tally; the dashboard shows this live (P7)
        console.print(f"[bold cyan]Cost estimate[/] ({ev.msg}):")
        counts = d.get("counts", {})
        console.print(
            f"  personas={counts.get('personas')} tasks={counts.get('tasks')} "
            f"(batches={counts.get('task_batches')}) images={counts.get('images')} "
            f"audio={counts.get('audio')} pdf={counts.get('pdf')}"
        )
        console.print(
            f"  [yellow]persona ${d.get('persona')} · task ${d.get('task')} · embed ${d.get('embed')} · "
            f"image ${d.get('image')} · audio ${d.get('audio')}[/]"
        )
        console.print(f"  [bold green]TOTAL ≈ ${d.get('total')}[/]")
    elif t == EventType.STAGE_STARTED:
        console.print(f"[blue]▶ stage[/] {ev.stage} {ev.msg}")
    elif t == EventType.STAGE_FINISHED:
        console.print(f"[green]✓ stage[/] {ev.stage} {ev.msg}")
    elif t == EventType.ERROR:
        console.print(f"[red]ERROR[/] {ev.msg}")
    elif t == EventType.LOG:
        console.print(f"[dim]· {ev.msg}[/]")
    elif t == EventType.RUN_FINISHED:
        console.print(f"[bold]Run finished.[/] {ev.data}")


def jsonl_logger(run_dir: Path):
    log_path = run_dir / "logs" / "run.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    fh = log_path.open("a", encoding="utf-8")

    def _listen(ev: Event) -> None:
        fh.write(json.dumps(ev.to_dict()) + "\n")
        fh.flush()

    return _listen


def _prompt_int(label: str, default: int) -> int:
    raw = console.input(f"{label} [[cyan]{default}[/]]: ").strip()
    return int(raw) if raw else default


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = Settings.from_args(args)

    # Interactive prompts when counts not supplied on the command line.
    if args.num_personas is None:
        settings.num_personas = _prompt_int("How many personas?", settings.num_personas)
    if args.tasks_per_persona is None:
        settings.tasks_per_persona = _prompt_int("How many tasks per persona?", settings.tasks_per_persona)
    if args.seed is not None:
        settings.seed = args.seed

    # Key presence check (warn, don't hard-fail in dry-run).
    missing = [k for k in ("anthropic", "gemini") if not settings.keys.get(k)]
    if missing and not settings.dry_run:
        console.print(f"[red]Missing API keys: {missing}. Add them to Api_Keys or env.[/]")
        return 2
    if missing:
        console.print(f"[yellow]Note: missing keys {missing} (ok for --dry-run).[/]")

    bus = EventBus()
    bus.subscribe(jsonl_logger(settings.run_dir))

    # Live dashboard for real interactive runs; plain log for dry-run / non-TTY / --plain.
    import sys

    def _drive():
        # Real runs use the error-collecting auto-recovery wrapper; dry-run is a single pass.
        if settings.dry_run or getattr(args, "no_recovery", False):
            orchestrator.run(settings, bus)
        else:
            orchestrator.run_with_recovery(settings, bus, max_passes=args.recovery_passes)

    use_dashboard = not args.plain and not settings.dry_run and sys.stdout.isatty()
    if use_dashboard:
        from .ui.dashboard import live_dashboard
        with live_dashboard(bus):
            _drive()
    else:
        bus.subscribe(console_listener)
        _drive()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
