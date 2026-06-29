"""TF-IDF based deduplication and coverage matrix for generated tasks."""

from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import TFIDF_SIMILARITY_THRESHOLD as SIMILARITY_THRESHOLD


def _fingerprint(task: dict) -> str:
    """Build a text fingerprint from key task fields."""
    parts = [
        task.get("task_title", ""),
        task.get("goal_summary", ""),
        task.get("domain", ""),
        task.get("subdomain", ""),
        task.get("privacy_scenario", ""),
        " ".join(task.get("expected_privacy_actions", [])),
        task.get("stratum_tag", ""),
        " ".join(task.get("openclaw_skills", [])),
    ]
    pv = task.get("persona_voice", {})
    if isinstance(pv, dict):
        parts.append(pv.get("tone", ""))
    return " ".join(parts).lower().strip()


def deduplicate_tasks(tasks: list[dict], threshold: float = SIMILARITY_THRESHOLD) -> tuple[list[dict], dict[str, Any]]:
    """Remove near-duplicate tasks based on TF-IDF cosine similarity."""
    if len(tasks) < 2:
        return tasks, {"total": len(tasks), "duplicates_removed": 0, "pairs": []}

    fingerprints = [_fingerprint(t) for t in tasks]

    vectorizer = TfidfVectorizer(
        max_features=5000,
        ngram_range=(1, 2),
        stop_words="english",
    )
    tfidf_matrix = vectorizer.fit_transform(fingerprints)
    sim_matrix = cosine_similarity(tfidf_matrix)

    to_remove = set()
    pairs = []
    n = len(tasks)
    for i in range(n):
        if i in to_remove:
            continue
        for j in range(i + 1, n):
            if j in to_remove:
                continue
            score = sim_matrix[i, j]
            if score >= threshold:
                to_remove.add(j)
                pairs.append({
                    "kept": tasks[i]["task_id"],
                    "removed": tasks[j]["task_id"],
                    "similarity": round(float(score), 3),
                })

    deduped = [t for idx, t in enumerate(tasks) if idx not in to_remove]

    report = {
        "total_before": len(tasks),
        "total_after": len(deduped),
        "duplicates_removed": len(to_remove),
        "threshold": threshold,
        "pairs": pairs,
        "avg_similarity": round(float(np.mean(sim_matrix[np.triu_indices(n, k=1)])), 3) if n > 1 else 0,
    }

    return deduped, report


def compute_coverage_matrix(tasks: list[dict]) -> dict[str, Any]:
    """Compute coverage across scenarios, domains, data levels, strata, and persona segments."""
    scenarios: dict[str, int] = {}
    domains: dict[str, int] = {}
    levels: dict[str, int] = {}
    tiers: dict[str, int] = {}
    jailbreak_vectors: dict[str, int] = {}
    strata: dict[str, int] = {}
    persona_voices: dict[str, int] = {}
    skills_used: dict[str, int] = {}

    from response_parser import CANONICAL_SCENARIO_LEVELS, L4_PII_FIELDS

    memory_recall_count = 0
    exec_approval_count = 0
    multimodal_count = 0
    min_tools_met = 0
    l3_plus_count = 0
    dev_cred_count = 0
    biometric_count = 0
    special_cat_count = 0
    has_persona_voice = 0
    has_stratum_tag = 0
    crosslink_grounded = 0
    min_skills_met = 0
    skills_per_task: list[int] = []
    skill_tier_combos: dict[str, int] = {}
    horizontals: dict[str, int] = {}
    canonical_levels_match = 0
    l4_pii_backed = 0
    exec_approval_consistent = 0
    subdomain_snake = 0
    levels_sorted = 0
    goal_has_no_name = 0
    htg_consent_ok = 0
    tool_res_tier_ok = 0
    pii_labels_canonical_ok = 0

    for t in tasks:
        sc = t.get("privacy_scenario", "?")
        scenarios[sc] = scenarios.get(sc, 0) + 1

        dom = t.get("domain", "?")
        domains[dom] = domains.get(dom, 0) + 1

        for lv in t.get("data_levels", []):
            levels[lv] = levels.get(lv, 0) + 1

        for tr in t.get("tool_tiers", []):
            tiers[tr] = tiers.get(tr, 0) + 1

        jv = t.get("jailbreak_vector")
        if jv:
            jailbreak_vectors[jv] = jailbreak_vectors.get(jv, 0) + 1

        st = t.get("stratum_tag", "")
        if st:
            strata[st] = strata.get(st, 0) + 1
            has_stratum_tag += 1

        pv = t.get("persona_voice", {})
        if isinstance(pv, dict) and pv.get("tone"):
            tone = pv["tone"]
            persona_voices[tone] = persona_voices.get(tone, 0) + 1
            has_persona_voice += 1

        task_skills = t.get("openclaw_skills", [])
        for skill in task_skills:
            skills_used[skill] = skills_used.get(skill, 0) + 1
        skill_count = len(task_skills)
        skills_per_task.append(skill_count)
        if skill_count >= 2:
            min_skills_met += 1

        task_tiers = set(t.get("tool_tiers", []))
        if "T1" in task_tiers and "T3" in task_tiers:
            combo = "T1+T3"
        elif "T1" in task_tiers and "T2" in task_tiers:
            combo = "T1+T2"
        elif len(task_tiers) == 1:
            combo = list(task_tiers)[0] + " only"
        else:
            combo = "+".join(sorted(task_tiers)) if task_tiers else "none"
        skill_tier_combos[combo] = skill_tier_combos.get(combo, 0) + 1

        # Detect memory recall via conversation_arc milestones (memory_file is always null)
        arc = t.get("conversation_arc") or []
        has_recall = any(
            "recall" in (str(m.get("milestone", "")).lower() + str(m.get("user_intent", "")).lower())
            or "remember" in (str(m.get("milestone", "")).lower() + str(m.get("user_intent", "")).lower())
            for m in arc
        )
        if has_recall:
            memory_recall_count += 1

        if t.get("exec_approval_points"):
            exec_approval_count += 1

        if t.get("multimodal_assets"):
            multimodal_count += 1

        if len(t.get("suggested_tools", [])) >= 2:
            min_tools_met += 1

        task_levels = set(t.get("data_levels", []))
        if task_levels & {"L3", "L4"}:
            l3_plus_count += 1

        pii_fields = t.get("pii_fields_exercised", [])
        pii_str = " ".join(pii_fields).upper()
        if any(x in pii_str for x in ("DEV_SSH", "DEV_GIT", "DEV_CLOUD", "DEV_ENV", "DEV_GPG")):
            dev_cred_count += 1
        if any(x in pii_str for x in ("BIO_FINGER", "BIO_IRIS", "BIO_VOICE", "BIO_DNA", "BIO_FACE")):
            biometric_count += 1
        if any(x in pii_str for x in ("SPECIAL_", "DEMO_RELIGION")):
            special_cat_count += 1

        hz = t.get("horizontal", "?")
        horizontals[hz] = horizontals.get(hz, 0) + 1

        sc_code = t.get("privacy_scenario", "")
        canonical = CANONICAL_SCENARIO_LEVELS.get(sc_code)
        if canonical and sorted(t.get("data_levels", [])) == sorted(canonical):
            canonical_levels_match += 1

        if "L4" in t.get("data_levels", []):
            pii_set = set(t.get("pii_fields_exercised", []))
            if pii_set & L4_PII_FIELDS:
                l4_pii_backed += 1
        else:
            l4_pii_backed += 1

        eap = t.get("exec_approval_points", [])
        epa = t.get("expected_privacy_actions", [])
        if not eap or "exec_approval" in epa:
            exec_approval_consistent += 1

        sd = t.get("subdomain", "")
        if isinstance(sd, str) and " " not in sd.strip():
            subdomain_snake += 1

        dl = t.get("data_levels", [])
        _order = {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4}
        if dl == sorted(dl, key=lambda x: _order.get(x, 9)):
            levels_sorted += 1

        gs = t.get("goal_summary", "")
        pid = t.get("persona_id", "")
        if "User" in gs or pid not in gs:
            goal_has_no_name += 1

        from response_parser import _PII_LABEL_CANONICAL, _TOOL_TIER_MAP
        task_tiers_set = set(t.get("tool_tiers", []))
        task_levels_set = set(t.get("data_levels", []))
        task_epa = set(t.get("expected_privacy_actions", []))
        htg_ok = True
        if "T3" in task_tiers_set and task_levels_set & {"L3", "L4"}:
            if "hard_block_plaintext" not in task_epa:
                htg_ok = False
        if "T3" in task_tiers_set and "L2" in task_levels_set:
            if "consent_gate" not in task_epa:
                htg_ok = False
        if htg_ok:
            htg_consent_ok += 1

        tr = t.get("tool_resolution", {})
        if isinstance(tr, dict) and tr.get("fallback_tool"):
            fb_tools = [s.strip() for s in tr["fallback_tool"].split("+")]
            max_rank = max({"T1": 1, "T2": 2, "T3": 3}.get(_TOOL_TIER_MAP.get(ft, "T1"), 1) for ft in fb_tools)
            declared_rank = {"T1": 1, "T2": 2, "T3": 3}.get(tr.get("fallback_tier", "T1"), 1)
            if max_rank <= declared_rank:
                tool_res_tier_ok += 1
            else:
                pass
        else:
            tool_res_tier_ok += 1

        oov_labels = [f for f in t.get("pii_fields_exercised", []) if f in _PII_LABEL_CANONICAL]
        if not oov_labels:
            pii_labels_canonical_ok += 1

        hooks = " ".join(t.get("realism_hooks", [])).lower()
        if "crosslink" in hooks or "event" in hooks or "trip" in hooks or "celebration" in hooks:
            crosslink_grounded += 1

    total = len(tasks)
    avg_skills = round(sum(skills_per_task) / total, 1) if total else 0
    return {
        "scenarios": dict(sorted(scenarios.items())),
        "domains": dict(sorted(domains.items())),
        "horizontals": dict(sorted(horizontals.items())),
        "data_levels": dict(sorted(levels.items())),
        "tool_tiers": dict(sorted(tiers.items())),
        "jailbreak_vectors": dict(sorted(jailbreak_vectors.items())),
        "strata": dict(sorted(strata.items())),
        "persona_voice_tones": dict(sorted(persona_voices.items())),
        "skills_used": dict(sorted(skills_used.items(), key=lambda x: -x[1])[:25]),
        "skill_tier_combos": dict(sorted(skill_tier_combos.items(), key=lambda x: -x[1])),
        "total_tasks": total,
        "unique_scenarios": len(scenarios),
        "unique_domains": len(domains),
        "unique_horizontals": len(horizontals),
        "unique_skills": len(skills_used),
        "unique_strata": len(strata),
        "unique_voice_tones": len(persona_voices),
        "avg_skills_per_task": avg_skills,
        "compliance": {
            "memory_recall": f"{memory_recall_count}/{total}",
            "exec_approval": f"{exec_approval_count}/{total}",
            "l3_plus_data": f"{l3_plus_count}/{total}",
            "min_2_tools": f"{min_tools_met}/{total}",
            "min_2_skills": f"{min_skills_met}/{total}",
            "multimodal_pii": f"{multimodal_count}/{total}",
            "jailbreak_tasks": f"{sum(jailbreak_vectors.values())}/{total}",
            "has_persona_voice": f"{has_persona_voice}/{total}",
            "has_stratum_tag": f"{has_stratum_tag}/{total}",
            "dev_credential_tasks": f"{dev_cred_count}/{total}",
            "biometric_tasks": f"{biometric_count}/{total}",
            "special_category_tasks": f"{special_cat_count}/{total}",
            "crosslink_grounded": f"{crosslink_grounded}/{total}",
        },
        "consistency": {
            "canonical_levels_match": f"{canonical_levels_match}/{total}",
            "l4_pii_backed": f"{l4_pii_backed}/{total}",
            "exec_approval_consistent": f"{exec_approval_consistent}/{total}",
            "subdomain_snake_case": f"{subdomain_snake}/{total}",
            "data_levels_sorted": f"{levels_sorted}/{total}",
            "goal_summary_no_name": f"{goal_has_no_name}/{total}",
            "htg_consent_matrix": f"{htg_consent_ok}/{total}",
            "tool_resolution_tier": f"{tool_res_tier_ok}/{total}",
            "pii_labels_canonical": f"{pii_labels_canonical_ok}/{total}",
        },
    }
