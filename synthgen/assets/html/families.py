"""Map each document kind to one of ~12 template families + a small accent config.
Keeps ~140 kinds covered by a handful of reusable, realistic HTML layouts.
"""

from __future__ import annotations

import re

# (regex on kind, family). First match wins — order specific → generic.
_RULES: list[tuple[str, str]] = [
    (r"invite|invitation", "invite"),
    (r"boarding-pass|ticket|hotel-booking|trip-itinerary|rental-car|reservation", "ticket"),
    (r"-log$|glucose|blood-pressure|sleep-tracking|ekg|heart-rate|step-count", "log_chart"),
    (r"passport|driver-licen|driving-licen|national-id|voter-id|student-id|employee-id|"
     r"residence-permit|visa-page|ssn-card|gym-card|business-card|insurance-card|"
     r"id-card|membership-card|vehicle-registration|library-card", "id_card"),
    (r"diploma|certificate|marriage-cert|birth-cert|naturaliz|vaccination|warranty|transcript-cert", "certificate"),
    (r"prescription|medication|doctor|discharge|therapy|lab-report|lab-result|medical|"
     r"vet-record|genomic|ekg-report|patient", "medical"),
    (r"court|summons|divorce|deed|title|police-report|immigration-form|permit-application|"
     r"public-filing|tax-return|w2|taxpayer-id|mortgage-document|notarized|affidavit", "legal"),
    (r"offer-letter|promotion|recommendation|referral|cover-letter|employment-contract|"
     r"lease-agreement|loan-agreement|performance-review|name-change|salary-letter|letter$", "letter"),
    (r"receipt|invoice|slip|purchase|order-confirmation", "receipt"),
    (r"bank|statement|mortgage-statement|credit-report|pay-stub|paystub|brokerage|"
     r"utility-bill|phone-bill|internet-bill|wire-transfer|toll-statement|loan", "financial"),
    (r"transcript|schedule|meal-plan|inventory|org-chart|exam-result|test-score|class-", "table"),
]

# Accent colour per family (header bands / rules), tuned to read like real documents.
FAMILY_ACCENT = {
    "financial": "#0f4c5c", "id_card": "#1a2958", "certificate": "#6b4f1d",
    "letter": "#27314a", "invite": "#d6336c", "log_chart": "#178a8a",
    "receipt": "#222222", "medical": "#5f0f40", "ticket": "#14464b",
    "table": "#2a3b2a", "legal": "#3c2414", "generic": "#3c3c46",
}


def family_for(kind: str) -> str:
    k = kind.replace(".real", "")
    for pat, fam in _RULES:
        if re.search(pat, k):
            return fam
    return "generic"


def accent_for(kind: str) -> str:
    return FAMILY_ACCENT.get(family_for(kind), FAMILY_ACCENT["generic"])
