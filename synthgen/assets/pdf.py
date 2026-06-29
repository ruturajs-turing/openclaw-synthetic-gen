"""PDF generator (reportlab — offline, no API cost). Renders a real-content document from
the shared docgen field templates: coloured header band, small 'SPECIMEN' subtitle, subject
box, labelled fields with the persona's real synthetic PII, and a tiny footer marker. No
large centre watermark.
"""

from __future__ import annotations

import random

from . import docgen
from .dispatcher import register
from ..manifest.extract import PlannedAsset
from ..config import Settings
from ..costs import CostModel
from ..events import EventBus


async def _generate(pa: PlannedAsset, settings: Settings, bus: EventBus, costs: CostModel) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    rng = random.Random(f"{pa.persona_id}:{pa.entry.id}")
    title = docgen.humanize(pa.entry.kind)
    cc = pa.context.get("country_code", "")
    name = pa.context.get("full_name", "")
    addr = docgen._addr(pa.context)
    fields = docgen.derive_fields(pa, rng)
    r, g, b = [c / 255 for c in docgen._CATEGORY_COLOR[docgen._category(pa.entry.kind)]]

    c = canvas.Canvas(str(pa.out_path), pagesize=A4)
    W, H = A4
    # Header band
    c.setFillColorRGB(r, g, b)
    c.rect(0, H - 90, W, 90, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(48, H - 52, title)
    c.setFont("Helvetica", 10)
    c.drawString(48, H - 74, f"SPECIMEN · {cc} · synthetic, no real PII")
    # Subject box
    c.setFillColorRGB(0.96, 0.97, 0.98)
    c.roundRect(48, H - 200, W - 96, 86, 8, fill=1, stroke=0)
    c.setFillColorRGB(0.53, 0.53, 0.53)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(64, H - 132, "SUBJECT")
    c.setFillColorRGB(0.07, 0.07, 0.07)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(64, H - 154, name)
    c.setFont("Helvetica", 11)
    c.setFillColorRGB(0.27, 0.27, 0.27)
    c.drawString(64, H - 174, str(addr)[:80])
    # Fields
    y = H - 240
    for label, value in fields:
        c.setFont("Helvetica-Bold", 9)
        c.setFillColorRGB(0.53, 0.53, 0.53)
        c.drawString(64, y, label)
        c.setFont("Helvetica", 13)
        c.setFillColorRGB(0.07, 0.07, 0.07)
        c.drawString(64, y - 18, str(value)[:80])
        y -= 48
    # Tiny footer marker (no centre watermark)
    c.setFont("Helvetica", 8)
    c.setFillColorRGB(0.73, 0.73, 0.73)
    c.drawCentredString(W / 2, 30, f"SYNTHETIC — AI-agent trajectory testing only · no real PII · {pa.entry.kind}")
    c.showPage()
    c.save()


register("pdf")(_generate)
