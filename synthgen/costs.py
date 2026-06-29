"""Cost estimation + running tally.

Rates are approximate published list prices (USD) and live here so they're easy to update
in one place. Estimation is intentionally heuristic — its job is to stop a full-manifest
image run from silently spending hundreds of dollars, not to bill to the cent.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# --- per-unit list prices (USD), approximate; edit here when pricing changes ---
# Text models: $ per 1M tokens (input, output).
TEXT_RATES = {
    "claude-opus-4-6": (15.0, 75.0),
    "claude-sonnet-4-20250514": (3.0, 15.0),
    "gpt-4o": (2.5, 10.0),
    "_default": (3.0, 15.0),
}
IMAGE_USD_PER_IMAGE = 0.039          # gemini-2.5-flash-image (Nanobanana), ~1 image
TTS_USD_PER_1K_CHARS = 0.015         # gpt-4o-mini-tts, approx
EMBED_USD_PER_1M_TOKENS = 0.15       # gemini-embedding-001

# Heuristic token sizes for a dry-run estimate (one API call == one batch of 5 tasks).
AVG_BATCH_INPUT_TOKENS = 4500
AVG_BATCH_OUTPUT_TOKENS = 6000
BATCH_SIZE = 5
AVG_PERSONA_EXPAND_INPUT = 3000
AVG_PERSONA_EXPAND_OUTPUT = 5000
AVG_AUDIO_CHARS = 600


def _text_cost(model: str, in_tok: int, out_tok: int) -> float:
    rin, rout = TEXT_RATES.get(model, TEXT_RATES["_default"])
    return in_tok / 1_000_000 * rin + out_tok / 1_000_000 * rout


@dataclass
class CostModel:
    spent_usd: float = 0.0
    breakdown: dict[str, float] = field(default_factory=lambda: {"persona": 0.0, "task": 0.0, "image": 0.0, "audio": 0.0, "pdf": 0.0, "embed": 0.0})

    # --- recording actual spend ---
    def add_text(self, model: str, in_tok: int, out_tok: int, bucket: str) -> float:
        c = _text_cost(model, in_tok, out_tok)
        self.spent_usd += c
        self.breakdown[bucket] = self.breakdown.get(bucket, 0.0) + c
        return c

    def add_image(self, n: int = 1) -> float:
        c = n * IMAGE_USD_PER_IMAGE
        self.spent_usd += c
        self.breakdown["image"] += c
        return c

    def add_audio(self, chars: int) -> float:
        c = chars / 1000 * TTS_USD_PER_1K_CHARS
        self.spent_usd += c
        self.breakdown["audio"] += c
        return c

    def would_exceed(self, extra_usd: float, budget_usd: float | None) -> bool:
        return budget_usd is not None and (self.spent_usd + extra_usd) > budget_usd

    # --- pre-run estimate (no spend) ---
    @staticmethod
    def estimate_run(
        *,
        num_personas: int,
        tasks_per_persona: int,
        persona_model: str,
        task_model: str,
        n_images: int = 0,
        n_audio: int = 0,
        n_pdf: int = 0,
    ) -> dict:
        persona = num_personas * _text_cost(persona_model, AVG_PERSONA_EXPAND_INPUT, AVG_PERSONA_EXPAND_OUTPUT)
        n_batches = num_personas * max(1, -(-tasks_per_persona // BATCH_SIZE))  # ceil
        task = n_batches * _text_cost(task_model, AVG_BATCH_INPUT_TOKENS, AVG_BATCH_OUTPUT_TOKENS)
        n_tasks = num_personas * tasks_per_persona
        embed = n_tasks * 1500 / 1_000_000 * EMBED_USD_PER_1M_TOKENS  # ~1.5k tokens/task embedded
        image = n_images * IMAGE_USD_PER_IMAGE
        audio = n_audio * AVG_AUDIO_CHARS / 1000 * TTS_USD_PER_1K_CHARS
        pdf = 0.0  # reportlab is local/offline, no API cost
        total = persona + task + embed + image + audio + pdf
        return {
            "persona": round(persona, 4), "task": round(task, 4), "embed": round(embed, 4),
            "image": round(image, 4), "audio": round(audio, 4), "pdf": round(pdf, 4),
            "total": round(total, 4),
            "counts": {"personas": num_personas, "tasks": n_tasks, "task_batches": n_batches,
                       "images": n_images, "audio": n_audio, "pdf": n_pdf},
        }


def _demo() -> None:
    est = CostModel.estimate_run(
        num_personas=2, tasks_per_persona=5,
        persona_model="claude-sonnet-4-20250514", task_model="claude-opus-4-6",
        n_images=10, n_audio=2, n_pdf=4,
    )
    assert est["total"] > 0
    assert est["pdf"] == 0.0
    assert abs(est["image"] - 10 * IMAGE_USD_PER_IMAGE) < 1e-9
    cm = CostModel()
    cm.add_image(3)
    assert abs(cm.spent_usd - 3 * IMAGE_USD_PER_IMAGE) < 1e-9
    assert cm.would_exceed(1.0, budget_usd=cm.spent_usd + 0.5)
    assert not cm.would_exceed(0.1, budget_usd=cm.spent_usd + 0.5)
    print("costs self-check OK:", est["total"], "USD for demo run")


if __name__ == "__main__":
    _demo()
