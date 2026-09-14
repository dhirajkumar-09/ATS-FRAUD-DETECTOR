"""
pdf_extractor.py — Phase 1 core (+ Phase 5 forensic extensions)
=================================================================
Extracts every text span from a PDF using PyMuPDF (primary) and cross-checks
layout structure with pdfplumber where ambiguous.

Phase 5 additions
------------------
- word_order  : per-page reading-order-vs-extraction-order disorder stats,
                used by fraud_detectors.detect_layer_order_mismatch()
- image_pages : per-page text-density vs image-coverage stats, used by
                fraud_detectors.detect_image_only_pages()

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

# Words per page above which we skip the O(n log n) inversion count (safety
# valve — a resume page should never realistically have this many words).
_MAX_WORDS_FOR_ORDER_CHECK = 4000
# Ignore pages with fewer words than this — too little signal to be meaningful.
_MIN_WORDS_FOR_ORDER_CHECK = 8


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
        - "word_order":  list of {page, word_count, disorder_ratio} — Feature 1
        - "image_pages": list of {page, text_char_count, image_area_ratio,
                                    is_suspected_image_only} — Feature 3
    """
    file_path = Path(file_path)
    raw_bytes = file_path.read_bytes()
    if len(raw_bytes) == 0:
        raise ValueError("Uploaded file is empty (0 bytes).")

    sha256 = _sha256(raw_bytes)
    spans, page_dims, page_count, word_order, image_pages = _extract_with_pymupdf(file_path)
    metadata = _extract_metadata(file_path)

    # Cross-verify with pdfplumber on pages where PyMuPDF found 0 spans
    empty_pages = {d["page"] for d in page_dims} - {s["page"] for s in spans}
    if empty_pages:
        logger.info("pdfplumber cross-check on pages: %s", empty_pages)
        try:
            fallback_spans = _extract_with_pdfplumber(file_path, pages=empty_pages)
            spans.extend(fallback_spans)
        except Exception as exc:
            logger.warning("pdfplumber fallback failed: %s", exc)

    return {
        "sha256":      sha256,
        "page_count":  page_count,
        "page_dims":   page_dims,
        "spans":       spans,
        "metadata":    metadata,
        "word_order":  word_order,
        "image_pages": image_pages,
        "font_glyph_anomalies": _extract_font_glyph_map(spans),
    }

# ─────────────────────────────────────────────────────────────────────────────
# Feature 4 — Font Substitution / Glyph Swap Detection (Heuristic Fallback)
# ─────────────────────────────────────────────────────────────────────────────

import re

def _extract_font_glyph_map(spans: list[dict]) -> list[dict]:
    """
    Heuristic fallback for Font-Substitution / Glyph-Swap detection.
    True ToUnicode CMap mismatch checks require parsing low-level PDF stream objects,
    which is brittle. Instead, we flag spans using subset-tagged custom fonts 
    (e.g., 'ABCDEF+FontName') that contain an unusually high density of 
    ATS keywords or Unicode Private Use Area (PUA) characters, indicating 
    likely glyph-swapped invisible stuffing.
    """
    anomalies = []
    
    ATS_KEYWORDS = {
        "python", "java", "kubernetes", "aws", "react", "agile", 
        "leadership", "synergy", "docker", "azure", "sql", "javascript", 
        "typescript", "scrum", "devops", "c++", "golang", "marketing", "sales"
    }
    
    for span in spans:
        font_name = span.get("font_name", "")
        if not font_name or not re.match(r'^[A-Z]{6}\+', font_name):
            continue
            
        text = span.get("text", "")
        if not text.strip():
            continue
            
        # 1. PUA character check (Common in glyph swaps)
        pua_count = sum(1 for c in text if 0xE000 <= ord(c) <= 0xF8FF)
        if pua_count > 0:
            anomalies.append({
                "page": span.get("page", 1),
                "font_name": font_name,
                "span_bbox": span.get("bbox"),
                "suspected_visual_text": "[unreadable/pua]",
                "suspected_extracted_text": text,
                "confidence": "high",
            })
            continue
            
        # 2. High ATS keyword density check
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        if not words or len(words) < 3:
            continue
            
        keyword_hits = [w for w in words if w in ATS_KEYWORDS]
        for kw in ["machine learning", "project management", "ci/cd"]:
            if kw in text_lower:
                keyword_hits.append(kw)
                
        density = len(keyword_hits) / len(words)
        if density > 0.4 and len(keyword_hits) >= 3:
            anomalies.append({
                "page": span.get("page", 1),
                "font_name": font_name,
                "span_bbox": span.get("bbox"),
                "suspected_visual_text": "[visually hidden/swapped]",
                "suspected_extracted_text": text,
                "confidence": "medium",
            })

    return anomalies

# ─────────────────────────────────────────────────────────────────────────────
# Private helpers — core extraction
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
) -> tuple[list[dict], list[dict], int, list[dict], list[dict]]:
    """
    Primary extraction using PyMuPDF (fitz).

    Returns (spans, page_dims, page_count, word_order, image_pages).
    Uses `page.get_text("rawdict")` which gives character-level runs.
    """
    spans: list[dict] = []
    page_dims: list[dict] = []
    word_order: list[dict] = []
    image_pages: list[dict] = []

    try:
        doc = fitz.open(str(file_path))
    except Exception as exc:
        raise ValueError(f"Invalid or corrupted PDF file: {exc}") from exc

    try:
        if getattr(doc, "is_encrypted", False) or getattr(doc, "needs_pass", False):
            raise ValueError("PDF is encrypted or password-protected. Please provide an unlocked document.")

        page_count = doc.page_count
        if page_count == 0:
            raise ValueError("PDF contains no pages.")

        for page_index in range(page_count):
            page_num = page_index + 1
            page = doc[page_index]

            page_w, page_h = page.rect.width, page.rect.height
            page_dims.append({
                "page":   page_num,
                "width":  page_w,
                "height": page_h,
            })

            # Expand clip so off-page text positioned outside page dimensions can be extracted and flagged
            expanded_clip = fitz.Rect(-2000, -2000, page_w + 2000, page_h + 2000)
            raw = page.get_text("rawdict", clip=expanded_clip, flags=fitz.TEXT_PRESERVE_WHITESPACE)
            page_char_count = 0
            for block_index, block in enumerate(raw.get("blocks", [])):
                if block.get("type") != 0:   # 0 = text block
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text")
                        if text is None and "chars" in span:
                            text = "".join(c.get("c", "") for c in span["chars"])
                        if not text:
                            continue
                        page_char_count += len(text.strip())

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
                            "page":       page_num,
                            "block_no":   block_index,
                            "origin":     "pymupdf",
                        })

            # ── Feature 1: PDF layer-order forensics ───────────────────────────
            word_order.append(_compute_word_order_signal(page, page_num))

            # ── Feature 3: image-only page detection ───────────────────────────
            image_pages.append(
                _compute_image_page_stats(page, page_num, page_char_count, page_w, page_h)
            )
    finally:
        doc.close()

    return spans, page_dims, page_count, word_order, image_pages



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
                        "block_no":   0,
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
# Feature 1 — PDF layer-order forensics
# ─────────────────────────────────────────────────────────────────────────────
# Compares the order words are *extracted* from the content stream (default
# PyMuPDF sort=False order — driven by the underlying text-showing operators)
# against the order a human eye would read them in (top-to-bottom,
# left-to-right). A genuine PDF's two orderings match almost perfectly. A
# resume where someone has scrambled the underlying text order (so it *looks*
# normal but an ATS/parser reading in stream order sees jumbled/stuffed
# content) shows a high disorder ratio here.

def _visual_sort_key(word: tuple) -> tuple:
    """
    word = (x0, y0, x1, y1, text, block_no, line_no, word_no)
    Bucket y0 into ~3pt bands so words on the same visual line sort by x
    first, rather than being thrown off by sub-pixel baseline jitter.
    """
    x0, y0 = word[0], word[1]
    return (round(y0 / 3.0), x0)


def _count_inversions(ranks: list[int]) -> int:
    """
    Count inversions in `ranks` (pairs i<j with ranks[i] > ranks[j]) using
    merge sort — O(n log n). Used to quantify how far the extraction order
    deviates from the visual reading order.
    """
    def merge_count(arr: list[int]) -> tuple[list[int], int]:
        if len(arr) <= 1:
            return arr, 0
        mid = len(arr) // 2
        left, inv_l = merge_count(arr[:mid])
        right, inv_r = merge_count(arr[mid:])
        merged: list[int] = []
        i = j = inv_split = 0
        while i < len(left) and j < len(right):
            if left[i] <= right[j]:
                merged.append(left[i])
                i += 1
            else:
                merged.append(right[j])
                j += 1
                inv_split += len(left) - i
        merged.extend(left[i:])
        merged.extend(right[j:])
        return merged, inv_l + inv_r + inv_split

    _, total = merge_count(ranks)
    return total


def _compute_word_order_signal(page: "fitz.Page", page_num: int) -> dict:
    """
    Returns {"page", "word_count", "disorder_ratio", "sample_words"} for one page.
    disorder_ratio is in [0, 1]: 0 = perfectly matches reading order,
    1 = maximally scrambled (reverse order).
    """
    try:
        words = page.get_text("words", sort=False)  # extraction / stream order
    except Exception as exc:  # noqa: BLE001
        logger.warning("word-order extraction failed on page %s: %s", page_num, exc)
        words = []

    n = len(words)
    if n < _MIN_WORDS_FOR_ORDER_CHECK or n > _MAX_WORDS_FOR_ORDER_CHECK:
        return {"page": page_num, "word_count": n, "disorder_ratio": 0.0, "sample_words": []}

    # visual_rank_by_extraction_index[i] = rank of the i-th extracted word
    # once everything is sorted into top-to-bottom / left-to-right order.
    order_by_visual = sorted(range(n), key=lambda i: _visual_sort_key(words[i]))
    visual_rank_by_extraction_index = [0] * n
    for visual_rank, extraction_index in enumerate(order_by_visual):
        visual_rank_by_extraction_index[extraction_index] = visual_rank

    inversions = _count_inversions(visual_rank_by_extraction_index)
    max_inversions = n * (n - 1) / 2 or 1
    disorder_ratio = round(inversions / max_inversions, 4)

    # Grab a short readable sample of the extraction-order text so the report
    # can show *what* looked scrambled.
    sample_words = [w[4] for w in words[:40]]

    return {
        "page": page_num,
        "word_count": n,
        "disorder_ratio": disorder_ratio,
        "sample_words": sample_words,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Feature 3 — image-only page detection (OCR-bypass check)
# ─────────────────────────────────────────────────────────────────────────────

def _compute_image_page_stats(
    page: "fitz.Page",
    page_num: int,
    text_char_count: int,
    page_w: float,
    page_h: float,
) -> dict:
    """
    Returns {"page", "text_char_count", "image_area_ratio",
             "is_suspected_image_only"} for one page.
    """
    page_area = max(page_w * page_h, 1.0)
    total_image_area = 0.0

    try:
        for img in page.get_images(full=True):
            xref = img[0]
            try:
                rects = page.get_image_rects(xref)
            except Exception:  # noqa: BLE001
                rects = []
            for rect in rects:
                total_image_area += max(rect.width, 0) * max(rect.height, 0)
    except Exception as exc:  # noqa: BLE001
        logger.warning("image stat extraction failed on page %s: %s", page_num, exc)

    image_area_ratio = round(min(total_image_area / page_area, 1.0), 4)

    # Suspected evasion: page is visually dominated by an image (>50% of the
    # page area) yet almost no extractable text exists on it.
    is_suspected = image_area_ratio > 0.5 and text_char_count < 25

    return {
        "page": page_num,
        "text_char_count": text_char_count,
        "image_area_ratio": image_area_ratio,
        "is_suspected_image_only": is_suspected,
    }


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
        "word_order":  result["word_order"],
        "image_pages": result["image_pages"],
        "first_5_spans": result["spans"][:5],
    }
    print(json.dumps(summary, indent=2))