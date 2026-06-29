"""Live console dashboard. Subscribes to the EventBus (same events a future GUI would use)
and renders a two-pane rich.Live layout: stage progress + scrolling log on the left, the
API-call side panel + running cost on the right.
"""

from __future__ import annotations

from collections import deque
from contextlib import contextmanager

from rich.console import Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..events import Event, EventBus, EventType
from ..orchestrator import STAGES

_STAGE_GLYPH = {"pending": "·", "running": "▶", "done": "✓"}


class RichDashboard:
    def __init__(self, bus: EventBus, run_id: str = "") -> None:
        self.run_id = run_id
        self.stage_status = {s: "pending" for s in STAGES}
        self.log: deque[str] = deque(maxlen=14)
        self.api: deque[dict] = deque(maxlen=12)
        self.in_flight = 0
        self.cost = 0.0
        self.counts = {"personas": 0, "tasks": 0, "assets": 0, "dedup": 0}
        self.live: Live | None = None
        bus.subscribe(self.on_event)

    # --- event ingestion ---
    def on_event(self, ev: Event) -> None:
        t = ev.type
        if t == EventType.RUN_STARTED:
            self.run_id = ev.data.get("run_id", self.run_id)
        elif t == EventType.STAGE_STARTED and ev.stage in self.stage_status:
            self.stage_status[ev.stage] = "running"
        elif t == EventType.STAGE_FINISHED and ev.stage in self.stage_status:
            self.stage_status[ev.stage] = "done"
        elif t == EventType.API_CALL_STARTED:
            self.in_flight += 1
        elif t == EventType.API_CALL_FINISHED:
            self.in_flight = max(0, self.in_flight - 1)
            self.api.append(ev.data)
        elif t == EventType.COST_UPDATE and "spent_usd" in ev.data:
            self.cost = ev.data["spent_usd"]
        elif t == EventType.PERSONA_GENERATED:
            self.counts["personas"] += 1
        elif t == EventType.TASK_BATCH_GENERATED:
            self.counts["tasks"] += ev.data.get("n", 0)
        elif t == EventType.ASSET_GENERATED:
            self.counts["assets"] += 1
        elif t == EventType.DEDUP_FLAGGED:
            self.counts["dedup"] += len(ev.data.get("flagged", []))
        if ev.msg:
            self.log.append(f"{ev.stage or t.value}: {ev.msg}")
        if self.live is not None:
            self.live.update(self.render())

    # --- rendering ---
    def _stages_panel(self) -> Panel:
        lines = []
        for s in STAGES:
            st = self.stage_status[s]
            color = {"pending": "dim", "running": "yellow", "done": "green"}[st]
            lines.append(Text(f"{_STAGE_GLYPH[st]} {s}", style=color))
        return Panel(Group(*lines), title="stages", border_style="blue")

    def _log_panel(self) -> Panel:
        return Panel(Group(*[Text(l, overflow="ellipsis", no_wrap=True) for l in self.log]),
                     title="log", border_style="blue")

    def _api_panel(self) -> Panel:
        tbl = Table(expand=True, show_edge=False)
        tbl.add_column("provider", style="cyan", no_wrap=True)
        tbl.add_column("kind", no_wrap=True)
        tbl.add_column("ms", justify="right")
        tbl.add_column("$", justify="right")
        for c in list(self.api)[-10:]:
            err = c.get("error")
            tbl.add_row(c.get("provider", "?"), c.get("kind", ""),
                        str(c.get("latency_ms", "")),
                        ("[red]ERR[/]" if err else f"{c.get('usd', 0):.4f}"))
        head = Text(f"in-flight: {self.in_flight}   cost: ${self.cost:.4f}", style="bold magenta")
        return Panel(Group(head, tbl), title="API calls", border_style="magenta")

    def render(self) -> Layout:
        root = Layout()
        root.split_column(
            Layout(Panel(Text(
                f"synthgen  run {self.run_id}   "
                f"personas {self.counts['personas']}  tasks {self.counts['tasks']}  "
                f"assets {self.counts['assets']}  dedup-flagged {self.counts['dedup']}",
                style="bold"), border_style="green"), size=3, name="head"),
            Layout(name="body"),
        )
        root["body"].split_row(
            Layout(Group(self._stages_panel(), self._log_panel()), name="left"),
            Layout(self._api_panel(), name="right"),
        )
        return root


@contextmanager
def live_dashboard(bus: EventBus, run_id: str = ""):
    dash = RichDashboard(bus, run_id)
    with Live(dash.render(), refresh_per_second=6, screen=False) as live:
        dash.live = live
        yield dash
