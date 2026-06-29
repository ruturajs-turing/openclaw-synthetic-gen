#!/usr/bin/env python3
"""
STAGE 2 — Expand persona spines into full workspace trees (LLM-driven).

For each persona in personas.json this:
  1. Builds a compact text "brief" from the spine.
  2. Asks an LLM for ONE JSON "life pack" (bio, journal, notes, asset_pack,
     crosslinks) — see prompts/artifact_prompts.py.
  3. Deterministically writes the on-disk workspace tree from that life pack,
     and builds calendar.ics + contacts.vcf in code.

Output layout (mirrors the extracted persona set):
  output/personas/P-0001/
    persona.json                      <- copy of the spine record
    MEMORY.md                         <- bio + dated journal
    asset_pack.json                   <- everyday-artifact text bodies
    crosslinks.json                   <- shared events with connected personas
    workspace/
      calendar.ics                    <- built in code from journal + birthday
      contacts.vcf                    <- built in code from self + connections
      memory/<date>.md                <- one file per journal entry
      memory/<date>.crosslink.md      <- one file per shared event
      notes/{journal_longform,hobby_log,reading_highlights,todo_list}.md

Usage
-----
    # See the exact prompt without spending tokens:
    python expand_persona.py --dry-run --limit 1

    # Expand the first 5 personas with Anthropic (needs ANTHROPIC_API_KEY):
    export ANTHROPIC_API_KEY=sk-ant-...
    python expand_persona.py --limit 5

    # Expand everything, 4 in parallel:
    python expand_persona.py --concurrency 4

    # Use an OpenAI-compatible endpoint (e.g. OpenRouter):
    export OPENAI_API_KEY=...; export OPENAI_BASE_URL=https://openrouter.ai/api/v1
    python expand_persona.py --provider openai --model anthropic/claude-sonnet-4
"""

import argparse
import hashlib
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from . import _kitconfig as config
from ._prompts import SYSTEM_PROMPT, build_life_pack_prompt
from ._prompts.artifact_prompts import schema_as_text


# ---------------------------------------------------------------------------
# Persona brief (text injected into the prompt)
# ---------------------------------------------------------------------------
def persona_brief(p: dict, id_to_name: dict) -> str:
    pv = p.get("pii_vault", {})
    platforms = sorted(k for k, v in p.get("platform_presence", {}).items() if v)
    t1 = ", ".join(h["id"] for h in p.get("hobbies", {}).get("tier_1", []))
    t3 = ", ".join(h["id"] for h in p.get("hobbies", {}).get("tier_3", []))
    conns = []
    for c in p.get("connections", []):
        nm = id_to_name.get(c["persona_id"], c["persona_id"])
        conns.append(f"{c['type']} -> {nm} ({c['persona_id']})")
    pers = p.get("personality", {})
    big5 = ", ".join(f"{k[:1].upper()}{v:.2f}" for k, v in pers.items()
                     if k in ("openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"))
    lines = [
        f"persona_id: {p['persona_id']}",
        f"name: {p.get('full_name') or (p['first_name'] + ' ' + p['last_name'])}",
        f"age {p['exact_age']} ({p['generation_label']}), {p['gender']}, {p['city']}",
        f"culture/language: {p['cultural_background']} / {p['primary_language']}",
        f"job: {p['job_title']} at {pv.get('employment', {}).get('employer', '?')} ({p['occupation_sector']}, {p['remote_work']})",
        f"education: {p['education_level']}",
        f"household: {p['marital_status']}, size {p['household_size']}, children {p['children_count']}",
        f"personality: MBTI {p.get('mbti','?')} | Big5 {big5}",
        f"digital intensity {pers.get('digital_engagement_intensity')}, creation propensity {pers.get('content_creation_propensity')}",
        f"platforms: {', '.join(platforms)}",
        f"hobbies (passions): {t1}",
        f"life-admin topics: {t3}",
        f"connections: {'; '.join(conns) if conns else 'none'}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# LLM clients
# ---------------------------------------------------------------------------
def call_anthropic(system: str, user: str, model: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ[config.ANTHROPIC_KEY_ENV])
    resp = client.messages.create(
        model=model,
        max_tokens=config.LLM_MAX_TOKENS,
        temperature=config.LLM_TEMPERATURE,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")


def call_openai(system: str, user: str, model: str) -> str:
    from openai import OpenAI
    client = OpenAI(
        api_key=os.environ[config.OPENAI_KEY_ENV],
        base_url=os.environ.get(config.OPENAI_BASE_URL_ENV) or None,
    )
    resp = client.chat.completions.create(
        model=model,
        max_tokens=config.LLM_MAX_TOKENS,
        temperature=config.LLM_TEMPERATURE,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    return resp.choices[0].message.content


def llm_call(system, user, provider, model):
    return call_openai(system, user, model) if provider == "openai" else call_anthropic(system, user, model)


def parse_json_object(text: str) -> dict:
    """Tolerant JSON extraction (handles stray markdown fences/prose)."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.lstrip().startswith("json"):
            text = text.lstrip()[4:]
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end + 1]
    return json.loads(text)


# ---------------------------------------------------------------------------
# Deterministic file builders
# ---------------------------------------------------------------------------
def _uid(*parts) -> str:
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:16] + "@personas.local"


def build_calendar_ics(p: dict, journal: list, crosslinks: list) -> str:
    name = p.get("full_name", p["persona_id"])
    out = ["BEGIN:VCALENDAR", "VERSION:2.0",
           "PRODID:-//persona-generator-kit//life-calendar 1.0//EN", "CALSCALE:GREGORIAN"]
    dob = p.get("date_of_birth", "1990-01-01").replace("-", "")
    out += ["BEGIN:VEVENT", f"UID:{_uid(p['persona_id'],'bday')}",
            "DTSTAMP:20250101T000000Z", f"DTSTART;VALUE=DATE:{dob}",
            "RRULE:FREQ=YEARLY", "SUMMARY:My birthday", "END:VEVENT"]
    for e in journal:
        d = e.get("date", "").replace("-", "")
        if len(d) == 8:
            title = (e.get("text", "")[:48] or "Journal entry").replace("\n", " ")
            out += ["BEGIN:VEVENT", f"UID:{_uid(p['persona_id'], d)}",
                    "DTSTAMP:20250101T000000Z", f"DTSTART;VALUE=DATE:{d}",
                    f"SUMMARY:{title}", "CATEGORIES:LIFE-EVENT", "END:VEVENT"]
    for link in crosslinks:
        for ev in link.get("events", []):
            d = ev.get("date", "").replace("-", "")
            if len(d) == 8:
                out += ["BEGIN:VEVENT", f"UID:{_uid(p['persona_id'], link.get('with',''), d)}",
                        "DTSTAMP:20250101T000000Z", f"DTSTART;VALUE=DATE:{d}",
                        f"SUMMARY:{ev.get('title','Shared event')} (with {link.get('with_name','')})",
                        "CATEGORIES:SOCIAL", "END:VEVENT"]
    out.append("END:VCALENDAR")
    return "\n".join(out) + "\n"


def build_contacts_vcf(p: dict, all_personas: dict) -> str:
    def card(full, org, email, tel, note):
        parts = full.split()
        given = parts[0] if parts else full
        family = parts[-1] if len(parts) > 1 else ""
        return ("BEGIN:VCARD\nVERSION:4.0\n"
                f"FN:{full}\nN:{family};{given};;;\n"
                f"ORG:{org}\nEMAIL:{email}\nTEL;TYPE=cell:{tel}\n"
                f"NOTE:{note}\nEND:VCARD")
    pv = p.get("pii_vault", {})
    cards = [card(p.get("full_name", p["persona_id"]),
                  pv.get("employment", {}).get("employer", ""),
                  p.get("email_synthetic", ""),
                  pv.get("contacts", {}).get("phone", ""), "self")]
    for c in p.get("connections", []):
        other = all_personas.get(c["persona_id"])
        if other:
            cards.append(card(other.get("full_name", c["persona_id"]),
                              other.get("pii_vault", {}).get("employment", {}).get("employer", ""),
                              other.get("email_synthetic", ""),
                              other.get("pii_vault", {}).get("contacts", {}).get("phone", ""),
                              c["type"]))
    return "\n".join(cards) + "\n"


def write_workspace(out_root: Path, p: dict, pack: dict, all_personas: dict):
    pdir = out_root / "personas" / p["persona_id"]
    ws = pdir / "workspace"
    (ws / "memory").mkdir(parents=True, exist_ok=True)
    (ws / "notes").mkdir(parents=True, exist_ok=True)

    (pdir / "persona.json").write_text(json.dumps(p, indent=2, ensure_ascii=False), encoding="utf-8")

    # MEMORY.md = bio + dated journal
    name = p.get("full_name", p["persona_id"])
    mem = [f"# MEMORY.md - {name} ({p['persona_id']})", "",
           f"<!-- {config.SYNTHETIC_BANNER} -->", "", pack.get("bio", ""), ""]
    journal = sorted(pack.get("journal", []), key=lambda e: e.get("date", ""))
    for e in journal:
        mem.append(f"## {e.get('date','')}\n{e.get('text','')}\n")
    (pdir / "MEMORY.md").write_text("\n".join(mem), encoding="utf-8")

    # Per-day memory files
    for e in journal:
        d = e.get("date")
        if d:
            (ws / "memory" / f"{d}.md").write_text(
                f"# {d}\n\n{e.get('text','')}\n", encoding="utf-8")

    # Notes
    notes = pack.get("notes", {})
    for key, fname in [("journal_longform", "journal_longform.md"),
                       ("hobby_log", "hobby_log.md"),
                       ("reading_highlights", "reading_highlights.md"),
                       ("todo_list", "todo_list.md")]:
        if notes.get(key):
            (ws / "notes" / fname).write_text(notes[key] + "\n", encoding="utf-8")

    # Asset pack
    ap = dict(pack.get("asset_pack", {}))
    ap["_note"] = config.SYNTHETIC_BANNER
    (pdir / "asset_pack.json").write_text(json.dumps(ap, indent=2, ensure_ascii=False), encoding="utf-8")

    # Crosslinks (+ per-event markdown)
    crosslinks = pack.get("crosslinks", [])
    (pdir / "crosslinks.json").write_text(
        json.dumps({"persona": p["persona_id"], "links": crosslinks}, indent=2, ensure_ascii=False),
        encoding="utf-8")
    for link in crosslinks:
        for ev in link.get("events", []):
            d = ev.get("date")
            if d:
                (ws / "memory" / f"{d}.crosslink.md").write_text(
                    f"# {d} - with {link.get('with_name','')} (SYNTHETIC crosslink)\n"
                    f"- **{ev.get('type','event')}** at {ev.get('location','')}: {ev.get('summary','')}\n",
                    encoding="utf-8")

    # Deterministic structured files
    (ws / "calendar.ics").write_text(build_calendar_ics(p, journal, crosslinks), encoding="utf-8")
    (ws / "contacts.vcf").write_text(build_contacts_vcf(p, all_personas), encoding="utf-8")


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def expand_one(p, id_to_name, all_personas, args):
    brief = persona_brief(p, id_to_name)
    user = build_life_pack_prompt(brief, schema_as_text())

    if args.dry_run:
        print("=" * 70)
        print(f"# DRY RUN — {p['persona_id']} {p.get('full_name','')}")
        print("=" * 70)
        print("--- SYSTEM ---\n" + SYSTEM_PROMPT)
        print("--- USER ---\n" + user)
        return p["persona_id"], "dry-run"

    model = args.model or (config.OPENAI_MODEL if args.provider == "openai" else config.ANTHROPIC_MODEL)
    raw = llm_call(SYSTEM_PROMPT, user, args.provider, model)
    try:
        pack = parse_json_object(raw)
    except json.JSONDecodeError:
        # Save the raw model output so the failure can be inspected, then re-raise.
        dbg = args.workspace_root / "_failed"
        dbg.mkdir(parents=True, exist_ok=True)
        (dbg / f"{p['persona_id']}.raw.txt").write_text(raw, encoding="utf-8")
        raise
    write_workspace(args.workspace_root, p, pack, all_personas)
    return p["persona_id"], "ok"


def main():
    ap = argparse.ArgumentParser(description="Stage 2: expand persona spines into workspace trees (LLM).")
    ap.add_argument("--spine", type=Path, default=config.DEFAULT_SPINE_PATH)
    ap.add_argument("--workspace-root", type=Path, default=config.DEFAULT_WORKSPACE_ROOT)
    ap.add_argument("--provider", choices=["anthropic", "openai"], default=config.LLM_PROVIDER)
    ap.add_argument("--model", default=None)
    ap.add_argument("--limit", type=int, default=0, help="Only expand the first N personas (0 = all).")
    ap.add_argument("--only", default="", help="Comma-separated persona ids to expand (e.g. P-0001,P-0002).")
    ap.add_argument("--concurrency", type=int, default=config.LLM_CONCURRENCY)
    ap.add_argument("--resume", action="store_true", help="Skip personas that already have MEMORY.md.")
    ap.add_argument("--dry-run", action="store_true", help="Print prompts; never call the API.")
    args = ap.parse_args()

    if not args.spine.exists():
        sys.exit(f"Spine not found: {args.spine}. Run generate_spine.py first.")
    personas = json.load(open(args.spine, encoding="utf-8"))["personas"]
    all_personas = {p["persona_id"]: p for p in personas}
    id_to_name = {pid: p.get("full_name", pid) for pid, p in all_personas.items()}

    if args.only:
        wanted = {s.strip() for s in args.only.split(",")}
        personas = [p for p in personas if p["persona_id"] in wanted]
    if args.limit:
        personas = personas[:args.limit]
    if args.resume:
        personas = [p for p in personas
                    if not (args.workspace_root / "personas" / p["persona_id"] / "MEMORY.md").exists()]

    print(f"Expanding {len(personas)} personas "
          f"({'DRY RUN' if args.dry_run else args.provider}) -> {args.workspace_root}")

    if args.dry_run or args.concurrency <= 1:
        for p in personas:
            pid_, status = expand_one(p, id_to_name, all_personas, args)
            if not args.dry_run:
                print(f"  {pid_}: {status}")
        return

    ok = err = 0
    with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
        futs = {ex.submit(expand_one, p, id_to_name, all_personas, args): p for p in personas}
        for fut in as_completed(futs):
            pid_ = futs[fut]["persona_id"]
            try:
                fut.result()
                ok += 1
                print(f"  {pid_}: ok ({ok}/{len(personas)})")
            except Exception as e:  # noqa: BLE001
                err += 1
                print(f"  {pid_}: ERROR {type(e).__name__}: {e}")
    print(f"Done. ok={ok} err={err}")


if __name__ == "__main__":
    main()
