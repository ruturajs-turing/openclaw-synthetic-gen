"""Load and enrich personas from personas-250-textual.json (or legacy privacy-personas.json)."""

import json
from pathlib import Path
from typing import Any


def load_personas(path: Path) -> list[dict[str, Any]]:
    """Load personas and enrich with derived fields useful for task generation."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    raw = data.get("personas", data) if isinstance(data, dict) else data
    if isinstance(raw, dict):
        raw = list(raw.values())

    enriched = []
    for p in raw:
        _is_v2 = "bio" in p or "communication_style" in p
        if _is_v2:
            _enrich_v2(p)
        else:
            _enrich_v1(p)
        enriched.append(p)

    return enriched


# ---------------------------------------------------------------------------
# V2 enrichment (pii-free-personas-250 / personas-250-textual.json)
# ---------------------------------------------------------------------------

def _enrich_v2(p: dict) -> None:
    """Derive task-generation fields from the new 250-persona schema."""
    p["_platforms"] = sorted(p.get("platform_presence", {}).keys())
    p["_pii_summary"] = _summarize_pii(p.get("pii_vault", {}))
    p["_data_level_map"] = _map_data_levels(p.get("data_labels", []))
    p["_connection_summary"] = _summarize_relationships(p)

    p.setdefault("first_name", p.get("full_name_display", "").split()[0] if p.get("full_name_display") else "")
    p.setdefault("last_name", " ".join(p.get("full_name_display", "").split()[1:]) if p.get("full_name_display") else "")

    stratum = p.get("stratum", "")
    p["_stratum_label"] = _stratum_label(stratum)
    p["_occupation_sector"] = _sector_from_stratum(stratum)

    p.setdefault("occupation_sector", p["_occupation_sector"])

    p.setdefault("education_level", _education_from_stratum(stratum))
    p.setdefault("exact_age", p.get("exact_age"))

    p.setdefault("children_count", max(0, p.get("household_size", 1) - 1) if p.get("marital_status") == "family" else 0)

    if not p.get("hobbies"):
        p["hobbies"] = {}

    p["_personality_tag"] = _personality_tag(p.get("personality", {}))
    p["_comm_tag"] = _comm_tag(p.get("communication_style", {}))

    mem_files = p.get("workspace", {}).get("memory_files", [])
    p["_memory_files"] = mem_files
    p["_memory_file_count"] = len(mem_files)

    crosslinks = p.get("crosslinks", [])
    p["_crosslink_names"] = list({
        cl.get("with_name", "") for cl in crosslinks if cl.get("with_name")
    })

    p["_has_dev_credentials"] = bool(p.get("pii_vault", {}).get("dev_credentials"))
    p["_has_biometrics"] = bool(p.get("pii_vault", {}).get("biometrics"))
    p["_has_special_category"] = bool(p.get("pii_vault", {}).get("special_category"))
    p["_has_vehicles"] = bool(p.get("pii_vault", {}).get("property", {}).get("vehicles"))


# ---------------------------------------------------------------------------
# V1 enrichment (legacy privacy-personas.json)
# ---------------------------------------------------------------------------

def _enrich_v1(p: dict) -> None:
    """Derive fields from the old 225-persona schema (backward compat)."""
    p["_platforms"] = sorted(
        k for k, v in p.get("platform_presence", {}).items() if v
    )
    p["_pii_summary"] = _summarize_pii(p.get("pii_vault", {}))
    p["_data_level_map"] = _map_data_levels(p.get("data_labels", []))
    p["_connection_summary"] = _summarize_connections_v1(p.get("connections", []))
    p["_stratum_label"] = ""
    p["_personality_tag"] = ""
    p["_comm_tag"] = ""
    p["_memory_files"] = []
    p["_memory_file_count"] = 0
    p["_crosslink_names"] = []
    p["_has_dev_credentials"] = False
    p["_has_biometrics"] = False
    p["_has_special_category"] = False
    p["_has_vehicles"] = False


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _summarize_pii(vault: dict) -> dict[str, list[str]]:
    """Return category -> list of field names that have values."""
    summary = {}
    for category, fields in vault.items():
        if isinstance(fields, dict):
            present = [k for k, v in fields.items() if v]
            if present:
                summary[category] = present
    return summary


DATA_LEVEL_MAP: dict[str, str] = {
    # ── L0: Public / non-sensitive ─────────────────────────────────────────
    "FIN_ROUTING_ALONE": "L0",
    "LOC_COUNTRY": "L0",
    "LOC_REGION": "L0",
    "PUB_AGGREGATE_STAT": "L0",
    "PUB_FILING_PUBLISHED": "L0",
    "PUB_GENERAL_KNOWLEDGE": "L0",
    "PUB_OPEN_PUBLICATION": "L0",
    "PUB_OSS_CODE": "L0",

    # ── L1: Caution ────────────────────────────────────────────────────────
    "BEHAV_AGGREGATE": "L1",
    "COMM_FREQUENCY_STAT": "L1",
    "COMM_TIMESTAMP": "L1",
    "CORP_CODENAME": "L1",
    "CORP_INTERNAL_URL": "L1",
    "CORP_REPO_SHA": "L1",
    "DEMO_AGE_BRACKET": "L1",
    "DEMO_LANGUAGE": "L1",
    "DEV_COOKIE_ID": "L1",
    "DEV_FINGERPRINT": "L1",
    "DEV_IDFA": "L1",
    "DEV_INSTALL_ID": "L1",
    "DEV_IP_ADDR": "L1",
    "DEV_MAC": "L1",
    "DEV_OS_VERSION": "L1",
    "DEV_PUSH_TOKEN": "L1",
    "DEV_USER_AGENT": "L1",
    "EMP_INDUSTRY": "L1",
    "FAM_RELATIONSHIP_STATUS": "L1",
    "HEALTH_BLOOD_TYPE": "L1",
    "HEALTH_VITAL": "L1",
    "ID_AREA_CODE": "L1",
    "ID_EMAIL_DOMAIN": "L1",
    "LOC_CITY": "L1",
    "LOC_GPS_CITY": "L1",
    "LOC_IP_GEO_CITY": "L1",
    "LOC_TIMEZONE": "L1",
    "META_FILE_TIMESTAMP": "L1",
    "NET_DEVICE_ID": "L1",

    # ── L2: Sensitive ──────────────────────────────────────────────────────
    "AI_FT_DATASET_SANITIZED": "L2",
    "AI_PROMPT_TEMPLATE": "L2",
    "AUTH_PUBLIC_KEY": "L2",
    "AUTH_USERNAME": "L2",
    "BEHAV_APP_USAGE": "L2",
    "BEHAV_BROWSE_HISTORY": "L2",
    "BEHAV_PURCHASE_HISTORY": "L2",
    "BEHAV_SEARCH_HISTORY": "L2",
    "BIO_PHYSICAL_DESC": "L2",
    "COMM_RECIPIENT_LIST": "L2",
    "COMM_SUBJECT_LINE": "L2",
    "CORP_INTERNAL_DOC": "L2",
    "CORP_ORG_CHART": "L2",
    "CORP_ROADMAP": "L2",
    "DEMO_GENDER": "L2",
    "DEMO_MARITAL": "L2",
    "EDU_INSTITUTION": "L2",
    "EMP_EMPLOYER": "L2",
    "EMP_ID": "L2",
    "EMP_TITLE": "L2",
    "FAM_HOUSEHOLD": "L2",
    "FAM_PARENT": "L2",
    "FAM_SPOUSE": "L2",
    "FIN_BILLING_ADDR": "L2",
    "FIN_CUSTOMER_ID": "L2",
    "FIN_PAN_LAST4": "L2",
    "FIN_TRANSACTION": "L2",
    "FIN_WALLET_ADDR": "L2",
    "GOV_NATIONALITY": "L2",
    "GOV_SSN_LAST4": "L2",
    "HEALTH_INSURANCE_ID": "L2",
    "HEALTH_PATIENT_MRN": "L2",
    "HEALTH_PROVIDER_APPT": "L2",
    "ID_DOB": "L2",
    "ID_EMAIL": "L2",
    "ID_FULL_NAME": "L2",
    "ID_PHONE": "L2",
    "ID_SOCIAL_HANDLE": "L2",
    "LEGAL_PUBLIC_CONVICTION": "L2",
    "LEGAL_PUBLIC_FILING": "L2",
    "LOC_POSTAL": "L2",
    "LOC_STREET_ADDR": "L2",
    "META_AUTHOR_FIELD": "L2",
    "PROP_VEHICLE_VIN": "L2",

    # ── L3: Highly sensitive ───────────────────────────────────────────────
    "AI_EVAL_SET": "L3",
    "AI_SYSTEM_PROMPT_PROPRIETARY": "L3",
    "AI_TRAINING_DATA_PII": "L3",
    "AUTH_SECURITY_QA": "L3",
    "AUTH_SESSION_TOKEN": "L3",
    "BEHAV_INFERRED_SENSITIVE": "L3",
    "BIO_PHOTO_FACE": "L3",
    "BIO_VOICE_RECORDING": "L3",
    "COMM_CALL_TRANSCRIPT": "L3",
    "COMM_DM_BODY": "L3",
    "COMM_DRAFT": "L3",
    "COMM_EMAIL_BODY": "L3",
    "COMM_SMS_BODY": "L3",
    "CORP_CUSTOMER_LIST": "L3",
    "CORP_INTERNAL_FIN": "L3",
    "CORP_SOURCE_CODE_CRITICAL": "L3",
    "DEMO_ETHNICITY": "L3",
    "DEMO_IMMIGRATION": "L3",
    "DEMO_POLITICAL": "L3",
    "DEMO_RELIGION": "L3",
    "DEMO_SEXUAL_ORIENTATION": "L3",
    "DEMO_UNION": "L3",
    "EDU_DISABILITY_ACCOM": "L3",
    "EDU_GRADES": "L3",
    "EMP_BACKGROUND_CHECK": "L3",
    "EMP_DISCIPLINARY": "L3",
    "EMP_PERF_REVIEW": "L3",
    "FAM_ABUSE_CONTACT": "L3",
    "FAM_ADOPTION": "L3",
    "FAM_CUSTODY": "L3",
    "FAM_MINOR_PII": "L3",
    "FIN_BALANCE": "L3",
    "FIN_CREDIT_REPORT": "L3",
    "FIN_SALARY": "L3",
    "FIN_STATEMENT": "L3",
    "FIN_TAX_RETURN": "L3",
    "GOV_VISA_STATUS": "L3",
    "GOV_VOTER_RECORD": "L3",
    "HEALTH_ADDICTION": "L3",
    "HEALTH_DIAGNOSIS": "L3",
    "HEALTH_DISABILITY": "L3",
    "HEALTH_IMAGING": "L3",
    "HEALTH_LAB_RESULT": "L3",
    "HEALTH_MEDICATION": "L3",
    "HEALTH_MENTAL_HEALTH": "L3",
    "HEALTH_REPRODUCTIVE": "L3",
    "HEALTH_THERAPY_NOTE": "L3",
    "LEGAL_INVESTIGATION_OPEN": "L3",
    "LEGAL_JUVENILE_RECORD": "L3",
    "LEGAL_PROTECTION_ORDER": "L3",
    "LEGAL_SEALED_RECORD": "L3",
    "LEGAL_VICTIM_ID": "L3",
    "LEGAL_WITNESS_ID": "L3",
    "LOC_GPS_PRECISE": "L3",
    "LOC_HOME_ADDR": "L3",
    "LOC_INDOOR_POSITION": "L3",
    "LOC_REALTIME_STREAM": "L3",
    "META_EXIF_GPS": "L3",
    "META_TRACK_CHANGES": "L3",

    # ── L4: Critical ───────────────────────────────────────────────────────
    "AI_JAILBREAK_PAYLOAD": "L4",
    "AI_RLHF_RAW_W_ANNOTATOR": "L4",
    "AI_UNRELEASED_WEIGHTS": "L4",
    "AUTH_API_KEY": "L4",
    "AUTH_OAUTH_REFRESH": "L4",
    "AUTH_PASSWORD": "L4",
    "AUTH_PRIVATE_KEY": "L4",
    "AUTH_RECOVERY_CODE": "L4",
    "AUTH_TOTP_SEED": "L4",
    "BIO_DNA_RAW": "L4",
    "BIO_FACE_EMBEDDING": "L4",
    "BIO_FINGERPRINT_TEMPLATE": "L4",
    "BIO_IRIS_TEMPLATE": "L4",
    "BIO_VOICEPRINT": "L4",
    "COMM_PRIVILEGED": "L4",
    "CORP_CUSTOMER_DUMP": "L4",
    "CORP_MODEL_WEIGHTS_FRONTIER": "L4",
    "CORP_PREANN_FINANCIAL": "L4",
    "CORP_TRADE_SECRET": "L4",
    "CORP_VULN_PREDISCLOSURE": "L4",
    "DEV_ENV_FILE": "L4",
    "FIN_BANK_ACCT": "L4",
    "FIN_CRYPTO_PRIVKEY": "L4",
    "FIN_CRYPTO_SEED": "L4",
    "FIN_CVV": "L4",
    "FIN_IBAN": "L4",
    "FIN_PAN_FULL": "L4",
    "GOV_DL_NUM": "L4",
    "GOV_NATIONAL_ID": "L4",
    "GOV_PASSPORT_NUM": "L4",
    "GOV_SSN_FULL": "L4",
    "GOV_TIN_PERSON": "L4",
    "HEALTH_GENETIC": "L4",

    # ── Aliases: legacy labels from prior batches → correct level ──────────
    "GOV_SSN": "L4",
    "GOV_PASSPORT": "L4",
    "GOV_DL": "L4",
    "GOV_TIN": "L4",
    "FIN_PAN": "L4",
    "BIO_FACE": "L3",
    "BIO_FACE_IMAGE": "L3",
    "BIO_FINGERPRINT": "L4",
    "BIO_IRIS": "L4",
    "BIO_DNA": "L4",
    "DEV_SSH_KEY": "L4",
    "DEV_SSH_KEYS": "L4",
    "DEV_GIT_TOKEN": "L4",
    "DEV_GIT_TOKENS": "L4",
    "DEV_CLOUD_CRED": "L4",
    "DEV_CLOUD_CREDENTIALS": "L4",
    "DEV_GPG_KEY": "L4",
    "DEV_GPG_KEYS": "L4",
    "DEV_API_TOKEN": "L4",
    "DEV_API_TOKENS": "L4",
    "DEV_ENV_FILES": "L4",
    "AUTH_SSH_KEY": "L4",
    "AUTH_SSH_KEYS": "L4",
    "AUTH_RECOVERY_CODES": "L4",
    "SPECIAL_RELIGION": "L3",
    "SPECIAL_ETHNICITY": "L3",
    "SPECIAL_SEXUAL_ORIENT": "L3",
    "SPECIAL_POLITICAL": "L3",
    "NET_IP_ADDRESS": "L1",
    "NET_MAC_ADDRESS": "L1",
    "PROP_VEHICLE_PLATE": "L2",
}


def _map_data_levels(labels: list[str]) -> dict[str, list[str]]:
    """Group persona's data labels by their sensitivity level."""
    levels: dict[str, list[str]] = {"L0": [], "L1": [], "L2": [], "L3": [], "L4": []}
    for label in labels:
        level = DATA_LEVEL_MAP.get(label, "L2")
        levels[level].append(label)
    return levels


def _summarize_relationships(p: dict) -> str:
    """Text summary of social graph from v2 schema."""
    parts = []
    for rel in p.get("relationships", []):
        role = rel.get("role", "unknown")
        eid = rel.get("entity_id", "?")
        parts.append(f"{role} ({eid})")
    for ce in p.get("context_entities", []):
        name = ce.get("display_name", "?")
        role = ce.get("entity_role", "?")
        parts.append(f"{name} [{role}]")
    return "; ".join(parts) if parts else "No connections."


def _summarize_connections_v1(connections: list[dict]) -> str:
    """Text summary from legacy connections array."""
    if not connections:
        return "No connections."
    parts = []
    for c in connections:
        parts.append(f"{c['type']} → {c['persona_id']} (shared: {', '.join(c.get('shared', []))})")
    return "; ".join(parts)


def _stratum_label(stratum: str) -> str:
    labels = {
        "S1_developer_researcher": "S1 Developer/Researcher",
        "S2_creative_professional": "S2 Creative Professional",
        "S3_proficient_professional": "S3 Proficient Professional",
        "S4_knowledge_worker": "S4 Knowledge Worker",
        "S5_general_user": "S5 General User",
    }
    return labels.get(stratum, stratum or "Unknown")


def _sector_from_stratum(stratum: str) -> str:
    mapping = {
        "S1_developer_researcher": "software_tech",
        "S2_creative_professional": "creative_arts",
        "S3_proficient_professional": "finance_legal",
        "S4_knowledge_worker": "data_analytics",
        "S5_general_user": "retail",
    }
    return mapping.get(stratum, "general")


def _education_from_stratum(stratum: str) -> str:
    mapping = {
        "S1_developer_researcher": "Master's or PhD",
        "S2_creative_professional": "Bachelor's",
        "S3_proficient_professional": "Bachelor's",
        "S4_knowledge_worker": "Bachelor's",
        "S5_general_user": "High School or Associate's",
    }
    return mapping.get(stratum, "Unknown")


def _personality_tag(personality: dict) -> str:
    """Short tag summarizing personality for prompt."""
    mbti = personality.get("mbti", "")
    temperament = personality.get("temperament", "")
    humor = personality.get("humor_style", "")
    values = personality.get("values", [])
    parts = [x for x in [mbti, temperament, humor] if x]
    if values:
        parts.append(f"values: {', '.join(values[:3])}")
    return " / ".join(parts) if parts else ""


def _comm_tag(comm: dict) -> str:
    """Short tag summarizing communication style."""
    parts = []
    for key in ("tone", "formality", "verbosity", "emoji_use"):
        val = comm.get(key, "")
        if val:
            parts.append(f"{key}={val}")
    return ", ".join(parts) if parts else ""


# ---------------------------------------------------------------------------
# Prompt brief builders
# ---------------------------------------------------------------------------

def persona_brief(p: dict) -> str:
    """Build a concise text profile for prompt injection.

    Automatically detects v1 vs v2 schema and adjusts output.
    """
    if "bio" in p or "communication_style" in p:
        return _persona_brief_v2(p)
    return _persona_brief_v1(p)


def _persona_brief_v2(p: dict) -> str:
    """Rich persona brief for the new 250-persona schema."""
    name = p.get("full_name_display", f"{p.get('first_name', '')} {p.get('last_name', '')}").strip()
    pid = p.get("persona_id", "?")
    age = p.get("exact_age", "?")
    gender = p.get("gender", "?")
    city = p.get("city", "?")
    country = p.get("country", "?")

    lines = [
        f"Persona: {name} ({pid})",
        f"Age {age}, {gender}, {city}, {country}",
        f"Stratum: {p.get('_stratum_label', p.get('stratum', '?'))}",
        f"Job: {p.get('job_title', '?')} at {p.get('employer', '?')} (team: {p.get('work_team', '?')})",
        f"Language: {p.get('primary_language', '?')}",
        f"Household: {p.get('marital_status', '?')}, size {p.get('household_size', '?')}",
    ]

    bio = p.get("bio", "")
    if bio:
        lines.append(f"\nBio: {bio}")

    personality = p.get("personality", {})
    if personality:
        mbti = personality.get("mbti", "?")
        big5 = (
            f"O{personality.get('openness', '?'):.2f} "
            f"C{personality.get('conscientiousness', '?'):.2f} "
            f"E{personality.get('extraversion', '?'):.2f} "
            f"A{personality.get('agreeableness', '?'):.2f} "
            f"N{personality.get('neuroticism', '?'):.2f}"
        ) if personality.get("openness") is not None else ""
        lines.append(
            f"Personality: {mbti}, {personality.get('temperament', '?')}, "
            f"humor={personality.get('humor_style', '?')}, "
            f"values={personality.get('values', [])}"
        )
        if big5:
            lines.append(f"Big Five: {big5}")
        lines.append(
            f"Digital engagement: {personality.get('digital_engagement_intensity', '?')}, "
            f"Content creation: {personality.get('content_creation_propensity', '?')}"
        )

    comm = p.get("communication_style", {})
    if comm:
        lines.append(
            f"Communication: tone={comm.get('tone', '?')}, formality={comm.get('formality', '?')}, "
            f"verbosity={comm.get('verbosity', '?')}, emoji={comm.get('emoji_use', '?')}"
        )
        catchphrases = comm.get("catchphrases", [])
        if catchphrases:
            lines.append(f"Catchphrases: {' | '.join(catchphrases[:3])}")
        langs = comm.get("languages_spoken", [])
        if langs:
            lines.append(f"Languages spoken: {', '.join(langs)}")

    inner = p.get("inner_life", "")
    if inner:
        lines.append(f"\nInner life: {inner[:300]}")

    pvp = p.get("public_vs_private", "")
    if pvp:
        lines.append(f"Public vs private: {pvp}")

    aspirations = p.get("aspirations", [])
    if aspirations:
        lines.append(f"Aspirations: {'; '.join(aspirations[:3])}")

    obsession = p.get("signature_obsession", "")
    if obsession:
        lines.append(f"Signature obsession: {obsession}")

    hyperfixation = p.get("current_hyperfixation", "")
    if hyperfixation:
        lines.append(f"Current hyperfixation: {hyperfixation}")

    contradictions = p.get("contradictions", [])
    if contradictions:
        lines.append(f"Contradictions: {'; '.join(contradictions[:2])}")

    hobbies = p.get("hobbies", {})
    if hobbies:
        hobby_tags = []
        for category, items in hobbies.items():
            if isinstance(items, list):
                hobby_tags.extend(items[:3])
            elif isinstance(items, str):
                hobby_tags.append(items)
        lines.append(f"Hobbies: {', '.join(str(h) for h in hobby_tags[:8])}")

    dislikes = p.get("dislikes", [])
    if dislikes:
        lines.append(f"Dislikes: {', '.join(dislikes[:4])}")

    food = p.get("food_preferences", [])
    if food:
        lines.append(f"Food preferences: {', '.join(food)}")

    places = p.get("favorite_places", [])
    if places:
        lines.append(f"Favorite places: {', '.join(places[:3])}")

    daily_life = p.get("daily_life", [])
    if daily_life:
        lines.append(f"Daily routines: {'; '.join(daily_life[:4])}")

    possessions = p.get("possessions", [])
    if possessions:
        lines.append(f"Key possessions: {', '.join(possessions[:6])}")

    lifestyle = p.get("lifestyle", {})
    if lifestyle:
        devices = lifestyle.get("devices", {})
        if devices:
            lines.append(f"Devices: laptop={devices.get('laptop', '?')}, phone={devices.get('phone_os', '?')}")
        subs = lifestyle.get("subscriptions", [])
        if subs:
            lines.append(f"Subscriptions: {', '.join(subs)}")

    money = p.get("money_attitude", "")
    if money:
        lines.append(f"Money attitude: {money}")

    roots = p.get("roots", {})
    if roots:
        migration = roots.get("migration_story", "")
        if migration:
            lines.append(f"Roots: {migration[:200]}")

    rel_narr = p.get("relationships_narrative", "")
    if rel_narr:
        lines.append(f"\nRelationships: {rel_narr[:300]}")

    lines.append(f"\nPlatforms: {', '.join(p.get('_platforms', []))}")
    lines.append(f"Data labels: {', '.join(p.get('data_labels', []))}")
    lines.append(f"PII vault categories: {', '.join(p.get('_pii_summary', {}).keys())}")
    lines.append(f"Connections: {p.get('_connection_summary', '')}")
    lines.append(f"Data levels → L4: {p['_data_level_map']['L4']}")
    lines.append(f"Data levels → L3: {p['_data_level_map']['L3']}")
    lines.append(f"Data levels → L2: {p['_data_level_map']['L2']}")

    if p.get("_has_dev_credentials"):
        lines.append("⚠ Has dev_credentials (SSH keys, Git tokens, cloud creds) — use in developer privacy tasks")
    if p.get("_has_biometrics"):
        lines.append("⚠ Has biometrics (fingerprint, iris, voiceprint, DNA) — use in L4 biometric scenarios")
    if p.get("_has_special_category"):
        sc = p.get("pii_vault", {}).get("special_category", {})
        sc_fields = [f"{k}={v}" for k, v in sc.items() if v]
        lines.append(f"⚠ Special category data: {', '.join(sc_fields)} — GDPR Art 9 handling required")
    if p.get("_has_vehicles"):
        vehicles = p.get("pii_vault", {}).get("property", {}).get("vehicles", [])
        if vehicles:
            v = vehicles[0]
            lines.append(f"Vehicle: {v.get('year', '')} {v.get('make', '')} {v.get('model', '')} (VIN, plate available)")

    lines.append(f"\nMemory files available: {p.get('_memory_file_count', 0)} dated entries")
    if p.get("_crosslink_names"):
        lines.append(f"Social crosslinks with: {', '.join(p['_crosslink_names'][:5])}")

    return "\n".join(lines)


def _persona_brief_v1(p: dict) -> str:
    """Legacy brief for old 225-persona schema."""
    lines = [
        f"Persona: {p['first_name']} {p['last_name']} ({p['persona_id']})",
        f"Age {p.get('exact_age', '?')}, {p.get('gender', '?')}, {p.get('city', '?')}",
        f"Job: {p.get('job_title', '?')} at {p.get('pii_vault', {}).get('employment', {}).get('employer', '?')} ({p.get('occupation_sector', '?')})",
        f"Education: {p.get('education_level', '?')}, Language: {p.get('primary_language', '?')}",
        f"Household: {p.get('marital_status', '?')}, size {p.get('household_size', '?')}, children: {p.get('children_count', '?')}",
        f"Platforms: {', '.join(p['_platforms'])}",
        f"Hobbies (tier 1): {', '.join(h['id'] for h in p.get('hobbies', {}).get('tier_1', []))}",
        f"Hobbies (tier 3 / life-admin): {', '.join(h['id'] for h in p.get('hobbies', {}).get('tier_3', []))}",
        f"Data labels available: {', '.join(p.get('data_labels', []))}",
        f"PII vault categories: {', '.join(p['_pii_summary'].keys())}",
        f"Connections: {p['_connection_summary']}",
        f"Data levels → L4: {p['_data_level_map']['L4']}",
        f"Data levels → L3: {p['_data_level_map']['L3']}",
        f"Data levels → L2: {p['_data_level_map']['L2']}",
    ]
    if p.get("partner_persona_id"):
        lines.append(f"Partner: {p['partner_persona_id']}")
    return "\n".join(lines)
