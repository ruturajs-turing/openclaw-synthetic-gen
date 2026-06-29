# Privacy Task Generator Pipeline

Generates privacy-focused task specifications for OpenClaw Privacy trajectories. Uses LLM-based generation (Anthropic Claude / OpenAI) with embedding-based deduplication to produce diverse, high-quality tasks across 250+ personas.

## Directory Structure

```
privacy-task-generator-pipeline/
├── generate.py                  # Main CLI entry point
├── task_generator.py            # Async generation orchestrator (Anthropic + OpenAI)
├── config.py                    # Configuration (API keys, model, concurrency)
├── response_parser.py           # Parses LLM responses into structured tasks
├── embedding_store.py           # Embedding-based deduplication (LanceDB + Gemini)
├── persona_loader.py            # Loads persona definitions with data levels
├── delivery_map_loader.py       # Loads delivery mapping data
├── topic_reuse_analyzer.py      # Detects topic reuse across tasks
├── similarity.py                # Coverage matrix + deduplication logic
├── existing_seq_inventory.py    # Tracks existing task sequence numbers
├── build_cuarena_csv.py         # Builds CUArena-format CSV from outputs
├── build_skills_catalog.py      # Regenerates skills catalog from CUArena
├── seed_embeddings.py           # Seeds embedding store with existing tasks
├── update_lancedb_batches.py    # Updates LanceDB with batch data
├── requirements.txt             # Python dependencies
│
├── prompts/                     # Prompt construction
│   ├── system_prompt.py         # System prompt builder
│   ├── user_prompt.py           # User prompt builder (per-persona context)
│   ├── skills_catalog.py        # Full skills catalog (67 skills)
│   ├── skills_rich_loader.py    # Rich skill metadata loader
│   └── skills_map.py            # Skills mapping
│
├── data/                        # Reference data
│   ├── cuarena_skills.json      # Machine-readable skills catalog
│   └── docs-manifest/           # Per-persona document manifests (P-XXXX.json)
│
├── docs/                        # Documentation
│   └── CUARENA_SKILLS_CATALOG.md  # Human-readable skills reference
│
├── extracted_memories/          # Per-persona extracted memory context
│   └── P-XXXX/                  # One folder per persona
│
├── outputs/                     # Generated task outputs
│   └── batch7_memory_workspace/
│       ├── tasks_all.json       # All generated tasks (master file)
│       ├── tasks_all.csv        # Flattened CSV version
│       ├── coverage_matrix.json # Scenario x domain coverage
│       ├── cuarena_upload_*.csv # CUArena-ready upload files
│       └── tasks_by_persona/    # Per-persona task JSONs
│
└── skill (3).md                 # OpenClaw Skill Map (67 skills with full metadata)
```

## Setup

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

## Environment Variables

Create a `.env` file:

```env
ANTHROPIC_API_KEY=sk-ant-...
# Or multiple keys for higher concurrency:
ANTHROPIC_API_KEY_1=sk-ant-...
ANTHROPIC_API_KEY_2=sk-ant-...

OPENAI_API_KEY=sk-...        # Optional, for OpenAI models
GOOGLE_API_KEY=...           # Required for Gemini embeddings (dedup)

MODEL=claude-opus-4-6        # Default model
TASKS_PER_PERSONA=20         # Tasks to generate per persona
CONCURRENCY=30               # Parallel API calls
```

## Usage

```bash
# Generate tasks for all personas
python generate.py

# Dry run (print prompts without calling API)
python generate.py --dry-run --limit 2

# Resume from where you left off
python generate.py --resume

# Generate for specific personas
python generate.py --personas P-0006:P-0100

# Custom model and concurrency
python generate.py --model claude-sonnet-4-20250514 --concurrency 10
```

## Task Schema

Each generated task includes:

| Field | Description |
|-------|-------------|
| `task_id` | Unique ID (e.g., P-0006-1) |
| `persona_id` | Source persona |
| `task_title` | Short descriptive title |
| `domain` / `subdomain` | Task categorization |
| `complexity_tier` | T1 (simple) to T4 (expert) |
| `goal_summary` | What the user wants to achieve |
| `privacy_scenario` | Privacy scenario type (A-G) |
| `data_levels` | Data sensitivity levels exercised |
| `tool_tiers` | Tool complexity tiers needed |
| `expected_privacy_actions` | Privacy behaviors to evaluate |
| `pii_fields_exercised` | PII types involved |
| `conversation_arc` | Multi-turn conversation structure |
| `suggested_tools` | Recommended tools for execution |
| `openclaw_skills` | Required OpenClaw skills |
| `rubric_hints` | Evaluation rubric guidance |
| `realism_hooks` | Context for realistic scenarios |

## Pipeline Architecture

1. **Persona Loading** — Loads persona profiles with data levels and context
2. **Memory Extraction** — Pulls relevant memories per persona for grounding
3. **Prompt Construction** — Builds system + user prompts with skill catalog, persona context, and prior task awareness
4. **LLM Generation** — Calls Claude/OpenAI with structured output expectations
5. **Response Parsing** — Extracts and validates task JSON from LLM output
6. **Deduplication** — Embedding similarity check against all prior tasks (threshold: 0.80)
7. **Topic Reuse Analysis** — TF-IDF based check for thematic repetition
8. **Output Assembly** — Writes per-persona JSONs, master CSV/JSON, coverage matrix

## Key Design Decisions

- **Multi-key rotation**: Supports multiple API keys for higher throughput
- **Embedding dedup**: Uses Gemini embeddings + LanceDB for semantic similarity
- **Batch-of-5**: Generates 5 tasks per API call (4 calls per persona for 20 tasks)
- **Resume support**: Skips personas with complete output files
- **Coverage tracking**: Ensures diversity across domains, scenarios, and complexity tiers
