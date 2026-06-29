"""FastAPI backend for the synthgen operator console.

Run model: each run is the existing CLI launched as a subprocess into `runs/<id>`, which
writes a JSONL event log (`logs/run.log`). The browser streams that log via SSE. This reuses
the CLI verbatim, makes Stop a real process kill, and Resume just a re-run of the same command.
Dry-run estimates are computed in-process (no subprocess, no network).
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from ..config import PROJECT_ROOT, Settings, load_keys
from .. import orchestrator

RUNS_DIR = PROJECT_ROOT / "runs"
STATIC = Path(__file__).parent / "static"

app = FastAPI(title="Openclaw SynthGen v3.0")
_procs: dict[str, subprocess.Popen] = {}  # run_id -> process


# ---------------- helpers ----------------
def _rid(run_id: str) -> str:
    """Canonical run id — strip to a safe slug. Used identically for the process map AND the
    run dir so a run id with spaces (e.g. 'Test 2') can't desync the two."""
    return "".join(c for c in str(run_id) if c.isalnum() or c in "-_") or "gui"


def _run_dir(run_id: str) -> Path:
    return RUNS_DIR / _rid(run_id)  # _rid also guards against path traversal


def _settings_from(body: dict) -> Settings:
    s = Settings()
    s.keys = load_keys()
    s.num_personas = int(body.get("personas", 1))
    s.tasks_per_persona = int(body.get("tasks", 5))
    if body.get("budget_usd") not in (None, ""):
        s.budget_usd = float(body["budget_usd"])
    if body.get("max_assets") not in (None, ""):
        s.max_assets = int(body["max_assets"])
    for m in ("persona_model", "task_model", "image_model", "tts_model"):
        if body.get(m):
            setattr(s, m, body[m])
    if body.get("doc_set") == "minimal" or body.get("minimal"):
        s.doc_set = "minimal"
    if body.get("seed") not in (None, ""):
        s.seed = int(body["seed"])
    s.run_dir = _run_dir(body.get("run_id", "gui"))
    s.dry_run = bool(body.get("dry_run"))
    return s


# ---------------- pages / static ----------------
@app.get("/", response_class=HTMLResponse)
def index():
    return (STATIC / "index.html").read_text(encoding="utf-8")


app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


# ---------------- run control ----------------
_MODELS_CACHE: dict = {}


def _tier(mid: str) -> str:
    s = mid.lower()
    if "opus" in s:
        return "max quality"
    if "sonnet" in s:
        return "balanced"
    if "haiku" in s:
        return "fast / cheap"
    if s.startswith(("o1", "o3", "o4")):
        return "reasoning (OpenAI)"
    if "mini" in s or "nano" in s:
        return "fast (OpenAI)"
    if s.startswith("gpt-5") or s.startswith("gpt-4.1"):
        return "max (OpenAI)"
    if "gpt-4o" in s or s.startswith("gpt-4"):
        return "balanced (OpenAI)"
    if s.startswith(("gpt", "chatgpt")):
        return "OpenAI"
    return ""


def _fetch_models() -> dict:
    if _MODELS_CACHE.get("data"):
        return _MODELS_CACHE["data"]
    keys = load_keys()
    text, image, tts, errors = [], [], [], {}
    # Anthropic — persona/task models (the pipeline calls Anthropic for text)
    try:
        import anthropic
        for m in anthropic.Anthropic(api_key=keys.get("anthropic", "")).models.list(limit=100).data:
            text.append({"id": m.id, "label": getattr(m, "display_name", m.id) or m.id, "tier": _tier(m.id)})
    except Exception as e:  # noqa: BLE001
        errors["anthropic"] = str(e)[:160]
    # OpenAI — chat models (persona/task alternatives) + TTS models
    try:
        from openai import OpenAI
        _skip = ("embedding", "whisper", "dall-e", "image", "realtime", "moderation",
                 "transcribe", "search", "instruct", "audio", "tts", "davinci", "babbage")
        for m in OpenAI(api_key=keys.get("openai", "")).models.list().data:
            mid = m.id
            low = mid.lower()
            dated = any(seg.isdigit() and len(seg) == 4 for seg in low.split("-"))  # snapshot suffix
            if "tts" in low or ("audio" in low and "speech" in low):
                if not dated:
                    tts.append({"id": mid, "label": mid})
            elif low.startswith(("gpt", "o1", "o3", "o4", "chatgpt")) and not dated and not any(x in low for x in _skip):
                text.append({"id": mid, "label": mid, "tier": _tier(mid)})
    except Exception as e:  # noqa: BLE001
        errors["openai"] = str(e)[:160]
    # Gemini — image-generation models (bind client to a var so it isn't GC'd mid-iteration)
    try:
        from google import genai
        gc = genai.Client(api_key=keys.get("gemini", ""))
        for m in list(gc.models.list()):
            name = (getattr(m, "name", "") or "").replace("models/", "")
            actions = getattr(m, "supported_actions", None) or getattr(m, "supported_generation_methods", []) or []
            if "embedding" in name:
                continue
            if "image" in name or "imagen" in name or any("image" in str(a).lower() for a in actions):
                image.append({"id": name, "label": name})
    except Exception as e:  # noqa: BLE001
        errors["gemini"] = str(e)[:160]

    def _pick(ids, *prefs):
        for p in prefs:
            for i in ids:
                if p == i:
                    return i
        for p in prefs:
            for i in ids:
                if p in i:
                    return i
        return ids[0] if ids else None

    tids, iids, ttids = [t["id"] for t in text], [x["id"] for x in image], [x["id"] for x in tts]
    recommended = {
        "task": _pick(tids, "claude-opus-4-8", "opus") or "claude-opus-4-8",
        "persona": _pick(tids, "claude-sonnet-4-6", "sonnet") or "claude-sonnet-4-6",
        "image": _pick(iids, "gemini-2.5-flash-image", "flash-image", "image") or "gemini-2.5-flash-image",
        "tts": _pick(ttids, "gpt-4o-mini-tts", "tts") or "gpt-4o-mini-tts",
    }
    # tier order: opus, sonnet, haiku, then the rest (newest-ish first)
    order = {"max quality": 0, "balanced": 1, "fast / cheap": 2, "": 3}
    text.sort(key=lambda t: (order.get(t["tier"], 3), t["id"]), reverse=False)
    data = {"text": text, "image": image, "tts": tts, "recommended": recommended, "errors": errors}
    if not errors:  # don't cache a partial/failed fetch — let it retry next call
        _MODELS_CACHE["data"] = data
    return data


@app.get("/models")
def models():
    return JSONResponse(_fetch_models())


@app.post("/estimate")
async def estimate(body: dict):
    s = _settings_from(body)
    return JSONResponse(orchestrator.estimate(s))


@app.post("/run")
async def run(body: dict):
    run_id = _rid(body.get("run_id", "gui"))
    rd = _run_dir(run_id)
    if run_id in _procs and _procs[run_id].poll() is None:
        raise HTTPException(409, "run already in progress")
    args = [sys.executable, "-m", "synthgen", "--plain", "--yes",
            "--run-dir", str(rd),
            "--personas", str(int(body.get("personas", 1))),
            "--tasks", str(int(body.get("tasks", 5)))]
    if body.get("budget_usd") not in (None, ""):
        args += ["--budget-usd", str(float(body["budget_usd"]))]
    if body.get("max_assets") not in (None, ""):
        args += ["--max-assets", str(int(body["max_assets"]))]
    for flag, key in (("--persona-model", "persona_model"), ("--task-model", "task_model"),
                      ("--image-model", "image_model"), ("--tts-model", "tts_model")):
        if body.get(key):
            args += [flag, body[key]]
    if body.get("doc_set") == "minimal" or body.get("minimal"):
        args += ["--minimal"]
    if body.get("seed") not in (None, ""):
        args += ["--seed", str(int(body["seed"]))]
    (rd / "logs").mkdir(parents=True, exist_ok=True)
    # fresh event log per launch so SSE starts clean
    (rd / "logs" / "run.log").write_text("", encoding="utf-8")
    # capture stderr so a crash is visible (logs/proc.err) instead of vanishing
    errf = open(rd / "logs" / "proc.err", "w")
    _procs[run_id] = subprocess.Popen(args, cwd=str(PROJECT_ROOT),
                                      stdout=subprocess.DEVNULL, stderr=errf,
                                      start_new_session=True)
    return {"run_id": run_id, "pid": _procs[run_id].pid}


@app.post("/stop")
async def stop(body: dict):
    run_id = _rid(body.get("run_id", "gui"))
    p = _procs.get(run_id)
    if p and p.poll() is None:
        try:
            os.killpg(os.getpgid(p.pid), signal.SIGTERM)
        except Exception:
            p.terminate()
        return {"stopped": True}
    return {"stopped": False}


@app.post("/reset-cost")
async def reset_cost(body: dict):
    rd = _run_dir(str(body.get("run_id", "gui")))
    sp = rd / "state.json"
    if sp.exists():
        d = json.loads(sp.read_text())
        d["cost_usd_spent"] = 0.0
        sp.write_text(json.dumps(d, indent=2))
        return {"reset": True}
    return {"reset": False}


# ---------------- live event stream (tail the JSONL log) ----------------
@app.get("/events")
async def events(run_id: str = "gui"):
    run_id = _rid(run_id)          # match the id used by /run (handles spaces, etc.)
    rd = _run_dir(run_id)
    log = rd / "logs" / "run.log"

    async def gen():
        last = 0
        # wait briefly for the log to appear
        for _ in range(50):
            if log.exists():
                break
            await asyncio.sleep(0.1)
        idle = 0
        while True:
            if log.exists():
                data = log.read_text(encoding="utf-8")
                if len(data) > last:
                    chunk = data[last:]
                    last = len(data)
                    for line in chunk.splitlines():
                        line = line.strip()
                        if line:
                            yield f"data: {line}\n\n"
                    idle = 0
            p = _procs.get(run_id)
            running = p is not None and p.poll() is None
            if not running:
                idle += 1
                if idle > 6:  # process gone and no new output → close stream
                    yield 'data: {"type":"stream_end"}\n\n'
                    return
            await asyncio.sleep(0.4)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ---------------- persona / asset browser ----------------
@app.get("/runs")
def list_runs():
    if not RUNS_DIR.exists():
        return {"runs": []}
    out = []
    for d in sorted(RUNS_DIR.iterdir()):
        if (d / "state.json").exists() or (d / "personas").exists():
            mf = d / "run_manifest.json"
            totals = json.loads(mf.read_text()).get("totals", {}) if mf.exists() else {}
            out.append({"run_id": d.name, "totals": totals})
    return {"runs": out}


@app.get("/personas")
def personas(run_id: str = "gui"):
    rd = _run_dir(run_id)
    pdir = rd / "personas"
    if not pdir.exists():
        return {"personas": []}
    out = []
    for d in sorted(pdir.iterdir()):
        if not d.is_dir():
            continue
        name = d.name
        face = rd / "assets" / "faces" / f"{name}.png"
        try:
            persona = json.loads((d / "persona.json").read_text())
            full = persona.get("full_name", name)
        except Exception:
            full = name
        ntasks = 0
        if (d / "tasks.json").exists():
            try:
                ntasks = len(json.loads((d / "tasks.json").read_text()))
            except Exception:
                pass
        ndocs = len(list((d / "docs").iterdir())) if (d / "docs").is_dir() else 0
        out.append({"persona_id": name, "name": full, "n_tasks": ntasks, "n_docs": ndocs,
                    "has_face": face.exists()})
    return {"personas": out}


@app.get("/persona/{pid}")
def persona_detail(pid: str, run_id: str = "gui"):
    rd = _run_dir(run_id)
    pid = "".join(c for c in pid if c.isalnum() or c in "-_")
    d = rd / "personas" / pid
    if not d.is_dir():
        raise HTTPException(404, "persona not found")

    def _read_json(p):
        try:
            return json.loads(p.read_text()) if p.exists() else None
        except Exception:
            return None

    docs = []
    if (d / "docs").is_dir():
        for f in sorted((d / "docs").iterdir()):
            if f.is_file():
                docs.append({"name": f.name, "ext": f.suffix.lower().lstrip("."),
                             "url": f"/asset?run_id={run_id}&path=personas/{pid}/docs/{f.name}"})
    mem = (d / "MEMORY.md")
    face = rd / "assets" / "faces" / f"{pid}.png"
    return {
        "persona_id": pid,
        "persona": _read_json(d / "persona.json"),
        "tasks": _read_json(d / "tasks.json"),
        "pii_index": _read_json(d / "pii_index.json"),
        "memory_md": mem.read_text(encoding="utf-8") if mem.exists() else "",
        "face_url": f"/asset?run_id={run_id}&path=assets/faces/{pid}.png" if face.exists() else None,
        "docs": docs,
    }


@app.get("/asset")
def asset(run_id: str = "gui", path: str = ""):
    rd = _run_dir(run_id).resolve()
    target = (rd / path).resolve()
    if not str(target).startswith(str(rd)) or not target.is_file():
        raise HTTPException(404, "asset not found")
    return FileResponse(str(target))


def main():
    import uvicorn
    RUNS_DIR.mkdir(exist_ok=True)
    host = os.getenv("SYNTHGEN_HOST", "127.0.0.1")
    port = int(os.getenv("SYNTHGEN_PORT", "8000"))
    print(f"Openclaw SynthGen v3.0 → http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    main()
