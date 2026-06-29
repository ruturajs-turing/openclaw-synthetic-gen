"""Load DELIVERY_MAP_SUMMARY.csv and extracted memory notes into per-persona inventories.

Provides two main functions:
  load_delivery_map()  → dict[persona_id, PersonaAssets]
  build_workspace_prompt_section(persona_id) → str for the LLM prompt
"""

from __future__ import annotations

import csv
import hashlib
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).parent
DELIVERY_MAP_PATH = BASE_DIR / "DELIVERY_MAP_SUMMARY.csv"
EXTRACTED_MEMORIES_DIR = BASE_DIR / "extracted_memories"

# Sensitivity ordering for sorting
_SENS_ORDER = {"high": 0, "med": 1, "": 2}


@dataclass
class AssetEntry:
    asset_kind: str
    category: str
    pii_sensitivity: str
    formats: str
    delivery_folder: str  # "document" or "media"
    zip_paths: list[str]
    in_memory: bool
    memory_ref: str


@dataclass
class PersonaAssets:
    persona_id: str
    persona_name: str
    documents: list[AssetEntry] = field(default_factory=list)
    media: list[AssetEntry] = field(default_factory=list)
    memory_notes: dict[str, str] = field(default_factory=dict)  # filename -> content
    memory_linked_docs: list[tuple[str, str]] = field(default_factory=list)  # (asset_kind, memory_ref)


def load_delivery_map(csv_path: Path | None = None) -> dict[str, PersonaAssets]:
    """Parse DELIVERY_MAP_SUMMARY.csv into per-persona asset inventories."""
    path = csv_path or DELIVERY_MAP_PATH
    personas: dict[str, PersonaAssets] = {}

    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pid = row["persona_id"]
            if pid not in personas:
                personas[pid] = PersonaAssets(
                    persona_id=pid,
                    persona_name=row["persona_name"],
                )

            entry = AssetEntry(
                asset_kind=row["asset_kind"],
                category=row["category"],
                pii_sensitivity=row["pii_sensitivity"],
                formats=row["formats"],
                delivery_folder=row["delivery_folder"],
                zip_paths=[p.strip() for p in row["zip_archive_paths"].split(";") if p.strip()],
                in_memory=row["in_memory"].strip().lower() == "yes",
                memory_ref=row.get("memory_ref", "").strip(),
            )

            if entry.delivery_folder == "document":
                personas[pid].documents.append(entry)
            else:
                personas[pid].media.append(entry)

            if entry.memory_ref:
                personas[pid].memory_linked_docs.append(
                    (entry.asset_kind, entry.memory_ref)
                )

    # Load extracted memory notes
    for pid, pa in personas.items():
        mem_dir = EXTRACTED_MEMORIES_DIR / pid
        if mem_dir.is_dir():
            for md_file in sorted(mem_dir.glob("*.md")):
                try:
                    pa.memory_notes[md_file.name] = md_file.read_text(encoding="utf-8")
                except Exception:
                    pass

    return personas


def _format_asset_line(entry: AssetEntry) -> str:
    """Single-line summary of an asset for the prompt."""
    sens_tag = {"high": "[HIGH]", "med": "[MED]", "": "[---]"}.get(
        entry.pii_sensitivity, "[---]"
    )
    fmt = entry.formats if entry.formats else "various"
    mem_flag = " *MEM-LINKED*" if entry.in_memory else ""
    return f"  {sens_tag} {entry.asset_kind} ({fmt}){mem_flag}"


def build_workspace_prompt_section(
    pa: PersonaAssets,
    batch_num: int = 1,
    max_memory_notes: int = 8,
    max_note_chars: int = 400,
) -> str:
    """Build the WORKSPACE section for a persona's LLM prompt.

    Includes:
    1. Document inventory (what the agent has in workspace)
    2. Media inventory (scans, photos, receipts the agent has)
    3. Memory notes (what the agent remembers from past sessions)
    4. Doc-memory links (which docs are referenced in which memories)
    """
    lines: list[str] = []

    # --- Documents ---
    docs_high = [d for d in pa.documents if d.pii_sensitivity == "high"]
    docs_med = [d for d in pa.documents if d.pii_sensitivity == "med"]
    docs_other = [d for d in pa.documents if d.pii_sensitivity not in ("high", "med")]

    lines.append("═══ AGENT'S WORKSPACE: DOCUMENTS (already in agent's filesystem) ═══")
    lines.append(f"The agent has {len(pa.documents)} documents in its workspace.")
    lines.append("Tasks should ask the agent to retrieve, analyze, edit, or share these.\n")

    if docs_high:
        lines.append("HIGH SENSITIVITY (L3/L4 — require privacy handling):")
        # Deduplicate by asset_kind
        seen = set()
        for d in sorted(docs_high, key=lambda x: x.asset_kind):
            if d.asset_kind not in seen:
                seen.add(d.asset_kind)
                lines.append(_format_asset_line(d))

    if docs_med:
        lines.append("\nMEDIUM SENSITIVITY (L2 — cautionary handling):")
        seen = set()
        for d in sorted(docs_med, key=lambda x: x.asset_kind):
            if d.asset_kind not in seen:
                seen.add(d.asset_kind)
                lines.append(_format_asset_line(d))

    if docs_other:
        other_kinds = sorted(set(d.asset_kind for d in docs_other))
        if len(other_kinds) > 15:
            lines.append(f"\nADDITIONAL DOCUMENTS ({len(other_kinds)} types):")
            lines.append(f"  {', '.join(other_kinds[:20])}{'...' if len(other_kinds) > 20 else ''}")
        else:
            lines.append(f"\nADDITIONAL DOCUMENTS:")
            for d in sorted(docs_other, key=lambda x: x.asset_kind):
                if d.asset_kind not in {x.asset_kind for x in docs_high + docs_med}:
                    lines.append(_format_asset_line(d))

    # --- Media ---
    lines.append(f"\n═══ AGENT'S WORKSPACE: MEDIA / SCANS (already in agent's filesystem) ═══")
    lines.append(f"The agent has {len(pa.media)} media files (scans, photos, receipts, IDs).\n")

    media_high = [m for m in pa.media if m.pii_sensitivity == "high"]
    media_med = [m for m in pa.media if m.pii_sensitivity == "med"]

    if media_high:
        lines.append("HIGH SENSITIVITY MEDIA:")
        seen = set()
        for m in sorted(media_high, key=lambda x: x.asset_kind):
            if m.asset_kind not in seen:
                seen.add(m.asset_kind)
                lines.append(_format_asset_line(m))

    if media_med:
        lines.append("\nMEDIUM SENSITIVITY MEDIA:")
        seen = set()
        for m in sorted(media_med, key=lambda x: x.asset_kind):
            if m.asset_kind not in seen:
                seen.add(m.asset_kind)
                lines.append(_format_asset_line(m))

    # --- Memory Notes ---
    if pa.memory_notes:
        lines.append(f"\n═══ AGENT'S MEMORY ({len(pa.memory_notes)} session notes) ═══")
        lines.append("The agent remembers these past sessions. Tasks can ask the agent to")
        lines.append("recall events, relationships, feelings, or document context from these.\n")

        # Select a batch-deterministic subset of notes
        all_notes = sorted(pa.memory_notes.keys())
        seed = int(hashlib.md5(f"{pa.persona_id}-{batch_num}".encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)

        # Categorize notes
        docref_notes = [n for n in all_notes if ".docref." in n]
        relationship_notes = [n for n in all_notes if ".note." in n and "photo" not in n.lower()]
        photo_notes = [n for n in all_notes if "photo" in n.lower() or ".note." not in n and ".docref." not in n]

        selected = []
        if docref_notes:
            selected.extend(rng.sample(docref_notes, min(3, len(docref_notes))))
        if relationship_notes:
            selected.extend(rng.sample(relationship_notes, min(4, len(relationship_notes))))
        if photo_notes:
            selected.extend(rng.sample(photo_notes, min(1, len(photo_notes))))

        selected = sorted(set(selected))[:max_memory_notes]

        for filename in selected:
            content = pa.memory_notes[filename]
            truncated = content[:max_note_chars].strip()
            if len(content) > max_note_chars:
                truncated += "..."
            lines.append(f"memory/{filename}:")
            lines.append(truncated)
            lines.append("")

        # List remaining notes the agent also has (titles only)
        remaining = [n for n in all_notes if n not in selected]
        if remaining:
            lines.append(f"Agent also has {len(remaining)} more memory notes:")
            lines.append(f"  {', '.join(remaining[:10])}{'...' if len(remaining) > 10 else ''}")

    # --- Doc-Memory Links ---
    if pa.memory_linked_docs:
        lines.append(f"\n═══ DOCUMENT-MEMORY LINKS (agent saw these docs in past sessions) ═══")
        lines.append("These documents were referenced in memory notes — the agent has prior")
        lines.append("context about them. Great for recall + re-analysis tasks.\n")
        for asset_kind, mem_ref in pa.memory_linked_docs[:8]:
            mem_file = Path(mem_ref).name
            lines.append(f"  {asset_kind} ← recalled in memory/{mem_file}")

    return "\n".join(lines)
