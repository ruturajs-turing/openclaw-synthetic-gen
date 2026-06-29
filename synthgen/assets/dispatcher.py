"""Manifest-driven asset dispatcher. Routes each PlannedAsset by modality to its generator,
ordering portraits first (so ID docs can reference the face), skipping already-generated
assets, and enforcing --max-assets / --budget-usd caps. In --dry-run it estimates only.

Generators register into GENERATORS lazily (filled by synthgen.assets.image/pdf/audio/stub
in P5) so this module is importable before those land.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path

from ..config import Settings
from ..costs import CostModel, IMAGE_USD_PER_IMAGE, TTS_USD_PER_1K_CHARS, AVG_AUDIO_CHARS
from ..events import Event, EventBus, EventType
from ..state import RunState
from ..manifest.extract import PlannedAsset

# modality -> async generator(planned, settings, bus, costs) -> None (writes file)
GENERATORS: dict[str, Callable[..., Awaitable[None]]] = {}

def register(modality: str):
    def deco(fn):
        GENERATORS[modality] = fn
        return fn
    return deco


def _is_paid(pa: PlannedAsset) -> bool:
    """Only API-backed assets cost money. Audio always; images only for genuine photographs
    (faces + photo scenes). Documents — incl. ID cards and `.real` composites — are rendered
    offline via Chromium + OpenCV and are free."""
    if pa.entry.modality == "audio":
        return True
    if pa.entry.modality == "image":
        from .kinds import is_paid_image
        # photos/faces and photoreal `.real` documents (img2img) cost money
        if pa.entry.path.endswith(".real.png") or pa.entry.kind.endswith(".real"):
            return True
        return is_paid_image(pa.entry.kind)
    return False


def _est_cost(pa: PlannedAsset) -> float:
    if not _is_paid(pa):
        return 0.0
    if pa.entry.modality == "audio":
        return AVG_AUDIO_CHARS / 1000 * TTS_USD_PER_1K_CHARS
    return IMAGE_USD_PER_IMAGE


def _portrait_first(plan: list[PlannedAsset]) -> list[PlannedAsset]:
    """Avatars/faces first so subsequent ID images can use them as a reference."""
    return sorted(plan, key=lambda pa: 0 if pa.entry.kind in ("avatar", "profile-photo", "face") else 1)


async def dispatch(plan: list[PlannedAsset], settings: Settings, bus: EventBus,
                   costs: CostModel, state: RunState) -> dict:
    sem = asyncio.Semaphore(max(1, settings.asset_concurrency))
    generated = skipped = capped = paid_generated = 0
    est_total = 0.0
    ordered = _portrait_first(plan)

    async def _one(pa: PlannedAsset):
        nonlocal generated, skipped, capped, paid_generated, est_total
        pid, mid = pa.persona_id, pa.entry.id
        est = _est_cost(pa)
        est_total += est

        if settings.dry_run:
            return  # estimate only; counted above

        if state.asset_is_done(pid, mid) or pa.out_path.exists():
            skipped += 1
            bus.emit(Event(EventType.ASSET_SKIPPED, persona_id=pid,
                           data={"path": pa.entry.path, "modality": pa.entry.modality}))
            return

        # Caps apply only to paid (API-backed) assets; offline renders are free + unbounded.
        if _is_paid(pa):
            if settings.max_assets is not None and paid_generated >= settings.max_assets:
                capped += 1
                return
            if costs.would_exceed(est, settings.budget_usd):
                capped += 1
                bus.log(f"budget cap reached (${settings.budget_usd}); skipping {pa.entry.path}", persona_id=pid)
                return

        gen = GENERATORS.get(pa.entry.modality) or GENERATORS.get("_default")
        if gen is None:
            return
        async with sem:
            try:
                pa.out_path.parent.mkdir(parents=True, exist_ok=True)
                await gen(pa, settings, bus, costs)
                state.mark_asset_done(pid, mid)
                state.cost_usd_spent = costs.spent_usd
                state.save()
                generated += 1
                if _is_paid(pa):
                    paid_generated += 1
                bus.emit(Event(EventType.ASSET_GENERATED, persona_id=pid,
                               data={"path": pa.entry.path, "modality": pa.entry.modality}))
            except Exception as e:  # noqa: BLE001
                bus.error(f"asset {pa.entry.path} failed: {type(e).__name__}: {e}", persona_id=pid)

    # Run in modality order but bounded; portraits first guarantees face availability.
    try:
        for pa in ordered:
            await _one(pa)
    finally:
        from . import render  # close the headless browser if it was launched
        await render.shutdown()

    summary = {"generated": generated, "skipped": skipped, "capped": capped,
               "estimated_usd": round(est_total, 4)}
    bus.log(f"assets: {summary}")
    return summary
