"""Async task generation orchestrator supporting Anthropic and OpenAI models."""

from __future__ import annotations

import asyncio
import json
import re
import time
from pathlib import Path
from typing import Any

from anthropic import AsyncAnthropic, RateLimitError, APIError
from openai import AsyncOpenAI, RateLimitError as OAIRateLimitError, APIError as OAIAPIError

from config import MODEL, BATCH_SIZE, MAX_RETRIES, MAX_REGEN_ATTEMPTS, CONCURRENCY, TASKS_PER_PERSONA, OUTPUT_DIR
from embedding_store import EmbeddingStore
from prompts.system_prompt import get_system_prompt
from prompts.user_prompt import build_user_prompt, load_prior_batch_titles
from response_parser import parse_tasks_response

TASK_ID_RE = re.compile(r"^P-(\d+)-(\d+)$")
TASK_ID_RE_V2 = re.compile(r"^P-(\d{4})-(\d+)$")


def _log(msg: str):
    print(msg, flush=True)


def _persona_complete(pid: str, start_seq: int, tasks_per_persona: int, output_dir: Path) -> bool:
    """True if persona JSON exists with all expected seq numbers."""
    fp = output_dir / "tasks_by_persona" / f"{pid}.json"
    if not fp.exists():
        return False
    try:
        tasks = json.loads(fp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    expected = set(range(start_seq, start_seq + tasks_per_persona))
    found: set[int] = set()
    for t in tasks:
        m = TASK_ID_RE.match(t.get("task_id", "")) or TASK_ID_RE_V2.match(t.get("task_id", ""))
        if m:
            found.add(int(m.group(2)))
    return expected.issubset(found)


async def generate_for_persona(
    client: AsyncAnthropic,
    persona: dict,
    persona_idx: int,
    model: str = MODEL,
    dry_run: bool = False,
    *,
    start_seq: int = 1,
    chat_batch: bool = False,
    enterprise_batch: bool = False,
    output_dir: Path = OUTPUT_DIR,
    prior_batch_titles: list[str] | None = None,
    tasks_per_persona: int = TASKS_PER_PERSONA,
    embed_store: EmbeddingStore | None = None,
    no_memory: bool = False,
    chat_focused: bool = False,
    persona_assets: Any | None = None,
) -> list[dict[str, Any]]:
    """Generate all tasks for a single persona (4 batches of 5 = 20 tasks by default)."""
    all_tasks: list[dict] = []
    num_batches = tasks_per_persona // BATCH_SIZE
    pid = persona["persona_id"]
    persona_num = int(pid.split("-")[-1])
    system_prompt = get_system_prompt(chat_batch=chat_batch, start_seq=start_seq,
                                      enterprise_batch=enterprise_batch)

    if prior_batch_titles is None and (chat_batch or enterprise_batch):
        prior_batch_titles = load_prior_batch_titles(pid)

    for batch_num in range(1, num_batches + 1):
        previously_generated = all_tasks[-25:] if all_tasks else []
        user_prompt = build_user_prompt(
            persona,
            batch_num,
            previously_generated,
            persona_num,
            start_seq=start_seq,
            chat_batch=chat_batch,
            prior_batch_titles=prior_batch_titles,
            enterprise_batch=enterprise_batch,
            no_memory=no_memory,
            chat_focused=chat_focused,
            persona_assets=persona_assets,
        )

        if dry_run:
            _log(
                f"  DRY RUN: {pid} batch {batch_num}/{num_batches} "
                f"seq {start_seq + (batch_num - 1) * 5:02d}-"
                f"{start_seq + batch_num * 5 - 1:02d} | "
                f"prompt={len(system_prompt) + len(user_prompt)} chars"
            )
            continue

        tasks = await _call_with_retries(
            client, system_prompt, user_prompt, model, pid, batch_num
        )

        # Embedding similarity gate: check new tasks against DB
        if embed_store and tasks:
            accepted, flagged = embed_store.check_batch(tasks)

            if flagged:
                flagged_ids = [t.get("task_id", "?") for t in flagged]
                _log(
                    f"  [EMBED] {pid} batch {batch_num}: "
                    f"{len(flagged)} tasks too similar, regenerating: {flagged_ids}"
                )

                for attempt in range(1, MAX_REGEN_ATTEMPTS + 1):
                    novelty_hint = (
                        f"\n\nIMPORTANT: The following task IDs were too similar to "
                        f"existing tasks and must be regenerated with DIFFERENT themes, "
                        f"domains, and scenarios. Avoid: "
                        f"{'; '.join(t.get('_flagged_reason', '') for t in flagged)}"
                    )
                    regen_prompt = user_prompt + novelty_hint

                    regen_tasks = await _call_with_retries(
                        client, system_prompt, regen_prompt, model,
                        pid, batch_num,
                    )

                    if regen_tasks:
                        regen_accepted, still_flagged = embed_store.check_batch(
                            regen_tasks
                        )
                        accepted.extend(regen_accepted)

                        if not still_flagged:
                            _log(
                                f"  [EMBED] {pid} batch {batch_num}: "
                                f"regen attempt {attempt} succeeded"
                            )
                            break

                        flagged = still_flagged
                        _log(
                            f"  [EMBED] {pid} batch {batch_num}: "
                            f"regen attempt {attempt}, "
                            f"{len(still_flagged)} still flagged"
                        )
                    else:
                        _log(
                            f"  [EMBED] {pid} batch {batch_num}: "
                            f"regen attempt {attempt} returned 0 tasks"
                        )
                        break

            # Store accepted tasks in LanceDB for future comparisons
            embed_store.store_batch(accepted)
            tasks = accepted

        all_tasks.extend(tasks)
        _log(
            f"  {pid} batch {batch_num}/{num_batches} -> {len(tasks)} tasks "
            f"(total: {len(all_tasks)})"
        )

    if all_tasks and not dry_run:
        out_dir = output_dir / "tasks_by_persona"
        out_dir.mkdir(parents=True, exist_ok=True)
        with open(out_dir / f"{pid}.json", "w", encoding="utf-8") as f:
            json.dump(all_tasks, f, indent=2, ensure_ascii=False)

    return all_tasks


def _is_openai_model(model: str) -> bool:
    """Check if the model string indicates an OpenAI model."""
    return model.startswith(("gpt-", "o1", "o3", "o4"))


async def _call_anthropic(
    client: AsyncAnthropic,
    system_prompt: str,
    user_prompt: str,
    model: str,
    persona_id: str,
    batch_num: int,
) -> list[dict]:
    """Call Anthropic Claude with retry logic."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = await client.messages.create(
                model=model,
                max_tokens=16384,
                temperature=0.9,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt},
                ],
            )
            text = response.content[0].text
            tasks = parse_tasks_response(text)

            if tasks:
                return tasks

            _log(
                f"  [WARN] {persona_id} batch {batch_num}: "
                f"parse returned 0 tasks (attempt {attempt})"
            )

        except RateLimitError:
            wait = 2 ** attempt * 5
            _log(
                f"  [RATE] {persona_id} batch {batch_num}, "
                f"waiting {wait}s (attempt {attempt})"
            )
            await asyncio.sleep(wait)

        except APIError as e:
            _log(f"  [ERR] {persona_id} batch {batch_num}: {e} (attempt {attempt})")
            if attempt == MAX_RETRIES:
                return []
            await asyncio.sleep(2 ** attempt)

        except Exception as e:
            _log(
                f"  [ERR] {persona_id} batch {batch_num}: "
                f"{type(e).__name__}: {e} (attempt {attempt})"
            )
            if attempt == MAX_RETRIES:
                return []
            await asyncio.sleep(2)

    return []


async def _call_openai(
    client: AsyncOpenAI,
    system_prompt: str,
    user_prompt: str,
    model: str,
    persona_id: str,
    batch_num: int,
) -> list[dict]:
    """Call OpenAI GPT with retry logic."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = await client.chat.completions.create(
                model=model,
                max_completion_tokens=16384,
                temperature=0.9,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            text = response.choices[0].message.content
            tasks = parse_tasks_response(text)

            if tasks:
                return tasks

            _log(
                f"  [WARN] {persona_id} batch {batch_num}: "
                f"parse returned 0 tasks (attempt {attempt})"
            )

        except OAIRateLimitError:
            wait = 2 ** attempt * 5
            _log(
                f"  [RATE] {persona_id} batch {batch_num}, "
                f"waiting {wait}s (attempt {attempt})"
            )
            await asyncio.sleep(wait)

        except OAIAPIError as e:
            _log(f"  [ERR] {persona_id} batch {batch_num}: {e} (attempt {attempt})")
            if attempt == MAX_RETRIES:
                return []
            await asyncio.sleep(2 ** attempt)

        except Exception as e:
            _log(
                f"  [ERR] {persona_id} batch {batch_num}: "
                f"{type(e).__name__}: {e} (attempt {attempt})"
            )
            if attempt == MAX_RETRIES:
                return []
            await asyncio.sleep(2)

    return []


async def _call_with_retries(
    client,
    system_prompt: str,
    user_prompt: str,
    model: str,
    persona_id: str,
    batch_num: int,
) -> list[dict]:
    """Route to the appropriate provider based on model name."""
    if _is_openai_model(model):
        return await _call_openai(client, system_prompt, user_prompt, model, persona_id, batch_num)
    return await _call_anthropic(client, system_prompt, user_prompt, model, persona_id, batch_num)


async def generate_all(
    personas: list[dict],
    api_key: str,
    model: str = MODEL,
    concurrency: int = CONCURRENCY,
    dry_run: bool = False,
    *,
    start_seq_map: dict[str, int] | None = None,
    chat_batch: bool = False,
    enterprise_batch: bool = False,
    output_dir: Path = OUTPUT_DIR,
    tasks_per_persona: int = TASKS_PER_PERSONA,
    prior_titles_map: dict[str, list[str]] | None = None,
    embed_store: EmbeddingStore | None = None,
    no_memory: bool = False,
    api_keys: list[str] | None = None,
    chat_focused: bool = False,
    assets_map: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Generate tasks for all personas with chunked concurrent processing.

    If api_keys is provided (multiple keys), clients are rotated round-robin
    across personas to distribute rate-limit quota.
    """
    # Build client pool — one client per unique key, rotated across personas
    use_openai = _is_openai_model(model)
    if use_openai:
        openai_keys = api_keys if api_keys else [api_key]
        clients = [AsyncOpenAI(api_key=k) for k in openai_keys]
        _log(f"  Using OpenAI ({model}) with {len(clients)} key(s)")
    elif api_keys and len(api_keys) > 1:
        clients = [AsyncAnthropic(api_key=k) for k in api_keys]
        _log(f"  Using {len(clients)} Anthropic API keys in round-robin rotation")
    else:
        clients = [AsyncAnthropic(api_key=api_key)]

    all_tasks: list[dict] = []
    start = time.time()
    total = len(personas)

    embed_info = ""
    if embed_store:
        stats = embed_store.get_stats()
        embed_info = f", embedding_store={stats['total_embeddings']} existing tasks"

    _log(
        f"\nProcessing {total} personas (concurrency={concurrency}, "
        f"batches_per_persona={tasks_per_persona // BATCH_SIZE}, "
        f"chat_batch={chat_batch}{embed_info})"
    )

    for chunk_start in range(0, total, concurrency):
        chunk = personas[chunk_start : chunk_start + concurrency]
        chunk_end = min(chunk_start + concurrency, total)
        _log(f"\n--- Chunk [{chunk_start + 1}-{chunk_end}] of {total} ---")

        coros = []
        for i, p in enumerate(chunk):
            pid = p["persona_id"]
            start_seq = (start_seq_map or {}).get(pid, 1)
            prior_titles = (prior_titles_map or {}).get(pid)
            assigned_client = clients[(chunk_start + i) % len(clients)]
            pa = (assets_map or {}).get(pid)
            coros.append(
                generate_for_persona(
                    assigned_client,
                    p,
                    i + chunk_start,
                    model,
                    dry_run,
                    start_seq=start_seq,
                    chat_batch=chat_batch,
                    enterprise_batch=enterprise_batch,
                    output_dir=output_dir,
                    prior_batch_titles=prior_titles,
                    tasks_per_persona=tasks_per_persona,
                    embed_store=embed_store,
                    no_memory=no_memory,
                    chat_focused=chat_focused,
                    persona_assets=pa,
                )
            )
        results = await asyncio.gather(*coros, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                _log(f"  [FATAL] {chunk[i]['persona_id']}: {result}")
            elif isinstance(result, list):
                all_tasks.extend(result)

        elapsed_so_far = time.time() - start
        tasks_so_far = len(all_tasks)
        rate = tasks_so_far / elapsed_so_far if elapsed_so_far > 0 else 0
        _log(
            f"  Progress: {chunk_end}/{total} personas | {tasks_so_far} tasks | "
            f"{elapsed_so_far:.0f}s | {rate:.1f} tasks/s"
        )

    elapsed = time.time() - start
    _log(f"\nDone! Generated {len(all_tasks)} tasks in {elapsed:.1f}s")
    if embed_store:
        stats = embed_store.get_stats()
        _log(f"  Embedding store: {stats['total_embeddings']} total tasks stored")
    return all_tasks
