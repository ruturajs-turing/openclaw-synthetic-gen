"""Compute per-persona next task seq from existing CU Arena uploads."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent
OUTPUTS = BASE / "outputs"

TASK_ID_RE = re.compile(r"^T-(\d+)-(\d+)$")
P_TASK_ID_RE = re.compile(r"^P-(\d+)-(\d+)$")

DEFAULT_SOURCES = [
    OUTPUTS / "cuarena_upload.csv",
    OUTPUTS / "cuarena_upload_new_40.csv",
    OUTPUTS / "regenerated" / "cuarena_upload_P-047_21-40.csv",
]


def _add_seq(existing: dict[str, set[int]], persona_num: int, seq: int) -> None:
    pid = f"P-{persona_num:03d}"
    existing.setdefault(pid, set()).add(seq)


def scan_csv(path: Path, existing: dict[str, set[int]]) -> None:
    if not path.exists():
        return
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            tid = (row.get("task_id") or "").strip()
            m = TASK_ID_RE.match(tid)
            if m:
                _add_seq(existing, int(m.group(1)), int(m.group(2)))


def scan_json_dir(path: Path, existing: dict[str, set[int]]) -> None:
    if not path.exists():
        return
    for fp in path.glob("P-*.json"):
        try:
            tasks = json.loads(fp.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for t in tasks:
            tid = t.get("task_id", "")
            m = P_TASK_ID_RE.match(tid)
            if not m:
                m = TASK_ID_RE.match(tid)
                if m:
                    _add_seq(existing, int(m.group(1)), int(m.group(2)))
            else:
                _add_seq(existing, int(m.group(1)), int(m.group(2)))


def load_existing_seqs(extra_sources: list[Path] | None = None) -> dict[str, set[int]]:
    existing: dict[str, set[int]] = {}
    sources = list(DEFAULT_SOURCES)
    if extra_sources:
        sources.extend(extra_sources)
    for src in sources:
        if src.suffix == ".csv":
            scan_csv(src, existing)
        elif src.is_dir():
            scan_json_dir(src, existing)
    return existing


def get_start_seq(persona_id: str, existing: dict[str, set[int]] | None = None) -> int:
    existing = existing if existing is not None else load_existing_seqs()
    seqs = existing.get(persona_id, set())
    if not seqs:
        return 21
    return max(seqs) + 1


def build_start_seq_map(persona_ids: list[str]) -> dict[str, int]:
    existing = load_existing_seqs()
    return {pid: get_start_seq(pid, existing) for pid in persona_ids}
