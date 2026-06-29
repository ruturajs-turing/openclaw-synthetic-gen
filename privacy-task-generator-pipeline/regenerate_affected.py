#!/usr/bin/env python3
"""Regenerate tasks for specific affected personas (P-137 through P-141).

This script targets only the personas whose attributes were corrected,
regenerates their 20 tasks each, and outputs them in CUArena CSV format.
"""

import asyncio
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import OPENAI_API_KEY, MODEL, PERSONAS_PATH, OUTPUT_DIR
from persona_loader import load_personas
from task_generator import generate_all
from build_cuarena_csv import transform

AFFECTED_PERSONAS = ["P-137", "P-138", "P-139", "P-140", "P-141"]


async def main():
    api_key = OPENAI_API_KEY
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    print(f"Loading personas from {PERSONAS_PATH}")
    all_personas = load_personas(PERSONAS_PATH)

    targets = [p for p in all_personas if p["persona_id"] in AFFECTED_PERSONAS]
    print(f"Found {len(targets)} affected personas: {[p['persona_id'] for p in targets]}")

    if len(targets) != len(AFFECTED_PERSONAS):
        missing = set(AFFECTED_PERSONAS) - {p["persona_id"] for p in targets}
        print(f"WARNING: Missing personas: {missing}", file=sys.stderr)

    print(f"\nGenerating tasks (model: {MODEL}, 20 per persona = {len(targets) * 20} total)...")
    tasks = await generate_all(
        personas=targets,
        api_key=api_key,
        model=MODEL,
        concurrency=5,
        dry_run=False,
    )

    if not tasks:
        print("ERROR: No tasks generated!", file=sys.stderr)
        sys.exit(1)

    print(f"\nGenerated {len(tasks)} tasks")

    out_dir = OUTPUT_DIR / "regenerated"
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "regenerated_tasks.json"
    with open(json_path, "w") as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)
    print(f"Saved raw tasks: {json_path}")

    csv_path = out_dir / "regenerated_cuarena.csv"
    rows = [transform(t) for t in tasks]
    fieldnames = [
        "task_id", "title", "domain", "category", "complexity",
        "estimated_turns", "goal_summary", "opening_message", "milestones",
        "suggested_skills", "eta", "reward",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    print(f"Saved CUArena CSV: {csv_path} ({len(rows)} rows)")

    # Also save per-persona JSONs
    by_persona = out_dir / "tasks_by_persona"
    by_persona.mkdir(exist_ok=True)
    grouped = {}
    for t in tasks:
        pid = t.get("persona_id", "unknown")
        grouped.setdefault(pid, []).append(t)
    for pid, ptasks in grouped.items():
        with open(by_persona / f"{pid}.json", "w") as f:
            json.dump(ptasks, f, indent=2, ensure_ascii=False)
    print(f"Saved per-persona JSONs in {by_persona}")

    print(f"\nDone! {len(tasks)} tasks ready for SQL generation.")


if __name__ == "__main__":
    asyncio.run(main())
