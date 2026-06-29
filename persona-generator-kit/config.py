"""
Central configuration for the Persona Generator Kit.

Everything tunable lives here so the person running the kit only edits one file.
All values can also be overridden on the command line (see --help on each script).
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
KIT_ROOT = Path(__file__).resolve().parent

# Where Stage 1 writes the structured persona records (the "spine" file).
DEFAULT_SPINE_PATH = KIT_ROOT / "output" / "personas.json"

# Where Stage 2 writes each persona's expanded workspace tree.
#   <DEFAULT_WORKSPACE_ROOT>/personas/P-0001/...
#   <DEFAULT_WORKSPACE_ROOT>/assets/...
DEFAULT_WORKSPACE_ROOT = KIT_ROOT / "output"

# ---------------------------------------------------------------------------
# Stage 1 — spine generation
# ---------------------------------------------------------------------------
# How many personas to generate by default.
DEFAULT_COUNT = 250

# Reproducibility: same seed + same count => byte-identical spine file.
DEFAULT_SEED = 42

# Persona id format. Width 4 => "P-0001" (matches the extracted persona set).
# Set to 3 if you want "P-001" (matches the legacy privacy-personas.json).
PERSONA_ID_WIDTH = 4

# The synthetic e-mail domain used when the kit invents addresses.
SYNTHETIC_EMAIL_DOMAIN = "example-personas.test"

# Reference "today" used to compute ages and to anchor life timelines.
REFERENCE_YEAR = 2026

# ---------------------------------------------------------------------------
# Stage 2 — LLM expansion
# ---------------------------------------------------------------------------
# Provider: "anthropic" (default) or "openai" (any OpenAI-compatible endpoint,
# e.g. OpenRouter — set OPENAI_BASE_URL + OPENAI_API_KEY).
LLM_PROVIDER = "anthropic"

# Model used to render free-text artifacts. Override with --model.
ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
OPENAI_MODEL = "anthropic/claude-sonnet-4"

# Generation knobs.
LLM_MAX_TOKENS = 8192
LLM_TEMPERATURE = 0.9          # higher = more personality variety
LLM_CONCURRENCY = 4            # parallel persona expansions

# Environment variable names the kit reads keys from.
ANTHROPIC_KEY_ENV = "ANTHROPIC_API_KEY"
OPENAI_KEY_ENV = "OPENAI_API_KEY"
OPENAI_BASE_URL_ENV = "OPENAI_BASE_URL"

# ---------------------------------------------------------------------------
# Safety
# ---------------------------------------------------------------------------
# Every generated artifact is tagged so it can never be mistaken for real PII.
# This banner is embedded into text specimens and metadata.
SYNTHETIC_BANNER = "SYNTHETIC SPECIMEN — generated persona — contains no real PII"
