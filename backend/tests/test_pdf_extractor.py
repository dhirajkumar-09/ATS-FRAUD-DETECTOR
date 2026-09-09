"""
tests/test_pdf_extractor.py — Phase 1 unit tests
=================================================
Run with:   pytest backend/tests/ -v
"""
from __future__ import annotations

import io
import struct
from pathlib import Path

import pytest

# ─────────────────────────────────────────────────────────────────────────────
# Helpers to build a tiny valid PDF in-memory (no file I/O needed)
# ─────────────────────────────────────────────────────────────────────────────

MINIMAL_PDF = b"""%PDF-1.4
1 0 obj<</Type /Catalog /Pages 2 0 R>>endobj
2 0 obj<</Type /Pages /Kids [3 0 R] /Count 1>>endobj
3 0 obj<</Type /Page /Parent 2 0 R /MediaBox [0 0 595 842]
  /Contents 4 0 R /Resources<</Font<</F1 5 0 R>>>>>>endobj
4 0 obj<</Length 44>>
stream
BT /F1 12 Tf 100 700 Td (Hello, World!) Tj ET
endstream
endobj
5 0 obj<</Type /Font /Subtype /Type1 /BaseFont /Helvetica>>endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000266 00000 n 
0000000360 00000 n 
trailer<</Size 6 /Root 1 0 R>>
startxref
441
%%EOF"""


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Write a minimal one-page PDF to a temp file."""
    p = tmp_path / "sample.pdf"
    p.write_bytes(MINIMAL_PDF)
    return p


# ─────────────────────────────────────────────────────────────────────────────
# Tests for extract_pdf
# ─────────────────────────────────────────────────────────────────────────────

def test_extract_returns_expected_keys(sample_pdf: Path) -> None:
    from app.services.pdf_extractor import extract_pdf

    result = extract_pdf(sample_pdf)

    assert "sha256"     in result
    assert "page_count" in result
    assert "page_dims"  in result
    assert "spans"      in result
    assert "metadata"   in result


def test_sha256_is_hex_string(sample_pdf: Path) -> None:
    from app.services.pdf_extractor import extract_pdf

    result = extract_pdf(sample_pdf)
    sha = result["sha256"]
    assert isinstance(sha, str)
    assert len(sha) == 64
    # All hex chars
    int(sha, 16)   # raises ValueError if not valid hex


def test_page_count(sample_pdf: Path) -> None:
    from app.services.pdf_extractor import extract_pdf

    result = extract_pdf(sample_pdf)
    assert result["page_count"] == 1


def test_page_dims_structure(sample_pdf: Path) -> None:
    from app.services.pdf_extractor import extract_pdf

    dims = extract_pdf(sample_pdf)["page_dims"]
    assert len(dims) == 1
    d = dims[0]
    assert d["page"] == 1
    assert d["width"]  > 0
    assert d["height"] > 0


def test_spans_list_type(sample_pdf: Path) -> None:
    from app.services.pdf_extractor import extract_pdf

    spans = extract_pdf(sample_pdf)["spans"]
    assert isinstance(spans, list)


def test_span_schema(sample_pdf: Path) -> None:
    """Every span must carry the required keys with correct types."""
    from app.services.pdf_extractor import extract_pdf

    spans = extract_pdf(sample_pdf)["spans"]
    if not spans:
        pytest.skip("Minimal PDF produced no spans (renderer-dependent)")

    for span in spans:
        assert isinstance(span["text"],       str)
        assert isinstance(span["font_name"],  str)
        assert isinstance(span["font_size"],  float)
        assert isinstance(span["font_color"], tuple)
        assert len(span["font_color"]) == 3
        assert isinstance(span["bold"],   bool)
        assert isinstance(span["italic"], bool)
        assert isinstance(span["bbox"],   tuple)
        assert len(span["bbox"]) == 4
        assert isinstance(span["page"],   int)
        assert span["page"] >= 1
        assert span["origin"] in ("pymupdf", "pdfplumber")


# ─────────────────────────────────────────────────────────────────────────────
# Tests for colour helper (private, tested via module import)
# ─────────────────────────────────────────────────────────────────────────────

def test_color_int_black() -> None:
    from app.services.pdf_extractor import _color_int_to_rgb

    assert _color_int_to_rgb(0x000000) == (0, 0, 0)


def test_color_int_white() -> None:
    from app.services.pdf_extractor import _color_int_to_rgb

    assert _color_int_to_rgb(0xFFFFFF) == (255, 255, 255)


def test_color_int_red() -> None:
    from app.services.pdf_extractor import _color_int_to_rgb

    assert _color_int_to_rgb(0xFF0000) == (255, 0, 0)


# ─────────────────────────────────────────────────────────────────────────────
# Tests for pdfplumber colour parser
# ─────────────────────────────────────────────────────────────────────────────

def test_parse_pdfplumber_color_none() -> None:
    from app.services.pdf_extractor import _parse_pdfplumber_color

    assert _parse_pdfplumber_color(None) == (0, 0, 0)


def test_parse_pdfplumber_color_greyscale() -> None:
    from app.services.pdf_extractor import _parse_pdfplumber_color

    assert _parse_pdfplumber_color(1.0) == (255, 255, 255)
    assert _parse_pdfplumber_color(0.0) == (0, 0, 0)


def test_parse_pdfplumber_color_rgb_tuple() -> None:
    from app.services.pdf_extractor import _parse_pdfplumber_color

    r, g, b = _parse_pdfplumber_color((1.0, 0.0, 0.5))
    assert r == 255
    assert g == 0
    assert 127 <= b <= 128   # 0.5 * 255


# ─────────────────────────────────────────────────────────────────────────────
# Tests for fraud_detectors stubs (they must all return lists)
# ─────────────────────────────────────────────────────────────────────────────

def test_all_detectors_return_lists(sample_pdf: Path) -> None:
    from app.services.pdf_extractor import extract_pdf
    from app.services.fraud_detectors import run_all_detectors

    result = extract_pdf(sample_pdf)
    signals = run_all_detectors(
        spans=result["spans"],
        page_dims=result["page_dims"],
    )
    assert isinstance(signals, list)
    # Phase 1: stubs return empty
    assert signals == []
