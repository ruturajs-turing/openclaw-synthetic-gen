#!/usr/bin/env python3
"""
STAGE 1 — Persona spine generation (deterministic, no API needed).

Produces a single `personas.json` with N fully-structured persona records:
demographics, Big-Five personality + derived MBTI, hobbies, platform presence,
a country-aware synthetic PII vault, sensitivity data-labels, and a social
graph of connections (couples, colleagues, friends, families, neighbours).

The output is the canonical "spine" that Stage 2 (expand_persona.py) turns into
a full filesystem of believable life artifacts.

Reproducible: same --seed + --count => identical output.

Usage
-----
    python generate_spine.py                       # 250 personas, seed 42
    python generate_spine.py --count 50 --seed 7
    python generate_spine.py --names-file names.csv # use real assigned names
    python generate_spine.py --out output/personas.json

Names file (optional)
---------------------
CSV or TSV with a header. The kit looks for these columns (case-insensitive),
any of which may be absent:
    name | full_name | persona_name      -> "First Last"
    email | email_synthetic              -> contact e-mail
    worker | annotator | assigned_worker -> owner/annotator id
If no name is given for a row, one is invented from the region name pools.
"""

import argparse
import csv
import json
import random
from pathlib import Path

from . import _kitconfig as config
from . import _pools as P


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def pid(n: int) -> str:
    return f"P-{n:0{config.PERSONA_ID_WIDTH}d}"


def age_band(age: int) -> str:
    for hi, label in [(25, "18-24"), (35, "25-34"), (45, "35-44"), (55, "45-54"), (65, "55-64")]:
        if age < hi:
            return label
    return "65+"


def generation_label(year: int) -> str:
    if year >= 1997:
        return "Gen Z"
    if year >= 1981:
        return "Millennial"
    if year >= 1965:
        return "Gen X"
    return "Baby Boomer"


def big_five_to_mbti(p: dict) -> str:
    """Rough Big-Five -> MBTI mapping; just a flavourful derived label."""
    e = "E" if p["extraversion"] >= 0.5 else "I"
    n = "N" if p["openness"] >= 0.5 else "S"
    t = "F" if p["agreeableness"] >= 0.55 else "T"
    j = "J" if p["conscientiousness"] >= 0.5 else "P"
    return e + n + t + j


def gen_personality(rng) -> dict:
    return {
        "openness": round(rng.uniform(0.1, 0.95), 4),
        "conscientiousness": round(rng.uniform(0.1, 0.95), 4),
        "extraversion": round(rng.uniform(0.1, 0.95), 4),
        "agreeableness": round(rng.uniform(0.1, 0.95), 4),
        "neuroticism": round(rng.uniform(0.05, 0.8), 4),
        "digital_engagement_intensity": round(rng.uniform(0.2, 0.95), 4),
        "content_creation_propensity": round(rng.uniform(0.05, 0.8), 4),
    }


def gen_platform_presence(rng) -> dict:
    presence = {p: False for p in P.PLATFORMS}
    presence["email"] = True
    for p in ["whatsapp", "youtube", "instagram", "linkedin"]:
        presence[p] = rng.random() < 0.6
    for p in P.PLATFORMS:
        if p not in ("email", "whatsapp", "youtube", "instagram", "linkedin"):
            presence[p] = rng.random() < 0.25
    if sum(presence.values()) < 4:
        for p in rng.sample(["whatsapp", "youtube", "instagram", "linkedin"], 2):
            presence[p] = True
    return presence


def gen_hobbies(rng) -> dict:
    pool = P.HOBBIES_POOL[:]
    rng.shuffle(pool)
    admin = rng.sample(P.LIFE_ADMIN_POOL, rng.randint(3, 4))
    return {
        "tier_1": [{"id": h, "tier": 1, "affinity_score": round(rng.uniform(0.03, 0.15), 4)} for h in pool[:3]],
        "tier_2": [{"id": h, "tier": 2, "affinity_score": round(rng.uniform(0.03, 0.10), 4)} for h in pool[3:6]],
        "tier_3": [{"id": h, "tier": 3, "affinity_score": None} for h in admin],
    }


def infer_gender(given: str, region: str) -> str:
    names = P.NAMES.get(region, {})
    if given in names.get("f", []):
        return "female"
    if given in names.get("m", []):
        return "male"
    g = given.lower()
    if any(g.endswith(s) for s in ("a", "i", "ah", "ia", "ina")):
        return "female"
    return "male"


def gen_pii_vault(rng, first, last, cc, city, lat, lon, income, job, birth_year) -> dict:
    q, a = rng.choice(P.SECURITY_QA)
    special = rng.choice("!@#$%&*")
    return {
        "auth": {
            "password": f"{first[0]}{last[:3].title()}{special}{birth_year}${rng.randint(10,99)}",
            "recovery_codes": P.gen_recovery_codes(rng),
            "security_qa": {"question": q, "answer": a},
            "username": f"{first.lower()}.{last.lower()}{str(birth_year)[-2:]}",
        },
        "government": {
            "ssn": P.gen_national_id(rng, cc),
            "passport_num": P.gen_passport_num(rng, cc),
            "dl_num": P.gen_drivers_license(rng, cc),
            "national_id": P.gen_national_id(rng, cc),
            "tin": P.gen_tax_id(rng, cc),
        },
        "financial": {
            "credit_card": P.gen_credit_card(rng),
            "cvv": str(rng.randint(100, 999)),
            "card_expiry": f"{rng.randint(1,12):02d}/{rng.randint(26,30)}",
            "bank_account": "".join(str(rng.randint(0, 9)) for _ in range(rng.randint(8, 12))),
            "iban": P.gen_iban(rng, cc),
            "salary": income,
            "crypto_wallet_addr": P.gen_crypto_wallet(rng),
        },
        "health": {
            "insurance_id": P.gen_insurance_id(rng),
            "diagnoses": rng.sample(P.DIAGNOSES_POOL, rng.randint(1, 3)),
            "medications": rng.sample(P.MEDICATIONS_POOL, rng.randint(1, 3)),
            "provider": f"Dr. {rng.choice('ABCDEFGHJKLMNPRS')}{''.join(rng.choices('aeiournlst', k=5))}, {rng.choice(['General Hospital','Medical Center','Health Clinic'])}",
            "blood_type": rng.choice(["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]),
        },
        "location": {
            "home_address": P.gen_address(rng, cc, city),
            "gps_precise": [round(lat + rng.uniform(-0.05, 0.05), 4), round(lon + rng.uniform(-0.05, 0.05), 4)],
        },
        "contacts": {
            "phone": P.gen_phone(rng, cc),
            "emergency_contact": f"{rng.choice(['Maria','John','Ana','Li','Sarah','David'])} {last} ({rng.choice(['sibling','parent','spouse','friend'])}) {P.gen_phone(rng, cc)}",
        },
        "employment": {
            "employer": rng.choice(P.EMPLOYERS),
            "employee_id": f"EMP-{rng.randint(100000, 999999)}",
            "title": job,
        },
    }


def gen_data_labels(rng, sector, marital, children) -> list:
    labels = list(P.DATA_LABELS_CORE)
    for cat in rng.sample(list(P.DATA_LABELS_EXTENDED), rng.randint(4, 7)):
        pool = P.DATA_LABELS_EXTENDED[cat]
        labels.extend(rng.sample(pool, min(rng.randint(1, 3), len(pool))))
    if sector in ("software_tech", "data_analytics"):
        labels.extend(rng.sample(P.DATA_LABELS_EXTENDED["corporate"], 2))
    if marital == "married_partnered":
        labels += ["FAM_SPOUSE", "FAM_HOUSEHOLD"]
    if children > 0:
        labels.append("FAM_MINOR_PII")
    if marital != "married_partnered" and "FAM_SPOUSE" in labels:
        labels.remove("FAM_SPOUSE")
    return sorted(set(labels))


# ---------------------------------------------------------------------------
# Names input
# ---------------------------------------------------------------------------
def load_names_file(path: Path) -> list:
    rows = []
    text = path.read_text(encoding="utf-8")
    delim = "\t" if "\t" in text.splitlines()[0] else ","
    reader = csv.DictReader(text.splitlines(), delimiter=delim)
    for r in reader:
        low = {(k or "").strip().lower(): (v or "").strip() for k, v in r.items()}
        name = low.get("name") or low.get("full_name") or low.get("persona_name") or ""
        email = low.get("email") or low.get("email_synthetic") or ""
        worker = low.get("worker") or low.get("annotator") or low.get("assigned_worker") or ""
        if name or email:
            rows.append({"full_name": name, "email_synthetic": email, "assigned_worker": worker})
    return rows


def pick_region_for_name(rng, name: str) -> str:
    """Best-effort region guess from family name; falls back to random."""
    low = name.lower()
    for region, pools in P.NAMES.items():
        for fam in pools["fam"]:
            if fam.lower() in low:
                return region
    return rng.choice(list(P.REGIONS))


def invent_name(rng, region: str):
    pools = P.NAMES[region]
    sex = rng.choice(["m", "f"])
    given = rng.choice(pools[sex])
    family = rng.choice(pools["fam"])
    return given, family, sex


# ---------------------------------------------------------------------------
# Connections (social graph)
# ---------------------------------------------------------------------------
SHARED = {
    "partner": ["household", "bank_account", "emergency_contacts", "health_insurance", "home_address"],
    "colleague": ["slack_workspace", "project_repos", "company_vpn", "office_wifi"],
    "friend": ["whatsapp_group", "gym_membership", "hobby_group", "streaming_account"],
    "family": ["family_photos", "emergency_contacts", "home_address", "family_whatsapp"],
    "neighbor": ["neighborhood_watch", "local_park", "community_board"],
    "classmate": ["alumni_group", "study_materials", "university_email"],
}


def build_clusters(rng, count):
    idx = list(range(count))
    rng.shuffle(idx)
    clusters, pos = [], 0

    def take(kind, lo, hi, groups):
        nonlocal pos
        for _ in range(groups):
            size = rng.randint(lo, hi)
            if pos + size <= count:
                clusters.append({"type": kind, "members": idx[pos:pos + size]})
                pos += size

    take("partner", 2, 2, max(1, count // 16))     # ~1/8 of people are partnered
    take("colleague", 3, 5, max(1, count // 30))
    take("friend", 3, 4, max(1, count // 40))
    take("family", 2, 3, max(1, count // 60))
    return clusters, idx[pos:]


def assign_connections(rng, personas, clusters, standalone):
    def link(a, b, kind, shared):
        personas[a]["connections"].append({"persona_id": personas[b]["persona_id"], "type": kind, "shared": shared})
        personas[b]["connections"].append({"persona_id": personas[a]["persona_id"], "type": kind, "shared": shared})

    for c in clusters:
        m, kind = c["members"], c["type"]
        if kind == "partner":
            a, b = m
            hh = personas[a]["household_id"]
            for x, y in ((a, b), (b, a)):
                personas[x]["household_id"] = hh
                personas[x]["marital_status"] = "married_partnered"
                personas[x]["couple_type"] = rng.choice(["heterosexual", "heterosexual", "same_sex"])
                personas[x]["partner_persona_id"] = personas[y]["persona_id"]
                personas[x]["household_size"] = max(2, personas[x]["children_count"] + 2)
            link(a, b, "partner", list(SHARED["partner"]))
        else:
            if kind == "colleague":
                emp = rng.choice(P.EMPLOYERS)
                for x in m:
                    personas[x]["pii_vault"]["employment"]["employer"] = emp
            for i in range(len(m)):
                for j in range(i + 1, len(m)):
                    link(m[i], m[j], kind, rng.sample(SHARED[kind], rng.randint(2, min(4, len(SHARED[kind])))))

    # A few neighbour / classmate links among the standalone people.
    for a in standalone[:max(1, len(standalone) // 3)]:
        if rng.random() < 0.6:
            b = rng.choice([j for j in range(len(personas)) if j != a])
            kind = rng.choice(["neighbor", "classmate"])
            if personas[b]["persona_id"] not in [c["persona_id"] for c in personas[a]["connections"]]:
                link(a, b, kind, rng.sample(SHARED[kind], 2))


# ---------------------------------------------------------------------------
# Build a single persona
# ---------------------------------------------------------------------------
def build_persona(rng, n, name_row=None):
    if name_row and name_row.get("full_name"):
        full = name_row["full_name"]
        parts = full.split(" ", 1)
        first, last = parts[0], (parts[1] if len(parts) > 1 else "")
        region = pick_region_for_name(rng, full)
        sex_hint = None
    else:
        region = rng.choice(list(P.REGIONS))
        first, last, sex_hint = invent_name(rng, region)
        full = f"{first} {last}"

    city, tz, lat, lon, lang, cultural, cc = rng.choice(P.REGIONS[region])

    birth_year = rng.randint(1962, 2004)
    dob = f"{birth_year}-{rng.randint(1,12):02d}-{rng.randint(1,28):02d}"
    age = config.REFERENCE_YEAR - birth_year

    gender = ("female" if sex_hint == "f" else "male" if sex_hint == "m"
              else infer_gender(first, region))

    sector = rng.choice(P.OCCUPATION_SECTORS)
    job = rng.choice(P.JOB_TITLES[sector])
    income_band, lo, hi = rng.choice(P.INCOME_BANDS)
    income = rng.randint(lo, hi)

    marital = rng.choice(P.MARITAL_STATUSES)
    children = 0
    child_range = None
    hh_size = 1
    couple_type = None
    if marital == "married_partnered":
        couple_type = rng.choice(["heterosexual", "heterosexual", "same_sex"])
        children = rng.choice([0, 0, 1, 2, 3])
        if children:
            child_range = rng.choice(["0-4", "5-12", "13-17", "mixed"])
        hh_size = 2 + children

    email = (name_row or {}).get("email_synthetic") or \
        f"{first.lower()}.{last.lower().replace(' ', '')}@{config.SYNTHETIC_EMAIL_DOMAIN}"

    personality = gen_personality(rng)
    vault = gen_pii_vault(rng, first, last or first, cc, city, lat, lon, income, job, birth_year)

    return {
        "persona_id": pid(n),
        "first_name": first,
        "last_name": last,
        "full_name": full,
        "email_synthetic": email,
        "assigned_worker": (name_row or {}).get("assigned_worker", ""),
        "date_of_birth": dob,
        "exact_age": age,
        "age_band": age_band(age),
        "generation_label": generation_label(birth_year),
        "gender": gender,
        "education_level": rng.choice(P.EDUCATION_LEVELS),
        "region": region,
        "country_code": cc,
        "city": city,
        "urbanicity": rng.choices(["urban", "suburban", "rural"], weights=[0.6, 0.3, 0.1])[0],
        "primary_language": lang,
        "timezone": tz,
        "latitude": lat,
        "longitude": lon,
        "cultural_background": cultural,
        "occupation_sector": sector,
        "job_title": job,
        "income_band": income_band,
        "income_exact": income,
        "stratum": rng.choice(P.STRATA),
        "household_id": f"HH-{n:0{config.PERSONA_ID_WIDTH}d}",
        "marital_status": marital,
        "couple_type": couple_type,
        "partner_persona_id": None,
        "children_count": children,
        "children_age_range": child_range,
        "household_size": hh_size,
        "remote_work": rng.choice(["remote", "on_site", "hybrid"]),
        "personality": personality,
        "mbti": big_five_to_mbti(personality),
        "platform_presence": gen_platform_presence(rng),
        "hobbies": gen_hobbies(rng),
        "pii_vault": vault,
        "data_labels": gen_data_labels(rng, sector, marital, children),
        "connections": [],
    }


def generate(count, seed, names_file=None, start_id=1):
    rng = random.Random(seed)
    name_rows = load_names_file(names_file) if names_file else []
    if name_rows:
        count = len(name_rows)

    personas = [
        build_persona(rng, start_id + i, name_rows[i] if i < len(name_rows) else None)
        for i in range(count)
    ]
    clusters, standalone = build_clusters(rng, count)
    assign_connections(rng, personas, clusters, standalone)
    return personas, clusters


def main():
    ap = argparse.ArgumentParser(description="Stage 1: generate persona spines (deterministic).")
    ap.add_argument("--count", type=int, default=config.DEFAULT_COUNT)
    ap.add_argument("--seed", type=int, default=config.DEFAULT_SEED)
    ap.add_argument("--names-file", type=Path, default=None, help="Optional CSV/TSV of names/emails/workers.")
    ap.add_argument("--start-id", type=int, default=1, help="First persona number (P-0001 by default).")
    ap.add_argument("--out", type=Path, default=config.DEFAULT_SPINE_PATH)
    args = ap.parse_args()

    personas, clusters = generate(args.count, args.seed, args.names_file, args.start_id)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"personas": personas}, f, indent=2, ensure_ascii=False)

    conns = sum(len(p["connections"]) for p in personas)
    print(f"Wrote {len(personas)} personas -> {args.out}")
    print(f"  seed={args.seed}  clusters={len(clusters)}  total_connections={conns}")
    ids = [p["persona_id"] for p in personas]
    assert len(ids) == len(set(ids)), "Duplicate persona ids!"
    print("  validation: unique ids OK")


if __name__ == "__main__":
    main()
