"""Per-task / per-persona document + PII extraction. Joins the manifest with the persona's
PII vault, data labels, and generated tasks to produce an AssetPlan (one PlannedAsset per
manifest entry) and a machine-readable pii_index.json (asset path -> PII fields + tiers).
This is the authoritative answer to "every document required, and the PII inside it".
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .loader import ManifestEntry, load_for
from ._pii import DATA_LEVEL_MAP

# kind substring -> canonical PII labels likely rendered into that asset.
KIND_PII_HINTS: dict[str, list[str]] = {
    "passport": ["GOV_PASSPORT_NUM", "ID_FULL_NAME", "BIO_PHOTO_FACE"],
    "driver": ["GOV_DL_NUM", "ID_FULL_NAME", "LOC_HOME_ADDR", "BIO_PHOTO_FACE"],
    "national-id": ["GOV_NATIONAL_ID", "ID_FULL_NAME", "BIO_PHOTO_FACE"],
    "voter": ["GOV_VOTER_RECORD", "ID_FULL_NAME", "LOC_HOME_ADDR"],
    "ssn": ["GOV_SSN_FULL"],
    "tax": ["GOV_TIN", "FIN_SALARY", "ID_FULL_NAME"],
    "bank-statement": ["FIN_BANK_ACCT", "FIN_PAN_LAST4", "ID_FULL_NAME", "LOC_HOME_ADDR"],
    "paystub": ["FIN_SALARY", "ID_FULL_NAME", "GOV_TIN"],
    "pay-stub": ["FIN_SALARY", "ID_FULL_NAME"],
    "credit": ["FIN_PAN_FULL", "FIN_CVV", "ID_FULL_NAME"],
    "invoice": ["FIN_TRANSACTION", "ID_FULL_NAME"],
    "insurance": ["HEALTH_INSURANCE_ID", "ID_FULL_NAME"],
    "prescription": ["HEALTH_MEDICATION", "HEALTH_DIAGNOSIS", "ID_FULL_NAME"],
    "medical": ["HEALTH_DIAGNOSIS", "HEALTH_MEDICATION", "ID_FULL_NAME"],
    "lab": ["HEALTH_LAB_RESULT", "ID_FULL_NAME"],
    "xray": ["HEALTH_IMAGING", "BIO_PHOTO_FACE"],
    "ultrasound": ["HEALTH_IMAGING"],
    "dental": ["HEALTH_IMAGING", "ID_FULL_NAME"],
    "biometric-face": ["BIO_FACE_EMBEDDING", "BIO_PHOTO_FACE"],
    "fingerprint": ["BIO_FINGERPRINT_TEMPLATE"],
    "iris": ["BIO_IRIS_TEMPLATE"],
    "voiceprint": ["BIO_VOICEPRINT"],
    "dna": ["HEALTH_GENETIC"],
    "avatar": ["BIO_PHOTO_FACE", "ID_FULL_NAME"],
    "profile-photo": ["BIO_PHOTO_FACE"],
    "face": ["BIO_PHOTO_FACE"],
    "address-book": ["ID_FULL_NAME", "ID_PHONE", "ID_EMAIL"],
    "contact": ["ID_FULL_NAME", "ID_PHONE", "ID_EMAIL"],
    "api-token": ["AUTH_API_KEY"],
    "password": ["AUTH_PASSWORD", "AUTH_USERNAME"],
    "birth-certificate": ["ID_FULL_NAME", "ID_DOB", "FAM_PARENT"],
    "gps": ["LOC_GPS_PRECISE"],
    "background-check": ["GOV_SSN_FULL", "ID_FULL_NAME", "LEGAL_PUBLIC_CONVICTION"],
    "dating-profile": ["DEMO_SEXUAL_ORIENTATION", "BIO_PHOTO_FACE"],
    "chat-export": ["COMM_DM_BODY"],
    "email": ["COMM_EMAIL_BODY", "COMM_SUBJECT_LINE"],
}


# Curated essential documents for the "minimal" doc set — one coherent everyday bundle
# (identity, finance, health, personal) instead of the full ~457-asset manifest.
MINIMAL_KINDS = {
    "avatar", "passport-page", "driver-license", "national-id-card", "employee-id-badge",
    "business-card", "bank-statement", "pay-stub", "paystub", "utility-bill", "invoice",
    "tax-return", "medical-prescription", "health-insurance-card", "lab-report",
    "resume", "email-message", "address-book-export", "boarding-pass", "birth-certificate",
}


def is_minimal_kind(kind: str) -> bool:
    return kind.replace(".real", "") in MINIMAL_KINDS


@dataclass
class PlannedAsset:
    persona_id: str
    entry: ManifestEntry
    out_path: Path
    pii_fields: list[str] = field(default_factory=list)
    pii_tiers: list[str] = field(default_factory=list)
    context: dict = field(default_factory=dict)


def _pii_for_kind(kind: str, persona_labels: set[str]) -> list[str]:
    fields: list[str] = []
    for sub, labels in KIND_PII_HINTS.items():
        if sub in kind:
            fields.extend(labels)
    # Keep labels the persona actually carries when known; always keep ID/name/photo basics.
    keep = [f for f in fields if f in persona_labels or f.startswith(("ID_", "BIO_PHOTO", "GOV_", "FIN_", "HEALTH_", "AUTH_", "LOC_", "COMM_"))]
    return sorted(set(keep))


def _tier(label: str) -> str:
    return DATA_LEVEL_MAP.get(label, "L2")


def build_plan(run_dir: Path, persona: dict, tasks: list[dict],
               mem_state: dict | None = None, minimal: bool = False) -> list[PlannedAsset]:
    pid = persona["persona_id"]
    persona_labels = set(persona.get("data_labels", []))
    # Union of PII the tasks actually exercise (so doc PII reflects real task usage).
    task_pii = {f for t in tasks for f in t.get("pii_fields_exercised", [])}

    # Reuse the LLM-written everyday-text bodies (email/blog/diary/etc.) as real content
    # for the matching document kinds.
    apack = {}
    apath = run_dir / "personas" / pid / "asset_pack.json"
    if apath.exists():
        try:
            apack = json.loads(apath.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            apack = {}

    ctx_base = {
        "full_name": persona.get("full_name"),
        "dob": persona.get("date_of_birth"),
        "city": persona.get("city"),
        "country_code": persona.get("country_code"),
        "primary_language": persona.get("primary_language"),
        "appearance": (mem_state or {}).get("appearance_descriptor"),
        "tts_voice": (mem_state or {}).get("tts_voice"),
        "pii_vault": persona.get("pii_vault", {}),
        "asset_pack": apack,
    }

    plan: list[PlannedAsset] = []
    for e in load_for(pid):
        if minimal and not is_minimal_kind(e.kind):
            continue
        pii = _pii_for_kind(e.kind, persona_labels)
        # fold in any task-exercised PII that shares a prefix with this asset's hinted PII
        if pii:
            prefixes = {p.split("_")[0] for p in pii}
            pii = sorted(set(pii) | {tp for tp in task_pii if tp.split("_")[0] in prefixes})
        tiers = sorted({_tier(p) for p in pii})
        plan.append(PlannedAsset(
            persona_id=pid, entry=e, out_path=run_dir / e.path,
            pii_fields=pii, pii_tiers=tiers, context=ctx_base,
        ))
    return plan


def write_pii_index(run_dir: Path, pid: str, plan: list[PlannedAsset]) -> Path:
    index = {
        pa.entry.path: {
            "kind": pa.entry.kind, "modality": pa.entry.modality,
            "pii_fields": pa.pii_fields, "pii_tiers": pa.pii_tiers,
        }
        for pa in plan
    }
    out = run_dir / "personas" / pid / "pii_index.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    return out
