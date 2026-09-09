"""
tests/test_fraud_detectors.py — Phase 2 unit tests
====================================================
Each detector is tested independently with crafted span / range fixtures.
No database, no API, no PDF parsing — pure function tests.
Run: pytest tests/test_fraud_detectors.py -v
"""
from __future__ import annotations

from datetime import date

import pytest

from app.services.fraud_detectors import (
    _rgb_distance,
    _unicode_script,
    detect_hidden_text,
    detect_homoglyphs,
    detect_offpage_or_zero_size,
    detect_timeline_issues,
    detect_zero_width_chars,
    extract_date_ranges,
    run_all_detectors,
)


# ─────────────────────────────────────────────────────────────────────────────
# Span factory
# ─────────────────────────────────────────────────────────────────────────────
def make_span(
    text: str = "Normal text",
    page: int = 1,
    font_size: float = 12.0,
    font_color: tuple = (0, 0, 0),
    bbox: tuple = (10.0, 10.0, 200.0, 22.0),
) -> dict:
    return {
        "text":       text,
        "font_name":  "Helvetica",
        "font_size":  font_size,
        "font_color": font_color,
        "bold":       False,
        "italic":     False,
        "bbox":       bbox,
        "page":       page,
        "origin":     "pymupdf",
    }


def make_page_dim(page: int = 1, width: float = 595.0, height: float = 842.0) -> dict:
    return {"page": page, "width": width, "height": height}


# ═════════════════════════════════════════════════════════════════════════════
# 1 · ZERO-WIDTH CHAR DETECTOR
# ═════════════════════════════════════════════════════════════════════════════
class TestDetectZeroWidthChars:
    def test_clean_span_returns_empty(self):
        signals = detect_zero_width_chars([make_span("Hello World")])
        assert signals == []

    def test_zero_width_space_detected(self):
        span = make_span("Python\u200BDeveloper")   # invisible space
        signals = detect_zero_width_chars([span])
        assert len(signals) == 1
        assert signals[0]["signal_type"] == "zero_width_chars"
        assert signals[0]["severity"] == "high"
        assert signals[0]["page"] == 1

    def test_soft_hyphen_detected(self):
        span = make_span("Micro\u00ADsoft")   # U+00AD soft hyphen
        signals = detect_zero_width_chars([span])
        assert len(signals) == 1

    def test_bom_detected(self):
        span = make_span("\uFEFFMachine Learning")
        signals = detect_zero_width_chars([span])
        assert len(signals) == 1

    def test_multiple_invisible_chars_one_signal_per_span(self):
        # Multiple ZW chars in ONE span → exactly 1 signal (mentions all of them)
        span = make_span("AI\u200B\u200CML\u2060Engineer")
        signals = detect_zero_width_chars([span])
        assert len(signals) == 1
        assert "ZERO WIDTH SPACE" in signals[0]["description"]

    def test_multiple_spans_each_flagged(self):
        spans = [
            make_span("Java\u200BScript", page=1),
            make_span("Clean text",       page=1),
            make_span("React\u200D",      page=2),
        ]
        signals = detect_zero_width_chars(spans)
        assert len(signals) == 2
        pages = {s["page"] for s in signals}
        assert pages == {1, 2}

    def test_bbox_preserved(self):
        bbox = (50.0, 100.0, 250.0, 115.0)
        span = make_span("AWS\u200B", bbox=bbox)
        signals = detect_zero_width_chars([span])
        assert signals[0]["bbox"] == bbox

    def test_evidence_text_truncated_at_200_chars(self):
        long_text = "A" * 150 + "\u200B" + "B" * 100
        span = make_span(long_text)
        signals = detect_zero_width_chars([span])
        assert len(signals[0]["evidence_text"]) <= 201   # 200 + ellipsis char


# ═════════════════════════════════════════════════════════════════════════════
# 2 · HOMOGLYPH DETECTOR
# ═════════════════════════════════════════════════════════════════════════════
class TestDetectHomoglyphs:
    def test_clean_latin_returns_empty(self):
        signals = detect_homoglyphs([make_span("Software Engineer")])
        assert signals == []

    def test_pure_cyrillic_returns_empty(self):
        # Pure Cyrillic (no Latin mix) should not be flagged
        signals = detect_homoglyphs([make_span("Разработчик")])
        assert signals == []

    def test_cyrillic_а_in_latin_word_detected(self):
        # Cyrillic "а" (U+0430) looks identical to Latin "a" (U+0061)
        mixed_word = "Jаva"   # the "а" is Cyrillic U+0430
        span = make_span(mixed_word)
        signals = detect_homoglyphs([span])
        assert len(signals) == 1
        assert signals[0]["signal_type"] == "homoglyph_substitution"
        assert signals[0]["severity"] == "high"
        assert "Cyrillic" in signals[0]["description"]

    def test_cyrillic_е_in_latin_word_detected(self):
        # Cyrillic "е" (U+0435) vs Latin "e" (U+0065)
        mixed_word = "Pythоn"   # "о" is Cyrillic U+043E
        span = make_span(mixed_word)
        signals = detect_homoglyphs([span])
        assert len(signals) == 1

    def test_page_number_preserved(self):
        mixed = "Jаva"
        span = make_span(mixed, page=3)
        signals = detect_homoglyphs([span])
        assert signals[0]["page"] == 3

    def test_single_signal_per_span(self):
        # Even if multiple words in a span are mixed, we emit one signal per span
        mixed = "Jаva Pythоn Rеact"
        signals = detect_homoglyphs([make_span(mixed)])
        assert len(signals) == 1

    def test_multiple_spans_flagged_independently(self):
        spans = [
            make_span("Jаva", page=1),       # Cyrillic а
            make_span("clean text", page=1),
            make_span("Pythоn", page=2),      # Cyrillic о
        ]
        signals = detect_homoglyphs(spans)
        assert len(signals) == 2


# ═════════════════════════════════════════════════════════════════════════════
# 3 · HIDDEN TEXT DETECTOR
# ═════════════════════════════════════════════════════════════════════════════
class TestDetectHiddenText:
    def test_black_text_on_white_clean(self):
        span = make_span("Visible", font_color=(0, 0, 0))
        signals = detect_hidden_text([span])
        assert signals == []

    def test_exact_white_on_white_high_severity(self):
        span = make_span("Hidden keywords", font_color=(255, 255, 255))
        signals = detect_hidden_text([span], background_color=(255, 255, 255))
        assert len(signals) == 1
        assert signals[0]["severity"] == "high"
        assert signals[0]["signal_type"] == "hidden_text"

    def test_near_white_within_threshold_medium(self):
        # RGB(240, 240, 240) — distance = sqrt(3*(15^2)) ≈ 26 < 30 → medium
        span = make_span("Ghost text", font_color=(240, 240, 240))
        signals = detect_hidden_text([span], threshold=30)
        assert len(signals) == 1
        assert signals[0]["severity"] == "medium"

    def test_near_white_within_10_is_high(self):
        span = make_span("Ghost", font_color=(250, 252, 255))   # dist ≈ 5.7
        signals = detect_hidden_text([span], threshold=30)
        assert len(signals) == 1
        assert signals[0]["severity"] == "high"

    def test_colour_just_outside_threshold_clean(self):
        # RGB(200, 200, 200) — dist ≈ 95 >> 30 → not flagged
        span = make_span("Grey text", font_color=(200, 200, 200))
        signals = detect_hidden_text([span], threshold=30)
        assert signals == []

    def test_custom_background_color(self):
        # Dark background (0,0,0): black text should be flagged
        span = make_span("Hidden on dark", font_color=(5, 5, 5))
        signals = detect_hidden_text([span], background_color=(0, 0, 0), threshold=30)
        assert len(signals) == 1

    def test_empty_text_not_flagged(self):
        span = make_span("   ", font_color=(255, 255, 255))
        signals = detect_hidden_text([span])
        assert signals == []

    def test_rgb_distance_helper(self):
        assert _rgb_distance((0, 0, 0), (0, 0, 0)) == 0.0
        assert abs(_rgb_distance((255, 255, 255), (0, 0, 0)) - 441.67) < 0.1
        assert abs(_rgb_distance((255, 0, 0), (0, 0, 0)) - 255.0) < 0.1


# ═════════════════════════════════════════════════════════════════════════════
# 4 · OFF-PAGE / ZERO-FONT-SIZE DETECTOR
# ═════════════════════════════════════════════════════════════════════════════
class TestDetectOffpageOrZeroSize:
    def test_normal_span_clean(self):
        span = make_span(bbox=(10.0, 10.0, 200.0, 22.0))
        dims = [make_page_dim()]
        assert detect_offpage_or_zero_size([span], dims) == []

    def test_zero_font_size_high(self):
        span = make_span(font_size=0.0)
        signals = detect_offpage_or_zero_size([span], [make_page_dim()])
        assert len(signals) == 1
        assert signals[0]["severity"] == "high"
        assert signals[0]["signal_type"] == "zero_or_tiny_font"

    def test_tiny_font_just_above_zero_medium(self):
        span = make_span(font_size=0.5)
        signals = detect_offpage_or_zero_size([span], [make_page_dim()], hidden_size_threshold=1.0)
        assert len(signals) == 1
        assert signals[0]["severity"] == "medium"

    def test_font_exactly_at_threshold_flagged(self):
        span = make_span(font_size=1.0)
        signals = detect_offpage_or_zero_size([span], [make_page_dim()], hidden_size_threshold=1.0)
        assert len(signals) == 1

    def test_font_just_above_threshold_clean(self):
        span = make_span(font_size=1.1)
        signals = detect_offpage_or_zero_size([span], [make_page_dim()], hidden_size_threshold=1.0)
        assert signals == []

    def test_off_right_edge(self):
        # Page is 595 wide; bbox starts at 600 → off right
        span = make_span(bbox=(600.0, 100.0, 700.0, 115.0))
        signals = detect_offpage_or_zero_size([span], [make_page_dim()])
        assert len(signals) == 1
        assert signals[0]["signal_type"] == "offpage_text"
        assert signals[0]["severity"] == "high"

    def test_off_bottom_edge(self):
        # Page is 842 tall; bbox starts at 900
        span = make_span(bbox=(10.0, 900.0, 200.0, 920.0))
        signals = detect_offpage_or_zero_size([span], [make_page_dim()])
        assert len(signals) == 1
        assert "bottom" in signals[0]["description"]

    def test_off_left_edge(self):
        span = make_span(bbox=(-50.0, 100.0, -10.0, 115.0))
        signals = detect_offpage_or_zero_size([span], [make_page_dim()])
        assert len(signals) == 1
        assert "left" in signals[0]["description"]

    def test_negative_y_off_top(self):
        span = make_span(bbox=(10.0, -30.0, 200.0, -10.0))
        signals = detect_offpage_or_zero_size([span], [make_page_dim()])
        assert len(signals) == 1
        assert "top" in signals[0]["description"]

    def test_missing_page_dims_no_crash(self):
        span = make_span(page=99, bbox=(600.0, 100.0, 700.0, 115.0))
        signals = detect_offpage_or_zero_size([span], [make_page_dim(page=1)])
        assert signals == []   # unknown page → skip safely

    def test_empty_text_not_flagged(self):
        span = make_span(text="  ", font_size=0.0)
        signals = detect_offpage_or_zero_size([span], [make_page_dim()])
        assert signals == []


# ═════════════════════════════════════════════════════════════════════════════
# 5 · TIMELINE INCONSISTENCY DETECTOR
# ═════════════════════════════════════════════════════════════════════════════
class TestDetectTimelineIssues:
    # ── extract_date_ranges ───────────────────────────────────────────────────
    def test_extract_month_year_range(self):
        spans = [make_span("Jan 2020 – Mar 2022 Software Engineer")]
        ranges = extract_date_ranges(spans)
        assert len(ranges) == 1
        assert ranges[0]["start"] == date(2020, 1, 1)
        assert ranges[0]["end"]   == date(2022, 3, 1)

    def test_extract_bare_year_range(self):
        spans = [make_span("2018 – 2020 Project Lead")]
        ranges = extract_date_ranges(spans)
        assert len(ranges) == 1
        assert ranges[0]["start"].year == 2018
        assert ranges[0]["end"].year   == 2020

    def test_extract_present(self):
        spans = [make_span("June 2022 – Present")]
        ranges = extract_date_ranges(spans)
        assert len(ranges) == 1
        assert ranges[0]["end"] >= date.today()

    def test_extract_multiple_ranges(self):
        text = "Jan 2018 – Dec 2019 Company A\nFeb 2020 – Present Company B"
        spans = [make_span(text)]
        ranges = extract_date_ranges(spans)
        assert len(ranges) == 2

    def test_no_dates_returns_empty(self):
        spans = [make_span("Skills: Python, SQL, Docker")]
        ranges = extract_date_ranges(spans)
        assert ranges == []

    # ── detect_timeline_issues ────────────────────────────────────────────────
    def test_clean_sequential_jobs_no_signals(self):
        ranges = [
            {"start": date(2018, 1, 1), "end": date(2019, 12, 1), "raw": "2018-2019", "page": 1, "bbox": None},
            {"start": date(2020, 1, 1), "end": date(2022, 6, 1),  "raw": "2020-2022", "page": 1, "bbox": None},
        ]
        assert detect_timeline_issues(ranges) == []

    def test_end_before_start_high_severity(self):
        ranges = [{
            "start": date(2022, 6, 1),
            "end":   date(2020, 1, 1),   # end before start!
            "raw":   "Jun 2022 – Jan 2020",
            "page":  1, "bbox": None,
        }]
        signals = detect_timeline_issues(ranges)
        assert any(s["signal_type"] == "timeline_end_before_start" for s in signals)
        assert all(s["severity"] == "high" for s in signals
                   if s["signal_type"] == "timeline_end_before_start")

    def test_future_start_date_flagged(self):
        from datetime import timedelta
        future = date.today() + timedelta(days=365)
        ranges = [{
            "start": future,
            "end":   date.today(),
            "raw":   "Future Job",
            "page":  1, "bbox": None,
        }]
        signals = detect_timeline_issues(ranges)
        assert any(s["signal_type"] == "timeline_future_start" for s in signals)

    def test_significant_overlap_medium_severity(self):
        ranges = [
            {"start": date(2019, 1, 1), "end": date(2021, 6, 1), "raw": "2019-mid2021", "page": 1, "bbox": None},
            {"start": date(2020, 1, 1), "end": date(2022, 1, 1), "raw": "2020-2022",    "page": 1, "bbox": None},
        ]
        signals = detect_timeline_issues(ranges)
        overlap_signals = [s for s in signals if s["signal_type"] == "timeline_overlap"]
        assert len(overlap_signals) >= 1
        assert overlap_signals[0]["severity"] == "medium"
        assert "17 month" in overlap_signals[0]["description"] or "month" in overlap_signals[0]["description"]

    def test_one_month_overlap_grace_no_signal(self):
        # Exactly 1 month overlap → within grace period, not flagged
        ranges = [
            {"start": date(2019, 1, 1), "end": date(2020, 2, 1), "raw": "A", "page": 1, "bbox": None},
            {"start": date(2020, 2, 1), "end": date(2021, 1, 1), "raw": "B", "page": 1, "bbox": None},
        ]
        overlap_signals = [
            s for s in detect_timeline_issues(ranges)
            if s["signal_type"] == "timeline_overlap"
        ]
        # 0-month overlap (boundaries touching) — should not flag
        assert len(overlap_signals) == 0

    def test_empty_ranges_no_crash(self):
        assert detect_timeline_issues([]) == []


# ═════════════════════════════════════════════════════════════════════════════
# 6 · Helpers
# ═════════════════════════════════════════════════════════════════════════════
class TestHelpers:
    def test_unicode_script_latin(self):
        assert _unicode_script("A") == "Latin"
        assert _unicode_script("z") == "Latin"

    def test_unicode_script_cyrillic(self):
        assert _unicode_script("а") == "Cyrillic"   # U+0430

    def test_unicode_script_greek(self):
        assert _unicode_script("α") == "Greek"       # U+03B1

    def test_unicode_script_digit_neutral(self):
        assert _unicode_script("5") == "Neutral"

    def test_unicode_script_space_neutral(self):
        assert _unicode_script(" ") == "Neutral"


# ═════════════════════════════════════════════════════════════════════════════
# 7 · run_all_detectors integration
# ═════════════════════════════════════════════════════════════════════════════
class TestRunAllDetectors:
    def test_clean_spans_return_empty(self):
        spans = [make_span("Software Engineer with 5 years experience")]
        dims  = [make_page_dim()]
        assert run_all_detectors(spans, dims) == []

    def test_all_signal_types_aggregated(self):
        spans = [
            # zero-width
            make_span("AWS\u200BCertified", page=1),
            # hidden text
            make_span("hidden keywords here", page=1, font_color=(255, 255, 255)),
            # tiny font
            make_span("ghost text", page=1, font_size=0.3),
            # date range (timeline check)
            make_span("Jan 2022 – Present", page=2),
        ]
        dims = [make_page_dim(1), make_page_dim(2)]
        signals = run_all_detectors(spans, dims)
        types = {s["signal_type"] for s in signals}
        assert "zero_width_chars"  in types
        assert "hidden_text"       in types
        assert "zero_or_tiny_font" in types

    def test_signals_all_have_required_keys(self):
        spans = [make_span("Java\u200BScript", font_color=(254, 255, 255))]
        dims  = [make_page_dim()]
        for sig in run_all_detectors(spans, dims):
            assert "signal_type"  in sig
            assert "severity"     in sig
            assert "page"         in sig
            assert "description"  in sig
            assert sig["severity"] in ("high", "medium", "low")
