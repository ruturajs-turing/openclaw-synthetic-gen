"""Image generation router (v2):
  * faces + photo scenes  -> Gemini 2.5 Flash Image (Nanobanana) — genuine photographs (paid)
  * all documents (incl. IDs) -> crisp HTML render via headless Chromium (free, legible)
  * `.real` documents + a sibling `.real.png` for every doc -> composite the crisp render onto
    a real surface photo (free, text stays sharp)

ID cards embed the persona's generated face. Diffusion is never used to draw document text.
"""

from __future__ import annotations

import base64
import random
import time
from functools import lru_cache
from pathlib import Path

from . import photoreal, render, surfaces
from .dispatcher import register
from .docgen import humanize
from .html import families, templates
from .kinds import FACE_KINDS, PHOTO_SCENE_KINDS
from ..config import Settings
from ..costs import CostModel
from ..events import Event, EventBus, EventType


@lru_cache(maxsize=4)
def _client(key: str):
    from google import genai
    return genai.Client(api_key=key)


def _extract_image_bytes(resp) -> bytes | None:
    for cand in getattr(resp, "candidates", None) or []:
        content = getattr(cand, "content", None)
        for part in (getattr(content, "parts", None) or []):
            inline = getattr(part, "inline_data", None)
            data = getattr(inline, "data", None) if inline else None
            if data:
                return data if isinstance(data, (bytes, bytearray)) else base64.b64decode(data)
    return None


def _portrait_path(settings: Settings, persona_id: str) -> Path:
    return settings.run_dir / "assets" / "faces" / f"{persona_id}.png"


def _call_image(settings, bus, costs, persona_id, kind, prompt, reference) -> bytes:
    """Low-level Nanobanana call (used for faces, photo scenes, and surface backgrounds)."""
    from google.genai import types
    contents: list = [prompt]
    if reference:
        contents.append(types.Part.from_bytes(data=reference, mime_type="image/png"))
    bus.emit(Event(EventType.API_CALL_STARTED, persona_id=persona_id,
                   data={"provider": "gemini", "model": settings.image_model, "kind": f"image:{kind}"}))
    t0 = time.perf_counter()
    try:
        resp = _client(settings.gemini_key).models.generate_content(
            model=settings.image_model, contents=contents)
        img = _extract_image_bytes(resp)
    except Exception as e:  # noqa: BLE001
        bus.emit(Event(EventType.API_CALL_FINISHED, persona_id=persona_id,
                       data={"provider": "gemini", "model": settings.image_model, "kind": f"image:{kind}",
                             "error": str(e), "latency_ms": round((time.perf_counter() - t0) * 1000)}))
        raise
    usd = costs.add_image(1)
    bus.emit(Event(EventType.API_CALL_FINISHED, persona_id=persona_id,
                   data={"provider": "gemini", "model": settings.image_model, "kind": f"image:{kind}",
                         "latency_ms": round((time.perf_counter() - t0) * 1000), "usd": round(usd, 5)}))
    bus.emit(Event(EventType.COST_UPDATE, data={"spent_usd": round(costs.spent_usd, 4)}))
    if not img:
        raise RuntimeError("image API returned no image bytes")
    return img


def _ensure_portrait(settings, bus, costs, pa) -> bytes:
    pp = _portrait_path(settings, pa.persona_id)
    if pp.exists():
        return pp.read_bytes()
    from .prompts import build_portrait_prompt
    img = _call_image(settings, bus, costs, pa.persona_id, "avatar", build_portrait_prompt(pa), None)
    pp.parent.mkdir(parents=True, exist_ok=True)
    pp.write_bytes(img)
    return img


def _real_path(out_path: Path) -> Path:
    name = out_path.name
    if name.endswith(".real.png"):
        return out_path
    return out_path.with_name(out_path.stem + ".real.png")


def _make_real(pa, png: bytes, settings, bus, costs) -> bytes:
    """Gold-standard photoreal version: image-to-image phone photo of the crisp render via
    Nanobanana (preserves content, adds a real physical scene). Falls back to an offline
    OpenCV composite when there's no key, in dry-run, or the budget cap is reached."""
    import random
    can_pay = (settings.gemini_key and not settings.dry_run
               and not costs.would_exceed(0.039, settings.budget_usd))
    if can_pay:
        from .prompts import build_realphoto_prompt
        try:
            prompt = build_realphoto_prompt(pa, random.Random(f"{pa.persona_id}:{pa.entry.id}"))
            return _call_image(settings, bus, costs, pa.persona_id, pa.entry.kind + ":real", prompt, png)
        except Exception as e:  # noqa: BLE001
            bus.log(f"{pa.persona_id}: img2img failed for {pa.entry.kind}, using composite: {e}")
    from . import photoreal, surfaces
    surf = surfaces.get_surface_bytes(settings, bus, costs, pa.persona_id,
                                      random.Random(f"surf:{pa.persona_id}"))
    return photoreal.composite(png, surf, f"{pa.persona_id}:{pa.entry.id}")


async def _generate(pa, settings: Settings, bus: EventBus, costs: CostModel) -> None:
    kind = pa.entry.kind

    # 1) Faces — genuine photograph (paid), cached and reused as ID reference.
    if kind in FACE_KINDS:
        img = _ensure_portrait(settings, bus, costs, pa)
        if pa.out_path != _portrait_path(settings, pa.persona_id):
            pa.out_path.write_bytes(img)
        return

    # 2) Photo scenes — genuine photograph (paid).
    if kind in PHOTO_SCENE_KINDS:
        from .prompts import _SD_MARK
        ref = _ensure_portrait(settings, bus, costs, pa) if kind == "family-photo" else None
        prompt = (f"A natural, photorealistic candid {humanize(kind)} photograph for a fictional person. "
                  f"Real camera look, true-to-life lighting and detail. {_SD_MARK}")
        pa.out_path.write_bytes(_call_image(settings, bus, costs, pa.persona_id, kind, prompt, ref))
        return

    # 3) Documents — crisp HTML render via Chromium (free, legible).
    face_b64 = None
    if families.family_for(kind) == "id_card" and "BIO_PHOTO_FACE" in pa.pii_fields:
        face_b64 = base64.b64encode(_ensure_portrait(settings, bus, costs, pa)).decode()
    html = templates.render_html(pa, face_b64=face_b64)
    png = await render.render_png(html)

    is_real_entry = pa.entry.path.endswith(".real.png") or kind.endswith(".real")
    if is_real_entry:
        pa.out_path.write_bytes(_make_real(pa, png, settings, bus, costs))
        return

    # Clean .png (crisp source-of-truth) + a sibling .real.png gold-standard phone photo.
    pa.out_path.write_bytes(png)
    real = _real_path(pa.out_path)
    if not real.exists():
        try:
            real.write_bytes(_make_real(pa, png, settings, bus, costs))
        except Exception as e:  # noqa: BLE001
            bus.log(f"{pa.persona_id}: .real skipped for {kind}: {e}")


register("image")(_generate)
