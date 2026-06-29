"""In-process event bus. Core logic emits events; UIs subscribe.

Synchronous pub/sub on whatever thread/loop calls emit(). A broken subscriber can never
kill generation (each callback is wrapped). Event is a flat, JSON-serializable dataclass
so a future GUI/SSE bridge can subscribe and forward without touching core code.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Callable


class EventType(str, Enum):
    RUN_STARTED = "run_started"
    RUN_FINISHED = "run_finished"
    STAGE_STARTED = "stage_started"
    STAGE_FINISHED = "stage_finished"
    STEP_STARTED = "step_started"
    STEP_FINISHED = "step_finished"
    API_CALL_STARTED = "api_call_started"
    API_CALL_FINISHED = "api_call_finished"
    PERSONA_GENERATED = "persona_generated"
    TASK_BATCH_GENERATED = "task_batch_generated"
    DEDUP_FLAGGED = "dedup_flagged"
    ASSET_GENERATED = "asset_generated"
    ASSET_SKIPPED = "asset_skipped"
    PERSONA_PACKAGED = "persona_packaged"
    COST_UPDATE = "cost_update"
    LOG = "log"
    ERROR = "error"


@dataclass
class Event:
    type: EventType
    ts: float = field(default_factory=time.time)
    persona_id: str | None = None
    stage: str | None = None
    msg: str = ""
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["type"] = self.type.value
        return d


Listener = Callable[[Event], None]


class EventBus:
    def __init__(self) -> None:
        self._subs: list[Listener] = []

    def subscribe(self, fn: Listener) -> Listener:
        self._subs.append(fn)
        return fn

    def emit(self, ev: Event) -> None:
        for fn in self._subs:
            try:
                fn(ev)
            except Exception:
                # A subscriber (UI/log) failing must never break generation.
                pass

    # Convenience helpers — keep call sites terse.
    def log(self, msg: str, **data) -> None:
        self.emit(Event(EventType.LOG, msg=msg, data=data))

    def error(self, msg: str, **data) -> None:
        self.emit(Event(EventType.ERROR, msg=msg, data=data))


def _demo() -> None:
    bus = EventBus()
    seen: list[Event] = []
    bus.subscribe(seen.append)

    def boom(_ev):
        raise RuntimeError("subscriber blew up")

    bus.subscribe(boom)  # must not propagate
    bus.emit(Event(EventType.STAGE_STARTED, stage="personas", msg="go"))
    bus.log("hello", n=1)
    assert len(seen) == 2, seen
    assert seen[0].to_dict()["type"] == "stage_started"
    assert seen[1].data == {"n": 1}
    print("events self-check OK")


if __name__ == "__main__":
    _demo()
