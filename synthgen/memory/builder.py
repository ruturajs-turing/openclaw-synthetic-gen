"""Stage 3 — structured memory. Closes the loop so memory reflects the actual generated
task history. Appends an agent-interaction-history section to MEMORY.md and writes
.mem_state.json: known facts, PII data-label refs, an appearance descriptor and TTS voice
(both deterministic, cached here for image/audio consistency in the asset stage).
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from .. import SYNTHETIC_BANNER
from ..events import Event, EventBus, EventType

# OpenAI TTS voices, split by perceived register so a persona keeps one voice.
_MALE_VOICES = ["onyx", "echo", "ash"]
_FEMALE_VOICES = ["shimmer", "nova", "sage"]
_NEUTRAL_VOICES = ["alloy", "fable"]

_HAIR = ["short", "cropped", "shoulder-length", "curly", "wavy", "straight", "tied-back"]
_BUILD = ["slim", "average", "athletic", "stocky", "tall and lean"]


def _appearance_descriptor(persona: dict, rng: random.Random) -> str:
    age = persona.get("exact_age", 40)
    gender = persona.get("gender", "person")
    culture = persona.get("cultural_background") or persona.get("primary_language") or ""
    noun = {"male": "man", "female": "woman"}.get(gender, "person")
    greying = " greying" if age >= 50 else ""
    hair = rng.choice(_HAIR)
    build = rng.choice(_BUILD)
    glasses = "wearing glasses, " if rng.random() < 0.35 else ""
    culture_str = f"{culture} " if culture else ""
    return (f"a {age}-year-old {culture_str}{noun}, {hair}{greying} hair, {build} build, "
            f"{glasses}neutral expression, plain background")


def _tts_voice(persona: dict, rng: random.Random) -> str:
    pool = {"male": _MALE_VOICES, "female": _FEMALE_VOICES}.get(persona.get("gender"), _NEUTRAL_VOICES)
    return rng.choice(pool)


def _known_facts(persona: dict) -> list[str]:
    pv = persona.get("pii_vault", {})
    facts = [
        f"name: {persona.get('full_name', persona['persona_id'])}",
        f"age {persona.get('exact_age')}, {persona.get('gender')}, lives in {persona.get('city')}",
        f"works as {persona.get('job_title')} at {pv.get('employment', {}).get('employer', '?')}",
        f"primary language: {persona.get('primary_language')}",
    ]
    diagnoses = pv.get("health", {}).get("diagnoses", [])
    if diagnoses:
        facts.append("health conditions: " + ", ".join(diagnoses))
    hobbies = [h.get("id") for h in persona.get("hobbies", {}).get("tier_1", [])]
    if hobbies:
        facts.append("main hobbies: " + ", ".join(hobbies))
    return facts


def build(run_dir: Path, persona: dict, tasks: list[dict], bus: EventBus) -> dict:
    pid = persona["persona_id"]
    pdir = run_dir / "personas" / pid
    pdir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(pid)  # deterministic per persona

    # 1. Append a synthetic agent-interaction history to MEMORY.md (task-derived).
    mem_path = pdir / "MEMORY.md"
    history = ["", "## Agent Interaction History (synthetic)", "",
               f"<!-- {SYNTHETIC_BANNER} -->", ""]
    for t in tasks:
        title = t.get("task_title", "task")
        goal = t.get("goal_summary", "")
        mf = t.get("memory_file")
        ref = f" _(ref: {mf})_" if mf else ""
        history.append(f"- **{t.get('task_id', '?')}** — {title}: {goal}{ref}")
    block = "\n".join(history) + "\n"
    if mem_path.exists():
        existing = mem_path.read_text(encoding="utf-8")
        if "## Agent Interaction History" not in existing:
            mem_path.write_text(existing.rstrip() + "\n" + block, encoding="utf-8")
    else:
        mem_path.write_text(f"# MEMORY.md - {pid}\n\n<!-- {SYNTHETIC_BANNER} -->\n" + block, encoding="utf-8")

    # 2. Machine memory state (.mem_state.json) — facts, refs, appearance, voice.
    state = {
        "persona_id": pid,
        "synthetic": True,
        "appearance_descriptor": _appearance_descriptor(persona, rng),
        "tts_voice": _tts_voice(persona, rng),
        "known_facts": _known_facts(persona),
        "data_labels": persona.get("data_labels", []),
        "sessions": [
            {"task_id": t.get("task_id"), "title": t.get("task_title"),
             "summary": t.get("goal_summary"), "memory_file": t.get("memory_file")}
            for t in tasks
        ],
        "last_session": tasks[-1].get("task_id") if tasks else None,
    }
    ws = pdir / "workspace"
    ws.mkdir(parents=True, exist_ok=True)
    (ws / ".mem_state.json").write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

    bus.emit(Event(EventType.STEP_FINISHED, stage="memory", persona_id=pid,
                   msg=f"{pid}: memory state written ({len(tasks)} sessions)"))
    return state


def build_all(run_dir: Path, personas: list[dict], tasks_map: dict[str, list[dict]],
              bus: EventBus) -> dict[str, dict]:
    out = {}
    for p in personas:
        out[p["persona_id"]] = build(run_dir, p, tasks_map.get(p["persona_id"], []), bus)
    return out
