"""Adapt a synthgen-generated persona (spine + expansion artifacts) into the rich dict
shape the lifted task prompts expect. Every field the prompts read is accessed via .get()
with defaults, so this only needs to supply what we have; missing fields degrade
gracefully. We reuse persona_loader._enrich_v2 to derive _data_level_map etc. from the
spine's data_labels + pii_vault.
"""

from __future__ import annotations

import json
from pathlib import Path

from ._kit_bootstrap import ensure_kit_on_path


def _read_json(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default
    except (json.JSONDecodeError, OSError):
        return default


def _read_text(p: Path) -> str | None:
    try:
        return p.read_text(encoding="utf-8") if p.exists() else None
    except OSError:
        return None


def to_task_persona(run_dir: Path, persona: dict) -> dict:
    """Build the enriched task-generation persona from our on-disk artifacts."""
    ensure_kit_on_path()
    from persona_loader import _enrich_v2  # vendored

    pid = persona["persona_id"]
    pdir = run_dir / "personas" / pid
    p = dict(persona)  # shallow copy of the spine record

    # asset_pack.json -> persona["asset_pack"]
    p["asset_pack"] = _read_json(pdir / "asset_pack.json", {})

    # crosslinks.json {"links": [...]} -> persona["crosslinks"]
    cross = _read_json(pdir / "crosslinks.json", {})
    p["crosslinks"] = cross.get("links", []) if isinstance(cross, dict) else []

    # workspace memory files -> persona["workspace"]["memory_entries"] (filename -> content)
    mem_dir = pdir / "workspace" / "memory"
    memory_entries: dict[str, str] = {}
    if mem_dir.is_dir():
        for md in sorted(mem_dir.glob("*.md")):
            try:
                memory_entries[md.name] = md.read_text(encoding="utf-8")
            except OSError:
                pass
    notes_dir = pdir / "workspace" / "notes"
    workspace = {
        "memory_files": sorted(memory_entries.keys()),
        "memory_entries": memory_entries,
        "journal": _read_text(notes_dir / "journal_longform.md"),
        "todo_list": _read_text(notes_dir / "todo_list.md"),
    }
    p["workspace"] = workspace

    # bio: prefer MEMORY.md opening, else resume summary.
    mem_md = _read_text(pdir / "MEMORY.md")
    if mem_md:
        body = [ln for ln in mem_md.splitlines() if ln and not ln.startswith(("#", "<!--"))]
        p.setdefault("bio", "\n".join(body[:6]).strip())
    elif p["asset_pack"].get("resume_summary"):
        p.setdefault("bio", p["asset_pack"]["resume_summary"])

    _enrich_v2(p)  # derives _data_level_map, _platforms, _personality_tag, etc.
    return p
