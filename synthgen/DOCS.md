# synthgen — Full Documentation & Command Reference

End-to-end synthetic-data pipeline: **personas → tasks → document/PII extraction → assets (real-looking documents, images, audio) → per-persona packaging**, with a live console dashboard and an event bus a GUI can subscribe to.

---

## 1. Install (one-time)

```bash
cd /Users/ruturajsolanki/OpenClaw_Synthetic_Gen
pip install -r synthgen/requirements.txt        # anthropic, openai, google-genai, lancedb,
                                                 # pyarrow, numpy, rich, reportlab, playwright, opencv-python
python -m playwright install chromium            # headless browser for crisp document rendering
```

**API keys** live in the project `Api_Keys` file (label format):
```
OpenAI: sk-...
Claude: sk-ant-...
Gemini: AQ...
```
Fallback to env vars `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` (or `GOOGLE_API_KEY`).
The single Gemini key powers embeddings **and** image generation.

---

## 2. Quick start

```bash
# 1) Estimate cost first — makes NO API calls:
python -m synthgen --dry-run --personas 5 --tasks 20

# 2) Interactive run (prompts for counts, shows the live dashboard):
python -m synthgen

# 3) A safe, bounded real run:
python -m synthgen --personas 1 --tasks 5 --max-assets 8 --budget-usd 2 --run-dir runs/demo

# 4) Full gold-standard asset set for one persona (~$5 in images):
python -m synthgen --personas 1 --tasks 5 --budget-usd 6 --run-dir runs/gold
```

---

## 3. CLI reference (`python -m synthgen [flags]`)

| Flag | Default | Meaning |
|------|---------|---------|
| `--personas N` | prompts | Number of personas to generate |
| `--tasks N` | prompts | Tasks per persona (HTG privacy tasks) |
| `--seed N` | 42 | Deterministic persona-spine seed (same seed+count = same personas) |
| `--run-dir PATH` | `runs/latest` | Output directory; **resumable** — re-running skips finished work |
| `--concurrency N` | 8 | Parallel text generation (persona expand / tasks) |
| `--asset-concurrency N` | 4 | Parallel asset generation |
| `--max-assets N` | none | Cap on **paid** assets (photos + `.real` document photos) this run |
| `--budget-usd D` | none | Hard dollar ceiling; paid generation stops/falls back when reached |
| `--persona-model M` | `claude-sonnet-4-6` | Model for persona expansion |
| `--task-model M` | `claude-opus-4-8` | Model for task generation |
| `--image-model M` | `gemini-2.5-flash-image` | Nanobanana image model |
| `--tts-model M` | `gpt-4o-mini-tts` | OpenAI TTS model (audio) |
| `--minimal` | off | Generate only the curated **essential documents** (IDs, finance, health, personal) instead of the full ~457-asset manifest — far fewer assets + cost |
| `--recovery-passes N` | 3 | Auto-recovery: max passes to re-run and backfill any failed/missing personas+tasks (collects all errors) |
| `--no-recovery` | off | Disable auto-recovery (single pass only) |
| `--dry-run` | off | Walk all stages, print a cost estimate, make **zero** API calls |
| `--plain` | off | Plain log output instead of the live dashboard (use for non-TTY / logs) |
| `--yes` / `-y` | off | Skip interactive count prompts |

**Persona selection / scale examples**
```bash
python -m synthgen --personas 50 --tasks 20 --concurrency 16 --run-dir runs/batch1
python -m synthgen --dry-run --personas 250 --tasks 20      # full-scale cost estimate
```

---

## 4. What each stage does

1. **personas** — deterministic spine (demographics, Big-Five, PII vault, social graph) + LLM expansion (MEMORY.md, asset_pack, crosslinks, calendar.ics, contacts.vcf).
2. **tasks** — HTG privacy tasks. Preserves **backpropagation** (last-25 tasks fed into the next prompt for story continuity) and **gemini-embedding + LanceDB dedup** (cosine ≥ 0.80, regen up to 3×).
3. **memory** — sectioned `MEMORY.md` (task-derived history) + `.mem_state.json` (facts, appearance descriptor, TTS voice).
4. **extract** — per persona, joins the ~457-asset manifest with PII → `pii_index.json` (asset → PII fields + L0–L4 tiers).
5. **assets** — generates documents/images/audio (see §5).
6. **package** — `PROVENANCE.txt` per persona + top-level `run_manifest.json`.

---

## 5. Asset generation (how the realistic documents work)

- **Clean documents** (`<kind>.png`, `.svg`, `.pdf`) — rendered crisply via **headless Chromium (HTML/CSS)** through ~12 template families (financial, id_card, certificate, letter, invite, log_chart, medical, receipt, ticket, table, legal, generic). Sharp, legible, filled with the persona's real synthetic PII. Offline & free.
- **Photoreal documents** (`<kind>.real.png`) — the crisp render is fed **image-to-image into Nanobanana**, which re-photographs it as a casual phone photo in a real scene (desk clutter, in-hand, bedsheet, car dashboard, kitchen) per `gold.md`. Text stays legible. **Paid** (~$0.039 each). Falls back to an offline OpenCV composite when over budget / no key.
- **Faces / photos** (`assets/faces/P-XXXX.png`, family/pet/travel photos) — natural casual phone-camera portraits via Nanobanana. **Paid.** Faces are reused as the photo on ID cards.
- **Structured files** (csv/json/html/text/md) — real content (logs with realistic rows; email/diary/blog reuse the persona's written `asset_pack` bodies). Offline & free.
- **Audio** — OpenAI TTS for audio-modality assets (manifest currently has none; generator is wired).

**Cost control:** only photos + `.real` document photos are "paid". `--dry-run` estimates, `--max-assets`/`--budget-usd` bound spend, and everything is resumable.

> ⚠️ `state.cost_usd_spent` persists in `run-dir/state.json` across runs. Before a fresh budget-bounded regen of an existing run, reset that field to 0 (or use a new `--run-dir`), otherwise the budget guard may fire immediately and fall back to composites.

---

## 6. Output layout (`run-dir/`)

```
run_manifest.json          # run index: counts, models, per-persona totals, cost
state.json                 # checkpoint (resume; tracks cost + done assets)
logs/run.log               # full JSONL event stream
task_embeddings_db/        # LanceDB (gemini-embedding) — dedup state
assets/faces/P-XXXX.png    # persona portraits
assets/surfaces/P-XXXX/    # cached desk/surface photos (composite fallback)
personas/P-XXXX/
  persona.json  MEMORY.md  asset_pack.json  crosslinks.json
  tasks.json               # generated HTG privacy tasks
  pii_index.json           # every asset → its PII fields + sensitivity tiers
  PROVENANCE.txt
  workspace/  (MEMORY.md, .mem_state.json, calendar.ics, contacts.vcf, memory/, notes/)
  docs/       (<kind>.png clean, <kind>.real.png photo, .svg, .pdf, .csv, .json, .txt, .html, placeholders)
```

---

## 7. Utility commands

```bash
# Module self-checks (offline, no keys): key parsing, cost estimate, resume, manifest, backprop, dashboard
python -m synthgen.test_synthgen

# Per-module self-checks
python -m synthgen.config        # Api_Keys parser
python -m synthgen.events        # event bus
python -m synthgen.state         # checkpoint round-trip
python -m synthgen.costs         # cost estimator

# Resume an interrupted run (same command re-run skips finished work, $0 extra)
python -m synthgen --personas 10 --tasks 20 --run-dir runs/batch1   # ...re-run identical to resume

# Inspect a generated persona in the existing viewer
#   open _pii_viewer_work and point it at runs/<name>/personas/P-XXXX/
```

---

## 7b. Web GUI (operator console)

```bash
python -m synthgen.gui            # → http://127.0.0.1:8000   (SYNTHGEN_HOST / SYNTHGEN_PORT to override)
```

A dark 3-pane operator console (FastAPI backend + browser, no build step):
- **Controls** (left): personas, tasks, budget, max-assets, models; **Dry-run estimate** + **Start** + **Stop** + **Reset cost**.
- **Live dashboard** (center/right): stage pipeline, scrolling log, API-call side panel, in-flight count, cost-vs-budget bar — streamed live over SSE.
- **Persona & asset browser**: pick a persona → tabs for the document/image gallery (clean + `.real` photos), `MEMORY.md`, `tasks.json`, `pii_index.json`.

How it runs: each run is the CLI launched as a subprocess into `runs/<run_id>`; the browser tails that run's `logs/run.log` (JSONL events) over SSE. **Stop** kills the process; **Resume** = start the same `run_id` again (skips finished work); **Reset cost** zeroes `state.json` cost. Asset file serving is path-traversal-guarded to the run dir.

## 7c. Failsafe & recovery

Real runs use an **error-collecting auto-recovery** wrapper (`orchestrator.run_with_recovery`): every stage is idempotent and skips work that already exists, so the pipeline automatically re-runs up to `--recovery-passes` times to backfill anything that failed (e.g. a transient malformed-JSON or rate-limit error), stopping when complete or when a pass makes no progress. Persona expansion retries 3× (JSON + transient API errors); task generation isolates per-persona failures; `.real` image generation falls back to an offline composite on error/over-budget. Every error is collected and written to `run-dir/errors.json`, and a **final result** is written to `run-dir/final_report.json` and emitted as the closing `RUN_FINISHED` event (shown as a banner + errors panel in the GUI):

```json
{ "complete": true, "passes": 1, "personas": {"total":3,"complete":3,"failed":[]},
  "n_errors": 0, "cost_usd": 4.99 }
```

Re-running the same `run-id` always self-heals: it backfills missing personas/assets and never re-pays for completed work.

## 8. Architecture (for the GUI)

Core logic is **UI-agnostic**: it never prints — it emits `Event`s on an in-process `EventBus` (`synthgen/events.py`). Events are flat, JSON-serializable dataclasses (`type, ts, persona_id, stage, msg, data`). The console dashboard (`synthgen/ui/dashboard.py`) is just one subscriber; a GUI subscribes the same way (or via the `logs/run.log` JSONL stream / a future SSE bridge). Event types: `RUN/STAGE/STEP_*`, `API_CALL_STARTED/FINISHED`, `PERSONA_GENERATED`, `TASK_BATCH_GENERATED`, `DEDUP_FLAGGED`, `ASSET_GENERATED/SKIPPED`, `PERSONA_PACKAGED`, `COST_UPDATE`, `LOG`, `ERROR`.

Run programmatically:
```python
from synthgen.config import Settings, load_keys
from synthgen.events import EventBus
from synthgen import orchestrator

s = Settings(); s.keys = load_keys(); s.num_personas = 1; s.tasks_per_persona = 5
bus = EventBus(); bus.subscribe(lambda ev: print(ev.type, ev.msg))
orchestrator.run(s, bus)
```
```
