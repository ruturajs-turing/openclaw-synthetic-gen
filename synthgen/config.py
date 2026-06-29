"""Settings + key loading for synthgen.

Keys come from the project `Api_Keys` file (label format: "OpenAI: ...", "Claude: ...",
"Gemini: ...") with a fallback to the standard environment variables so CI/secrets keep
working. The single Gemini key serves both embeddings and Nanobanana image generation.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# Project root = parent of this package (…/OpenClaw_Synthetic_Gen).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_API_KEYS_FILE = PROJECT_ROOT / "Api_Keys"

# Where existing inputs live (the proven pipelines we lift logic + data from).
PERSONA_KIT_DIR = PROJECT_ROOT / "persona-generator-kit"
TASK_PIPELINE_DIR = PROJECT_ROOT / "privacy-task-generator-pipeline"
DOCS_MANIFEST_DIR = TASK_PIPELINE_DIR / "data" / "docs-manifest"
CLASSIFICATION_MD = PROJECT_ROOT / "Imp_Docs_must_Review" / "Classification.md"

# Label -> canonical provider name. Case-insensitive match on the label.
_LABEL_MAP = {"openai": "openai", "claude": "anthropic", "anthropic": "anthropic", "gemini": "gemini", "google": "gemini"}


def load_keys(path: Path | str = DEFAULT_API_KEYS_FILE) -> dict[str, str]:
    """Parse the Api_Keys label file -> {"openai","anthropic","gemini"}.

    Lines look like "Label: <value>" (or "Label = <value>"). Unknown labels are ignored.
    Falls back to OPENAI_API_KEY / ANTHROPIC_API_KEY / GEMINI_API_KEY|GOOGLE_API_KEY env
    for any provider not found in the file.
    """
    keys: dict[str, str] = {}
    p = Path(path)
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            sep = ":" if ":" in line else ("=" if "=" in line else None)
            if not sep:
                continue
            label, _, value = line.partition(sep)
            provider = _LABEL_MAP.get(label.strip().lower())
            value = value.strip()
            if provider and value:
                keys[provider] = value

    # Env fallback per provider.
    keys.setdefault("openai", os.getenv("OPENAI_API_KEY", "").strip())
    keys.setdefault("anthropic", os.getenv("ANTHROPIC_API_KEY", "").strip())
    keys.setdefault("gemini", os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", "")).strip())
    return {k: v for k, v in keys.items() if v}


@dataclass
class Settings:
    # Run identity / output
    run_dir: Path = PROJECT_ROOT / "runs" / "latest"

    # Stage knobs
    num_personas: int = 1
    tasks_per_persona: int = 20
    seed: int | None = None        # None => a fresh random seed per run (set for reproducibility)
    persona_id_width: int = 4

    # Models
    persona_model: str = "claude-sonnet-4-6"
    task_model: str = "claude-opus-4-8"
    embedding_model: str = "gemini-embedding-001"
    image_model: str = "gemini-2.5-flash-image"
    tts_model: str = "gpt-4o-mini-tts"

    # Concurrency
    concurrency: int = 8          # text generation (persona expand / tasks)
    asset_concurrency: int = 4    # image/pdf/audio generation

    # Cost / safety controls
    dry_run: bool = False
    max_assets: int | None = None         # cap total assets generated this run
    budget_usd: float | None = None       # hard dollar ceiling for the run
    similarity_threshold: float = 0.80
    max_regen_attempts: int = 3

    # Asset scope: "full" = the whole ~457-asset manifest; "minimal" = a curated core set
    # of essential documents (IDs, finance, health, personal) — far fewer assets + cost.
    doc_set: str = "full"

    # Keys (populated from load_keys)
    keys: dict[str, str] = field(default_factory=dict)

    @property
    def openai_key(self) -> str:
        return self.keys.get("openai", "")

    @property
    def anthropic_key(self) -> str:
        return self.keys.get("anthropic", "")

    @property
    def gemini_key(self) -> str:
        return self.keys.get("gemini", "")

    @classmethod
    def from_args(cls, args, keys_file: Path | str = DEFAULT_API_KEYS_FILE) -> "Settings":
        s = cls()
        s.keys = load_keys(keys_file)
        for name in (
            "num_personas", "tasks_per_persona", "seed", "concurrency",
            "asset_concurrency", "dry_run", "max_assets", "budget_usd",
        ):
            val = getattr(args, name, None)
            if val is not None:
                setattr(s, name, val)
        if getattr(args, "minimal", False):
            s.doc_set = "minimal"
        if getattr(args, "run_dir", None):
            s.run_dir = Path(args.run_dir)
        for m in ("persona_model", "task_model", "image_model", "tts_model"):
            val = getattr(args, m, None)
            if val:
                setattr(s, m, val)
        return s


def _demo() -> None:
    """Self-check: parse a temp label file and confirm the three providers map."""
    import tempfile

    sample = "OpenAI: sk-openai-AAAA\nClaude = sk-ant-BBBB\nGemini: AQ.CCCC\n# comment\nJunk line\n"
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write(sample)
        tmp = f.name
    got = load_keys(tmp)
    os.unlink(tmp)
    assert got == {"openai": "sk-openai-AAAA", "anthropic": "sk-ant-BBBB", "gemini": "AQ.CCCC"}, got
    print("config self-check OK:", sorted(got))


if __name__ == "__main__":
    _demo()
