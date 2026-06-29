#!/usr/bin/env python3
"""Build CUArena skills catalog (JSON + Markdown) from OpenClaw baseline sources."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
CUARENA_SKILLS = REPO / "CUArena" / "api" / "scripts" / "openclaw_skills"
TOOL_TIERS = REPO / "cuarena-pipeline" / "src" / "stage0" / "tool_tiers.json"
SKILL_MAP = REPO / "skill (3).md"
OUT_JSON = ROOT / "data" / "cuarena_skills.json"
OUT_MD = ROOT / "docs" / "CUARENA_SKILLS_CATALOG.md"

TIER_LABEL = {1: "T1 (Local)", 2: "T2 (Enterprise / 1P Cloud)", 3: "T3 (3P External)"}

# Bundled / plugin skills present in CUArena sandboxes but not in install_batch_v1.sh
EXTRA_SKILLS: list[dict] = [
    {"id": "browser-automation", "category": "Browser & Control", "source": "plugin",
     "description": "Playwright browser automation: navigate, fill forms, scrape, screenshot.",
     "path": "~/.openclaw/plugin-skills/browser-automation/SKILL.md"},
    {"id": "hatch-trust", "category": "Privacy", "source": "plugin",
     "description": "HTG reference: data classification, tool tiers, consent protocols.",
     "path": "~/.openclaw/plugin-skills/hatch-trust/SKILL.md"},
    {"id": "obsidian-vault-maintainer", "category": "Knowledge", "source": "plugin",
     "description": "Maintain Obsidian vault: links, tags, templates, daily notes.",
     "path": "~/.openclaw/plugin-skills/obsidian-vault-maintainer/SKILL.md"},
    {"id": "wiki-maintainer", "category": "Knowledge", "source": "plugin",
     "description": "Maintain OpenClaw memory wiki with source-backed updates.",
     "path": "~/.openclaw/plugin-skills/wiki-maintainer/SKILL.md"},
    {"id": "clawhub", "category": "Integrations", "source": "bundled",
     "description": "ClawHub registry client (bundled with OpenClaw npm package).",
     "path": "/usr/lib/node_modules/openclaw/skills/clawhub/SKILL.md"},
    {"id": "gh-issues", "category": "Development", "source": "bundled",
     "description": "GitHub Issues CLI workflows.",
     "path": "/usr/lib/node_modules/openclaw/skills/gh-issues/SKILL.md"},
    {"id": "node-connect", "category": "Development", "source": "bundled",
     "description": "Connect OpenClaw nodes and inspect gateway status.",
     "path": "/usr/lib/node_modules/openclaw/skills/node-connect/SKILL.md"},
    {"id": "session-logs", "category": "AI & Meta", "source": "bundled",
     "description": "Search and manage agent session logs.",
     "path": "/usr/lib/node_modules/openclaw/skills/session-logs/SKILL.md"},
    {"id": "sherpa-onnx-tts", "category": "Media", "source": "bundled",
     "description": "Local offline text-to-speech via Sherpa ONNX.",
     "path": "/usr/lib/node_modules/openclaw/skills/sherpa-onnx-tts/SKILL.md"},
    {"id": "taskflow", "category": "Automation", "source": "bundled",
     "description": "Task management: create, prioritize, schedule, delegate.",
     "path": "/usr/lib/node_modules/openclaw/skills/taskflow/SKILL.md"},
    {"id": "taskflow-inbox-triage", "category": "Automation", "source": "bundled",
     "description": "Email triage: categorize, prioritize, draft replies.",
     "path": "/usr/lib/node_modules/openclaw/skills/taskflow-inbox-triage/SKILL.md"},
    {"id": "video-frames", "category": "Media", "source": "bundled",
     "description": "Extract frames from video files.",
     "path": "/usr/lib/node_modules/openclaw/skills/video-frames/SKILL.md"},
    {"id": "summarize", "category": "Documents", "source": "bundled",
     "description": "Summarize documents, meetings, articles.",
     "path": "/usr/lib/node_modules/openclaw/skills/summarize/SKILL.md"},
    {"id": "wacli", "category": "Integrations", "source": "bundled",
     "description": "WhatsApp CLI: send/receive messages and media.",
     "path": "/usr/lib/node_modules/openclaw/skills/wacli/SKILL.md"},
    {"id": "spotify-player", "category": "Integrations", "source": "bundled",
     "description": "Spotify playback control.",
     "path": "/usr/lib/node_modules/openclaw/skills/spotify-player/SKILL.md"},
]

SOCIAL_PLUGINS = [
    {"id": "openclaw-facebook", "description": "Facebook posting and page management via ClawHub plugin."},
    {"id": "openclaw-reddit", "description": "Reddit browsing and posting via ClawHub plugin."},
    {"id": "openclaw-instagram", "description": "Instagram content workflows via ClawHub plugin."},
    {"id": "openclaw-youtube", "description": "YouTube upload and channel workflows via ClawHub plugin."},
    {"id": "openclaw-linkedin", "description": "LinkedIn posting and profile workflows via ClawHub plugin."},
]

# Short descriptions for batch skills not fully covered in skill (3).md
BATCH_DESCRIPTIONS: dict[str, str] = {
    "nano-pdf": "Extract and manipulate PDF text locally.",
    "mcporter": "Port or migrate skills between OpenClaw environments.",
    "debug-pro": "Advanced code debugging and error analysis.",
    "legaldoc-ai": "Draft legal document outlines and clauses.",
    "test-runner": "Create and run automated test suites.",
    "eventbrite": "Search and manage Eventbrite events via API gateway.",
    "workout": "Workout plans: sets, reps, exercise routines.",
    "openai-whisper": "Local speech-to-text transcription (offline).",
    "caldav-calendar": "CalDAV calendar client for personal calendar servers.",
    "skill-hub": "Browse and install ClawHub skills (excluded from strict baseline install).",
}

VERIFY_CATEGORIES: dict[str, str] = {
    "code": "Development", "debug-pro": "Development", "backend-patterns": "Development",
    "devops": "Development", "docker-essentials": "Development", "api-dev": "Development",
    "nextjs-expert": "Development", "sql-toolkit": "Development",
    "code-analysis-skills": "Development", "test-runner": "Development",
    "data-analysis": "Data & Research", "academic-research": "Data & Research",
    "stock-analysis": "Data & Research", "polymarket": "Data & Research",
    "word-docx": "Documents", "excel-xlsx": "Documents", "powerpoint-pptx": "Documents",
    "markdown-converter": "Documents", "nano-pdf": "Documents", "legaldoc-ai": "Documents",
    "ffmpeg-video-editor": "Media", "openai-whisper": "Media", "edge-tts": "Media",
    "openai-whisper-api": "Media", "openrouter-transcribe": "Media",
    "ui-ux-pro-max": "Design", "frontend-design-3": "Design",
    "mermaid-diagrams": "Design", "excalidraw": "Design",
    "automation-workflows": "Automation", "productivity": "Automation",
    "agent-team-orchestration": "Automation", "caldav-calendar": "Automation",
    "self-improving": "AI & Meta", "self-reflection": "AI & Meta",
    "humanizer": "AI & Meta", "skill-creator": "AI & Meta", "mcporter": "AI & Meta",
    "marketing-mode": "Business", "cfo": "Business",
    "language-learning": "Communication", "relationship-skills": "Communication",
    "health": "Health", "healthcheck": "Health", "workout": "Health", "mechanic": "Lifestyle",
    "weather": "Utilities", "news-summary": "Utilities", "sudoku": "Utilities",
    "ontology": "Knowledge", "flight-search": "Utilities", "plan2meal": "Utilities",
    "moltspaces": "Utilities",
    "slack": "Integrations", "notion": "Integrations", "trello": "Integrations",
    "github": "Integrations", "gog": "Integrations", "goplaces": "Integrations",
    "api-gateway": "Integrations", "eventbrite": "Integrations",
}


def _read_batch_skills() -> list[str]:
    text = (CUARENA_SKILLS / "install_batch_v1.sh").read_text(encoding="utf-8")
    match = re.search(r"SKILLS=\(\n(.*?)\n\)", text, re.S)
    if not match:
        raise SystemExit("Could not parse SKILLS from install_batch_v1.sh")
    block = match.group(1)
    return re.findall(r"[\w-]+", block)


def _read_key_requirements() -> dict[str, list[str]]:
    text = (CUARENA_SKILLS / "verify_batch_v1.py").read_text(encoding="utf-8")
    tree = ast.parse(text)
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", "") == "SKILL_KEY_REQUIREMENTS":
            return ast.literal_eval(node.value)
    return {}


def _read_tiers() -> dict[str, int]:
    data = json.loads(TOOL_TIERS.read_text(encoding="utf-8"))
    return data["tool"]


def _parse_skill_map() -> dict[str, dict[str, str]]:
    if not SKILL_MAP.exists():
        return {}
    text = SKILL_MAP.read_text(encoding="utf-8")
    entries: dict[str, dict[str, str]] = {}
    blocks = re.split(r"\n## Skill: ", text)
    for block in blocks[1:]:
        lines = block.strip().splitlines()
        skill_id = lines[0].strip()
        path = ""
        purpose = ""
        for line in lines[1:]:
            if line.startswith("**Path:**"):
                path = line.replace("**Path:**", "").strip().strip("`")
            if line.strip() == "### Purpose":
                continue
            if purpose == "" and line.strip() and not line.startswith("#") and not line.startswith("**"):
                purpose = line.strip()
                break
        entries[skill_id] = {"path": path, "description": purpose}
        if skill_id == "code-analysis":
            entries["code-analysis-skills"] = entries[skill_id].copy()
    return entries


def _read_enterprise_skills() -> list[dict]:
    base = CUARENA_SKILLS / "enterprise-skills" / "skills"
    skills = []
    for skill_dir in sorted(base.iterdir()):
        if not skill_dir.is_dir():
            continue
        md = skill_dir / "SKILL.md"
        text = md.read_text(encoding="utf-8")
        name = re.search(r"^name:\s*(.+)$", text, re.M)
        desc = re.search(r"^description:\s*(.+)$", text, re.M)
        skill_id = (name.group(1).strip() if name else skill_dir.name)
        skills.append({
            "id": skill_id,
            "folder": skill_dir.name,
            "description": (desc.group(1).strip() if desc else ""),
            "path": f"~/.openclaw/workspace/skills/{skill_dir.name}/SKILL.md",
            "source": "enterprise",
            "category": "Enterprise Odoo" if skill_id.startswith("enterprise-odoo-") else "Enterprise",
        })
    return skills


def _workspace_path(skill_id: str, source: str, folder: str = "") -> str:
    if source == "enterprise":
        return f"~/.openclaw/workspace/skills/{folder or skill_id}/SKILL.md"
    if source == "plugin":
        return EXTRA_SKILLS[[s["id"] for s in EXTRA_SKILLS].index(skill_id)]["path"]
    if source == "bundled":
        for s in EXTRA_SKILLS:
            if s["id"] == skill_id:
                return s["path"]
        return f"/usr/lib/node_modules/openclaw/skills/{skill_id}/SKILL.md"
    return f"~/.openclaw/workspace/skills/{skill_id}/SKILL.md"


def build_catalog() -> dict:
    batch = _read_batch_skills()
    tiers = _read_tiers()
    keys = _read_key_requirements()
    skill_map = _parse_skill_map()
    enterprise = _read_enterprise_skills()

    skills: list[dict] = []

    for skill_id in batch:
        meta = skill_map.get(skill_id, {})
        skills.append({
            "id": skill_id,
            "tier": tiers.get(skill_id, 1),
            "category": VERIFY_CATEGORIES.get(skill_id, "General"),
            "source": "registry_batch_v1",
            "description": meta.get("description") or BATCH_DESCRIPTIONS.get(skill_id, ""),
            "path": meta.get("path") or _workspace_path(skill_id, "registry"),
            "requires_keys": keys.get(skill_id, []),
            "in_baseline": skill_id != "skill-hub",
        })

    for ent in enterprise:
        sid = ent["id"]
        skills.append({
            "id": sid,
            "tier": tiers.get(sid, tiers.get("enterprise-mail" if sid == "enterprise-email" else sid, 2)),
            "category": ent["category"],
            "source": "enterprise",
            "description": ent["description"],
            "path": ent["path"],
            "requires_keys": keys.get(sid, keys.get(sid.replace("enterprise-email", "enterprise-mail"), ["VAULT_API_KEY", "GATEWAY_URL"])),
            "in_baseline": True,
            "aliases": ["enterprise-mail"] if sid == "enterprise-email" else [],
        })

    for extra in EXTRA_SKILLS:
        sid = extra["id"]
        skills.append({
            "id": sid,
            "tier": tiers.get(sid, 1),
            "category": extra["category"],
            "source": extra["source"],
            "description": extra["description"],
            "path": extra["path"],
            "requires_keys": keys.get(sid, []),
            "in_baseline": True,
        })

    for plugin in SOCIAL_PLUGINS:
        sid = plugin["id"]
        skills.append({
            "id": sid,
            "tier": tiers.get(sid, 3),
            "category": "Social Plugins",
            "source": "social_plugin",
            "description": plugin["description"],
            "path": f"~/.openclaw/workspace/plugins/{sid}/SKILL.md",
            "requires_keys": [],
            "in_baseline": True,
        })

    # Deduplicate by id (keep first)
    seen: set[str] = set()
    unique: list[dict] = []
    for s in skills:
        if s["id"] in seen:
            continue
        seen.add(s["id"])
        unique.append(s)

    unique.sort(key=lambda s: (s["tier"], s["category"], s["id"]))

    return {
        "version": "cuarena_baseline_v1",
        "generated_from": [
            str(CUARENA_SKILLS / "install_batch_v1.sh"),
            str(CUARENA_SKILLS / "enterprise-skills"),
            str(TOOL_TIERS),
        ],
        "workspace_paths": {
            "runtime_root": "~/.openclaw/workspace",
            "registry_skills": "~/.openclaw/workspace/skills/<skill-id>/SKILL.md",
            "enterprise_skills": "~/.openclaw/workspace/skills/<folder>/SKILL.md",
            "enterprise_source_repo": "CUArena/api/scripts/openclaw_skills/enterprise-skills/skills/",
            "installer_scripts": "~/.openclaw/workspace/tools/openclaw_skills/",
            "plugin_skills": "~/.openclaw/plugin-skills/<skill-id>/SKILL.md",
            "bundled_skills": "/usr/lib/node_modules/openclaw/skills/<skill-id>/SKILL.md",
        },
        "counts": {
            "registry_batch": len(batch),
            "enterprise": len(enterprise),
            "social_plugins": len(SOCIAL_PLUGINS),
            "extra_bundled_plugin": len(EXTRA_SKILLS),
            "total": len(unique),
        },
        "skills": unique,
    }


def render_markdown(catalog: dict) -> str:
    lines = [
        "# CUArena OpenClaw Skills Catalog",
        "",
        "Complete inventory of skills available in CUArena baseline sandboxes, for **privacy task generation** and trajectory design.",
        "",
        f"**Total skills:** {catalog['counts']['total']}  ",
        f"**Registry batch:** {catalog['counts']['registry_batch']} · **Enterprise:** {catalog['counts']['enterprise']} · **Social plugins:** {catalog['counts']['social_plugins']} · **Bundled/plugin extras:** {catalog['counts']['extra_bundled_plugin']}",
        "",
        "Regenerate: `python build_skills_catalog.py`",
        "",
        "---",
        "",
        "## Workspace paths",
        "",
        "| What | Path |",
        "| --- | --- |",
        "| Runtime workspace root | `~/.openclaw/workspace` |",
        "| Installed registry + enterprise skills | `~/.openclaw/workspace/skills/<name>/SKILL.md` |",
        "| Enterprise skill source (repo) | `CUArena/api/scripts/openclaw_skills/enterprise-skills/skills/` |",
        "| Install scripts (in sandbox) | `~/.openclaw/workspace/tools/openclaw_skills/` |",
        "| Plugin skills | `~/.openclaw/plugin-skills/<name>/SKILL.md` |",
        "| Bundled npm skills | `/usr/lib/node_modules/openclaw/skills/<name>/SKILL.md` |",
        "",
        "## Trust tiers (for task design)",
        "",
        "| Tier | Label | Task-gen note |",
        "| --- | --- | --- |",
        "| **T1** | Local | Safe for L0–L4; prefer for sensitive persona data. |",
        "| **T2** | Enterprise / 1P cloud | Requires `VAULT_API_KEY` + `GATEWAY_URL` from assigned persona. L3/L4 needs consent. |",
        "| **T3** | 3P external | L1 only by default; L2+ requires explicit consent gate in task. |",
        "",
        "## Task generation usage",
        "",
        "When generating tasks (`openclaw_skills` field):",
        "",
        "1. Pick **1–3 skill IDs** from the tables below (use the `id` column exactly).",
        "2. Use **at least 10 different skills** across 20 tasks per persona.",
        "3. For **T3 skills**, include a `consent_gate` or `hard_block` in `expected_privacy_actions`.",
        "4. Prefer **T2 enterprise** skills (`enterprise-*`) over T3 equivalents when the persona has enterprise access (e.g. `enterprise-calendar` instead of `caldav-calendar`).",
        "5. Machine-readable list: [`data/cuarena_skills.json`](../data/cuarena_skills.json).",
        "",
        "---",
        "",
    ]

    by_tier: dict[int, list[dict]] = {1: [], 2: [], 3: []}
    for s in catalog["skills"]:
        by_tier.setdefault(s["tier"], []).append(s)

    for tier in (1, 2, 3):
        items = by_tier.get(tier, [])
        lines += [f"## {TIER_LABEL[tier]} ({len(items)} skills)", ""]
        lines += ["| ID | Category | Source | Description | Keys |", "| --- | --- | --- | --- | --- |"]
        for s in items:
            keys = ", ".join(s["requires_keys"]) if s["requires_keys"] else "—"
            desc = (s["description"] or "—")[:120].replace("|", "/")
            lines.append(f"| `{s['id']}` | {s['category']} | {s['source']} | {desc} | {keys} |")
        lines.append("")

    lines += [
        "---",
        "",
        "## Excluded from strict baseline",
        "",
        "| Skill | Reason |",
        "| --- | --- |",
        "| `skill-hub` | ClawHub download blocked by VirusTotal flag in shared snapshot |",
        "",
        "## Aliases",
        "",
        "| Use in tasks | Also known as |",
        "| --- | --- |",
        "| `enterprise-email` | `enterprise-mail` |",
        "| `code-analysis-skills` | `code-analysis` |",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    catalog = build_catalog()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    OUT_MD.write_text(render_markdown(catalog), encoding="utf-8")
    print(f"Wrote {OUT_JSON} ({catalog['counts']['total']} skills)")
    print(f"Wrote {OUT_MD}")


if __name__ == "__main__":
    main()
