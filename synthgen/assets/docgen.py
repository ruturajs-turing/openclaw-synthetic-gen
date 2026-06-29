"""Document renderer — produces clean, real-content document images (PNG via Pillow) and
the matching SVG, in the style of the reference `generic_doc` generator: a coloured header
band, a small 'SPECIMEN · <CC> · synthetic, no real PII' subtitle, a SUBJECT box with the
persona's real name + address, kind-appropriate labelled fields filled with realistic
synthetic values, and a small footer marker. No giant centre watermark — the synthetic
marker is the header subtitle + a tiny footer line only.
"""

from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Header band colour by document category — gives visual variety like real document sets.
_CATEGORY_COLOR = {
    "finance": (15, 76, 92), "gov": (26, 41, 88), "health": (95, 15, 64),
    "legal": (60, 36, 20), "travel": (20, 70, 70), "edu": (40, 60, 30),
    "work": (35, 35, 60), "id": (26, 41, 88), "default": (60, 60, 70),
}
_KIND_CATEGORY = [
    ("bank|pay|paystub|invoice|salary|wire|loan|mortgage|credit|tax|w2|financial|receipt|toll|expense|crypto", "finance"),
    ("passport|license|licence|national-id|voter|ssn|id-card|residence|visa|immigration|naturaliz|citizen", "id"),
    ("medical|health|lab|prescription|medication|doctor|discharge|therapy|glucose|blood|ekg|vaccination|insurance-card|patient", "health"),
    ("court|jury|police|divorce|legal|notar|deed|title|name-change|permit|public-filing|lease|loan-agreement", "legal"),
    ("boarding|hotel|trip|itinerary|rental-car|ride|transit|parking|vehicle", "travel"),
    ("diploma|transcript|exam|course|thesis|assignment|class|student|standardized|school", "edu"),
    ("employ|offer|promotion|performance|resume|cover-letter|recommendation|badge|business-card|org-chart", "work"),
]

_FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial.ttf",
]


def _category(kind: str) -> str:
    import re
    k = kind.replace(".real", "")
    for pat, cat in _KIND_CATEGORY:
        if re.search(pat, k):
            return cat
    return "default"


def _font(size: int, bold: bool = False):
    paths = _FONT_CANDIDATES[1:] if bold else _FONT_CANDIDATES[:1]
    for p in paths + _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def humanize(kind: str) -> str:
    return kind.replace(".real", "").replace("-", " ").replace("_", " ").title()


def _addr(ctx: dict) -> str:
    vault = ctx.get("pii_vault", {})
    addr = vault.get("location", {}).get("home_address")
    if addr:
        return addr
    return f"{ctx.get('city', '')}".strip(", ")


def derive_fields(pa, rng: random.Random) -> list[tuple[str, str]]:
    """Realistic label/value pairs: a generic spine + kind-specific enrichment, all
    grounded in the persona's real synthetic PII where relevant."""
    ctx = pa.context
    vault = ctx.get("pii_vault", {})
    kind = pa.entry.kind.replace(".real", "")
    year = 2024 + rng.randint(0, 2)
    issue = f"{year}-{rng.randint(1,12):02d}-{rng.randint(1,28):02d}"
    fields: list[tuple[str, str]] = [
        ("DOCUMENT NO", f"{kind[:3].upper()}-{rng.randint(100000, 999999)}"),
        ("ISSUE DATE", issue),
        ("STATUS", rng.choice(["Valid", "Active", "Issued", "Confirmed"])),
        ("REFERENCE NO", f"REF-{rng.randint(100000, 999999)}"),
    ]
    gov, fin, health = vault.get("government", {}), vault.get("financial", {}), vault.get("health", {})
    if "passport" in kind and gov.get("passport_num"):
        fields = [("PASSPORT NO", gov["passport_num"]), ("NATIONALITY", ctx.get("country_code", "")),
                  ("DATE OF BIRTH", ctx.get("dob", "")), ("DATE OF ISSUE", issue),
                  ("DATE OF EXPIRY", f"{year+9}-{issue[5:]}"), ("AUTHORITY", "Ministry of Interior")]
    elif ("license" in kind or "licence" in kind) and gov.get("dl_num"):
        fields = [("LICENCE NO", gov["dl_num"]), ("CLASS", rng.choice(["B", "C", "A"])),
                  ("DATE OF BIRTH", ctx.get("dob", "")), ("ISSUED", issue),
                  ("EXPIRES", f"{year+5}-{issue[5:]}"), ("ADDRESS", _addr(ctx))]
    elif "bank" in kind or "statement" in kind:
        fields = [("ACCOUNT NO", fin.get("bank_account", str(rng.randint(10**9, 10**10)))),
                  ("IBAN", fin.get("iban", "")), ("STATEMENT PERIOD", f"{issue[:7]}"),
                  ("OPENING BALANCE", f"{rng.randint(1000,9000)}.{rng.randint(0,99):02d}"),
                  ("CLOSING BALANCE", f"{rng.randint(1000,9000)}.{rng.randint(0,99):02d}")]
    elif "pay" in kind or "salary" in kind or "w2" in kind:
        sal = fin.get("salary", rng.randint(40000, 120000))
        fields = [("EMPLOYEE", ctx.get("full_name", "")),
                  ("EMPLOYER", vault.get("employment", {}).get("employer", "")),
                  ("PERIOD", issue[:7]), ("GROSS PAY", f"{round(sal/12,2)}"),
                  ("NET PAY", f"{round(sal/12*0.72,2)}"), ("YTD", f"{sal}")]
    elif "prescription" in kind or "medication" in kind or "doctor" in kind:
        meds = health.get("medications", ["—"])
        dx = health.get("diagnoses", ["—"])
        fields = [("PATIENT", ctx.get("full_name", "")), ("DATE", issue),
                  ("DIAGNOSIS", ", ".join(dx[:2])), ("MEDICATION", ", ".join(meds[:2])),
                  ("PRESCRIBER", health.get("provider", "Dr. A. Rossi")), ("REFILLS", str(rng.randint(0, 3)))]
    elif "insurance" in kind:
        fields = [("MEMBER", ctx.get("full_name", "")),
                  ("MEMBER ID", health.get("insurance_id", f"INS-{rng.randint(10**6,10**7)}")),
                  ("PLAN", rng.choice(["Premium", "Standard", "Family"])), ("GROUP", str(rng.randint(1000, 9999))),
                  ("EFFECTIVE", issue)]
    elif "utility" in kind or "bill" in kind:
        fields = [("ACCOUNT", str(rng.randint(10**7, 10**8))), ("BILLING PERIOD", issue[:7]),
                  ("AMOUNT DUE", f"{rng.randint(40,300)}.{rng.randint(0,99):02d}"),
                  ("DUE DATE", f"{year}-{rng.randint(1,12):02d}-{rng.randint(1,28):02d}"),
                  ("SERVICE ADDRESS", _addr(ctx))]
    return fields


def _layout(pa, rng):
    title = humanize(pa.entry.kind)
    cc = pa.context.get("country_code", "")
    subtitle = f"SPECIMEN · {cc} · synthetic, no real PII".replace("·  ·", "·")
    name = pa.context.get("full_name", "")
    addr = _addr(pa.context)
    footer = f"SYNTHETIC — AI-agent trajectory testing only · no real PII · {pa.entry.kind.replace('.real','')}"
    return title, subtitle, name, addr, derive_fields(pa, rng), footer


def render_png(pa) -> bytes:
    import io
    rng = random.Random(f"{pa.persona_id}:{pa.entry.id}")
    title, subtitle, name, addr, fields, footer = _layout(pa, rng)
    W, H = 760, 980
    color = _CATEGORY_COLOR[_category(pa.entry.kind)]
    img = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 120], fill=color)
    d.text((40, 40), title, font=_font(30, bold=True), fill=(255, 255, 255))
    d.text((40, 88), subtitle, font=_font(14), fill=(223, 231, 239))
    # Subject box
    d.rounded_rectangle([40, 150, 720, 270], radius=10, fill=(244, 246, 249), outline=(221, 227, 234))
    d.text((56, 168), "SUBJECT", font=_font(12, bold=True), fill=(136, 136, 136))
    d.text((56, 192), name, font=_font(20, bold=True), fill=(17, 17, 17))
    d.text((56, 224), addr, font=_font(14), fill=(68, 68, 68))
    # Fields
    y = 320
    for label, value in fields:
        d.text((56, y), label, font=_font(13, bold=True), fill=(136, 136, 136))
        d.text((56, y + 22), str(value)[:70], font=_font(17), fill=(17, 17, 17))
        y += 60
    # Tiny footer marker
    d.text((W / 2, 950), footer, font=_font(10), fill=(187, 187, 187), anchor="mm")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def render_svg(pa) -> str:
    rng = random.Random(f"{pa.persona_id}:{pa.entry.id}")
    title, subtitle, name, addr, fields, footer = _layout(pa, rng)
    r, g, b = _CATEGORY_COLOR[_category(pa.entry.kind)]
    color = f"#{r:02x}{g:02x}{b:02x}"

    def esc(s):
        return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="760" height="980" viewBox="0 0 760 980" '
        'font-family="Helvetica, Arial, sans-serif">',
        f'<desc>SYNTHETIC SPECIMEN ({pa.entry.kind}). Synthetic, no real PII.</desc>',
        '<rect x="0" y="0" width="760" height="980" fill="#ffffff"/>',
        f'<rect x="0" y="0" width="760" height="120" fill="{color}"/>',
        f'<text x="40" y="62" font-size="30" font-weight="bold" fill="#ffffff">{esc(title)}</text>',
        f'<text x="40" y="96" font-size="14" fill="#dfe7ef">{esc(subtitle)}</text>',
        '<rect x="40" y="150" width="680" height="120" rx="10" fill="#f4f6f9" stroke="#dde3ea"/>',
        '<text x="56" y="184" font-size="12" fill="#888" font-weight="bold">SUBJECT</text>',
        f'<text x="56" y="212" font-size="20" fill="#111" font-weight="bold">{esc(name)}</text>',
        f'<text x="56" y="238" font-size="14" fill="#444">{esc(addr)}</text>',
    ]
    y = 320
    for label, value in fields:
        parts.append(f'<text x="56" y="{y}" font-size="13" fill="#888" font-weight="bold">{esc(label)}</text>')
        parts.append(f'<text x="56" y="{y+22}" font-size="17" fill="#111">{esc(value)}</text>')
        y += 60
    parts.append(f'<text x="380" y="950" text-anchor="middle" font-size="10" fill="#bbb">{esc(footer)}</text>')
    parts.append("</svg>")
    return "\n".join(parts)
