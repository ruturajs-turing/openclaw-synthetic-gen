# synthgen — unified synthetic data pipeline

One CLI runs the full chain end-to-end with live progress + an API-call side panel:

**personas → tasks (backprop + gemini-embedding dedup + memory) → document/PII extraction → assets (Nanobanana images, PDFs, TTS audio, structured stubs) → per-persona packaging.**

Everything is synthetic (seeded spine + LLM); every artifact carries a `SYNTHETIC SPECIMEN` marker.

## Setup

```bash
pip install -r synthgen/requirements.txt
```

Keys are read from the project `Api_Keys` file (labels `OpenAI:`, `Claude:`, `Gemini:`),
falling back to `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` env vars. The one
Gemini key serves both embeddings and image generation.

## Run

```bash
# Estimate cost first — makes NO API calls (full-manifest images are expensive):
python -m synthgen --dry-run --personas 5 --tasks 20

# Interactive: prompts for persona/task counts, shows the live dashboard:
python -m synthgen

# A safe, bounded real run (recommended first real run):
python -m synthgen --personas 1 --tasks 5 --max-assets 5 --budget-usd 2 --run-dir runs/demo
```

Key flags: `--personas N`, `--tasks N`, `--max-assets N` (cap API images/audio),
`--budget-usd D` (hard dollar ceiling), `--dry-run`, `--plain` (no dashboard),
`--run-dir PATH` (resumable), `--concurrency` / `--asset-concurrency`, `--seed`.

## Output (`run_dir/`)

```
run_manifest.json          # run index: counts, models, per-persona totals, cost
state.json                 # checkpoint (re-running skips finished work, $0 extra)
logs/run.log               # full JSONL event stream
task_embeddings_db/        # LanceDB (gemini-embedding) — dedup state, persists
assets/faces/P-XXXX.png    # persona portraits (reference for ID-doc images)
personas/P-XXXX/
  persona.json  MEMORY.md  asset_pack.json  crosslinks.json
  tasks.json               # generated privacy tasks (HTG schema)
  pii_index.json           # every asset -> its PII fields + sensitivity tiers
  PROVENANCE.txt
  workspace/  (MEMORY.md, .mem_state.json, calendar.ics, contacts.vcf, memory/, notes/)
  docs/       (images, pdfs, svgs, structured files, audio)
```

## Cost note

Full-manifest image generation is ~$5.7 per persona (147 images × ~$0.039). Always
`--dry-run` first; use `--max-assets` / `--budget-usd` to bound real runs. PDFs and
structured/SVG files are generated offline (free).

## Tests

```bash
python -m synthgen.test_synthgen     # offline self-checks (no keys/network)
```

## Architecture

Core logic is UI-agnostic: it emits events on an `EventBus`; the console dashboard is one
subscriber, so a future GUI subscribes the same way. The proven persona-spine, HTG task
prompts, response parser, and embedding-dedup logic are vendored from the original
pipelines under `personas/_*` and `tasks/_kit/` (lifted, not rewritten). New code is the
orchestrator, events/state/costs, manifest extraction, asset generators, packaging, and UI.
