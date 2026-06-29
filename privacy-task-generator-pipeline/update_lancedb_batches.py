#!/usr/bin/env python3
"""Remove batch1 embeddings and seed batch3 into LanceDB."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn

from config import GOOGLE_API_KEY, LANCEDB_PATH
from embedding_store import EmbeddingStore, _task_to_text

console = Console()


def remove_batch1(batch1_path: Path) -> int:
    import lancedb

    db = lancedb.connect(str(LANCEDB_PATH))
    tbl = db.open_table("task_embeddings")
    before = tbl.count_rows()
    console.print(f"[cyan]Before removal:[/cyan] {before} embeddings")

    tasks = json.loads(batch1_path.read_text(encoding="utf-8"))
    task_ids = [t["task_id"] for t in tasks]
    console.print(f"[yellow]Removing {len(task_ids)} batch1 tasks...[/yellow]")

    for i, task_id in enumerate(task_ids, 1):
        tbl.delete(f"task_id = '{task_id}'")
        if i % 250 == 0 or i == len(task_ids):
            console.print(f"  Removed {i}/{len(task_ids)}")

    after = tbl.count_rows()
    removed = before - after
    console.print(f"[green]After removal:[/green] {after} embeddings (removed {removed})")
    return removed


def seed_batch3(batch3_path: Path, api_key: str, batch_size: int = 100) -> int:
    console.print(f"\n[bold]Loading batch3 tasks from[/bold] {batch3_path}")
    tasks = json.loads(batch3_path.read_text(encoding="utf-8"))
    console.print(f"  Loaded {len(tasks)} tasks")

    store = EmbeddingStore(api_key=api_key)
    stats = store.get_stats()
    console.print(f"  Existing embeddings before seed: {stats['total_embeddings']}")

    existing_ids: set[str] = set()
    if store.table.count_rows() > 0:
        rows = store.table.search().select(["task_id"]).limit(20000).to_list()
        existing_ids = {str(r["task_id"]) for r in rows}

    tasks_to_seed = [t for t in tasks if t.get("task_id", "") not in existing_ids]
    if not tasks_to_seed:
        console.print("[green]All batch3 tasks already seeded.[/green]")
        return 0

    console.print(f"[bold]Seeding {len(tasks_to_seed)} batch3 tasks[/bold]")
    total_seeded = 0
    start = time.time()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task_bar = progress.add_task("Embedding & storing", total=len(tasks_to_seed))

        for i in range(0, len(tasks_to_seed), batch_size):
            chunk = tasks_to_seed[i : i + batch_size]
            texts = [_task_to_text(t) for t in chunk]

            for attempt in range(5):
                try:
                    embeddings = store.embed_texts(texts)
                    break
                except Exception as e:
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                        wait = 2 ** (attempt + 1)
                        progress.console.print(
                            f"  [yellow]Rate limited, waiting {wait}s (attempt {attempt + 1}/5)[/yellow]"
                        )
                        time.sleep(wait)
                    else:
                        raise
            else:
                progress.console.print("[red]Failed after 5 retries, skipping batch[/red]")
                continue

            for task, emb in zip(chunk, embeddings):
                task["_embedding"] = emb

            store.store_batch(chunk)
            total_seeded += len(chunk)
            progress.update(task_bar, advance=len(chunk))

            if i + batch_size < len(tasks_to_seed):
                time.sleep(1.5)

    elapsed = time.time() - start
    final_stats = store.get_stats()
    console.print(
        f"\n[bold green]Done![/bold green] Seeded {total_seeded} tasks in {elapsed:.1f}s"
    )
    console.print(f"  Total embeddings in DB: {final_stats['total_embeddings']}")
    return total_seeded


def main() -> None:
    parser = argparse.ArgumentParser(description="Remove batch1 and seed batch3 in LanceDB")
    parser.add_argument(
        "--batch1",
        type=Path,
        default=Path("outputs/batch1_no_memory/tasks_all.json"),
        help="Batch1 tasks file whose embeddings should be removed",
    )
    parser.add_argument(
        "--batch3",
        type=Path,
        default=Path("outputs/batch3/tasks_all.json"),
        help="Batch3 tasks file to seed",
    )
    parser.add_argument("--api-key", type=str, default=GOOGLE_API_KEY)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--remove-only", action="store_true")
    parser.add_argument("--seed-only", action="store_true")
    args = parser.parse_args()

    if not args.api_key and not args.remove_only:
        console.print("[red]GOOGLE_API_KEY required for seeding[/red]")
        sys.exit(1)

    if not args.seed_only:
        if not args.batch1.exists():
            console.print(f"[red]Batch1 file not found: {args.batch1}[/red]")
            sys.exit(1)
        remove_batch1(args.batch1)

    if not args.remove_only:
        if not args.batch3.exists():
            console.print(f"[red]Batch3 file not found: {args.batch3}[/red]")
            sys.exit(1)
        seed_batch3(args.batch3, args.api_key, args.batch_size)


if __name__ == "__main__":
    main()
