#!/usr/bin/env python3
"""Seed the LanceDB embedding store with tasks from an existing batch.

Run this once before generating new batches so the embedding similarity gate
can compare new tasks against previously generated ones.

Usage:
    python seed_embeddings.py --input outputs/v7_delivery_250x15_no_google/tasks_all.json
    python seed_embeddings.py --input outputs/v7_delivery_250x15_no_google/tasks_all.json --batch-size 50
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn

from config import GOOGLE_API_KEY
from embedding_store import EmbeddingStore, _task_to_text

console = Console()


def seed(input_path: Path, api_key: str, batch_size: int = 100, clear: bool = False):
    """Load tasks from JSON and seed them into the LanceDB embedding store."""
    console.print(f"\n[bold]Loading tasks from[/bold] {input_path}")
    with open(input_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    console.print(f"  Loaded {len(tasks)} tasks")

    store = EmbeddingStore(api_key=api_key)
    stats = store.get_stats()

    if clear:
        console.print(f"  [yellow]Clearing existing {stats['total_embeddings']} embeddings[/yellow]")
        store.drop_table()
        stats = store.get_stats()

    if stats["total_embeddings"] > 0:
        console.print(
            f"  [cyan]Existing embeddings:[/cyan] {stats['total_embeddings']} "
            f"(new tasks will be appended)"
        )

    # Check for tasks already in the DB to avoid duplicates
    existing_ids = set()
    if store.table.count_rows() > 0:
        existing_df = store.table.to_pandas()
        existing_ids = set(existing_df["task_id"].tolist())
        console.print(f"  Skipping {len(existing_ids)} tasks already in DB")

    tasks_to_seed = [t for t in tasks if t.get("task_id", "") not in existing_ids]
    if not tasks_to_seed:
        console.print("[green]All tasks already seeded. Nothing to do.[/green]")
        return

    console.print(
        f"\n[bold]Seeding {len(tasks_to_seed)} tasks[/bold] "
        f"(batch_size={batch_size}, model={stats['model']})"
    )

    start = time.time()
    total_seeded = 0

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

            # Retry with exponential backoff for rate limits
            for attempt in range(5):
                try:
                    embeddings = store.embed_texts(texts)
                    break
                except Exception as e:
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                        wait = 2 ** (attempt + 1)
                        progress.console.print(
                            f"  [yellow]Rate limited, waiting {wait}s (attempt {attempt+1}/5)[/yellow]"
                        )
                        time.sleep(wait)
                    else:
                        raise
            else:
                progress.console.print(f"  [red]Failed after 5 retries, skipping batch[/red]")
                continue

            for task, emb in zip(chunk, embeddings):
                task["_embedding"] = emb

            store.store_batch(chunk)
            total_seeded += len(chunk)
            progress.update(task_bar, advance=len(chunk))

            # Brief pause between batches to avoid rate limits
            if i + batch_size < len(tasks_to_seed):
                time.sleep(1.5)

    elapsed = time.time() - start
    final_stats = store.get_stats()
    console.print(
        f"\n[bold green]Done![/bold green] Seeded {total_seeded} tasks in {elapsed:.1f}s"
    )
    console.print(
        f"  Total embeddings in DB: {final_stats['total_embeddings']}"
    )
    console.print(f"  DB path: {final_stats['db_path']}")


def main():
    parser = argparse.ArgumentParser(description="Seed embedding store with existing tasks")
    parser.add_argument(
        "--input", type=Path, required=True,
        help="Path to tasks_all.json from a previous batch",
    )
    parser.add_argument(
        "--api-key", type=str, default=GOOGLE_API_KEY,
        help="Google AI API key (or set GOOGLE_API_KEY env var)",
    )
    parser.add_argument(
        "--batch-size", type=int, default=100,
        help="Number of tasks to embed per API call (max 100)",
    )
    parser.add_argument(
        "--clear", action="store_true",
        help="Clear existing embeddings before seeding",
    )
    args = parser.parse_args()

    if not args.api_key:
        console.print(
            "[red]Error: GOOGLE_API_KEY not set. "
            "Use --api-key or add GOOGLE_API_KEY to .env[/red]"
        )
        sys.exit(1)

    if not args.input.exists():
        console.print(f"[red]Error: Input file not found: {args.input}[/red]")
        sys.exit(1)

    seed(args.input, args.api_key, args.batch_size, args.clear)


if __name__ == "__main__":
    main()
