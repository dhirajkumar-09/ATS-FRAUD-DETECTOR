"""
heatmap_generator.py — Phase 4
================================
Two responsibilities:

1. generate_heatmap()      — burns severity-coloured, semi-transparent
                              rectangles + a small label onto a copy of the
                              original PDF at each FraudSignal's bbox.
2. render_page_images()    — rasterises each page of a PDF (heatmap or
                              original) to PNG bytes, for the dashboard /
                              embedding in the forensic report. Uses
                              PyMuPDF's built-in renderer, so no Poppler /
                              pdf2image system dependency is required.
"""
from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF

# ── Severity → RGBA colour (0-1 floats, PyMuPDF convention) ─────────────────
SEVERITY_COLORS: dict[str, tuple[float, float, float]] = {
    "high":   (0.90, 0.15, 0.15),   # red
    "medium": (0.95, 0.55, 0.10),   # orange
    "low":    (0.95, 0.80, 0.10),   # yellow
}
DEFAULT_COLOR = (0.5, 0.5, 0.5)     # grey fallback for unknown severity
FILL_OPACITY = 0.28
BORDER_WIDTH = 1.2
DEFAULT_DPI = 150


def generate_heatmap(
    original_pdf_path: Path,
    signals: list[dict],
    output_path: Path,
) -> Path:
    """
    Copy the original PDF and draw a coloured rectangle over every signal
    that has a bbox, colour-coded by severity, with a small tag showing the
    signal type. Signals without a bbox (e.g. timeline issues) are skipped
    since there's nowhere on the page to draw them.

    Parameters
    ----------
    original_pdf_path : Path to the source PDF on disk.
    signals            : list of dicts shaped like FraudSignal rows, e.g.
                          {"signal_type": str, "severity": "high"|"medium"|"low",
                           "page": int (1-indexed), "bbox": (x0,y0,x1,y1) | None,
                           "description": str, ...}
    output_path        : where to write the annotated PDF.

    Returns
    -------
    Path to the annotated PDF (same as output_path).
    """
    doc = fitz.open(original_pdf_path)

    try:
        for sig in signals:
            bbox = sig.get("bbox")
            if not bbox or any(v is None for v in bbox):
                continue  # nothing to draw — e.g. timeline_issue has no bbox

            page_num = sig.get("page", 1) - 1  # bbox pages are 1-indexed
            if page_num < 0 or page_num >= doc.page_count:
                continue

            page = doc[page_num]
            rect = fitz.Rect(*bbox)
            color = SEVERITY_COLORS.get(sig.get("severity", ""), DEFAULT_COLOR)

            # Semi-transparent filled rectangle, coloured border
            annot = page.add_rect_annot(rect)
            annot.set_colors(stroke=color, fill=color)
            annot.set_opacity(FILL_OPACITY)
            annot.set_border(width=BORDER_WIDTH)
            annot.update()

            # Small text tag above the box naming the signal type
            label = sig.get("signal_type", "signal").replace("_", " ")
            label_point = fitz.Point(rect.x0, max(rect.y0 - 2, 0))
            page.insert_text(
                label_point,
                label,
                fontsize=6,
                color=color,
                fontname="helv",
                render_mode=0,
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(output_path, garbage=4, deflate=True)
    finally:
        doc.close()

    return output_path


def render_page_images(
    pdf_path: Path,
    dpi: int = DEFAULT_DPI,
) -> list[bytes]:
    """
    Rasterise every page of a PDF to PNG bytes using PyMuPDF (no Poppler /
    pdf2image dependency needed). Used to feed the Streamlit heatmap viewer
    and to embed page images in the forensic PDF report.

    Returns a list of PNG byte-strings, one per page, in page order.
    """
    doc = fitz.open(pdf_path)
    images: list[bytes] = []
    try:
        zoom = dpi / 72.0  # PDF default is 72 dpi
        matrix = fitz.Matrix(zoom, zoom)
        for page in doc:
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            images.append(pix.tobytes("png"))
    finally:
        doc.close()

    return images