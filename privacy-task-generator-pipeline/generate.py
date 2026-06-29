#!/usr/bin/env python3
"""Privacy Task Generator — Main CLI entry point."""

import argparse
import asyncio
import csv
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

sys.path.insert(0, str(Path(__file__).parent))

from config import (
    ANTHROPIC_API_KEY, ANTHROPIC_API_KEYS, CONCURRENCY, GOOGLE_API_KEY, MODEL,
    OPENAI_API_KEY, OUTPUT_DIR, PERSONAS_PATH, TASKS_PER_PERSONA,
)
from embedding_store import EmbeddingStore
from existing_seq_inventory import build_start_seq_map
from persona_loader import DATA_LEVEL_MAP, load_personas
from response_parser import _TOOL_TIER_MAP
from similarity import compute_coverage_matrix, deduplicate_tasks
from task_generator import _persona_complete, generate_all

console = Console()

CHAT_BATCH_OUTPUT = OUTPUT_DIR / "chat_batch_v2"


def _parse_persona_ids(spec: str) -> set[str]:
    """Parse persona ID specs in both 3-digit (P-142) and 4-digit (P-0142) formats.

    Accepts: 'P-0142,P-0143' or 'P-0142:P-0225' or 'P-142,P-143' or 'P-142:P-225'
    """
    ids: set[str] = set()
    for part in spec.split(","):
        part = part.strip()
        if ":" in part:
            lo, hi = part.split(":", 1)
            lo_n = int(lo.strip().split("-")[-1])
            hi_n = int(hi.strip().split("-")[-1])
            lo_digits = len(lo.strip().split("-")[-1])
            fmt_width = max(lo_digits, 4)
            for n in range(lo_n, hi_n + 1):
                ids.add(f"P-{n:0{fmt_width}d}")
        else:
            ids.add(part)
    return ids


def save_json(tasks: list[dict], path: Path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)
    console.print(f"  [green]Saved[/green] {path} ({len(tasks)} tasks)")


def save_csv(tasks: list[dict], path: Path):
    if not tasks:
        return
    flat_fields = [
        "task_id", "persona_id", "task_title", "domain", "subdomain",
        "horizontal", "complexity_tier", "goal_summary", "privacy_scenario",
        "memory_file", "memory_note_content", "jailbreak_vector", "jailbreak_prompt",
        "stratum_tag",
    ]
    array_fields = [
        "data_levels", "tool_tiers", "expected_privacy_actions",
        "pii_fields_exercised", "suggested_tools", "realism_hooks",
        "exec_approval_points", "multimodal_assets", "openclaw_skills",
    ]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=flat_fields + array_fields + [
                "rubric_hints_correctness", "rubric_hints_privacy",
                "rubric_hints_completeness", "conversation_arc_count",
                "tool_resolution_preferred", "tool_resolution_fallback",
                "tool_resolution_reason",
                "persona_voice_tone", "persona_voice_formality", "persona_voice_verbosity",
            ],
        )
        writer.writeheader()
        for t in tasks:
            row = {k: t.get(k, "") for k in flat_fields}
            for af in array_fields:
                val = t.get(af, [])
                row[af] = "; ".join(val) if isinstance(val, list) else str(val)
            hints = t.get("rubric_hints", {})
            row["rubric_hints_correctness"] = hints.get("correctness", "")
            row["rubric_hints_privacy"] = hints.get("privacy_compliance", "")
            row["rubric_hints_completeness"] = hints.get("completeness", "")
            row["conversation_arc_count"] = len(t.get("conversation_arc", []))
            tr = t.get("tool_resolution", {})
            row["tool_resolution_preferred"] = tr.get("preferred_tier", "")
            row["tool_resolution_fallback"] = tr.get("fallback_tier", "")
            row["tool_resolution_reason"] = tr.get("resolution_reason", "")
            pv = t.get("persona_voice", {})
            row["persona_voice_tone"] = pv.get("tone", "") if isinstance(pv, dict) else ""
            row["persona_voice_formality"] = pv.get("formality", "") if isinstance(pv, dict) else ""
            row["persona_voice_verbosity"] = pv.get("verbosity", "") if isinstance(pv, dict) else ""
            writer.writerow(row)
    console.print(f"  [green]Saved[/green] {path}")


COMPLEXITY_LABEL = {1: "simple", 2: "moderate", 3: "complex"}
ETA_LABEL = {1: "15 min", 2: "30 min", 3: "60 min"}
REWARD_LABEL = {1: 2.0, 2: 5.0, 3: 10.0}


def save_cuarena_csv(tasks: list[dict], path: Path):
    """Export tasks in CUArena upload format (12 columns, T-prefixed IDs)."""
    if not tasks:
        return
    fieldnames = [
        "task_id", "title", "domain", "category", "complexity",
        "estimated_turns", "goal_summary", "opening_message",
        "milestones", "suggested_skills", "eta", "reward",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        for t in tasks:
            tier = t.get("complexity_tier", 1)
            arc = t.get("conversation_arc", [])
            task_id = t.get("task_id", "")
            if task_id.startswith("P-"):
                task_id = "T-" + task_id[2:]
            row = {
                "task_id": task_id,
                "title": t.get("task_title", ""),
                "domain": t.get("domain", ""),
                "category": (t.get("subdomain", "") or "").replace("_", " "),
                "complexity": COMPLEXITY_LABEL.get(tier, "simple"),
                "estimated_turns": len(arc),
                "goal_summary": t.get("goal_summary", ""),
                "opening_message": (arc[0].get("user_intent", "") or "") if arc else "",
                "milestones": " | ".join(
                    s.get("milestone", "") or "" for s in arc
                ),
                "suggested_skills": " | ".join(t.get("openclaw_skills", [])),
                "eta": ETA_LABEL.get(tier, "15 min"),
                "reward": REWARD_LABEL.get(tier, 2.0),
            }
            writer.writerow(row)
    console.print(f"  [green]Saved[/green] {path} (CUArena format)")


def save_per_persona(tasks: list[dict], output_dir: Path):
    by_persona_dir = output_dir / "tasks_by_persona"
    by_persona_dir.mkdir(exist_ok=True)
    grouped: dict[str, list] = {}
    for t in tasks:
        pid = t.get("persona_id", "unknown")
        grouped.setdefault(pid, []).append(t)
    for pid, ptasks in grouped.items():
        save_json(ptasks, by_persona_dir / f"{pid}.json")


def print_coverage(coverage: dict):
    table = Table(title="Coverage Matrix")
    table.add_column("Category", style="bold")
    table.add_column("Distribution", style="cyan")

    for key in ["scenarios", "domains", "horizontals", "data_levels", "tool_tiers",
                "jailbreak_vectors", "strata", "persona_voice_tones"]:
        dist = coverage.get(key, {})
        if dist:
            formatted = ", ".join(f"{k}: {v}" for k, v in dist.items())
            table.add_row(key.replace("_", " ").title(), formatted)

    tier_combos = coverage.get("skill_tier_combos", {})
    if tier_combos:
        formatted = ", ".join(f"{k}: {v}" for k, v in tier_combos.items())
        table.add_row("Skill Tier Combos", formatted)

    skills = coverage.get("skills_used", {})
    if skills:
        top_skills = ", ".join(f"{k}: {v}" for k, v in list(skills.items())[:15])
        table.add_row("Top Skills Used", top_skills)

    table.add_row("Total Tasks", str(coverage.get("total_tasks", 0)))
    table.add_row("Unique Scenarios", str(coverage.get("unique_scenarios", 0)))
    table.add_row("Unique Domains", str(coverage.get("unique_domains", 0)))
    table.add_row("Unique Skills", str(coverage.get("unique_skills", 0)))
    table.add_row("Unique Horizontals", str(coverage.get("unique_horizontals", 0)))
    table.add_row("Unique Strata", str(coverage.get("unique_strata", 0)))
    table.add_row("Avg Skills/Task", str(coverage.get("avg_skills_per_task", 0)))

    compliance = coverage.get("compliance", {})
    if compliance:
        table.add_section()
        for label, val in compliance.items():
            display_label = label.replace("_", " ").title()
            table.add_row(f"[req] {display_label}", str(val))

    consistency = coverage.get("consistency", {})
    if consistency:
        table.add_section()
        for label, val in consistency.items():
            display_label = label.replace("_", " ").title()
            table.add_row(f"[fix] {display_label}", str(val))

    console.print(table)


def validate_batch(tasks: list[dict]) -> list[str]:
    """Return a list of validation errors found in the batch. Empty = clean."""
    errors: list[str] = []
    for t in tasks:
        tid = t.get("task_id", "?")

        for label in t.get("pii_fields_exercised", []):
            if label not in DATA_LEVEL_MAP:
                errors.append(f"{tid}: OOV PII label '{label}'")

        if t.get("jailbreak_vector") and not t.get("jailbreak_prompt"):
            errors.append(
                f"{tid}: jailbreak_vector={t['jailbreak_vector']} "
                f"but empty jailbreak_prompt"
            )

        for tool in t.get("suggested_tools", []):
            if tool not in _TOOL_TIER_MAP:
                errors.append(f"{tid}: unregistered tool '{tool}' (defaults to T1)")

    return errors


def _load_prior_titles(prior_dir: Path) -> dict[str, list[dict]]:
    """Load full task dicts from a prior batch for backpropagation."""
    tasks_map: dict[str, list[dict]] = {}
    by_persona = prior_dir / "tasks_by_persona"
    if not by_persona.exists():
        return tasks_map
    for fp in sorted(by_persona.glob("P-*.json")):
        try:
            tasks = json.loads(fp.read_text(encoding="utf-8"))
            pid = fp.stem
            tasks_map[pid] = tasks
        except (json.JSONDecodeError, OSError):
            pass
    return tasks_map


def _load_prior_titles_multi(prior_dirs: list[Path]) -> dict[str, list[dict]]:
    """Merge task dicts from multiple prior batch dirs (sorted by seq number).

    Tasks from all dirs are combined per persona, sorted by seq so earlier
    sessions appear first — giving the LLM a chronological interaction history.
    """
    combined: dict[str, list[dict]] = {}
    for prior_dir in prior_dirs:
        batch_map = _load_prior_titles(prior_dir)
        for pid, tasks in batch_map.items():
            combined.setdefault(pid, []).extend(tasks)
    # Sort each persona's tasks by seq number for chronological order
    import re as _re
    _SEQ_RE = _re.compile(r"-(\d+)$")
    for pid in combined:
        combined[pid].sort(key=lambda t: int(m.group(1)) if (m := _SEQ_RE.search(t.get("task_id", ""))) else 0)
    return combined


def _collect_tasks_from_dir(output_dir: Path) -> list[dict]:
    """Load all per-persona JSON files from output dir."""
    tasks: list[dict] = []
    by_persona = output_dir / "tasks_by_persona"
    if not by_persona.exists():
        return tasks
    for fp in sorted(by_persona.glob("P-*.json")):
        try:
            tasks.extend(json.loads(fp.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            pass
    return tasks


def main():
    parser = argparse.ArgumentParser(description="Privacy Task Generator")
    parser.add_argument("--personas", type=Path, default=PERSONAS_PATH)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--tasks-per-persona", type=int, default=TASKS_PER_PERSONA)
    parser.add_argument("--concurrency", type=int, default=CONCURRENCY)
    parser.add_argument("--model", type=str, default=MODEL)
    parser.add_argument("--api-key", type=str, default=ANTHROPIC_API_KEY)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-dedup", action="store_true")
    parser.add_argument(
        "--chat-batch", action="store_true",
        help="Generate chat.technonous.com tasks (6 per persona) with seq 21+",
    )
    parser.add_argument(
        "--start-seq", type=str, default=None,
        help="Starting seq number or 'auto' (reads existing uploads)",
    )
    parser.add_argument(
        "--chat-zip", type=Path, default=None,
        help="Path to users.zip chat login kits",
    )
    parser.add_argument(
        "--enterprise-batch", action="store_true",
        help="Enterprise mode: block social media platforms, prefer enterprise skills",
    )
    parser.add_argument(
        "--persona-ids", type=str, default=None,
        help="Comma-separated persona IDs or range (e.g. P-142,P-143 or P-142:P-225)",
    )
    parser.add_argument(
        "--prior-batch-dir", type=Path, default=None, nargs="+",
        help="One or more prior batch output dirs (merged chronologically for memory recall)",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Exit non-zero if validation finds OOV labels, missing jailbreak prompts, or unregistered tools",
    )
    parser.add_argument(
        "--no-embedding", action="store_true",
        help="Disable embedding-based similarity gate (fall back to TF-IDF only)",
    )
    parser.add_argument(
        "--no-memory", action="store_true",
        help="Disable memory recall requirements (for first-time interaction batches)",
    )
    parser.add_argument(
        "--chat-focused", action="store_true",
        help="90%% chat.technonous.com tasks using crosslinks (Batch 4+)",
    )
    parser.add_argument(
        "--google-api-key", type=str, default=GOOGLE_API_KEY,
        help="Google AI API key for text-embedding-004 (or set GOOGLE_API_KEY env var)",
    )
    parser.add_argument(
        "--use-delivery-map", action="store_true",
        help="Use DELIVERY_MAP_SUMMARY.csv + extracted memories for per-persona workspace grounding",
    )
    parser.add_argument(
        "--delivery-map-csv", type=Path, default=None,
        help="Path to DELIVERY_MAP_SUMMARY.csv (auto-detected if not set)",
    )
    args = parser.parse_args()

    output_dir = args.output
    if output_dir is None:
        output_dir = CHAT_BATCH_OUTPUT if args.chat_batch else OUTPUT_DIR

    is_openai = args.model.startswith(("gpt-", "o1", "o3", "o4"))
    if is_openai:
        if not OPENAI_API_KEY and not args.dry_run:
            console.print("[red]Error: OPENAI_API_KEY not set in .env[/red]")
            sys.exit(1)
        args.api_key = OPENAI_API_KEY
    elif not args.api_key and not args.dry_run:
        console.print(
            "[red]Error: ANTHROPIC_API_KEY not set. Use --api-key or export ANTHROPIC_API_KEY.[/red]"
        )
        sys.exit(1)

    if args.chat_zip:
        import chat_login_loader
        chat_login_loader.DEFAULT_ZIP = args.chat_zip

    console.print(f"\n[bold]Loading personas from[/bold] {args.personas}")
    personas = load_personas(args.personas)
    console.print(f"  Loaded {len(personas)} personas")

    if args.persona_ids:
        allowed = _parse_persona_ids(args.persona_ids)
        personas = [p for p in personas if p["persona_id"] in allowed]
        console.print(f"  Filtered to {len(personas)} personas by --persona-ids")

    if args.limit:
        personas = personas[: args.limit]
        console.print(f"  Limited to first {args.limit} personas")

    start_seq_map: dict[str, int] | None = None
    if args.start_seq == "auto":
        persona_ids = [p["persona_id"] for p in personas]
        start_seq_map = build_start_seq_map(persona_ids)
        sample = list(start_seq_map.items())[:3]
        console.print(f"  Auto start_seq (sample): {sample}")
    elif args.start_seq is not None:
        fixed = int(args.start_seq)
        start_seq_map = {p["persona_id"]: fixed for p in personas}
        console.print(f"  Fixed start_seq: {fixed}")

    if args.resume:
        remaining = []
        for p in personas:
            pid = p["persona_id"]
            seq = (start_seq_map or {}).get(pid, 1)
            if _persona_complete(pid, seq, args.tasks_per_persona, output_dir):
                continue
            remaining.append(p)
        skipped = len(personas) - len(remaining)
        personas = remaining
        console.print(f"  Resuming: skipped {skipped} complete, {len(personas)} remaining")

    if not personas:
        console.print("[yellow]No personas to process.[/yellow]")
        if args.chat_batch and output_dir.exists():
            tasks = _collect_tasks_from_dir(output_dir)
            if tasks:
                console.print(f"  Found {len(tasks)} existing tasks in {output_dir}")
        return

    # Load prior batch titles for backpropagation
    prior_titles_map: dict[str, list[str]] | None = None
    if args.prior_batch_dir:
        dirs = args.prior_batch_dir if isinstance(args.prior_batch_dir, list) else [args.prior_batch_dir]
        if len(dirs) > 1:
            prior_titles_map = _load_prior_titles_multi(dirs)
            console.print(f"  Loaded prior titles from {len(dirs)} dirs: {[str(d) for d in dirs]}")
        else:
            prior_titles_map = _load_prior_titles(dirs[0])
            console.print(f"  Loaded prior titles from {dirs[0]}")
        sample_counts = [(pid, len(t)) for pid, t in list(prior_titles_map.items())[:3]]
        console.print(f"  Sample task counts: {sample_counts}")

    # Initialize embedding store for semantic similarity gate
    embed_store: EmbeddingStore | None = None
    if not args.no_embedding and not args.dry_run:
        if args.google_api_key:
            embed_store = EmbeddingStore(api_key=args.google_api_key)
            stats = embed_store.get_stats()
            console.print(
                f"\n[bold]Embedding store[/bold] initialized "
                f"({stats['total_embeddings']} existing embeddings, "
                f"threshold={stats['threshold']}, model={stats['model']})"
            )
        else:
            console.print(
                "[yellow]Warning: GOOGLE_API_KEY not set. "
                "Embedding similarity gate disabled (TF-IDF only).[/yellow]"
            )

    # Load delivery map for per-persona workspace grounding
    assets_map = None
    if args.use_delivery_map:
        from delivery_map_loader import load_delivery_map
        csv_path = args.delivery_map_csv
        if csv_path is None:
            csv_path = Path(__file__).parent / "DELIVERY_MAP_SUMMARY.csv"
        console.print(f"\n[bold]Loading delivery map[/bold] from {csv_path}")
        assets_map = load_delivery_map(csv_path)
        personas_with_assets = sum(1 for pid in assets_map if any(
            p["persona_id"] == pid for p in personas
        ))
        sample_pid = next((p["persona_id"] for p in personas), None)
        sample_pa = assets_map.get(sample_pid)
        mem_count = len(sample_pa.memory_notes) if sample_pa else 0
        doc_count = len(sample_pa.documents) if sample_pa else 0
        console.print(
            f"  Loaded {len(assets_map)} personas | "
            f"Matched: {personas_with_assets} | "
            f"Sample {sample_pid}: {doc_count} docs, {mem_count} memory notes"
        )

    mode = "enterprise batch" if args.enterprise_batch else "chat batch" if args.chat_batch else "standard"
    console.print(
        f"\n[bold]Generating tasks[/bold] ({mode}, {args.tasks_per_persona} per persona, "
        f"model: {args.model}, output: {output_dir})"
    )

    effective_keys = [OPENAI_API_KEY] if is_openai else (ANTHROPIC_API_KEYS if len(ANTHROPIC_API_KEYS) > 1 else None)
    tasks = asyncio.run(
        generate_all(
            personas=personas,
            api_key=args.api_key,
            api_keys=effective_keys,
            model=args.model,
            concurrency=args.concurrency,
            dry_run=args.dry_run,
            start_seq_map=start_seq_map,
            chat_batch=args.chat_batch,
            enterprise_batch=args.enterprise_batch,
            output_dir=output_dir,
            tasks_per_persona=args.tasks_per_persona,
            prior_titles_map=prior_titles_map,
            embed_store=embed_store,
            no_memory=args.no_memory,
            chat_focused=args.chat_focused,
            assets_map=assets_map,
        )
    )

    if args.dry_run:
        console.print("\n[yellow]Dry run complete -- no tasks generated.[/yellow]")
        return

    if not tasks:
        console.print("[yellow]No new tasks generated this run.[/yellow]")
        tasks = _collect_tasks_from_dir(output_dir)
        if not tasks:
            console.print("[red]No tasks found.[/red]")
            return
        console.print(f"  Loaded {len(tasks)} tasks from existing output")

    if not args.no_dedup:
        console.print(f"\n[bold]Deduplicating[/bold] ({len(tasks)} tasks)")
        tasks, sim_report = deduplicate_tasks(tasks)
        console.print(
            f"  Removed {sim_report['duplicates_removed']} duplicates -> {len(tasks)} remaining"
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        save_json(sim_report, output_dir / "similarity_report.json")

    # ── Post-dedup backfill ──────────────────────────────────────────────────
    # After deduplication some personas may have fewer than tasks_per_persona.
    # Regenerate the missing tasks so every persona ends up complete.
    if not args.dry_run:
        import re as _re
        _TASK_ID_RE = _re.compile(r"^P-(\d{4})-(\d+)$")

        # Count existing tasks per persona
        from collections import defaultdict
        persona_tasks: dict[str, list[dict]] = defaultdict(list)
        for t in tasks:
            persona_tasks[t["persona_id"]].append(t)

        underfull = {
            pid: ptasks
            for pid, ptasks in persona_tasks.items()
            if len(ptasks) < args.tasks_per_persona
        }

        if underfull:
            console.print(
                f"\n[bold yellow]Post-dedup backfill[/bold yellow]: "
                f"{len(underfull)} personas need top-up"
            )
            backfill_personas = [p for p in personas if p["persona_id"] in underfull]
            backfill_start_seq: dict[str, int] = {}
            for pid, ptasks in underfull.items():
                max_seq = max(
                    (int(m.group(2)) for t in ptasks
                     if (m := _TASK_ID_RE.match(t.get("task_id", "")))),
                    default=int(args.start_seq) - 1,
                )
                backfill_start_seq[pid] = max_seq + 1

            backfill_per_persona = {
                pid: args.tasks_per_persona - len(ptasks)
                for pid, ptasks in underfull.items()
            }
            # All underfull personas need the same count; use the max needed
            max_needed = max(backfill_per_persona.values())

            console.print(
                f"  Personas: {list(underfull.keys())} | "
                f"Max missing: {max_needed} tasks each"
            )

            for pid, needed in backfill_per_persona.items():
                console.print(f"  Backfilling {pid}: {needed} tasks from seq {backfill_start_seq[pid]}")

            extra_tasks = asyncio.run(
                generate_all(
                    personas=backfill_personas,
                    api_key=args.api_key,
                    api_keys=effective_keys,
                    model=args.model,
                    concurrency=min(args.concurrency, len(backfill_personas)),
                    dry_run=False,
                    start_seq_map=backfill_start_seq,
                    chat_batch=args.chat_batch,
                    enterprise_batch=args.enterprise_batch,
                    output_dir=output_dir,
                    tasks_per_persona=max_needed,
                    prior_titles_map=prior_titles_map,
                    embed_store=embed_store,
                    no_memory=args.no_memory,
                    chat_focused=args.chat_focused,
                )
            )

            # Trim to exactly what each persona needs
            trimmed: list[dict] = []
            for t in extra_tasks:
                pid = t["persona_id"]
                if backfill_per_persona.get(pid, 0) > 0:
                    trimmed.append(t)
                    backfill_per_persona[pid] -= 1

            tasks.extend(trimmed)
            console.print(
                f"  [green]Backfill complete:[/green] +{len(trimmed)} tasks "
                f"-> {len(tasks)} total"
            )
        else:
            console.print(
                f"\n[green]All {len(personas)} personas have full {args.tasks_per_persona} tasks.[/green]"
            )
    # ────────────────────────────────────────────────────────────────────────

    console.print(f"\n[bold]Validating batch[/bold] ({len(tasks)} tasks)")
    validation_errors = validate_batch(tasks)
    if validation_errors:
        console.print(f"  [yellow]Validation warnings: {len(validation_errors)}[/yellow]")
        for err in validation_errors[:20]:
            console.print(f"    [yellow]•[/yellow] {err}")
        if len(validation_errors) > 20:
            console.print(f"    … and {len(validation_errors) - 20} more")
        if args.strict:
            console.print("[red]Strict mode: aborting due to validation errors.[/red]")
            sys.exit(1)
    else:
        console.print("  [green]All checks passed.[/green]")

    output_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"\n[bold]Saving outputs to[/bold] {output_dir}")
    save_json(tasks, output_dir / "tasks_all.json")
    save_csv(tasks, output_dir / "tasks_all.csv")
    save_cuarena_csv(tasks, output_dir / "cuarena_upload_tasks_all.csv")
    save_per_persona(tasks, output_dir)

    coverage = compute_coverage_matrix(tasks)
    save_json(coverage, output_dir / "coverage_matrix.json")
    print_coverage(coverage)

    console.print(f"\n[bold green]Complete![/bold green] {len(tasks)} tasks saved to {output_dir}\n")


if __name__ == "__main__":
    main()
