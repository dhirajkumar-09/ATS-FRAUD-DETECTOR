"""
ocr_helper.py — Phase 5, Feature 3 support
=============================================
When `pdf_extractor` flags a page as "suspected image-only" (large embedded
image, almost no extractable text), this module rasterises that page and
runs OCR on it, so the report can show what text was actually hiding behind
the picture — text that a naive ATS text-extraction pass would completely
miss.

Uses PyMuPDF (already a hard dependency) to render the page to a pixmap, and
pytesseract + the system Tesseract binary to OCR it.

Both pytesseract and the Tesseract binary are OPTIONAL. If either is
missing, `ocr_page_text()` returns None with a clear status string instead
of raising — the rest of the pipeline degrades gracefully, exactly like the
existing pikepdf fallback in pdf_extractor.py.
"""
from __future__ import annotations

import logging
from pathlib import Path

import fitz  # PyMuPDF

try:
    import pytesseract
    from PIL import Image
    import io as _io
    _PYTESSERACT_AVAILABLE = True
except ImportError:
    _PYTESSERACT_AVAILABLE = False

logger = logging.getLogger(__name__)

DEFAULT_OCR_DPI = 250


def ocr_status() -> str:
    """Human-readable status of the OCR backend, for API responses / UI."""
    if not _PYTESSERACT_AVAILABLE:
        return "unavailable (pip install pytesseract pillow)"
    try:
        pytesseract.get_tesseract_version()
        return "ready"
    except Exception:  # noqa: BLE001
        return "unavailable (Tesseract binary not found — install the system package)"


def ocr_page_text(pdf_path: str | Path, page_num: int, dpi: int = DEFAULT_OCR_DPI) -> dict:
    """
    Rasterise `page_num` (1-indexed) of the PDF at `pdf_path` and run OCR.

    Returns
    -------
    {
        "available": bool,     # whether OCR actually ran
        "status":    str,      # human-readable status / error
        "text":      str,      # OCR'd text, "" if unavailable/failed
        "char_count": int,
    }
    """
    if not _PYTESSERACT_AVAILABLE:
        return {"available": False, "status": ocr_status(), "text": "", "char_count": 0}

    try:
        doc = fitz.open(str(pdf_path))
        try:
            if page_num < 1 or page_num > doc.page_count:
                return {
                    "available": False,
                    "status": f"page {page_num} out of range",
                    "text": "", "char_count": 0,
                }
            page = doc[page_num - 1]
            zoom = dpi / 72.0
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            png_bytes = pix.tobytes("png")
        finally:
            doc.close()

        image = Image.open(_io.BytesIO(png_bytes))
        text = pytesseract.image_to_string(image)
        text = text.strip()
        return {
            "available": True,
            "status": "ok",
            "text": text,
            "char_count": len(text),
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("OCR failed on page %s: %s", page_num, exc)
        return {
            "available": False,
            "status": f"OCR error: {exc}",
            "text": "", "char_count": 0,
        }