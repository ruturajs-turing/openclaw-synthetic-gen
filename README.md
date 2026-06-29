# OpenClaw Synthetic Gen

End-to-end synthetic-data generation for OpenClaw privacy-research personas:
**personas → privacy tasks → document/PII extraction → realistic assets (documents, images, audio) → per-persona packaging.**

All data is synthetic and fictional — every artifact carries a `SYNTHETIC SPECIMEN` marker and contains no real PII.

## Components

- **`synthgen/`** — the unified pipeline + CLI (start here). Full docs: [`synthgen/DOCS.md`](synthgen/DOCS.md).
- **`persona-generator-kit/`** — deterministic persona spine + LLM expansion (source the pipeline lifts from).
- **`privacy-task-generator-pipeline/`** — HTG privacy-task generator + the per-persona asset manifest (`data/docs-manifest/`).
- **`_pii_viewer_work/`** — Apps Script viewer for browsing generated persona folders.

## Quick start

```bash
pip install -r synthgen/requirements.txt
python -m playwright install chromium
# add keys to ./Api_Keys  (OpenAI: / Claude: / Gemini:)  — gitignored

python -m synthgen --dry-run --personas 5 --tasks 20          # cost estimate, no API calls
python -m synthgen --personas 1 --tasks 5 --budget-usd 2 --run-dir runs/demo
```

See [`synthgen/DOCS.md`](synthgen/DOCS.md) for the full command reference, stages, asset pipeline, and architecture.

## Notes

- `Api_Keys`, `runs/`, generated `outputs/`, LanceDB stores, `.zip` archives, and confidential docs are **gitignored**.
- Requires Python 3.9+, and API keys for Anthropic (tasks/personas), Google Gemini (embeddings + images), and OpenAI (TTS).
