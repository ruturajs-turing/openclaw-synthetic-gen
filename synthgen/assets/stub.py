"""Offline generators for non-image modalities, producing REAL, relevant content (not bare
placeholders): SVG documents via the shared docgen template, text/markdown/html bodies that
reuse the persona's LLM-written asset_pack where possible, realistic CSV logs, and structured
JSON. The synthetic marker is a small footer/comment line only.
"""

from __future__ import annotations

import json
import random

from . import docgen
from .. import SYNTHETIC_BANNER
from .dispatcher import register
from ..config import Settings
from ..costs import CostModel
from ..events import EventBus
from ..manifest.extract import PlannedAsset

_MARK = "synthetic — no real PII"


def _ctx(pa):
    return pa.context, pa.context.get("asset_pack", {}), pa.context.get("full_name", "")


# --- SVG: real templated document (matches the image/.png style) ---
async def _gen_svg(pa, settings, bus, costs):
    pa.out_path.write_bytes(docgen.render_svg(pa).encode())


# --- text/markdown bodies, reusing real LLM-written content where it fits ---
def _text_body(pa) -> str:
    ctx, ap, name = _ctx(pa)
    kind = pa.entry.kind
    title = docgen.humanize(kind)
    if "email" in kind and ap.get("email_body"):
        return f"Subject: {ap.get('email_subject', title)}\nFrom: {name}\n\n{ap['email_body']}\n\n— {_MARK}"
    if "diary" in kind and ap.get("diary_entry"):
        return f"{title}\n\n{ap['diary_entry']}\n\n({_MARK})"
    if ("meeting" in kind or "transcript" in kind) and ap.get("meeting_note"):
        return f"{title} — {ap.get('meeting_topic','')}\n\n{ap['meeting_note']}\n\n({_MARK})"
    if "voice" in kind or "audio" in kind:
        return f"{title} (transcript)\n\n{ap.get('voice_reminder') or ap.get('diary_entry','')}\n\n({_MARK})"
    if "address-book" in kind:
        v = ctx.get("pii_vault", {})
        return (f"{title}\n{name}\t{ctx.get('city','')}\n"
                f"phone\t{v.get('contacts',{}).get('phone','')}\n\n{_MARK}")
    if "api-token" in kind or "key" in kind:
        rng = random.Random(f"{pa.persona_id}:{pa.entry.id}")
        tok = "".join(rng.choice("abcdef0123456789") for _ in range(40))
        return f"# {title}\n# {SYNTHETIC_BANNER}\nTOKEN={tok}\n"
    body = ap.get("blog_excerpt") or ap.get("resume_summary") or ap.get("social_post") or ""
    return f"{title}\nPersona: {name} — {ctx.get('city','')}\n\n{body}\n\n({_MARK})"


async def _gen_text(pa, settings, bus, costs):
    pa.out_path.write_bytes(_text_body(pa).encode())


# --- HTML: a simple but real-looking page ---
async def _gen_html(pa, settings, bus, costs):
    ctx, ap, name = _ctx(pa)
    body = ap.get("blog_excerpt") or ap.get("social_post") or ap.get("resume_summary") or ""
    title = docgen.humanize(pa.entry.kind)
    html = (
        f"<!doctype html><html lang='en'><head><meta charset='utf-8'><title>{title}</title>"
        "<style>body{font-family:Arial,sans-serif;max-width:760px;margin:40px auto;color:#222}"
        "header{border-bottom:2px solid #5f0f40;padding-bottom:8px}small{color:#999}</style></head>"
        f"<body><header><h1>{title}</h1><small>{name} · {ctx.get('city','')}</small></header>"
        f"<main><p>{body}</p></main><footer><small>{_MARK}</small></footer></body></html>\n"
    )
    pa.out_path.write_bytes(html.encode())


# --- CSV logs with realistic rows ---
_CSV_HEADERS = {
    "glucose-log": ("date,time,mg_dl,note", lambda r: f"2026-0{r.randint(1,9)}-{r.randint(10,28)},08:0{r.randint(0,5)},{r.randint(80,180)},fasting"),
    "blood-pressure-log": ("date,systolic,diastolic,pulse", lambda r: f"2026-0{r.randint(1,9)}-{r.randint(10,28)},{r.randint(110,140)},{r.randint(70,90)},{r.randint(60,90)}"),
    "nutrition-log": ("date,meal,calories,protein_g", lambda r: f"2026-0{r.randint(1,9)}-{r.randint(10,28)},{r.choice(['breakfast','lunch','dinner'])},{r.randint(300,800)},{r.randint(10,45)}"),
    "transaction-export": ("date,description,amount,balance", lambda r: f"2026-0{r.randint(1,9)}-{r.randint(10,28)},{r.choice(['Grocery','Fuel','Salary','Transfer'])},{r.randint(-200,2000)}.{r.randint(0,99):02d},{r.randint(1000,9000)}.00"),
}


async def _gen_csv(pa, settings, bus, costs):
    rng = random.Random(f"{pa.persona_id}:{pa.entry.id}")
    spec = _CSV_HEADERS.get(pa.entry.kind)
    if spec:
        header, rowfn = spec
        rows = [header] + [rowfn(rng) for _ in range(12)]
    else:
        header = "date,field,value"
        rows = [f"# {SYNTHETIC_BANNER}", header] + [
            f"2026-0{rng.randint(1,9)}-{rng.randint(10,28)},{pa.entry.kind},{rng.randint(1,999)}" for _ in range(10)]
    rows.append(f"# {_MARK}")
    pa.out_path.write_bytes(("\n".join(rows) + "\n").encode())


# --- JSON: structured, with real persona fields + flagged synthetic ---
async def _gen_json(pa, settings, bus, costs):
    ctx, ap, name = _ctx(pa)
    data = {
        "_synthetic": True, "_note": _MARK, "kind": pa.entry.kind,
        "persona_id": pa.persona_id, "subject": name, "city": ctx.get("city"),
        "pii_fields": pa.pii_fields, "pii_tiers": pa.pii_tiers,
        "generated_for": "AI-agent privacy trajectory testing",
    }
    pa.out_path.write_bytes(json.dumps(data, indent=2, ensure_ascii=False).encode())


# --- binary / unhandled: a labelled, valid-ish placeholder ---
async def _gen_default(pa, settings, bus, costs):
    pa.out_path.write_bytes(
        (f"{docgen.humanize(pa.entry.kind)} ({pa.entry.modality})\n"
         f"Persona {pa.persona_id} — {pa.context.get('full_name','')}\n{SYNTHETIC_BANNER}\n").encode())


register("svg")(_gen_svg)
register("html")(_gen_html)
register("json")(_gen_json)
register("csv")(_gen_csv)
for _m in ("text", "md", "code", "xml"):
    register(_m)(_gen_text)
for _m in ("ics", "gpx", "vcf", "sqlite", "xlsx", "docx", "pptx", "ipynb", "parquet", "archive", "fasta", "_default"):
    register(_m)(_gen_default)
