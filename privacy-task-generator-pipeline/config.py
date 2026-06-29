import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
PERSONAS_PATH = BASE_DIR / "personas-250-v2-textual.json"
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

def _load_all_anthropic_keys() -> list[str]:
    """Load all ANTHROPIC_API_KEY_N keys (1-indexed). Falls back to ANTHROPIC_API_KEY."""
    keys: list[str] = []
    i = 1
    while True:
        k = os.getenv(f"ANTHROPIC_API_KEY_{i}", "").strip()
        if not k:
            break
        keys.append(k)
        i += 1
    if not keys:
        k = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if k:
            keys.append(k)
    return keys

ANTHROPIC_API_KEYS: list[str] = _load_all_anthropic_keys()
ANTHROPIC_API_KEY: str = ANTHROPIC_API_KEYS[0] if ANTHROPIC_API_KEYS else ""
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
MODEL = os.getenv("MODEL", "claude-opus-4-6")
TASKS_PER_PERSONA = int(os.getenv("TASKS_PER_PERSONA", "20"))
BATCH_SIZE = 5  # tasks per API call (4 batches per persona)
CONCURRENCY = int(os.getenv("CONCURRENCY", "30"))
MAX_RETRIES = 3

# Embedding-based similarity (primary gate - semantic)
SIMILARITY_THRESHOLD = 0.80
EMBEDDING_MODEL = "gemini-embedding-001"
LANCEDB_PATH = BASE_DIR / "task_embeddings_db"
MAX_REGEN_ATTEMPTS = 3

# TF-IDF similarity (secondary safety net - keyword-based)
TFIDF_SIMILARITY_THRESHOLD = 0.75
