"""Offline self-checks for synthgen's non-trivial logic. No network, no API keys.

Run: python -m synthgen.test_synthgen   (or pytest synthgen/test_synthgen.py)
Covers the load-bearing pieces: key parsing, cost estimate, state resume, manifest
remap + PII extraction, the backprop prompt section, and dashboard ingestion.
"""

from __future__ import annotations

import tempfile
from pathlib import Path


def test_config_keys():
    from .config import load_keys
    import os
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("OpenAI: sk-o\nClaude = sk-ant\nGemini: g-key\n")
        tmp = f.name
    got = load_keys(tmp)
    os.unlink(tmp)
    assert got == {"openai": "sk-o", "anthropic": "sk-ant", "gemini": "g-key"}, got


def test_cost_estimate():
    from .costs import CostModel, IMAGE_USD_PER_IMAGE
    est = CostModel.estimate_run(num_personas=2, tasks_per_persona=5,
                                 persona_model="claude-sonnet-4-6", task_model="claude-opus-4-8",
                                 n_images=10, n_audio=0, n_pdf=4)
    assert est["pdf"] == 0.0 and est["total"] > 0
    assert abs(est["image"] - 10 * IMAGE_USD_PER_IMAGE) < 1e-9


def test_state_resume():
    from .state import RunState
    with tempfile.TemporaryDirectory() as d:
        st = RunState.load_or_init(d)
        st.mark_asset_done("P-0001", "A-0001")
        st.save()
        st2 = RunState.load_or_init(d)
        assert st2.asset_is_done("P-0001", "A-0001") and st2.run_id == st.run_id


def test_manifest_remap_and_pii():
    from .manifest.loader import load_for
    from .manifest.extract import build_plan
    man = load_for("P-0001")
    assert man and all("P-0006" not in e.path for e in man)
    persona = {"persona_id": "P-0001", "data_labels": ["GOV_PASSPORT_NUM", "ID_FULL_NAME"],
               "pii_vault": {"government": {"passport_num": "Z123"}}}
    with tempfile.TemporaryDirectory() as d:
        plan = build_plan(Path(d), persona, [], {})
    passport = [pa for pa in plan if pa.entry.kind == "passport-page"]
    assert passport and "GOV_PASSPORT_NUM" in passport[0].pii_fields


def test_backprop_section_present():
    """Batch 2 prompt must carry the prior-tasks section; batch 1 must not."""
    from .tasks._kit_bootstrap import ensure_kit_on_path
    ensure_kit_on_path()
    from prompts.user_prompt import build_user_prompt
    from persona_loader import _enrich_v2
    persona = {"persona_id": "P-0001", "first_name": "Sam", "last_name": "Doe",
               "data_labels": [], "pii_vault": {}, "hobbies": {},
               "platform_presence": {}, "workspace": {"memory_entries": {}}, "asset_pack": {},
               "crosslinks": []}
    _enrich_v2(persona)  # adapter always runs this; derives _platforms, _data_level_map, etc.
    prior = [{"task_id": "P-0001-01", "domain": "Health", "subdomain": "meds",
              "task_title": "Analyze medication timing", "openclaw_skills": ["health"]}]
    up1 = build_user_prompt(persona, 1, [], 1, start_seq=1, persona_assets=None)
    up2 = build_user_prompt(persona, 2, prior, 1, start_seq=1, persona_assets=None)
    marker = "ALREADY GENERATED THIS SESSION"
    assert marker not in up1 and marker in up2
    assert "Analyze medication timing" in up2


def test_dashboard_ingest():
    from .events import EventBus, Event, EventType
    from .ui.dashboard import RichDashboard
    bus = EventBus()
    dash = RichDashboard(bus)
    bus.emit(Event(EventType.STAGE_STARTED, stage="tasks"))
    bus.emit(Event(EventType.TASK_BATCH_GENERATED, data={"n": 5}))
    bus.emit(Event(EventType.DEDUP_FLAGGED, data={"flagged": ["x"]}))
    dash.render()  # must not raise
    assert dash.counts["tasks"] == 5 and dash.counts["dedup"] == 1
    assert dash.stage_status["tasks"] == "running"


def main():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  ok: {fn.__name__}")
    print(f"all {len(fns)} self-checks passed")


if __name__ == "__main__":
    main()
