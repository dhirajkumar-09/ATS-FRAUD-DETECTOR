"""
pdf_extractor.py — Phase 1 core
================================
Extracts every text span from a PDF using PyMuPDF (primary) and cross-checks
layout structure with pdfplumber where ambiguous.

Each span returned is a plain dict:
{
    "text":       str,           # raw characters in this run
    "font_name":  str,
    "font_size":  float,         # in points
    "font_color": tuple[int,int,int],   # RGB 0-255
    "bold":       bool,
    "italic":     bool,
    "bbox":       tuple[float,float,float,float],  # x0,y0,x1,y1 in PDF-points
    "page":       int,           # 1-indexed
    "origin":     str,           # "pymupdf" | "pdfplumber"
}

Page dimensions are returned separately as:
{
    "page": int,
    "width": float,
    "height": float,
}
"""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

import fitz          # PyMuPDF
import pdfplumber

# pikepdf is optional — it requires C++ Build Tools on Windows and has no
# Python 3.14 wheel yet.  We fall back to PyMuPDF's doc.metadata.
try:
    import pikepdf as _pikepdf
    _PIKEPDF_AVAILABLE = True
except ImportError:
    _pikepdf = None          # type: ignore[assignment]
    _PIKEPDF_AVAILABLE = False

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def extract_pdf(file_path: str | Path) -> dict[str, Any]:
    """
    Full extraction pipeline.  Returns a dict with:
        - "sha256":      SHA-256 hex of the raw file bytes
        - "page_count":  int
        - "page_dims":   list of {page, width, height}
        - "spans":       list of span dicts (all pages combined)
        - "metadata":    dict from pikepdf (creator, producer, mod-date …)
    """
    file_path = Path(file_path)
    raw_bytes = file_path.read_bytes()

    sha256 = _sha256(raw_bytes)
    spans, page_dims, page_count = _extract_with_pymupdf(file_path)
    metadata = _extract_metadata(file_path)

    # Cross-verify with pdfplumber on pages where PyMuPDF found 0 spans
    empty_pages = {d["page"] for d in page_dims} - {s["page"] for s in spans}
    if empty_pages:
        logger.info("pdfplumber cross-check on pages: %s", empty_pages)
        fallback_spans = _extract_with_pdfplumber(file_path, pages=empty_pages)
        spans.extend(fallback_spans)

    return {
        "sha256":     sha256,
        "page_count": page_count,
        "page_dims":  page_dims,
        "spans":      spans,
        "metadata":   metadata,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Private helpers
# ─────────────────────────────────────────────────────────────────────────────

def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _color_int_to_rgb(color_int: int) -> tuple[int, int, int]:
    """
    PyMuPDF encodes colour as a 24-bit integer 0xRRGGBB.
    Returns (R, G, B) each 0-255.
    """
    r = (color_int >> 16) & 0xFF
    g = (color_int >> 8) & 0xFF
    b = color_int & 0xFF
    return (r, g, b)


def _extract_with_pymupdf(
    file_path: Path,
) -> tuple[list[dict], list[dict], int]:
    """
    Primary extraction using PyMuPDF (fitz).

    Returns (spans, page_dims, page_count).
    Uses `page.get_text("rawdict")` which gives character-level runs.
    """
    spans: list[dict] = []
    page_dims: list[dict] = []

    doc = fitz.open(str(file_path))
    page_count = doc.page_count

    for page_index in range(page_count):
        page_num = page_index + 1
        page = doc[page_index]

        page_dims.append({
            "page":   page_num,
            "width":  page.rect.width,
            "height": page.rect.height,
        })

        raw = page.get_text("rawdict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
        for block in raw.get("blocks", []):
            if block.get("type") != 0:   # 0 = text block
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "")
                    if not text:
                        continue

                    color_int = span.get("color", 0)
                    rgb = _color_int_to_rgb(color_int)

                    flags = span.get("flags", 0)
                    # PyMuPDF flag bits: bit 4 = bold, bit 1 = italic
                    bold   = bool(flags & (1 << 4))
                    italic = bool(flags & (1 << 1))

                    bbox = span.get("bbox", (0, 0, 0, 0))

                    spans.append({
                        "text":       text,
                        "font_name":  span.get("font", ""),
                        "font_size":  round(span.get("size", 0.0), 3),
                        "font_color": rgb,
                        "bold":       bold,
                        "italic":     italic,
                        "bbox":       (
                            round(bbox[0], 3), round(bbox[1], 3),
                            round(bbox[2], 3), round(bbox[3], 3),
                        ),
                        "page":   page_num,
                        "origin": "pymupdf",
                    })

    doc.close()
    return spans, page_dims, page_count


def _extract_with_pdfplumber(
    file_path: Path,
    pages: set[int] | None = None,
) -> list[dict]:
    """
    Fallback / cross-check extraction using pdfplumber.
    `pages` is a set of 1-indexed page numbers to process.
    Returns span dicts tagged with origin="pdfplumber".
    """
    spans: list[dict] = []

    with pdfplumber.open(str(file_path)) as pdf:
        for page_index, page in enumerate(pdf.pages):
            page_num = page_index + 1
            if pages is not None and page_num not in pages:
                continue

            chars = page.chars or []
            # Group consecutive chars with identical style into spans
            current: dict | None = None

            for ch in chars:
                text   = ch.get("text", "")
                size   = round(float(ch.get("size", 0)), 3)
                font   = ch.get("fontname", "")
                color  = _parse_pdfplumber_color(ch.get("non_stroking_color"))
                x0     = round(float(ch.get("x0",   0)), 3)
                y0     = round(float(ch.get("top",   0)), 3)
                x1     = round(float(ch.get("x1",   0)), 3)
                y1     = round(float(ch.get("bottom", 0)), 3)

                same_style = (
                    current is not None
                    and current["font_name"] == font
                    and current["font_size"] == size
                    and current["font_color"] == color
                    and current["page"] == page_num
                )

                if same_style:
                    current["text"] += text
                    current["bbox"] = (
                        current["bbox"][0], current["bbox"][1],
                        x1, y1,
                    )
                else:
                    if current:
                        spans.append(current)
                    current = {
                        "text":       text,
                        "font_name":  font,
                        "font_size":  size,
                        "font_color": color,
                        "bold":       False,   # pdfplumber doesn't expose this cheaply
                        "italic":     False,
                        "bbox":       (x0, y0, x1, y1),
                        "page":       page_num,
                        "origin":     "pdfplumber",
                    }
            if current:
                spans.append(current)

    return spans


def _parse_pdfplumber_color(
    color: Any,
) -> tuple[int, int, int]:
    """
    pdfplumber returns colour in several formats:
     - None  → black (0, 0, 0)
     - float  → greyscale 0.0-1.0
     - (r, g, b) floats 0.0-1.0
    Returns (R, G, B) each 0-255.
    """
    if color is None:
        return (0, 0, 0)
    if isinstance(color, (int, float)):
        v = int(float(color) * 255)
        return (v, v, v)
    if isinstance(color, (list, tuple)) and len(color) >= 3:
        return tuple(int(c * 255) for c in color[:3])   # type: ignore[return-value]
    return (0, 0, 0)


def _extract_metadata(file_path: Path) -> dict[str, str]:
    """
    Extract PDF metadata. Strategy:
      1. PyMuPDF doc.metadata  — always available, covers creator/producer/dates
      2. pikepdf docinfo + XMP — richer, but optional (needs C++ build tools on Win)

    Returns a plain string-keyed dict for JSON serialisation.
    """
    meta: dict[str, str] = {}

    # ── 1. PyMuPDF (always available) ────────────────────────────────────────
    try:
        doc = fitz.open(str(file_path))
        for key, value in (doc.metadata or {}).items():
            if value:
                meta[key] = str(value)
        doc.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("PyMuPDF metadata extraction failed: %s", exc)

    # ── 2. pikepdf — richer XMP metadata (optional) ───────────────────────────
    if _PIKEPDF_AVAILABLE:
        try:
            with _pikepdf.open(str(file_path)) as pdf:
                docinfo = pdf.docinfo
                for key in docinfo:
                    try:
                        meta[f"pikepdf:{key}"] = str(docinfo[key])
                    except Exception:  # noqa: BLE001
                        pass
                with pdf.open_metadata() as xmp:
                    for ns, tag in xmp.items():
                        try:
                            meta[f"xmp:{tag}"] = str(xmp[ns, tag])
                        except Exception:  # noqa: BLE001
                            pass
        except Exception as exc:  # noqa: BLE001
            logger.warning("pikepdf metadata extraction failed: %s", exc)
    else:
        meta["_pikepdf_status"] = "not installed (Python 3.14 wheel unavailable)"

    return meta


# ─────────────────────────────────────────────────────────────────────────────
# Quick CLI test helper (run: python -m app.services.pdf_extractor <file.pdf>)
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m app.services.pdf_extractor <path/to/resume.pdf>")
        sys.exit(1)

    result = extract_pdf(sys.argv[1])
    # Print summary rather than all spans (can be thousands of lines)
    summary = {
        "sha256":     result["sha256"],
        "page_count": result["page_count"],
        "span_count": len(result["spans"]),
        "page_dims":  result["page_dims"],
        "metadata":   result["metadata"],
        "first_5_spans": result["spans"][:5],
    }
    print(json.dumps(summary, indent=2))
