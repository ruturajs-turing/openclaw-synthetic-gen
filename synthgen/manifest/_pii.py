"""Re-export the canonical PII label -> sensitivity tier map (L0–L4) from the vendored
task kit, so the manifest layer can classify document PII without re-deriving the taxonomy.
"""

from __future__ import annotations

from ..tasks._kit_bootstrap import ensure_kit_on_path

ensure_kit_on_path()
from persona_loader import DATA_LEVEL_MAP  # noqa: E402  (vendored)

__all__ = ["DATA_LEVEL_MAP"]
