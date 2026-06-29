"""HTML/CSS document templates — ~12 realistic families on a shared paper shell. Each
returns a full HTML string with crisp, legible text and a SMALL synthetic marker (header
subtitle + tiny footer; never a centre watermark). Rendered to PNG by render.py (Chromium).
"""

from __future__ import annotations

import html as _html
import random

from .families import accent_for, family_for
from .. import docgen
from ... import SYNTHETIC_BANNER

A4_W = 820  # px at scale 1; renderer uses device_scale_factor=2 for sharpness


def _esc(s) -> str:
    return _html.escape(str(s if s is not None else ""))


def _money(n) -> str:
    return f"{float(n):,.2f}"


def _ctx(pa):
    c = pa.context
    return c, c.get("pii_vault", {}), c.get("full_name", ""), c.get("asset_pack", {})


def _shell(pa, accent: str, body: str, *, pad=True) -> str:
    cc = pa.context.get("country_code", "")
    title = docgen.humanize(pa.entry.kind)
    sub = f"SPECIMEN · {cc} · synthetic, no real PII".replace("·  ·", "·")
    footer = f"SYNTHETIC — AI-agent trajectory testing only · no real PII · {pa.entry.kind.replace('.real','')}"
    body_pad = "padding:36px 44px;" if pad else ""
    return f"""<!doctype html><html><head><meta charset="utf-8">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:{A4_W}px;font-family:'Helvetica Neue',Arial,'Segoe UI',sans-serif;color:#1a1a1a;background:#fff;-webkit-font-smoothing:antialiased}}
.page{{width:{A4_W}px;min-height:1100px;background:#fff;position:relative}}
.band{{background:{accent};color:#fff;padding:22px 44px}}
.band h1{{font-size:30px;font-weight:700;letter-spacing:.2px}}
.band .sub{{font-size:13px;opacity:.85;margin-top:4px}}
.body{{{body_pad}}}
.foot{{position:absolute;bottom:18px;left:0;right:0;text-align:center;font-size:10px;color:#b9b9b9}}
.muted{{color:#8a8a8a}} .lbl{{font-size:11px;font-weight:700;color:#8a8a8a;letter-spacing:.4px}}
.val{{font-size:16px;color:#111;margin-top:2px}} .row{{margin-bottom:16px}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{text-align:left;color:#8a8a8a;font-size:11px;border-bottom:2px solid #e3e3e3;padding:8px 6px}}
td{{padding:7px 6px;border-bottom:1px solid #eee}}
</style></head><body><div class="page">
<div class="band"><h1>{_esc(title)}</h1><div class="sub">{_esc(sub)}</div></div>
<div class="body">{body}</div>
<div class="foot">{_esc(footer)}</div>
</div></body></html>"""


def _subject(name, addr) -> str:
    return (f'<div style="background:#f4f6f9;border:1px solid #dde3ea;border-radius:10px;'
            f'padding:16px 18px;margin-bottom:24px"><div class="lbl">ACCOUNT HOLDER</div>'
            f'<div style="font-size:20px;font-weight:700;margin-top:3px">{_esc(name)}</div>'
            f'<div class="muted" style="font-size:13px">{_esc(addr)}</div></div>')


def _fields_grid(fields) -> str:
    cells = "".join(f'<div class="row"><div class="lbl">{_esc(l)}</div>'
                    f'<div class="val">{_esc(v)}</div></div>' for l, v in fields)
    return f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px 40px">{cells}</div>'


# ---------------- families ----------------
def _financial(pa, rng):
    c, vault, name, _ = _ctx(pa)
    fin = vault.get("financial", {})
    addr = docgen._addr(c)
    opening = rng.randint(1500, 40000) + rng.random()
    inflow = rng.randint(1000, 30000) + rng.random()
    outflow = rng.randint(500, 25000) + rng.random()
    closing = opening + inflow - outflow
    inst = rng.choice(["Northbridge Mutual", "Crest Federal", "Harbor & Vale", "Meridian Bank"]) + " (specimen)"
    summary = f"""<div style="display:flex;gap:0;border:1px solid #e3e3e3;border-radius:8px;overflow:hidden;margin:18px 0">
      {''.join(f'<div style="flex:1;padding:14px 16px;border-right:1px solid #eee"><div class="lbl">{l}</div><div style="font-size:18px;font-weight:700;color:{col}">EUR {_money(v)}</div></div>' for l,v,col in [('OPENING',opening,'#111'),('MONEY IN',inflow,'#1a7d3c'),('MONEY OUT',outflow,'#b0202a'),('CLOSING',closing,'#111')])}
    </div>"""
    rows = ""
    bal = opening
    for _ in range(8):
        amt = rng.randint(-1200, 2500) + rng.random()
        bal += amt
        desc = rng.choice(["Card payment", "Direct debit", "Salary", "Transfer", "Grocery", "Utilities", "Refund"])
        rows += (f"<tr><td>2026-0{rng.randint(1,9)}-{rng.randint(10,28)}</td><td>{desc}</td>"
                 f"<td style='text-align:right;color:{'#1a7d3c' if amt>=0 else '#b0202a'}'>{_money(amt)}</td>"
                 f"<td style='text-align:right'>{_money(bal)}</td></tr>")
    head = (f'<div style="display:flex;justify-content:space-between"><div><div class="lbl">ACCOUNT HOLDER</div>'
            f'<div style="font-size:18px;font-weight:700">{_esc(name)}</div><div class="muted">{_esc(addr)}</div></div>'
            f'<div style="text-align:right"><div class="lbl">ACCOUNT NO</div><div class="val">{_esc(fin.get("bank_account","55710787"))}</div>'
            f'<div class="muted" style="font-size:12px">IBAN {_esc(fin.get("iban",""))}</div></div></div>')
    body = (f'<div class="muted" style="font-size:13px;margin-bottom:6px">{inst} — Monthly Account Statement · '
            f'Period 01–30 Jun 2026 · Page 1 of 1</div>{head}{summary}'
            f'<table><tr><th>DATE</th><th>DESCRIPTION</th><th style="text-align:right">AMOUNT</th>'
            f'<th style="text-align:right">BALANCE</th></tr>{rows}</table>')
    return body


def _receipt(pa, rng):
    c, vault, name, _ = _ctx(pa)
    merchant = rng.choice(["Corner Market", "MediCare Pharmacy", "City Hardware", "Cafe Aurora", "QuickMart"])
    items = [(rng.choice(["Milk", "Bread", "Coffee", "Batteries", "Notebook", "Aspirin", "Olive Oil", "Eggs"]),
              round(rng.uniform(1.2, 24.9), 2)) for _ in range(rng.randint(4, 8))]
    total = sum(p for _, p in items)
    lines = "".join(f"<tr><td>{_esc(n)}</td><td style='text-align:right'>{_money(p)}</td></tr>" for n, p in items)
    inner = (f'<div style="max-width:380px;margin:0 auto;font-family:\'Courier New\',monospace">'
             f'<div style="text-align:center;font-weight:700;font-size:18px">{merchant}</div>'
             f'<div style="text-align:center" class="muted">{_esc(docgen._addr(c))}</div><hr style="margin:10px 0">'
             f'<table>{lines}</table><hr style="margin:10px 0">'
             f'<div style="display:flex;justify-content:space-between;font-weight:700;font-size:16px">'
             f'<span>TOTAL</span><span>{_money(total)}</span></div>'
             f'<div class="muted" style="text-align:center;margin-top:8px">Customer: {_esc(name)} · 2026-0{rng.randint(1,9)}-{rng.randint(10,28)}</div></div>')
    return inner


def _id_card(pa, rng, face_b64=None):
    c, vault, name, _ = _ctx(pa)
    gov = vault.get("government", {})
    fields = docgen.derive_fields(pa, rng)
    photo = (f'<img src="data:image/png;base64,{face_b64}" style="width:150px;height:190px;'
             f'object-fit:cover;border-radius:6px;border:1px solid #ccc">' if face_b64
             else '<div style="width:150px;height:190px;background:#e9edf2;border-radius:6px"></div>')
    rows = "".join(f'<div class="row"><div class="lbl">{_esc(l)}</div><div class="val">{_esc(v)}</div></div>'
                   for l, v in fields)
    mrz = ""
    if "passport" in pa.entry.kind:
        s = (name.upper().replace(" ", "<") + "<" * 20)[:39]
        n = (gov.get("passport_num", "Z0000000") + "<" * 20)[:30]
        mrz = (f'<div style="font-family:\'Courier New\',monospace;font-size:15px;letter-spacing:2px;'
               f'background:#f4f4f4;padding:10px;margin-top:18px;border-radius:4px">P&lt;{c.get("country_code","")}{_esc(s)}<br>{_esc(n)}</div>')
    return (f'<div style="display:flex;gap:24px">{photo}'
            f'<div style="flex:1;display:grid;grid-template-columns:1fr 1fr;gap:4px 30px">{rows}</div></div>{mrz}')


def _certificate(pa, rng):
    c, vault, name, _ = _ctx(pa)
    return (f'<div style="border:6px double {accent_for(pa.entry.kind)};padding:40px;text-align:center;margin-top:10px">'
            f'<div style="font-size:15px;letter-spacing:3px;color:#8a8a8a">THIS CERTIFIES THAT</div>'
            f'<div style="font-size:34px;font-weight:700;margin:18px 0;font-family:Georgia,serif">{_esc(name)}</div>'
            f'<div style="font-size:16px;max-width:480px;margin:0 auto;color:#444">has satisfied all requirements for '
            f'<b>{_esc(docgen.humanize(pa.entry.kind))}</b> and is hereby duly recognised.</div>'
            f'<div style="display:flex;justify-content:space-between;margin-top:60px;font-size:13px">'
            f'<div>____________________<br>Date: 2026-0{rng.randint(1,9)}-{rng.randint(10,28)}</div>'
            f'<div style="width:80px;height:80px;border:2px solid {accent_for(pa.entry.kind)};border-radius:50%;'
            f'display:flex;align-items:center;justify-content:center;color:{accent_for(pa.entry.kind)};font-size:11px">SEAL</div>'
            f'<div>____________________<br>Registrar</div></div></div>')


def _letter(pa, rng):
    c, vault, name, ap = _ctx(pa)
    body = ap.get("email_body") or ap.get("cover_letter_line") or ap.get("recommendation_line") or \
        f"This letter concerns {docgen.humanize(pa.entry.kind)} for the above-named individual."
    return (f'<div style="font-size:13px;text-align:right;color:#555">2026-0{rng.randint(1,9)}-{rng.randint(10,28)}</div>'
            f'<div style="margin:18px 0"><b>{_esc(name)}</b><br><span class="muted">{_esc(docgen._addr(c))}</span></div>'
            f'<div style="font-size:15px;line-height:1.7;white-space:pre-wrap;max-width:620px">{_esc(body)}</div>'
            f'<div style="margin-top:48px">Sincerely,<br><br><b>{_esc(name)}</b></div>')


def _legal(pa, rng):
    c, vault, name, _ = _ctx(pa)
    fields = [("CASE NO", f"{rng.randint(2024,2026)}-CV-{rng.randint(1000,9999)}"),
              ("FILED", f"2026-0{rng.randint(1,9)}-{rng.randint(10,28)}"),
              ("PARTY", name), ("JURISDICTION", c.get("city", ""))]
    clause = ("IT IS HEREBY ORDERED that the matter referenced above is recorded in accordance with applicable "
              "statute. This is a synthetic specimen document produced for AI-agent evaluation and has no legal effect.")
    return (f'<div style="text-align:center;font-weight:700;letter-spacing:1px;margin-bottom:10px">IN THE DISTRICT COURT</div>'
            f'{_fields_grid(fields)}<hr style="margin:18px 0">'
            f'<div style="font-size:14px;line-height:1.8">{_esc(clause)}</div>'
            f'<div style="margin-top:50px;font-size:13px">____________________<br>Clerk of Court</div>')


def _invite(pa, rng):
    c, vault, name, _ = _ctx(pa)
    child = rng.choice(["Zoe", "Leo", "Mia", "Noah", "Aria", "Liam"]) + " " + name.split()[-1] if name else "The Family"
    age = rng.randint(6, 14)
    venue = rng.choice(["Sala Feste", "Sunshine Hall", "The Play Barn", "Garden Pavilion"])
    return (f'<div style="border:3px dashed #d6336c;border-radius:14px;padding:34px;text-align:center;margin-top:8px;'
            f'background:#fffdf9">'
            f'<div style="font-size:30px;color:#d6336c;font-weight:700">You\'re Invited! 🎉</div>'
            f'<div style="font-size:16px;margin-top:14px;color:#555">to celebrate</div>'
            f'<div style="font-size:38px;color:#3b2e7e;font-weight:700;margin:6px 0">{_esc(child)}</div>'
            f'<div style="font-size:20px;color:#e8730a">turning {age}!</div>'
            f'<div style="background:#eef4fb;border-radius:10px;padding:18px;margin:24px auto;max-width:440px;text-align:left;font-size:15px;line-height:2">'
            f'📅 Sat 21 Jun 2026<br>🕐 13:00 — 18:00<br>📍 {venue} — {_esc(c.get("city",""))}<br>'
            f'🎈 Hosted by {_esc(name)}</div>'
            f'<div style="color:#d6336c;font-weight:700;font-size:17px">RSVP to {_esc(vault.get("contacts",{}).get("phone",""))}</div>'
            f'<div class="muted" style="font-size:13px">{_esc(c.get("primary_language") and "")}{_esc(pa.context.get("full_name",""))}</div></div>')


def _log_chart(pa, rng):
    title = docgen.humanize(pa.entry.kind)
    unit = "mmHg sys" if "blood" in pa.entry.kind else ("mg/dL" if "glucose" in pa.entry.kind else "value")
    base = 120 if "blood" in pa.entry.kind else (110 if "glucose" in pa.entry.kind else 50)
    n = 40
    vals = [base + rng.randint(-25, 30) for _ in range(n)]
    w, h = 720, 320
    lo, hi = min(vals) - 5, max(vals) + 5
    pts = " ".join(f"{40 + i*(w-60)/(n-1):.0f},{h-20-(v-lo)/(hi-lo)*(h-50):.0f}" for i, v in enumerate(vals))
    svg = (f'<svg width="{w}" height="{h}" style="margin-top:10px">'
           f'<polyline points="{pts}" fill="none" stroke="#178a8a" stroke-width="2.5"/>'
           f'<line x1="40" y1="{h-20}" x2="{w-20}" y2="{h-20}" stroke="#ccc"/></svg>')
    return (f'<div style="font-size:20px;font-weight:700;font-style:italic">{title} ({unit})</div>{svg}'
            f'<div class="muted" style="font-size:12px;margin-top:8px">40 readings · 2026 · subject {_esc(pa.context.get("full_name",""))}</div>')


def _medical(pa, rng):
    c, vault, name, _ = _ctx(pa)
    health = vault.get("health", {})
    fields = [("PATIENT", name), ("DOB", c.get("dob", "")),
              ("PROVIDER", health.get("provider", "Dr. A. Rossi, City Clinic")),
              ("DATE", f"2026-0{rng.randint(1,9)}-{rng.randint(10,28)}"),
              ("DIAGNOSIS", ", ".join(health.get("diagnoses", ["—"])[:2])),
              ("MEDICATION", ", ".join(health.get("medications", ["—"])[:2]))]
    results = "".join(f"<tr><td>{t}</td><td>{rng.randint(60,140)}</td><td>{lo}-{hi}</td><td>{'Normal' if rng.random()>.3 else 'High'}</td></tr>"
                      for t, lo, hi in [("Glucose", 70, 110), ("Cholesterol", 120, 200), ("Hemoglobin", 12, 17), ("BP sys", 90, 120)])
    return (f'<div style="font-weight:700;color:{accent_for(pa.entry.kind)};margin-bottom:10px">City Medical Center (specimen)</div>'
            f'{_fields_grid(fields)}<table style="margin-top:18px"><tr><th>TEST</th><th>VALUE</th><th>REF RANGE</th><th>FLAG</th></tr>{results}</table>')


def _ticket(pa, rng):
    c, vault, name, _ = _ctx(pa)
    code = "".join(rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ0123456789") for _ in range(6))
    bars = "".join(f'<rect x="{i*6}" y="0" width="{rng.choice([2,3,4])}" height="60" fill="#111"/>' for i in range(60))
    fields = [("PASSENGER", name), ("FLIGHT", f"{rng.choice(['AZ','LH','BA','AF'])}{rng.randint(100,999)}"),
              ("FROM", c.get("city", "")[:3].upper()), ("TO", rng.choice(["LHR", "JFK", "CDG", "FCO"])),
              ("GATE", f"{rng.choice('ABCD')}{rng.randint(1,30)}"), ("SEAT", f"{rng.randint(1,40)}{rng.choice('ABCDEF')}")]
    return (f'<div style="border:2px solid {accent_for(pa.entry.kind)};border-radius:10px;display:flex;overflow:hidden">'
            f'<div style="flex:2;padding:24px">{_fields_grid(fields)}<svg width="372" height="60" style="margin-top:14px">{bars}</svg></div>'
            f'<div style="flex:1;border-left:2px dashed #bbb;padding:24px;background:#fafafa;text-align:center">'
            f'<div class="lbl">BOOKING</div><div style="font-size:24px;font-weight:700;letter-spacing:2px">{code}</div>'
            f'<div class="muted" style="margin-top:30px">2026-0{rng.randint(1,9)}-{rng.randint(10,28)}</div></div></div>')


def _table(pa, rng):
    c, vault, name, _ = _ctx(pa)
    rows = "".join(f"<tr><td>{r}</td><td>{rng.choice(['A','B','A-','B+','Pass'])}</td><td>{rng.randint(1,6)}</td>"
                   f"<td>{rng.randint(60,99)}</td></tr>"
                   for r in ["Mathematics", "Literature", "Science", "History", "Arts", "Physical Ed"])
    return (f'<div class="row"><div class="lbl">NAME</div><div class="val">{_esc(name)}</div></div>'
            f'<table style="margin-top:14px"><tr><th>SUBJECT</th><th>GRADE</th><th>CREDITS</th><th>SCORE</th></tr>{rows}</table>')


def _generic(pa, rng):
    c, vault, name, _ = _ctx(pa)
    return _subject(name, docgen._addr(c)) + _fields_grid(docgen.derive_fields(pa, rng))


_FAMILY = {
    "financial": _financial, "receipt": _receipt, "certificate": _certificate, "letter": _letter,
    "legal": _legal, "invite": _invite, "log_chart": _log_chart, "medical": _medical,
    "ticket": _ticket, "table": _table, "generic": _generic,
}


def render_html(pa, face_b64: str | None = None) -> str:
    rng = random.Random(f"{pa.persona_id}:{pa.entry.id}")
    fam = family_for(pa.entry.kind)
    accent = accent_for(pa.entry.kind)
    if fam == "id_card":
        body = _id_card(pa, rng, face_b64=face_b64)
    else:
        body = _FAMILY.get(fam, _generic)(pa, rng)
    return _shell(pa, accent, body)
