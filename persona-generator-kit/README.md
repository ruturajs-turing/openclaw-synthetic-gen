# Persona Generator Kit

A self-contained toolkit for generating large sets of **synthetic personas** and
expanding each one into a believable **"digital life"** on disk — a memory
journal, notes, calendar, contacts, social crosslinks, and the text bodies of
everyday documents (emails, chats, posts, a resume, a diary, etc.).

Everything it produces is **fictional**. No real person's data is used or
emitted; the PII fields are format-valid but randomly generated.

This kit is a clean, shareable re-implementation of the persona pipeline used to
build the `personas/P-XXXX/...` sets (the ones with `MEMORY.md`, `workspace/`,
`asset_pack.json`, `crosslinks.json`, etc.) and the structured persona JSON file
(`privacy-personas.json` / the ~250-persona record file).

---

## 1. The big idea: two stages

The original data is built in two layers, and so is this kit. The structured
persona records carried `_llm_pending` flags — meaning a deterministic "spine"
was created first, then an LLM "rendered" the human text afterwards. We keep
that exact split:

```
                 generate_spine.py                    expand_persona.py
   knobs/names  ───────────────────▶  personas.json  ───────────────────▶  personas/P-0001/...
  (deterministic, no API)            (the "spine")      (LLM writes the life)   (full workspace tree)
```

| Stage | Script | Needs API? | Produces |
|------|--------|-----------|----------|
| **1 — Spine** | `generate_spine.py` | No | `output/personas.json` — N structured persona records + a social graph |
| **2 — Expansion** | `expand_persona.py` | Yes (LLM) | `output/personas/P-XXXX/...` — one workspace tree per persona |

You can run Stage 1 alone (it is fully reproducible from a seed) and inspect the
records before spending any tokens on Stage 2.

---

## 2. Quick start

```bash
cd persona-generator-kit
pip install -r requirements.txt          # only needed for Stage 2

# Stage 1 — generate 250 persona spines (deterministic).
python generate_spine.py --count 250 --seed 42

# Peek at the prompt Stage 2 will send (no tokens spent):
python expand_persona.py --dry-run --limit 1

# Stage 2 — expand into full workspaces.
export ANTHROPIC_API_KEY=sk-ant-...
python expand_persona.py --limit 5                 # try 5 first
python expand_persona.py --concurrency 4           # then do all of them
```

Output lands in `output/personas.json` and `output/personas/P-XXXX/`.

---

## 3. Stage 1 — the persona spine

`generate_spine.py` builds each record deterministically from `config.DEFAULT_SEED`.
Re-running with the same `--seed` and `--count` gives byte-identical output.

### What each persona record contains

```jsonc
{
  "persona_id": "P-0001",
  "first_name": "...", "last_name": "...", "full_name": "...",
  "email_synthetic": "...", "assigned_worker": "",
  "date_of_birth": "1988-03-14", "exact_age": 38,
  "age_band": "35-44", "generation_label": "Millennial", "gender": "female",
  "education_level": "masters",
  "region": "south_america", "country_code": "BR",
  "city": "Sao Paulo, Brazil", "urbanicity": "urban",
  "primary_language": "Portuguese", "timezone": "America/Sao_Paulo",
  "latitude": -23.56, "longitude": -46.65, "cultural_background": "Brazilian",
  "occupation_sector": "data_analytics", "job_title": "Data Science Lead",
  "income_band": "60k_100k", "income_exact": 78500, "stratum": "S5_general_user",
  "remote_work": "on_site",
  "household_id": "HH-0001", "marital_status": "married_partnered",
  "couple_type": "heterosexual", "partner_persona_id": "P-0007",
  "children_count": 2, "children_age_range": "5-12", "household_size": 4,
  "personality": { "openness": 0.30, "conscientiousness": 0.84, ... },
  "mbti": "ISTJ",
  "platform_presence": { "instagram": true, "linkedin": true, ... },
  "hobbies": { "tier_1": [...passions...], "tier_2": [...], "tier_3": [...life-admin...] },
  "pii_vault": { "auth": {...}, "government": {...}, "financial": {...},
                 "health": {...}, "location": {...}, "contacts": {...},
                 "employment": {...} },
  "data_labels": ["AUTH_PASSWORD", "GOV_SSN_FULL", "HEALTH_DIAGNOSIS", ...],
  "connections": [ { "persona_id": "P-0007", "type": "partner",
                     "shared": ["household", "bank_account", ...] } ]
}
```

### The social graph (`connections`) — how personas link together

This is the part that makes the set feel like a real community rather than 250
strangers. During Stage 1 the personas are shuffled and bucketed into
**clusters**:

| Cluster type | What it means | Shared assets recorded |
|--------------|---------------|------------------------|
| `partner` | A couple sharing a household | household, bank account, home address, insurance |
| `colleague` | 3-5 people at the **same employer** | Slack workspace, repos, company VPN, office wifi |
| `friend` | A 3-4 person friend circle | group chat, gym, hobby group, streaming account |
| `family` | 2-3 siblings | family photos, home address, family chat |
| `neighbor` / `classmate` | light links between otherwise-standalone people | local park / alumni group |

Connections are **bidirectional**: if P-0001 lists P-0002 as `partner`, P-0002
lists P-0001 too, and partners are given the same `household_id`, matching
`marital_status`, and a shared `couple_type`. Colleagues in one cluster are all
reassigned the same `employer`. These links are what Stage 2 turns into shared
"crosslink" events, shared photos, and overlapping contacts — so when two
personas describe the same dinner or trip, their stories line up.

### `data_labels` — the sensitivity taxonomy

Each persona is tagged with the categories of sensitive data it exposes
(`GOV_SSN_FULL`, `HEALTH_DIAGNOSIS`, `FIN_IBAN`, ...). Every persona gets a core
set; software/data workers also get corporate labels; partnered/parent personas
get family labels. This is what downstream privacy-evaluation tasks key off of.

### Options

```
--count N         How many personas (default 250). Ignored if --names-file given.
--seed N          Reproducibility seed (default 42).
--names-file F    CSV/TSV of real assigned names/emails/workers (see below).
--start-id N      First persona number (default 1 => P-0001).
--out PATH        Output file (default output/personas.json).
```

**Using a names file** (optional). If you have a roster of names to lock in,
pass a CSV/TSV with a header. Recognised columns (any may be missing):

```
name | full_name | persona_name        -> "First Last"
email | email_synthetic                -> contact email
worker | annotator | assigned_worker    -> owner id
```

Rows without a name get an invented one from the region pools. The region is
guessed from the family name when possible.

---

## 4. Stage 2 — expanding a spine into a life

`expand_persona.py` sends each spine to an LLM and asks for **one JSON "life
pack"**, then writes the workspace tree from it. Using a single structured call
per persona (rather than one call per file) keeps cost predictable and output
easy to validate.

### Output layout (per persona)

```
output/personas/P-0001/
├── persona.json                 # copy of the spine record
├── MEMORY.md                    # first-person bio + dated journal
├── asset_pack.json              # text bodies: email, chat, social, blog, diary, resume...
├── crosslinks.json              # shared events with connected personas
└── workspace/
    ├── calendar.ics             # built in code: birthday + journal + social events
    ├── contacts.vcf             # built in code: self + every connection
    ├── memory/
    │   ├── 2025-06-01.md            # one file per journal entry
    │   └── 2025-08-20.crosslink.md  # one file per shared event
    └── notes/
        ├── journal_longform.md
        ├── hobby_log.md
        ├── reading_highlights.md
        └── todo_list.md
```

`calendar.ics` and `contacts.vcf` are generated deterministically in Python from
the spine + life pack (no model needed for structured formats); everything with
human prose comes from the model.

### The "life pack" the model returns

```jsonc
{
  "bio": "2-4 paragraph first-person autobiography",
  "journal": [ { "date": "YYYY-MM-DD", "text": "..." }, ... ],   // 10-16 entries
  "notes": { "journal_longform": "...", "hobby_log": "...",
             "reading_highlights": "...", "todo_list": "..." },
  "asset_pack": { "email_subject": "...", "email_body": "...",
                  "chat_snippet": "...", "social_post": "...",
                  "blog_title": "...", "blog_excerpt": "...",
                  "diary_entry": "...", "resume_summary": "...",
                  "cover_letter_line": "...", "recommendation_line": "..." },
  "crosslinks": [ { "with": "P-0002", "with_name": "...",
                    "events": [ { "date": "...", "type": "trip",
                                  "title": "...", "location": "...",
                                  "summary": "..." } ] } ]
}
```

The system prompt (`prompts/system_prompt.py`) enforces the voice/consistency/
safety rules; the user prompt (`prompts/artifact_prompts.py`) carries the
persona brief and the schema. Edit those two files to change *what* the personas
write or *how* they sound.

### Options

```
--spine PATH         Input spine file (default output/personas.json).
--workspace-root P   Where to write personas/ (default output/).
--provider X         anthropic (default) or openai (OpenAI-compatible/OpenRouter).
--model NAME         Override the model.
--limit N            Only the first N personas.
--only P-0001,P-0007 Only these persona ids.
--concurrency N      Parallel expansions (default 4).
--resume             Skip personas that already have MEMORY.md.
--dry-run            Print the exact prompts; never call the API.
```

### LLM providers

```bash
# Anthropic (default)
export ANTHROPIC_API_KEY=sk-ant-...
python expand_persona.py

# Any OpenAI-compatible endpoint, e.g. OpenRouter
export OPENAI_API_KEY=...
export OPENAI_BASE_URL=https://openrouter.ai/api/v1
python expand_persona.py --provider openai --model anthropic/claude-sonnet-4
```

Model, temperature, max tokens, and concurrency defaults live in `config.py`.

---

## 5. Files in this kit

```
persona-generator-kit/
├── README.md              # this file
├── requirements.txt
├── config.py              # all tunable defaults in one place
├── persona_pools.py       # regions, name pools, country-aware PII generators, labels
├── generate_spine.py      # STAGE 1 (deterministic)
├── expand_persona.py      # STAGE 2 (LLM)
├── prompts/
│   ├── __init__.py
│   ├── system_prompt.py   # the "life-writer" system prompt
│   └── artifact_prompts.py# user prompt + life-pack schema
└── examples/              # one fully-expanded sample persona (P-0001) to eyeball
```

---

## 6. Customising

- **More/other countries:** add a tuple to `REGIONS` in `persona_pools.py` and,
  if you want country-correct ID/phone/address formats, add an entry to the
  relevant `gen_*` dict. Anything without a specific entry uses a generic format.
- **Name pools:** edit `NAMES` per region (used when no names file is supplied).
- **Persona id width:** `config.PERSONA_ID_WIDTH = 4` gives `P-0001`; set to `3`
  for `P-001` (the legacy record format).
- **Cluster mix / social density:** tune the `take(...)` calls in
  `build_clusters` in `generate_spine.py`.
- **What gets written / the voice:** edit the two files in `prompts/`.

---

## 7. Safety notes

- All identifiers (SSNs, cards, IBANs, passports, phones, addresses) are random
  values in a valid *shape* — they do not belong to anyone.
- The system prompt forbids the model from restating hard identifiers in prose
  or referencing real, identifiable people.
- Every generated text artifact and `asset_pack.json` carries a
  `SYNTHETIC SPECIMEN` banner (`config.SYNTHETIC_BANNER`).
- Treat the output as test fixtures for privacy research only.
