"""Constants the vendored persona-kit modules (_spine_src, _builders) reference as
`config.*`. Mirrors the originals from persona-generator-kit/config.py so the lifted
logic runs unchanged. Tunables that synthgen overrides (model, counts) are passed in
explicitly by the orchestrator, not read from here.
"""

from pathlib import Path

from .. import SYNTHETIC_BANNER as _BANNER

# Spine
PERSONA_ID_WIDTH = 4
REFERENCE_YEAR = 2026
SYNTHETIC_EMAIL_DOMAIN = "example-personas.test"
DEFAULT_COUNT = 250
DEFAULT_SEED = 42

# Expansion / builders
SYNTHETIC_BANNER = _BANNER
LLM_MAX_TOKENS = 8192
LLM_TEMPERATURE = 0.9
LLM_CONCURRENCY = 4
ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
OPENAI_MODEL = "anthropic/claude-sonnet-4"
LLM_PROVIDER = "anthropic"
ANTHROPIC_KEY_ENV = "ANTHROPIC_API_KEY"
OPENAI_KEY_ENV = "OPENAI_API_KEY"
OPENAI_BASE_URL_ENV = "OPENAI_BASE_URL"

# Paths (only used if the originals' main() ran; synthgen drives via the orchestrator).
DEFAULT_SPINE_PATH = Path("output/personas.json")
DEFAULT_WORKSPACE_ROOT = Path("output")
