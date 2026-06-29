"""
Builds the per-persona user prompt for Stage 2 and documents the JSON
"life pack" schema the model must return.

Stage 2 deliberately asks for ONE structured object per persona (instead of
many small calls). The Python side then deterministically renders that object
into the on-disk workspace tree (MEMORY.md, dated journal files, notes,
asset_pack.json, crosslinks.json), and builds calendar.ics / contacts.vcf
itself. This keeps cost predictable and output easy to validate.
"""

import json

# Human/machine description of what the model returns. Also embedded in README.
LIFE_PACK_SCHEMA = {
    "bio": "string — 2-4 paragraph first-person 'who I am' autobiography for MEMORY.md.",
    "journal": [
        {
            "date": "YYYY-MM-DD",
            "text": "string — a dated first-person journal entry (2-6 sentences).",
        }
    ],
    "notes": {
        "journal_longform": "string — one long, single-day reflective markdown entry.",
        "hobby_log": "string — markdown log of progress on the persona's tier-1 hobbies.",
        "reading_highlights": "string — markdown list of books/articles + highlighted quotes.",
        "todo_list": "string — markdown checklist mixing work + life-admin tasks.",
    },
    "asset_pack": {
        "email_subject": "string", "email_body": "string",
        "chat_snippet": "string — a few back-and-forth IM lines (use 'Me:' / name:).",
        "social_post": "string", "blog_title": "string", "blog_excerpt": "string",
        "diary_entry": "string", "resume_summary": "string",
        "cover_letter_line": "string", "recommendation_line": "string",
    },
    "crosslinks": [
        {
            "with": "P-XXXX (a connected persona id from the spine)",
            "with_name": "string (that person's name)",
            "events": [
                {
                    "date": "YYYY-MM-DD", "type": "celebration|trip|favor|message|meetup",
                    "title": "string", "location": "string",
                    "summary": "string — first-person account of the shared moment.",
                }
            ],
        }
    ],
}


def build_life_pack_prompt(brief: str, schema_hint: str) -> str:
    return f"""Here is the PERSONA SPINE you must bring to life:

{brief}

──────────────────────────────────────────────────────────────────────
Write this persona's digital life as a single JSON object with EXACTLY these
top-level keys: "bio", "journal", "notes", "asset_pack", "crosslinks".

Field requirements:
- bio: 2-4 first-person paragraphs. Capture personality, work, hobbies, and an
  honest inner contradiction or recurring worry.
- journal: 10-16 entries spread across the last ~12 months (oldest first). Mix
  ordinary days, a hobby breakthrough, a relationship moment, a work friction.
- notes.*: realistic markdown bodies (see schema). reading_highlights should fit
  the persona's interests; todo_list should mix job tasks with life-admin
  (matching their tier-3 topics).
- asset_pack: short, voice-true text bodies. The email/chat/social/diary fields
  may use the persona's primary language; resume/cover/recommendation lines in
  English.
- crosslinks: ONE entry per named connection in the spine (partner, colleagues,
  friends, family). Each with 2-3 dated shared events consistent with the
  relationship type. If the spine has no connections, return an empty list.

Schema reference (types only):
{schema_hint}

Return ONLY the JSON object."""


def schema_as_text() -> str:
    return json.dumps(LIFE_PACK_SCHEMA, indent=2, ensure_ascii=False)
