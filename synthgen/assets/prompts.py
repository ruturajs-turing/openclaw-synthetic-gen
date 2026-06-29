"""Prompts for the Nanobanana image model, per the gold-standard spec (Downloads/gold.md):
real-world phone-camera captures of documents and natural casual portraits — NOT clean
flat scans or studio shots. The `.real` photos are produced image-to-image from the crisp
HTML render so the document content is preserved while the model adds a believable physical
scene, paper imperfections, lighting, and phone-camera character.
"""

from __future__ import annotations

import random

from .docgen import humanize
from .html.families import family_for

_NEG = ("Synthetic sample, no real logos, no real institutions, no real IDs, no official seals, "
        "no scannable QR or barcode, no celebrity likeness, no real signatures.")

_LEGIBLE = ("The page FILLS MOST OF THE FRAME and the whole document stays in SHARP FOCUS with "
            "EVERY LINE OF TEXT CRISP AND FULLY LEGIBLE, identical wording to the input.")

# family -> pool of capture scenarios (gold §11). Each is tuned to keep text legible.
_SCENARIOS = {
    "receipt": [
        "a faded thermal receipt resting on a car dashboard in afternoon sunlight, slightly curled with one crease, soft windshield glare in a corner, blurred dashboard vents behind",
        "a receipt on a kitchen counter next to a ceramic mug, warm overhead light, a small curl at the edge, crumbs and a blurred fruit bowl in the background",
    ],
    "invite": [
        "a printed invitation card standing on a wooden table with a warm blurred living-room background and soft bokeh lights, gentle daylight",
        "a colorful invitation held in one hand near a window, soft daylight, slight paper curve, thumb at the lower edge",
    ],
    "id_card": [
        "an ID card lying flat on a dark desk surface, photographed from almost directly above, even soft light, faint shadow, slight rotation",
    ],
    "log_chart": [
        "a printed chart on a nightstand in warm lamp light, photographed from above, one faint fold line across the middle, soft shadow",
    ],
    "letter": [
        "a printed letter on a wooden desk photographed from near-overhead, a pen and the edge of a notebook at the margins, warm light, a slightly bent corner",
        "a letter held in one hand near a window with soft side light, the page curving slightly, thumb visible at one edge",
    ],
    "_default": [
        "the printed page lying slightly rotated on a wooden office desk with a pen, sticky notes and the edge of a coffee mug at the margins, warm overhead light, soft shadow and one dog-eared corner",
        "the printed page on a wrinkled bedsheet in soft morning window light, off-centre with a bent lower corner and light creases",
        "the printed report on a cluttered desk beside a laptop edge and a charging cable, mixed warm and cool light, faint fold lines",
    ],
}


# Authentic real-world layouts per document family (researched), so generated documents
# follow genuine conventions. Fictional data/orgs only — never real logos or institutions.
REAL_LAYOUT_HINTS = {
    "id_card": ("a real ID document layout: holder portrait photo, full name, document number, "
                "date of birth, sex, nationality, date of issue and expiry, issuing authority; "
                "passports also carry a 2-line machine-readable zone of 44 monospaced characters "
                "using < fillers along the bottom (ICAO 9303)"),
    "financial": ("a real statement/payslip layout: institution name + statement period header, "
                  "account-holder block, a summary band (opening / money in / money out / closing — "
                  "or gross pay, deductions, net pay, year-to-date), then a dated line-item table "
                  "with amounts and a running balance"),
    "medical": ("a real clinical lab report layout: lab/clinic header, patient block (name, DOB, sex, "
                "ordering physician, collection date), then a results table with columns "
                "Test / Result + unit / Reference range / Flag (H, L or Normal)"),
    "receipt": ("a real receipt layout: merchant name + address centered at top, date and time, "
                "itemized lines with prices, subtotal, tax, total, and a payment-method footer"),
    "ticket": ("a real boarding-pass layout: airline + flight number, passenger name, from/to airport "
               "codes, date, gate, seat, boarding group, a barcode strip, and a detachable stub"),
    "certificate": ("a real certificate layout: decorative border, large title, 'this certifies that "
                    "<name>', the achievement, date, an embossed seal, and signature lines"),
    "letter": ("a real formal letter layout: letterhead, date, recipient address block, salutation, "
               "body paragraphs, closing and signature"),
    "legal": ("a real court/legal document layout: court name centered, case number, party caption, "
              "numbered clauses in formal legal language, and a clerk signature/seal at the foot"),
    "log_chart": "a real tracking chart: titled axis with a plotted line of dated readings and units",
    "invite": "a real event invitation: decorative card, headline, celebrant/event, date/time/location, RSVP contact",
}


def layout_hint(kind: str) -> str:
    return REAL_LAYOUT_HINTS.get(family_for(kind), "")


def is_portrait(kind: str) -> bool:
    return kind in {"avatar", "profile-photo", "face", "selfie"}


def build_portrait_prompt(pa) -> str:
    appearance = pa.context.get("appearance") or "a person with a natural, relaxed expression"
    return (
        f"A realistic synthetic profile photo of a fictional person: {appearance}. "
        "It should look like a normal phone-camera portrait, NOT a studio shoot: natural facial "
        "asymmetry, realistic skin texture with subtle imperfections, slightly imperfect hair, "
        "normal everyday clothing, and a believable casual background (apartment wall, bookshelf, "
        "or office). Imperfect but flattering soft lighting, mild phone-camera compression, "
        "realistic depth of field, natural color balance. No glamour retouching, no plastic skin, "
        "no uncanny symmetry, no celebrity or real-person likeness, no logos or ID badges."
    )


def build_realphoto_prompt(pa, rng: random.Random) -> str:
    fam = family_for(pa.entry.kind)
    pool = _SCENARIOS.get(fam, _SCENARIOS["_default"])
    scene = rng.choice(pool)
    hint = REAL_LAYOUT_HINTS.get(fam, "")
    hint_txt = f"Preserve {hint}. " if hint else ""
    return (
        f"Re-photograph this exact '{humanize(pa.entry.kind)}' as a casual, realistic smartphone "
        f"photo: {scene}. Photographed from near-overhead, only slightly rotated (3–8 degrees). "
        f"{hint_txt}{_LEGIBLE} Natural phone-camera character — subtle grain, mild perspective, "
        f"realistic shadows — but the document text must remain perfectly readable. Documentary "
        f"style, like a normal person quickly photographed a real paper; not a product mockup, not "
        f"cinematic. {_NEG}"
    )
