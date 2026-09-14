"""
test_risk_scoring.py — Comprehensive Test Suite for Explainable Trust Score Engine
=================================================================================
Tests all 10 required test cases from the specification + prompt injection + reproducibility:
  1. Clean resume (no false positives, risk = 0, Verified)
  2. White/invisible text (detected, risk allocated, DEFINITIVE/STRONG evidence)
  3. Tiny-font text (detected <= 1.0pt, risk allocated)
  4. Zero-width characters (U+200B/U+200C detected, codepoints identified, DEFINITIVE)
  5. Homoglyph characters (Cyrillic lookalikes detected, script identified, STRONG)
  6. Off-page text (detected outside bounding canvas, distance computed, DEFINITIVE)
  7. Combined manipulation (multiple categories, capped at 100 risk points)
  8. Normal multilingual resume (legitimate accents/scripts, NO false positives)
  9. Unusual but legitimate fonts (clean text with standard fonts, no false fraud signals)
  10. Legitimate metadata (normal creation/mod timestamps, no high signals)
  11. Prompt injection detector (instruction override attempt detected)
  12. Reproducibility test (same PDF scanned twice produces identical score and signals)
"""
from __future__ import annotations

from pathlib import Path
import pytest

from app.services.pdf_extractor import extract_pdf
from app.services.fraud_detectors import run_all_detectors, detect_prompt_injection
from app.services.risk_config import compute_risk_score, RISK_WEIGHTS, TOTAL_MAX
from app.services.trust_score import compute_trust_score
from tests.generate_fixtures import (
    generate_all_fixtures,
    generate_clean_resume,
    generate_hidden_text_resume,
    generate_tiny_font_resume,
    generate_zero_width_resume,
    generate_homoglyphs_resume,
    generate_offpage_text_resume,
    generate_combined_manipulation_resume,
    generate_multilingual_clean_resume,
    generate_unusual_font_resume,
    generate_prompt_injection_resume,
)


@pytest.fixture(scope="session", autouse=True)
def ensure_fixtures():
    """Generate all test PDF fixtures before running tests."""
    return generate_all_fixtures()


# ── Test 1: Clean Resume (No False Positives) ──────────────────────────────
def test_clean_resume_zero_risk():
    pdf_path = generate_clean_resume()
    extracted = extract_pdf(pdf_path)
    signals = run_all_detectors(
        spans=extracted["spans"],
        page_dims=extracted["page_dims"],
        metadata=extracted["metadata"],
        word_order=extracted.get("word_order"),
        image_pages=extracted.get("image_pages"),
        font_glyph_anomalies=extracted.get("font_glyph_anomalies"),
    )

    # Clean resume must have 0 high-severity signals and 0 risk points
    high_signals = [s for s in signals if s["severity"] == "high"]
    assert len(high_signals) == 0, f"False positive high signals found: {high_signals}"

    risk = compute_risk_score(signals)
    assert risk["total"] == 0, f"Clean resume should have 0 risk points, got {risk['total']}"

    fraud_summary = {"total": len(signals), "high": 0, "medium": 0, "low": 0, "signals": signals}
    trust = compute_trust_score(fraud_summary, ai_content_score=10.0, signals=signals)
    assert trust["score"] >= 75.0, f"Expected Verified score (>=75), got {trust['score']}"
    assert trust["label"] == "Verified"
    assert trust["forensic_risk_score"] == 0


# ── Test 2: White / Near-White Invisible Text ──────────────────────────────
def test_hidden_white_text_detected():
    pdf_path = generate_hidden_text_resume()
    extracted = extract_pdf(pdf_path)
    signals = run_all_detectors(
        spans=extracted["spans"],
        page_dims=extracted["page_dims"],
        metadata=extracted["metadata"],
    )

    hidden_signals = [s for s in signals if s["signal_type"] == "hidden_text"]
    assert len(hidden_signals) >= 1, "Expected at least 1 hidden_text signal"

    sig = hidden_signals[0]
    assert sig["severity"] in ("high", "medium")
    assert sig["evidence_strength"] in ("DEFINITIVE", "STRONG")
    assert sig["risk_points"] > 0
    assert sig["evidence"] is not None
    assert "rgb_distance" in sig["evidence"]

    risk = compute_risk_score(signals)
    assert risk["breakdown"]["hidden_text"] > 0
    assert risk["total"] >= 10


# ── Test 3: Tiny Font Text (<= 1.0pt) ──────────────────────────────────────
def test_tiny_font_detected():
    pdf_path = generate_tiny_font_resume()
    extracted = extract_pdf(pdf_path)
    signals = run_all_detectors(
        spans=extracted["spans"],
        page_dims=extracted["page_dims"],
        metadata=extracted["metadata"],
    )

    tiny_signals = [s for s in signals if s["signal_type"] == "zero_or_tiny_font"]
    assert len(tiny_signals) >= 1, "Expected zero_or_tiny_font signal"

    sig = tiny_signals[0]
    assert sig["evidence_strength"] in ("DEFINITIVE", "STRONG")
    assert sig["evidence"]["font_size"] <= 1.0

    risk = compute_risk_score(signals)
    assert risk["breakdown"]["hidden_text"] > 0


# ── Test 4: Zero-Width Characters ──────────────────────────────────────────
def test_zero_width_chars_detected():
    pdf_path = generate_zero_width_resume()
    extracted = extract_pdf(pdf_path)
    signals = run_all_detectors(
        spans=extracted["spans"],
        page_dims=extracted["page_dims"],
        metadata=extracted["metadata"],
    )

    zw_signals = [s for s in signals if s["signal_type"] == "zero_width_chars"]
    assert len(zw_signals) >= 1, "Expected zero_width_chars signal"

    sig = zw_signals[0]
    assert sig["severity"] == "high"
    assert sig["evidence_strength"] == "DEFINITIVE"
    assert sig["risk_points"] == RISK_WEIGHTS["zero_width_chars"]
    assert sig["evidence"] is not None
    assert sig["evidence"]["occurrence_count"] > 0

    # Ensure codepoints like U+200B or U+200C are identified
    codepoints = [c["codepoint"] for c in sig["evidence"]["characters"]]
    assert any(cp in ("U+200B", "U+200C") for cp in codepoints)

    risk = compute_risk_score(signals)
    assert risk["breakdown"]["zero_width_chars"] == RISK_WEIGHTS["zero_width_chars"]


# ── Test 5: Homoglyph Characters ───────────────────────────────────────────
def test_homoglyphs_detected():
    pdf_path = generate_homoglyphs_resume()
    extracted = extract_pdf(pdf_path)
    signals = run_all_detectors(
        spans=extracted["spans"],
        page_dims=extracted["page_dims"],
        metadata=extracted["metadata"],
    )

    homoglyph_signals = [s for s in signals if s["signal_type"] == "homoglyph_substitution"]
    assert len(homoglyph_signals) >= 1, "Expected homoglyph_substitution signal"

    sig = homoglyph_signals[0]
    assert sig["severity"] == "high"
    assert sig["evidence_strength"] == "STRONG"
    assert sig["risk_points"] == RISK_WEIGHTS["homoglyph"]
    assert sig["evidence"] is not None
    assert "suspect_chars" in sig["evidence"]

    risk = compute_risk_score(signals)
    assert risk["breakdown"]["homoglyph"] == RISK_WEIGHTS["homoglyph"]


# ── Test 6: Off-Page Text ──────────────────────────────────────────────────
def test_offpage_text_detected():
    pdf_path = generate_offpage_text_resume()
    extracted = extract_pdf(pdf_path)
    signals = run_all_detectors(
        spans=extracted["spans"],
        page_dims=extracted["page_dims"],
        metadata=extracted["metadata"],
    )

    offpage_signals = [s for s in signals if s["signal_type"] == "offpage_text"]
    assert len(offpage_signals) >= 1, "Expected offpage_text signal"

    sig = offpage_signals[0]
    assert sig["severity"] == "high"
    assert sig["evidence_strength"] == "DEFINITIVE"
    assert sig["evidence"]["distance_outside_pt"] > 0

    risk = compute_risk_score(signals)
    assert risk["breakdown"]["offpage"] == RISK_WEIGHTS["offpage"]


# ── Test 7: Combined Manipulation & 100-Point Capping ─────────────────────
def test_combined_manipulation_capped_at_100():
    pdf_path = generate_combined_manipulation_resume()
    extracted = extract_pdf(pdf_path)
    signals = run_all_detectors(
        spans=extracted["spans"],
        page_dims=extracted["page_dims"],
        metadata=extracted["metadata"],
    )

    # Should detect homoglyphs, zero-width chars, hidden text, and prompt injection
    types_found = {s["signal_type"] for s in signals}
    assert "homoglyph_substitution" in types_found
    assert "zero_width_chars" in types_found
    assert "hidden_text" in types_found

    risk = compute_risk_score(signals)
    assert risk["total"] <= TOTAL_MAX
    assert risk["total"] >= 50, f"Expected high total risk, got {risk['total']}"

    fraud_summary = {
        "total": len(signals),
        "high": sum(1 for s in signals if s["severity"] == "high"),
        "medium": sum(1 for s in signals if s["severity"] == "medium"),
        "low": sum(1 for s in signals if s["severity"] == "low"),
        "signals": signals,
    }
    trust = compute_trust_score(fraud_summary, ai_content_score=20.0, signals=signals)
    assert trust["label"] == "High Risk"
    assert trust["score"] <= 44.0  # Capped due to multiple high signals


# ── Test 8: Multilingual Clean Resume (No False Positives) ─────────────────
def test_multilingual_clean_no_false_positives():
    pdf_path = generate_multilingual_clean_resume()
    extracted = extract_pdf(pdf_path)
    signals = run_all_detectors(
        spans=extracted["spans"],
        page_dims=extracted["page_dims"],
        metadata=extracted["metadata"],
    )

    # Legitimate French / German accents (François, Müller) must NOT trigger homoglyph fraud
    homoglyphs = [s for s in signals if s["signal_type"] == "homoglyph_substitution"]
    assert len(homoglyphs) == 0, f"False positive homoglyph found: {homoglyphs}"

    high_signals = [s for s in signals if s["severity"] == "high"]
    assert len(high_signals) == 0, f"False positive high signals found: {high_signals}"

    risk = compute_risk_score(signals)
    assert risk["total"] == 0, f"Expected 0 risk points, got {risk['total']}"


# ── Test 9: Unusual but Legitimate Fonts ───────────────────────────────────
def test_unusual_font_clean():
    pdf_path = generate_unusual_font_resume()
    extracted = extract_pdf(pdf_path)
    signals = run_all_detectors(
        spans=extracted["spans"],
        page_dims=extracted["page_dims"],
        metadata=extracted["metadata"],
        font_glyph_anomalies=extracted.get("font_glyph_anomalies"),
    )

    # Courier font alone is NOT fraud
    high_signals = [s for s in signals if s["severity"] == "high"]
    assert len(high_signals) == 0, f"Unexpected high signals in standard font: {high_signals}"


# ── Test 10: Legitimate Metadata (Weak Signal / No High Signals) ───────────
def test_legitimate_metadata():
    clean_metadata = {
        "creator": "Microsoft Word",
        "producer": "macOS Quartz PDFContext",
        "creationDate": "D:20230501100000",
        "modDate": "D:20230501100000",
    }
    signals = run_all_detectors(
        spans=[],
        page_dims=[],
        metadata=clean_metadata,
    )

    # Word with identical creation and mod date should have no high or medium red flags
    high_med = [s for s in signals if s["severity"] in ("high", "medium")]
    assert len(high_med) == 0


# ── Test 11: Prompt Injection Detector ─────────────────────────────────────
def test_prompt_injection_detector():
    pdf_path = generate_prompt_injection_resume()
    extracted = extract_pdf(pdf_path)
    injection_signals = detect_prompt_injection(extracted["spans"])

    assert len(injection_signals) >= 1, "Expected prompt injection to be detected"
    sig = injection_signals[0]
    assert sig["signal_type"] == "prompt_injection"
    assert sig["evidence_strength"] in ("STRONG", "MODERATE")
    assert sig["risk_points"] == RISK_WEIGHTS["prompt_injection"]
    assert sig["evidence"] is not None
    assert "ignore previous instructions" in sig["evidence"]["matched_text"].lower()


# ── Test 12: Reproducibility (Same PDF = Exactly Same Score) ───────────────
def test_score_reproducibility():
    pdf_path = generate_hidden_text_resume()

    extracted_1 = extract_pdf(pdf_path)
    signals_1 = run_all_detectors(extracted_1["spans"], extracted_1["page_dims"], metadata=extracted_1["metadata"])
    risk_1 = compute_risk_score(signals_1)
    trust_1 = compute_trust_score({"total": len(signals_1), "high": 1, "medium": 0, "low": 0}, 20.0, signals=signals_1)

    extracted_2 = extract_pdf(pdf_path)
    signals_2 = run_all_detectors(extracted_2["spans"], extracted_2["page_dims"], metadata=extracted_2["metadata"])
    risk_2 = compute_risk_score(signals_2)
    trust_2 = compute_trust_score({"total": len(signals_2), "high": 1, "medium": 0, "low": 0}, 20.0, signals=signals_2)

    assert risk_1["total"] == risk_2["total"]
    assert risk_1["breakdown"] == risk_2["breakdown"]
    assert trust_1["score"] == trust_2["score"]
    assert trust_1["label"] == trust_2["label"]
    assert len(signals_1) == len(signals_2)
    for s1, s2 in zip(signals_1, signals_2):
        assert s1["signal_type"] == s2["signal_type"]
        assert s1["risk_points"] == s2["risk_points"]
