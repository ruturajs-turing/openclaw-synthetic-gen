"""Parse chat.technonous.com login kits from users.zip."""

from __future__ import annotations

import re
import zipfile
from functools import lru_cache
from pathlib import Path

DEFAULT_ZIP = Path(__file__).resolve().parent.parent / "users.zip"

_PERSONA_HEADER = re.compile(
    r"^##\s+(.+?)\s+\((P-\d+)\)\s*$", re.MULTILINE
)
_TABLE_ROW = re.compile(r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|", re.MULTILINE)


def _parse_table_section(text: str, heading: str) -> list[dict[str, str]]:
    idx = text.find(heading)
    if idx == -1:
        return []
    section = text[idx:]
    next_h = section.find("\n## ", 1)
    if next_h != -1:
        section = section[:next_h]
    rows: list[dict[str, str]] = []
    for line in section.splitlines():
        m = _TABLE_ROW.match(line.strip())
        if not m or m.group(1).lower() in ("name", "---"):
            continue
        name, jid, password, relation = (g.strip() for g in m.groups())
        row: dict[str, str] = {"name": name, "jid": jid, "relation": relation}
        if password and password != "—":
            row["password"] = password
        pid = re.search(r"\(P-(\d+)\)", relation)
        if pid:
            row["persona_id"] = f"P-{pid.group(1)}"
        rows.append(row)
    return rows


def _parse_persona_block(block: str, persona_id: str, full_name: str) -> dict:
    jid_m = re.search(r"\*\*JID:\*\*\s+`([^`]+)`", block)
    pass_m = re.search(r"\*\*Password:\*\*\s+`([^`]+)`", block)
    role_m = re.search(r"\*\*Role:\*\*\s+(.+)", block)
    loc_m = re.search(r"\*\*Location:\*\*\s+(.+)", block)
    return {
        "persona_id": persona_id,
        "full_name": full_name.strip(),
        "jid": jid_m.group(1).strip() if jid_m else "",
        "password": pass_m.group(1).strip() if pass_m else "",
        "role": role_m.group(1).strip() if role_m else "",
        "location": loc_m.group(1).strip() if loc_m else "",
        "relatives_friends": _parse_table_section(block, "### Relatives & extra friends"),
        "persona_connections": _parse_table_section(block, "### All persona-to-persona connections"),
    }


@lru_cache(maxsize=1)
def load_chat_kits(zip_path: str | None = None) -> dict[str, dict]:
    path = Path(zip_path) if zip_path else DEFAULT_ZIP
    if not path.exists():
        raise FileNotFoundError(f"Chat login zip not found: {path}")

    kits: dict[str, dict] = {}
    with zipfile.ZipFile(path) as zf:
        for name in zf.namelist():
            if not name.endswith(".md"):
                continue
            text = zf.read(name).decode("utf-8")
            for m in _PERSONA_HEADER.finditer(text):
                full_name, persona_id = m.group(1), m.group(2)
                start = m.end()
                nxt = _PERSONA_HEADER.search(text, start)
                block = text[start:nxt.start() if nxt else len(text)]
                kits[persona_id] = _parse_persona_block(block, persona_id, full_name)
    return kits


def get_chat_kit(persona_id: str, zip_path: str | None = None) -> dict | None:
    return load_chat_kits(zip_path).get(persona_id)


def build_chat_prompt_section(kit: dict | None) -> str:
    if not kit:
        return ""

    lines = [
        "═══ CHAT PLATFORM (chat.technonous.com) ═══",
        f"Persona JID: `{kit['jid']}`",
        f"Password: `{kit['password']}`",
        f"Role: {kit.get('role', '')} | Location: {kit.get('location', '')}",
        "",
        "Relatives / synthetic friends (use for messaging tasks):",
    ]
    for r in kit.get("relatives_friends", [])[:5]:
        lines.append(f"  • {r['name']} — `{r['jid']}` ({r['relation']})")
    lines.append("")
    lines.append("Persona-to-persona connections (prefer for coordinate/ping tasks):")
    for c in kit.get("persona_connections", [])[:5]:
        pid = c.get("persona_id", "")
        lines.append(f"  • {c['name']} — `{c['jid']}` ({c['relation']}{f', {pid}' if pid else ''})")
    lines.extend([
        "",
        "Chat task rules:",
        "- User MUST ask agent to use browser at chat.technonous.com (never API shortcuts)",
        "- Use ONLY this persona's JID/password — never another persona's credentials",
        "- Include real friend JID(s) from the lists above in user_intent / goal_summary",
        "- Treat password as L4 ephemeral unless user explicitly consents to memory",
    ])
    return "\n".join(lines)
