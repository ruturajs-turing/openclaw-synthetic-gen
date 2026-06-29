#!/usr/bin/env python3
"""Diagnose CU Arena CSV import readiness and DB overlap."""

from __future__ import annotations

import argparse
import asyncio
import csv
import io
import os
import re
from pathlib import Path

TASK_ID_RE = re.compile(r"^T-\d+-\d+$")

REQUIRED = {"task_id", "title"}


def load_csv(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or not REQUIRED.issubset(reader.fieldnames):
        raise SystemExit(f"Invalid CSV: need columns {REQUIRED}, got {reader.fieldnames}")
    return list(reader)


def analyze_csv(rows: list[dict]) -> dict:
    ids = [r["task_id"].strip() for r in rows if r.get("task_id")]
    bad = [i for i in ids if not TASK_ID_RE.match(i)]
    dup = [i for i in set(ids) if ids.count(i) > 1]
    seq21 = sum(1 for i in ids if int(i.split("-")[-1]) >= 21)
    return {
        "rows": len(rows),
        "task_ids": len(ids),
        "bad_ids": bad[:5],
        "dup_ids": dup[:5],
        "seq21_plus": seq21,
        "sample_first": ids[0] if ids else None,
        "sample_last": ids[-1] if ids else None,
    }


async def check_db_overlap(ids: list[str], database_url: str) -> dict:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(url)
    existing = 0
    sample_existing: list[str] = []
    total_tasks = 0
    async with engine.connect() as conn:
        r = await conn.execute(text("SELECT COUNT(*) FROM tasks"))
        total_tasks = r.scalar() or 0
        for tid in ids:
            r = await conn.execute(text("SELECT 1 FROM tasks WHERE id = :id"), {"id": tid})
            if r.scalar():
                existing += 1
                if len(sample_existing) < 5:
                    sample_existing.append(tid)
    await engine.dispose()
    return {
        "total_tasks_in_db": total_tasks,
        "csv_ids_already_in_db": existing,
        "csv_ids_new": len(ids) - existing,
        "sample_existing": sample_existing,
    }


def main():
    parser = argparse.ArgumentParser(description="Check CU Arena CSV import readiness")
    parser.add_argument("csv", type=Path, nargs="?", default=Path("outputs/chat_batch_v2/cuarena_upload.csv"))
    parser.add_argument("--db", action="store_true", help="Check overlap against DATABASE_URL")
    args = parser.parse_args()

    if not args.csv.exists():
        raise SystemExit(f"File not found: {args.csv}")

    rows = load_csv(args.csv)
    info = analyze_csv(rows)
    print(f"CSV: {args.csv}")
    print(f"  rows: {info['rows']}")
    print(f"  task_ids: {info['task_ids']} (seq 21+: {info['seq21_plus']})")
    print(f"  range: {info['sample_first']} .. {info['sample_last']}")
    if info["bad_ids"]:
        print(f"  BAD task_id format: {info['bad_ids']}")
    if info["dup_ids"]:
        print(f"  DUPLICATE task_ids: {info['dup_ids']}")

    print("\nImport notes:")
    print("  - CU Arena import is INSERT-ONLY by default (existing task_ids are SKIPPED)")
    print("  - Use batch name e.g. 'privacy-chat-v2' in Admin → Add tasks")
    print("  - After import, filter by batch and click Release to make tasks live")
    print("  - Enable 'Update existing draft/paused tasks' to upsert re-imports")

    if args.db:
        db_url = os.environ.get("DATABASE_URL", "")
        if not db_url:
            env = Path(__file__).resolve().parent.parent / "CUArena" / "api" / ".env"
            if env.exists():
                for line in env.read_text().splitlines():
                    if line.startswith("DATABASE_URL="):
                        db_url = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
        if not db_url:
            print("\nDATABASE_URL not set — skip DB check")
            return
        ids = [r["task_id"].strip() for r in rows if r.get("task_id")]
        try:
            overlap = asyncio.run(check_db_overlap(ids, db_url))
        except Exception as e:
            print(f"\nDB check failed: {type(e).__name__}: {e}")
            print("  (Is Postgres running? cd CUArena && docker compose up -d db)")
            return
        print(f"\nDB overlap:")
        print(f"  total tasks in DB: {overlap['total_tasks_in_db']}")
        print(f"  CSV ids already in DB: {overlap['csv_ids_already_in_db']}")
        print(f"  CSV ids that would IMPORT: {overlap['csv_ids_new']}")
        if overlap["sample_existing"]:
            print(f"  sample existing: {overlap['sample_existing']}")
        if overlap["csv_ids_already_in_db"] == len(ids):
            print("\n  → All rows already exist. Re-import will skip unless upsert=true.")


if __name__ == "__main__":
    main()
