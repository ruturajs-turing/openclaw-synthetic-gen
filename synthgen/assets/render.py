"""Headless-Chromium HTML→PNG renderer (Playwright, async). One browser per run, reused
across all renders; produces crisp, legible document images at 2x device scale.
"""

from __future__ import annotations

_pw = None
_browser = None


async def _browser_get():
    global _pw, _browser
    if _browser is None:
        from playwright.async_api import async_playwright
        _pw = await async_playwright().start()
        _browser = await _pw.chromium.launch(args=["--no-sandbox", "--force-color-profile=srgb"])
    return _browser


async def render_png(html: str, width: int = 820, scale: int = 2) -> bytes:
    """Render an HTML string to a full-page PNG (height grows to fit content)."""
    browser = await _browser_get()
    page = await browser.new_page(viewport={"width": width, "height": 1100}, device_scale_factor=scale)
    try:
        await page.set_content(html, wait_until="networkidle")
        return await page.screenshot(full_page=True)
    finally:
        await page.close()


async def shutdown() -> None:
    global _pw, _browser
    try:
        if _browser is not None:
            await _browser.close()
    finally:
        _browser = None
        if _pw is not None:
            await _pw.stop()
            _pw = None
