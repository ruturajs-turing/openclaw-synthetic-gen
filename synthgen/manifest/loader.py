"""Load the per-persona asset manifest. The source docs-manifest files are keyed to
specific template personas (e.g. P-0006); since every persona gets the same ~457-asset
inventory, we treat one file as the canonical template and remap the persona id into the
paths for whichever persona we're generating.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from ..config import DOCS_MANIFEST_DIR

_PID_RE = re.compile(r"P-\d{4}")


@dataclass(frozen=True)
class ManifestEntry:
    id: str
    title: str
    kind: str
    path: str          # persona-relative, e.g. "personas/P-0001/docs/bank-statement.pdf"
    modality: str      # image | pdf | svg | text | csv | json | audio | ...
    mime: str | None


@lru_cache(maxsize=1)
def _template() -> tuple[str, tuple[dict, ...]]:
    """Return (template_pid, entries). Picks the lowest-numbered manifest file."""
    files = sorted(DOCS_MANIFEST_DIR.glob("P-*.json"))
    if not files:
        raise FileNotFoundError(f"no docs-manifest files under {DOCS_MANIFEST_DIR}")
    tpid = files[0].stem
    entries = json.loads(files[0].read_text(encoding="utf-8"))
    return tpid, tuple(entries)


def load_for(persona_id: str) -> list[ManifestEntry]:
    """Instantiate the template manifest for `persona_id`, remapping the template id."""
    tpid, entries = _template()
    out: list[ManifestEntry] = []
    for e in entries:
        path = e["path"].replace(tpid, persona_id)
        out.append(ManifestEntry(
            id=e.get("id", ""), title=e.get("title", ""), kind=e.get("kind", ""),
            path=path, modality=(e.get("modality") or "").lower(), mime=e.get("mime"),
        ))
    return out


def modality_counts(persona_id: str = "P-0001") -> dict[str, int]:
    counts: dict[str, int] = {}
    for e in load_for(persona_id):
        counts[e.modality] = counts.get(e.modality, 0) + 1
    return counts
