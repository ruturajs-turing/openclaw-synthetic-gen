"""Surface backgrounds for photoreal composites. Generates a few empty desk/table photos
per persona via Nanobanana (no text → no garbling), cached + reused. Falls back to a
procedural wood/desk texture when there's no Gemini key or the budget cap is reached, so
`.real.png` always works offline.
"""

from __future__ import annotations

import io
import random
from pathlib import Path

import numpy as np

_N = 3
_PROMPTS = [
    "Top-down photograph of an empty light wooden desk surface, soft natural daylight, no objects, no paper, no text, realistic wood grain.",
    "Overhead photo of an empty matte table top, neutral soft lighting, subtle texture, no objects, no text.",
    "Photograph of an empty dark wooden nightstand surface, warm ambient lamp light, no objects, no text.",
]


def _surf_dir(settings, persona_id: str) -> Path:
    return settings.run_dir / "assets" / "surfaces" / persona_id


def _procedural(seed, w=1400, h=1700) -> bytes:
    from PIL import Image
    nr = np.random.default_rng(abs(hash(seed)) % (2**32))
    base = np.array([(150, 120, 90), (120, 95, 70), (175, 160, 140)][nr.integers(0, 3)], np.float32)
    img = np.ones((h, w, 3), np.float32) * base
    # wood-ish vertical grain + noise + soft vignette
    grain = np.sin(np.linspace(0, nr.uniform(30, 60), w))[None, :, None] * 10
    img += grain
    img += nr.normal(0, 7, img.shape)
    yy = np.linspace(0.85, 1.05, h)[:, None, None]
    img *= yy
    arr = np.clip(img, 0, 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


def ensure_surfaces(settings, bus, costs, persona_id: str) -> list[Path]:
    d = _surf_dir(settings, persona_id)
    existing = sorted(d.glob("*.png"))
    if existing:
        return existing
    d.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for i in range(_N):
        p = d / f"{i}.png"
        data = None
        # Try real surface photo if we have a key and aren't over budget.
        if settings.gemini_key and not (settings.dry_run) and not costs.would_exceed(0.039, settings.budget_usd):
            try:
                from .image import _call_image
                data = _call_image(settings, bus, costs, persona_id, "surface", _PROMPTS[i % len(_PROMPTS)], None)
            except Exception as e:  # noqa: BLE001
                bus.log(f"surface gen failed ({persona_id} {i}), using procedural: {e}")
        if not data:
            data = _procedural(f"surf:{persona_id}:{i}")
        p.write_bytes(data)
        paths.append(p)
    return paths


def get_surface_bytes(settings, bus, costs, persona_id: str, rng) -> bytes:
    paths = ensure_surfaces(settings, bus, costs, persona_id)
    return rng.choice(paths).read_bytes()
