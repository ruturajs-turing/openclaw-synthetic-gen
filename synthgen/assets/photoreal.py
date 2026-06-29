"""Composite a crisp document render onto a surface photo to make a photorealistic
'.real.png' (paper lying on a desk): slight perspective + rotation, soft drop shadow, paper
edge, subtle lighting + grain. Text stays sharp because the render is the overlay layer, not
a diffusion output. Pure OpenCV/NumPy — offline and free.
"""

from __future__ import annotations

import io
import numpy as np


def _to_rgb(png_bytes: bytes) -> np.ndarray:
    from PIL import Image
    im = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    return np.array(im)[:, :, ::-1].copy()  # RGB->BGR for cv2


def _to_png(bgr: np.ndarray) -> bytes:
    import cv2
    ok, buf = cv2.imencode(".png", bgr)
    return buf.tobytes()


def composite(doc_png: bytes, surface_png: bytes, seed="0") -> bytes:
    import cv2

    rng = np.random.default_rng(abs(hash(seed)) % (2**32))
    doc = _to_rgb(doc_png)
    surf = _to_rgb(surface_png)
    # Trim very tall renders to their content-ish top portion so paper isn't mostly blank.
    dh, dw = doc.shape[:2]
    if dh > dw * 1.6:
        doc = doc[: int(dw * 1.5)]
        dh = doc.shape[0]

    # Add a small white paper margin around the render.
    pad = max(8, dw // 40)
    doc = cv2.copyMakeBorder(doc, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=(252, 252, 250))
    dh, dw = doc.shape[:2]

    # Canvas = surface resized to a comfortable landscape/portrait frame around the doc.
    cw, ch = int(dw * 1.5), int(dh * 1.35)
    surf = cv2.resize(surf, (cw, ch))
    canvas = surf.astype(np.float32)

    # Target quad: doc centred, scaled to ~78% of canvas height, with small perspective jitter + rotation.
    scale = (ch * 0.8) / dh
    tw, th = dw * scale, dh * scale
    cx, cy = cw / 2, ch / 2
    j = tw * 0.04
    base = np.float32([[cx - tw/2, cy - th/2], [cx + tw/2, cy - th/2],
                       [cx + tw/2, cy + th/2], [cx - tw/2, cy + th/2]])
    jit = base + rng.uniform(-1, 1, size=base.shape).astype(np.float32) * j
    ang = rng.uniform(-4, 4) * np.pi / 180
    R = np.float32([[np.cos(ang), -np.sin(ang)], [np.sin(ang), np.cos(ang)]])
    dst = ((jit - [cx, cy]) @ R.T + [cx, cy]).astype(np.float32)
    src = np.float32([[0, 0], [dw, 0], [dw, dh], [0, dh]])
    M = cv2.getPerspectiveTransform(src, dst)

    warped = cv2.warpPerspective(doc.astype(np.float32), M, (cw, ch))
    mask = cv2.warpPerspective(np.ones((dh, dw), np.float32), M, (cw, ch))

    # Soft drop shadow: blurred, offset, darkens the surface beneath the sheet.
    sh = cv2.GaussianBlur(mask, (0, 0), sigmaX=cw * 0.012)
    off = int(cw * 0.01)
    sh = np.roll(sh, (off, off), axis=(0, 1))[:, :, None]
    canvas *= (1 - 0.38 * np.clip(sh, 0, 1))

    m3 = np.clip(mask, 0, 1)[:, :, None]
    canvas = warped * m3 + canvas * (1 - m3)

    # Subtle global lighting gradient + fine grain for photographic feel.
    yy = np.linspace(0.92, 1.06, ch)[:, None, None]
    canvas *= yy
    canvas += rng.normal(0, 3.0, canvas.shape)
    return _to_png(np.clip(canvas, 0, 255).astype(np.uint8))
