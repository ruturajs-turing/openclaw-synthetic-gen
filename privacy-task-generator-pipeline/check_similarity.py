#!/usr/bin/env python3
"""Post-generation similarity check against LanceDB.

Embeds all tasks from a new batch and queries LanceDB (containing the prior batch)
to flag any tasks that exceed the similarity threshold.

Usage:
    python check_similarity.py --input outputs/batch2_memory/tasks_all.json
    python check_similarity.py --input outputs/batch2_memory/tasks_all.json --threshold 0.5
    python check_similarity.py --input outputs/batch2_memory/tasks_all.json --output flagged_tasks.json
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from config import GOOGLE_API_KEY, SIMILARITY_THRESHOLD
from embedding_store import EmbeddingStore, _task_to_text, _task_to_narrative_text

console = Console()


def check_similarity(
    input_path: Path,
    api_key: str,
    threshold: float = SIMILARITY_THRESHOLD,
    batch_size: int = 50,
    output_path: Path | None = None,
    narrow: bool = False,
) -> list[dict]:
    """Embed new tasks and check each against existing LanceDB entries."""
    console.print(f"\n[bold]Loading tasks from[/bold] {input_path}")
    with open(input_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)
    console.print(f"  Loaded {len(tasks)} tasks")

    text_fn = _task_to_narrative_text if narrow else _task_to_text
    mode_label = "narrative-only" if narrow else "full-fields"
    console.print(f"  Embedding mode: [cyan]{mode_label}[/cyan]")

    store = EmbeddingStore(api_key=api_key)
    stats = store.get_stats()
    console.print(
        f"  LanceDB has {stats['total_embeddings']} existing embeddings "
        f"(threshold={threshold})"
    )

    if stats["total_embeddings"] == 0:
        console.print(
            "[yellow]Warning: LanceDB is empty — nothing to compare against. "
            "All tasks will pass.[/yellow]"
        )
        return []

    flagged: list[dict] = []
    total_checked = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task_bar = progress.add_task("Checking similarity", total=len(tasks))

        for i in range(0, len(tasks), batch_size):
            chunk = tasks[i : i + batch_size]
            texts = [text_fn(t) for t in chunk]

            for attempt in range(5):
                try:
                    embeddings = store.embed_texts(texts)
                    break
                except Exception as e:
                    if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                        wait = 2 ** (attempt + 1)
                        progress.console.print(
                            f"  [yellow]Rate limited, waiting {wait}s "
                            f"(attempt {attempt+1}/5)[/yellow]"
                        )
                        time.sleep(wait)
                    else:
                        raise
            else:
                progress.console.print(
                    f"  [red]Failed after 5 retries, skipping batch "
                    f"(tasks {i}-{i+len(chunk)})[/red]"
                )
                progress.update(task_bar, advance=len(chunk))
                continue

            for task, embedding in zip(chunk, embeddings):
                results = (
                    store.table.search(embedding)
                    .metric("cosine")
                    .limit(3)
                    .to_pandas()
                )
                if not results.empty:
                    max_similarity = 1.0 - results["_distance"].min()
                    if max_similarity >= threshold:
                        similar_id = results.iloc[
                            results["_distance"].idxmin()
                        ]["task_id"]
                        flagged.append({
                            "task_id": task.get("task_id", "?"),
                            "persona_id": task.get("persona_id", "?"),
                            "task_title": task.get("task_title", "?"),
                            "similarity": round(float(max_similarity), 4),
                            "similar_to": similar_id,
                        })

            total_checked += len(chunk)
            progress.update(task_bar, advance=len(chunk))

            if i + batch_size < len(tasks):
                time.sleep(1.0)

    console.print(f"\n[bold]Results:[/bold]")
    console.print(f"  Checked: {total_checked}")
    console.print(f"  Passed: {total_checked - len(flagged)}")
    console.print(f"  Flagged: {len(flagged)}")

    if flagged:
        table = Table(title=f"Flagged Tasks (similarity >= {threshold})")
        table.add_column("Task ID", style="red")
        table.add_column("Persona")
        table.add_column("Title", max_width=40)
        table.add_column("Similarity", justify="right")
        table.add_column("Similar To")

        for f in flagged[:50]:
            table.add_row(
                f["task_id"],
                f["persona_id"],
                f["task_title"][:40],
                f"{f['similarity']:.4f}",
                f["similar_to"],
            )

        if len(flagged) > 50:
            table.add_row("...", "...", f"({len(flagged) - 50} more)", "...", "...")

        console.print(table)

        persona_ids = sorted(set(f["persona_id"] for f in flagged))
        console.print(
            f"\n[bold]Personas needing regeneration ({len(persona_ids)}):[/bold]"
        )
        console.print(f"  --persona-ids {','.join(persona_ids)}")

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(flagged, f, indent=2, ensure_ascii=False)
        console.print(f"\n  Flagged tasks saved to: {output_path}")

    return flagged


def main():
    parser = argparse.ArgumentParser(
        description="Post-generation similarity check against LanceDB"
    )
    parser.add_argument(
        "--input", type=Path, required=True,
        help="Path to tasks_all.json from the new batch",
    )
    parser.add_argument(
        "--api-key", type=str, default=GOOGLE_API_KEY,
        help="Google AI API key (or set GOOGLE_API_KEY env var)",
    )
    parser.add_argument(
        "--threshold", type=float, default=SIMILARITY_THRESHOLD,
        help=f"Similarity threshold (default: {SIMILARITY_THRESHOLD})",
    )
    parser.add_argument(
        "--batch-size", type=int, default=50,
        help="Number of tasks to embed per API call",
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Output path for flagged tasks JSON (optional)",
    )
    parser.add_argument(
        "--narrow", action="store_true",
        help="Use narrative-only embedding (title + goal + arc) instead of all fields",
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

    flagged = check_similarity(
        args.input, args.api_key, args.threshold, args.batch_size, args.output,
        narrow=args.narrow,
    )
    sys.exit(1 if flagged else 0)


if __name__ == "__main__":
    main()
