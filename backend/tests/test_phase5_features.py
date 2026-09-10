"""
tests/test_phase5_features.py — Phase 5 unit tests
======================================================
Covers the four new features:
  1. PDF layer-order forensics   (detect_layer_order_mismatch)
  2. Metadata forensics          (detect_metadata_red_flags)
  3. Image-only page detection   (detect_image_only_pages)
  4. Trust Score badge           (compute_trust_score)

Pure function tests — no PDF parsing, no database, no API.
Run: pytest tests/test_phase5_features.py -v
"""
from __future__ import annotations

from app.services.fraud_detectors import (
    detect_image_only_pages,
    detect_layer_order_mismatch,
    detect_metadata_red_flags,
)
from app.services.trust_score import compute_trust_score


# ─────────────────────────────────────────────────────────────────────────────
# 1. Layer-order forensics
# ─────────────────────────────────────────────────────────────────────────────
def test_layer_order_no_signal_when_low_disorder():
    word_order = [{"page": 1, "word_count": 50, "disorder_ratio": 0.02, "sample_words": []}]
    signals = detect_layer_order_mismatch(word_order)
    assert signals == []


def test_layer_order_medium_signal():
    word_order = [{"page": 1, "word_count": 50, "disorder_ratio": 0.20, "sample_words": ["a", "b"]}]
    signals = detect_layer_order_mismatch(word_order)
    assert len(signals) == 1
    assert signals[0]["severity"] == "medium"
    assert signals[0]["signal_type"] == "layer_order_mismatch"


def test_layer_order_high_signal():
    word_order = [{"page": 2, "word_count": 80, "disorder_ratio": 0.55, "sample_words": ["x"]}]
    signals = detect_layer_order_mismatch(word_order)
    assert len(signals) == 1
    assert signals[0]["severity"] == "high"
    assert signals[0]["page"] == 2


def test_layer_order_empty_input():
    assert detect_layer_order_mismatch(None) == []
    assert detect_layer_order_mismatch([]) == []


# ─────────────────────────────────────────────────────────────────────────────
# 2. Metadata forensics
# ─────────────────────────────────────────────────────────────────────────────
def test_metadata_flags_generic_builder_tool():
    meta = {"creator": "Canva", "producer": "Canva PDF Export", "creationDate": "D:20200101120000"}
    signals = detect_metadata_red_flags(meta)
    types = {s["signal_type"] for s in signals}
    assert "metadata_generic_builder_tool" in types


def test_metadata_flags_rapid_edit_window():
    import datetime
    now = datetime.datetime.now()
    created_dt = now - datetime.timedelta(minutes=10)
    created_str = "D:" + created_dt.strftime("%Y%m%d%H%M%S")
    mod_str = "D:" + now.strftime("%Y%m%d%H%M%S")
    meta = {"creator": "Microsoft Word", "creationDate": created_str, "modDate": mod_str}
    signals = detect_metadata_red_flags(meta)
    types = {s["signal_type"] for s in signals}
    assert "metadata_rapid_edit_window" in types


def test_metadata_flags_stripped_metadata():
    signals = detect_metadata_red_flags({})
    types = {s["signal_type"] for s in signals}
    assert "metadata_stripped" in types


def test_metadata_clean_document_no_signals():
    import datetime
    old_date = "D:20180512090000"
    meta = {"creator": "Microsoft Word", "producer": "Microsoft Word", "creationDate": old_date, "modDate": old_date}
    signals = detect_metadata_red_flags(meta)
    assert signals == []


# ─────────────────────────────────────────────────────────────────────────────
# 3. Image-only page detection
# ─────────────────────────────────────────────────────────────────────────────
def test_image_only_page_flagged():
    image_pages = [
        {"page": 1, "text_char_count": 5, "image_area_ratio": 0.95, "is_suspected_image_only": True},
    ]
    signals = detect_image_only_pages(image_pages)
    assert len(signals) == 1
    assert signals[0]["severity"] == "high"
    assert signals[0]["signal_type"] == "image_only_page"


def test_normal_page_not_flagged():
    image_pages = [
        {"page": 1, "text_char_count": 1200, "image_area_ratio": 0.05, "is_suspected_image_only": False},
    ]
    assert detect_image_only_pages(image_pages) == []


def test_image_only_empty_input():
    assert detect_image_only_pages(None) == []


# ─────────────────────────────────────────────────────────────────────────────
# 4. Trust Score
# ─────────────────────────────────────────────────────────────────────────────
def test_trust_score_clean_resume_is_high():
    result = compute_trust_score(
        fraud_summary={"high": 0, "medium": 0, "low": 0},
        ai_content_score=10.0,
        true_match_score=80.0,
    )
    assert result["score"] > 80
    assert result["label"] == "Verified"


def test_trust_score_high_fraud_is_high_risk():
    result = compute_trust_score(
        fraud_summary={"high": 3, "medium": 1, "low": 0},
        ai_content_score=90.0,
        true_match_score=20.0,
    )
    assert result["label"] == "High Risk"
    assert result["score"] < 45


def test_trust_score_without_jd_renormalises_weights():
    result = compute_trust_score(
        fraud_summary={"high": 0, "medium": 0, "low": 0},
        ai_content_score=0.0,
        true_match_score=None,
    )
    assert result["breakdown"]["match_component"] is None
    assert result["score"] == 100.0


def test_trust_score_bounds():
    result = compute_trust_score(
        fraud_summary={"high": 20, "medium": 20, "low": 20},
        ai_content_score=100.0,
        true_match_score=0.0,
    )
    assert 0.0 <= result["score"] <= 100.0
    assert result["label"] == "High Risk"