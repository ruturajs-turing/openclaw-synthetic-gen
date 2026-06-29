"""Asset generators register themselves into dispatcher.GENERATORS on import."""


def register_all() -> None:
    """Import every generator module so it registers. Tolerant of not-yet-built ones."""
    for mod in ("stub", "pdf", "image", "audio"):
        try:
            __import__(f"{__name__}.{mod}", fromlist=["_"])
        except Exception:
            pass
