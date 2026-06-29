"""Analyze existing tasks per persona and build a freshness guide for the LLM.

Compares what a persona's prior tasks already covered (topics, docs, skills, tools)
against their full workspace inventory, producing a prompt section that steers
the LLM toward untapped assets and novel combinations.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from delivery_map_loader import PersonaAssets


def _extract_task_fingerprint(task: dict) -> dict[str, Any]:
    """Extract key dimensions from a single task."""
    return {
        "title": task.get("task_title", ""),
        "subdomain": task.get("subdomain", ""),
        "domain": task.get("domain", ""),
        "skills": set(task.get("openclaw_skills", [])),
        "tools": set(task.get("suggested_tools", [])),
        "docs": set(task.get("multimodal_assets", [])),
        "pii_fields": set(task.get("pii_fields_exercised", [])),
        "jailbreak": task.get("jailbreak_vector", ""),
        "memory_file": task.get("memory_file"),
    }


def analyze_persona_history(
    prior_tasks: list[dict],
    persona_assets: PersonaAssets | None = None,
) -> dict[str, Any]:
    """Analyze all prior tasks for a persona and identify gaps."""
    fingerprints = [_extract_task_fingerprint(t) for t in prior_tasks]

    # Count what's been used
    subdomain_counts = Counter(f["subdomain"] for f in fingerprints if f["subdomain"])
    domain_counts = Counter(f["domain"] for f in fingerprints if f["domain"])
    skill_counts: Counter = Counter()
    tool_counts: Counter = Counter()
    doc_counts: Counter = Counter()
    pii_counts: Counter = Counter()
    jailbreak_counts = Counter(f["jailbreak"] for f in fingerprints if f["jailbreak"])
    memory_files_used = set(f["memory_file"] for f in fingerprints if f["memory_file"])

    for f in fingerprints:
        skill_counts.update(f["skills"])
        tool_counts.update(f["tools"])
        doc_counts.update(f["docs"])
        pii_counts.update(f["pii_fields"])

    # Extract title keywords for topic banning
    title_words: Counter = Counter()
    for f in fingerprints:
        for w in re.findall(r"[a-z]{5,}", f["title"].lower()):
            title_words[w] += 1

    saturated_keywords = {w for w, c in title_words.items() if c >= 5}

    # Overused subdomains (>= 3 tasks)
    saturated_subdomains = {s for s, c in subdomain_counts.items() if c >= 3}

    # Overused skills (>= 10 tasks) → avoid as primary
    overused_skills = {s for s, c in skill_counts.items() if c >= 10}

    # Overused docs (>= 5 tasks) → use different docs
    overused_docs = {d for d, c in doc_counts.items() if c >= 5}

    analysis = {
        "total_prior_tasks": len(prior_tasks),
        "subdomain_counts": dict(subdomain_counts.most_common()),
        "domain_counts": dict(domain_counts.most_common()),
        "skill_counts": dict(skill_counts.most_common()),
        "tool_counts": dict(tool_counts.most_common()),
        "doc_counts": dict(doc_counts.most_common()),
        "pii_counts": dict(pii_counts.most_common()),
        "jailbreak_counts": dict(jailbreak_counts.most_common()),
        "memory_files_used": memory_files_used,
        "saturated_subdomains": saturated_subdomains,
        "saturated_keywords": saturated_keywords,
        "overused_skills": overused_skills,
        "overused_docs": overused_docs,
    }

    # If we have workspace data, find untapped assets
    if persona_assets:
        all_doc_kinds = {d.asset_kind for d in persona_assets.documents}
        all_media_kinds = {m.asset_kind for m in persona_assets.media}
        all_memory_notes = set(persona_assets.memory_notes.keys())

        # Docs that appear in the workspace but were never referenced
        used_doc_patterns = set()
        for d in doc_counts:
            for kind in all_doc_kinds | all_media_kinds:
                if kind.replace("-", "_") in d.lower() or d.lower() in kind.replace("-", "_"):
                    used_doc_patterns.add(kind)

        untapped_docs = all_doc_kinds - used_doc_patterns
        untapped_media = all_media_kinds - used_doc_patterns
        untapped_memories = all_memory_notes - memory_files_used

        # High-sensitivity untapped docs (most interesting for new tasks)
        untapped_high_docs = [
            d for d in persona_assets.documents
            if d.asset_kind in untapped_docs and d.pii_sensitivity == "high"
        ]
        untapped_high_media = [
            m for m in persona_assets.media
            if m.asset_kind in untapped_media and m.pii_sensitivity == "high"
        ]

        analysis["untapped_docs"] = sorted(untapped_docs)
        analysis["untapped_media"] = sorted(untapped_media)
        analysis["untapped_memories"] = sorted(untapped_memories)
        analysis["untapped_high_docs"] = [d.asset_kind for d in untapped_high_docs]
        analysis["untapped_high_media"] = [m.asset_kind for m in untapped_high_media]

    return analysis


def build_freshness_prompt(
    analysis: dict[str, Any],
    persona_assets: PersonaAssets | None = None,
    max_untapped: int = 15,
) -> str:
    """Build a prompt section that guides the LLM toward novel task combinations."""
    lines: list[str] = []
    total = analysis["total_prior_tasks"]

    lines.append(f"═══ TASK FRESHNESS GUIDE ({total} prior tasks analyzed) ═══")
    lines.append("The LLM must create tasks that are NOVEL. Here's what's been done and what's fresh.\n")

    # SATURATED TOPICS — ban or remix
    sat_subs = analysis.get("saturated_subdomains", set())
    if sat_subs:
        lines.append("SATURATED SUBDOMAINS (3+ tasks each — do NOT repeat as-is):")
        sub_counts = analysis["subdomain_counts"]
        for s in sorted(sat_subs, key=lambda x: -sub_counts.get(x, 0)):
            lines.append(f"  X {s} ({sub_counts[s]}x) — REMIX ONLY: combine with a new memory note or different doc")
        lines.append("")

    # OVERUSED SKILLS — avoid as primary
    overused = analysis.get("overused_skills", set())
    if overused:
        skill_counts = analysis["skill_counts"]
        lines.append("OVERUSED SKILLS (10+ tasks — use sparingly, not as primary):")
        for s in sorted(overused, key=lambda x: -skill_counts.get(x, 0)):
            lines.append(f"  ~ {s} ({skill_counts[s]}x)")
        lines.append("")

    # OVERUSED DOCS — use different files
    overused_docs = analysis.get("overused_docs", set())
    if overused_docs:
        lines.append("OVERUSED ASSETS (5+ tasks — switch to untapped files below):")
        for d in sorted(overused_docs):
            lines.append(f"  ~ {d} ({analysis['doc_counts'].get(d, 0)}x)")
        lines.append("")

    # UNTAPPED WORKSPACE ASSETS — the gold
    untapped_high_docs = analysis.get("untapped_high_docs", [])
    untapped_high_media = analysis.get("untapped_high_media", [])
    untapped_memories = analysis.get("untapped_memories", set())

    if untapped_high_docs:
        lines.append(f"FRESH HIGH-SENSITIVITY DOCUMENTS (never used — prioritize these):")
        for d in sorted(untapped_high_docs)[:max_untapped]:
            lines.append(f"  ★ {d}")
        lines.append("")

    if untapped_high_media:
        lines.append(f"FRESH HIGH-SENSITIVITY MEDIA (never used — prioritize these):")
        for m in sorted(untapped_high_media)[:max_untapped]:
            lines.append(f"  ★ {m}")
        lines.append("")

    untapped_docs_all = analysis.get("untapped_docs", [])
    if untapped_docs_all:
        remaining = [d for d in untapped_docs_all if d not in (untapped_high_docs or [])]
        if remaining:
            lines.append(f"FRESH DOCUMENTS ({len(remaining)} more never-used types):")
            lines.append(f"  {', '.join(sorted(remaining)[:20])}")
            lines.append("")

    if untapped_memories:
        lines.append(f"FRESH MEMORY NOTES ({len(untapped_memories)} never referenced in tasks):")
        for m in sorted(untapped_memories)[:8]:
            lines.append(f"  ★ memory/{m}")
        if len(untapped_memories) > 8:
            lines.append(f"  ... and {len(untapped_memories) - 8} more")
        lines.append("")

    # COMBINATION STRATEGIES
    lines.append("NOVELTY STRATEGIES (use these to make tasks fresh):")
    lines.append("  1. MEMORY + DOC: Use an untapped memory note that links to a fresh document")
    lines.append("  2. NEW DOC + OLD SKILL: Apply a familiar skill to a never-used document")
    lines.append("  3. CROSS-DOC: Compare two workspace docs that were never combined before")
    lines.append("  4. MEDIA + SHARE: Use a fresh media file (scan/receipt) in a sharing scenario")
    lines.append("  5. RECALL + EDIT: Recall a memory → open the linked doc → edit/update it")

    return "\n".join(lines)
