"""Run checkpoint for resumability. One JSON file: run_dir/state.json.

Re-running an identical command skips completed personas/tasks/assets so we never re-pay
for an already-generated (LLM/image/audio) artifact. Asset granularity is a set of
"P-XXXX:manifest_id" strings — enough to never regenerate a $-costing asset twice.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RunState:
    run_dir: Path
    run_id: str = ""
    stage_done: dict[str, bool] = field(default_factory=dict)
    personas_done: set[str] = field(default_factory=set)
    tasks_done: set[str] = field(default_factory=set)
    assets_done: set[str] = field(default_factory=set)
    cost_usd_spent: float = 0.0

    @property
    def path(self) -> Path:
        return self.run_dir / "state.json"

    @classmethod
    def load_or_init(cls, run_dir: Path | str) -> "RunState":
        run_dir = Path(run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        p = run_dir / "state.json"
        if p.exists():
            d = json.loads(p.read_text(encoding="utf-8"))
            return cls(
                run_dir=run_dir,
                run_id=d.get("run_id", ""),
                stage_done=d.get("stage_done", {}),
                personas_done=set(d.get("personas_done", [])),
                tasks_done=set(d.get("tasks_done", [])),
                assets_done=set(d.get("assets_done", [])),
                cost_usd_spent=float(d.get("cost_usd_spent", 0.0)),
            )
        st = cls(run_dir=run_dir, run_id=uuid.uuid4().hex[:12])
        st.save()
        return st

    def save(self) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(
                {
                    "run_id": self.run_id,
                    "stage_done": self.stage_done,
                    "personas_done": sorted(self.personas_done),
                    "tasks_done": sorted(self.tasks_done),
                    "assets_done": sorted(self.assets_done),
                    "cost_usd_spent": round(self.cost_usd_spent, 6),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    # --- asset-level helpers ---
    @staticmethod
    def asset_key(persona_id: str, manifest_id: str) -> str:
        return f"{persona_id}:{manifest_id}"

    def asset_is_done(self, persona_id: str, manifest_id: str) -> bool:
        return self.asset_key(persona_id, manifest_id) in self.assets_done

    def mark_asset_done(self, persona_id: str, manifest_id: str) -> None:
        self.assets_done.add(self.asset_key(persona_id, manifest_id))


def _demo() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        st = RunState.load_or_init(d)
        assert st.run_id and not st.assets_done
        st.mark_asset_done("P-0001", "A-0001")
        st.cost_usd_spent = 1.25
        st.save()
        st2 = RunState.load_or_init(d)
        assert st2.run_id == st.run_id
        assert st2.asset_is_done("P-0001", "A-0001")
        assert st2.cost_usd_spent == 1.25
    print("state self-check OK")


if __name__ == "__main__":
    _demo()
