"""Put the vendored task-pipeline modules (synthgen/tasks/_kit) on sys.path so their
original bare cross-imports (`from persona_loader import ...`, `from prompts.user_prompt
import ...`, `import config`) resolve unchanged. This keeps the proven HTG prompts,
parser, and embedding dedup byte-for-byte identical to the source pipeline.
"""

from __future__ import annotations

import sys
from pathlib import Path

_KIT = Path(__file__).resolve().parent / "_kit"


def ensure_kit_on_path() -> None:
    p = str(_KIT)
    if p not in sys.path:
        sys.path.insert(0, p)
