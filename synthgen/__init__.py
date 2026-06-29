"""synthgen — unified end-to-end synthetic data pipeline.

persona generation -> task generation (backprop + gemini-embedding dedup + memory)
-> document/PII extraction -> asset generation (images/pdf/audio) -> per-persona packaging.

Core logic is UI-agnostic: it emits events on an EventBus (see synthgen.events) rather
than printing, so a console dashboard today and a GUI later can both subscribe.
"""

__version__ = "0.1.0"

SYNTHETIC_BANNER = "SYNTHETIC SPECIMEN — generated test data — contains no real PII"
