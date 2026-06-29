#!/usr/bin/env python3
"""Validate chat batch task output: seq ranges, chat quota, milestone quality."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

TASK_ID_RE = re.compile(r"^P-(\d+)-(\d+)$")
VAGUE_MILESTONE = re.compile(
    r"^(User|Agent)\s+(states|responds|asks|replies|says)\b", re.IGNORECASE
)
CHAT_MARKERS = ("chat.technonous.com", "technonous", "browser-automation")


def _load_tasks(path: Path) -> list[dict]:
    if path.is_dir():
        tasks: list[dict] = []
        for fp in sorted(path.glob("P-*.json")):
            tasks.extend(json.loads(fp.read_text(encoding="utf-8")))
        return tasks
    return json.loads(path.read_text(encoding="utf-8"))


def _is_chat_task(task: dict) -> bool:
    skills = task.get("openclaw_skills") or []
    if "browser-automation" not in skills:
        return False
    blob = " ".join([
        task.get("task_title", ""),
        task.get("goal_summary", ""),
        " ".join(
            step.get("milestone", "") + " " + step.get("user_intent", "")
            for step in task.get("conversation_arc", [])
        ),
    ]).lower()
    return any(m in blob for m in ("chat.technonous", "technonous"))


def validate_tasks(
    tasks: list[dict],
    *,
    expected_start: dict[str, int] | None = None,
    tasks_per_persona: int = 20,
    chat_quota: int = 6,
) -> dict:
    by_persona: dict[str, list[dict]] = defaultdict(list)
    for t in tasks:
        by_persona[t.get("persona_id", "unknown")].append(t)

    errors: list[str] = []
    warnings: list[str] = []
    stats = Counter()

    all_ids = [t.get("task_id") for t in tasks]
    dup_ids = [tid for tid, c in Counter(all_ids).items() if c > 1]
    if dup_ids:
        errors.append(f"Duplicate task_ids: {dup_ids[:10]}")

    for pid, ptasks in sorted(by_persona.items()):
        seqs: list[int] = []
        for t in ptasks:
            m = TASK_ID_RE.match(t.get("task_id", ""))
            if m:
                seqs.append(int(m.group(2)))

        start = (expected_start or {}).get(pid, min(seqs) if seqs else 21)
        expected = set(range(start, start + tasks_per_persona))
        found = set(seqs)
        missing = expected - found
        extra = found - expected

        if missing:
            errors.append(f"{pid}: missing seq {sorted(missing)[:5]}{'...' if len(missing) > 5 else ''}")
        if extra:
            warnings.append(f"{pid}: unexpected seq {sorted(extra)}")

        chat_count = sum(1 for t in ptasks if _is_chat_task(t))
        stats["chat_tasks"] += chat_count
        if chat_count != chat_quota:
            errors.append(f"{pid}: {chat_count} chat tasks (expected {chat_quota})")

        for t in ptasks:
            arc = t.get("conversation_arc", [])
            n = len(arc)
            if n < 4 or n > 6:
                warnings.append(f"{t.get('task_id')}: {n} arc steps (expected 4-6)")
            for step in arc:
                ms = step.get("milestone", "")
                if VAGUE_MILESTONE.match(ms.strip()):
                    warnings.append(f"{t.get('task_id')}: vague milestone '{ms}'")

    return {
        "personas": len(by_persona),
        "total_tasks": len(tasks),
        "errors": errors,
        "warnings": warnings,
        "stats": dict(stats),
    }


def main():
    parser = argparse.ArgumentParser(description="Validate chat batch output")
    parser.add_argument("path", type=Path, help="tasks_all.json or tasks_by_persona/ dir")
    parser.add_argument("--chat-quota", type=int, default=6)
    parser.add_argument("--tasks-per-persona", type=int, default=20)
    args = parser.parse_args()

    if not args.path.exists():
        print(f"ERROR: {args.path} not found", file=sys.stderr)
        sys.exit(1)

    tasks = _load_tasks(args.path)
    result = validate_tasks(
        tasks,
        tasks_per_persona=args.tasks_per_persona,
        chat_quota=args.chat_quota,
    )

    print(f"Personas: {result['personas']}")
    print(f"Total tasks: {result['total_tasks']}")
    print(f"Errors: {len(result['errors'])}")
    print(f"Warnings: {len(result['warnings'])}")

    for e in result["errors"][:20]:
        print(f"  ERROR: {e}")
    if len(result["errors"]) > 20:
        print(f"  ... and {len(result['errors']) - 20} more errors")

    for w in result["warnings"][:10]:
        print(f"  WARN: {w}")
    if len(result["warnings"]) > 10:
        print(f"  ... and {len(result['warnings']) - 10} more warnings")

    sys.exit(1 if result["errors"] else 0)


if __name__ == "__main__":
    main()
