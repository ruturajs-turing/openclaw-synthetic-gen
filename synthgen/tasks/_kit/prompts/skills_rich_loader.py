"""Parse to_riju/skills.md into structured skill descriptions.

Provides rich Purpose + Capabilities + Tools for each of the 67 skills,
used to build more detailed prompt sections than the one-liner catalog.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

SKILLS_MD_PATH = Path(__file__).parent.parent / "skill (3).md"

_RICH_SKILLS: dict[str, dict[str, str]] | None = None


def _parse_skills_md(path: Path | None = None) -> dict[str, dict[str, str]]:
    """Parse skills.md into {skill_name: {purpose, tools, capabilities, requirements, output}}."""
    path = path or SKILLS_MD_PATH
    if not path.exists():
        return {}

    text = path.read_text(encoding="utf-8")
    skills: dict[str, dict[str, str]] = {}
    current_skill: str | None = None
    current_section: str | None = None
    section_lines: list[str] = []

    for line in text.split("\n"):
        skill_match = re.match(r"^## Skill:\s+(.+)$", line)
        if skill_match:
            if current_skill and current_section and section_lines:
                skills.setdefault(current_skill, {})[current_section] = "\n".join(section_lines).strip()
            current_skill = skill_match.group(1).strip()
            current_section = None
            section_lines = []
            continue

        section_match = re.match(r"^### (Purpose|Tools Used|Capabilities|Requirements|Output)$", line)
        if section_match:
            if current_skill and current_section and section_lines:
                skills.setdefault(current_skill, {})[current_section] = "\n".join(section_lines).strip()
            current_section = section_match.group(1).lower().replace(" ", "_")
            section_lines = []
            continue

        if line.startswith("**Path:**"):
            continue

        if current_skill and current_section:
            section_lines.append(line)

    if current_skill and current_section and section_lines:
        skills.setdefault(current_skill, {})[current_section] = "\n".join(section_lines).strip()

    return skills


def get_rich_skills() -> dict[str, dict[str, str]]:
    """Load and cache the rich skill descriptions."""
    global _RICH_SKILLS
    if _RICH_SKILLS is None:
        _RICH_SKILLS = _parse_skills_md()
    return _RICH_SKILLS


def get_skill_detail(skill_name: str) -> str:
    """Get a compact rich description for a single skill (Purpose + key Capabilities)."""
    skills = get_rich_skills()
    info = skills.get(skill_name)
    if not info:
        return ""

    parts = []
    purpose = info.get("purpose", "")
    if purpose:
        # Truncate to first 2 sentences or 200 chars
        sentences = re.split(r"(?<=[.!?])\s+", purpose)
        short_purpose = " ".join(sentences[:2])
        if len(short_purpose) > 250:
            short_purpose = short_purpose[:247] + "..."
        parts.append(f"Purpose: {short_purpose}")

    caps = info.get("capabilities", "")
    if caps:
        cap_items = [line.strip("- ").strip() for line in caps.split("\n") if line.strip().startswith("-")]
        if cap_items:
            top_caps = [re.sub(r"\*\*([^*]+)\*\*", r"\1", c)[:100] for c in cap_items[:5]]
            parts.append("Can: " + " | ".join(top_caps))

    tools = info.get("tools_used", "")
    if tools:
        tool_items = [line.strip("- ").strip() for line in tools.split("\n") if line.strip().startswith("-")]
        if tool_items:
            cleaned = []
            for t in tool_items[:4]:
                name = t.split("—")[0].strip().strip("`").strip("*").strip()
                if name:
                    cleaned.append(name)
            if cleaned:
                parts.append("Tools: " + ", ".join(cleaned))

    return "\n    ".join(parts)
