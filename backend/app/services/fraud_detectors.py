"""
fraud_detectors.py — Phase 2
=============================
Five independent, pure fraud-detection functions.
Each returns a list of SignalDict — no database, no I/O, fully unit-testable.

SignalDict schema
-----------------
{
    "signal_type":    str,    # snake_case identifier
    "severity":       str,    # "high" | "medium" | "low"
    "page":           int,    # 1-indexed
    "bbox":           tuple[float, float, float, float] | None,
    "description":    str,    # human-readable explanation
    "evidence_text":  str | None,   # up to 200 chars of offending text
}
"""
from __future__ import annotations

import math
import re
import unicodedata
from datetime import date, datetime
from typing import Any

from dateutil import parser as du_parser
from dateutil.relativedelta import relativedelta

# ── Type alias ────────────────────────────────────────────────────────────────
SignalDict = dict[str, Any]

# ─────────────────────────────────────────────────────────────────────────────
# 1. ZERO-WIDTH CHARACTER DETECTOR
# ─────────────────────────────────────────────────────────────────────────────
# These characters are invisible but picked up by ATS keyword parsers.
_ZERO_WIDTH_CHARS: dict[str, str] = {
    "\u200B": "ZERO WIDTH SPACE",
    "\u200C": "ZERO WIDTH NON-JOINER",
    "\u200D": "ZERO WIDTH JOINER",
    "\u200E": "LEFT-TO-RIGHT MARK",
    "\u200F": "RIGHT-TO-LEFT MARK",
    "\u2060": "WORD JOINER",
    "\u2061": "FUNCTION APPLICATION",
    "\u2062": "INVISIBLE TIMES",
    "\u2063": "INVISIBLE SEPARATOR",
    "\u2064": "INVISIBLE PLUS",
    "\uFEFF": "ZERO WIDTH NO-BREAK SPACE (BOM)",
    "\u00AD": "SOFT HYPHEN",
    "\u180E": "MONGOLIAN VOWEL SEPARATOR",
    "\u034F": "COMBINING GRAPHEME JOINER",
}
_ZW_PATTERN = re.compile(
    "[" + "".join(re.escape(c) for c in _ZERO_WIDTH_CHARS) + "]"
)


def detect_zero_width_chars(spans: list[dict]) -> list[SignalDict]:
    """
    Scan every text span for invisible Unicode characters used to stuff
    hidden keywords into the document.

    Severity: HIGH — deliberate manipulation, invisible to human reviewers.
    """
    signals: list[SignalDict] = []

    for span in spans:
        text = span.get("text", "")
        matches = list(_ZW_PATTERN.finditer(text))
        if not matches:
            continue

        char_names = sorted(
            {_ZERO_WIDTH_CHARS.get(m.group(), unicodedata.name(m.group(), "UNKNOWN"))
             for m in matches}
        )
        description = (
            f"Found {len(matches)} invisible character(s) in span: "
            + ", ".join(char_names)
        )

        signals.append({
            "signal_type":   "zero_width_chars",
            "severity":      "high",
            "page":          span["page"],
            "bbox":          span.get("bbox"),
            "description":   description,
            "evidence_text": _snippet(text),
        })

    return signals


# ─────────────────────────────────────────────────────────────────────────────
# 2. HOMOGLYPH DETECTOR
# ─────────────────────────────────────────────────────────────────────────────
# Attackers swap visually identical characters from different scripts, e.g.
# Cyrillic "а" (U+0430) instead of Latin "a" (U+0061).
# Strategy: tokenise each span into words; flag any word that mixes scripts
# where at least one script is Latin *and* at least one is Cyrillic or Greek.

def _unicode_script(char: str) -> str:
    """
    Coarse script classification by codepoint range.
    Returns a string label such as 'Latin', 'Cyrillic', 'Greek', etc.
    """
    cp = ord(char)
    if (0x0041 <= cp <= 0x005A or   # A-Z
            0x0061 <= cp <= 0x007A or   # a-z
            0x00C0 <= cp <= 0x00D6 or   # Latin Extended
            0x00D8 <= cp <= 0x00F6 or
            0x00F8 <= cp <= 0x024F or
            0x1E00 <= cp <= 0x1EFF):    # Latin Extended Additional
        return "Latin"
    if 0x0400 <= cp <= 0x04FF:
        return "Cyrillic"
    if 0x0370 <= cp <= 0x03FF or 0x1F00 <= cp <= 0x1FFF:
        return "Greek"
    if 0x0590 <= cp <= 0x05FF:
        return "Hebrew"
    if 0x0600 <= cp <= 0x06FF:
        return "Arabic"
    # Digits, punctuation, combining marks → neutral
    cat = unicodedata.category(char)
    if cat.startswith(("N", "P", "Z", "M", "C")):
        return "Neutral"
    return "Other"


# Known visually-deceptive Cyrillic/Greek characters and their Latin lookalikes
_SUSPICIOUS_LOOKALIKES: frozenset[str] = frozenset(
    # Cyrillic homoglyphs
    "аеорсухАВСЕНІКМОРТХ"
    # Greek homoglyphs
    "αβγδεζηθικλμνξοπρστυφχψω"
    "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ"
)

_WORD_RE = re.compile(r"\b[\w]+\b", re.UNICODE)


def detect_homoglyphs(spans: list[dict]) -> list[SignalDict]:
    """
    Flag words that mix Latin characters with visually-identical Cyrillic or
    Greek codepoints — a common technique to evade keyword blacklists while
    still appearing correct to human readers.

    Severity: HIGH — intentional character substitution.
    """
    signals: list[SignalDict] = []

    for span in spans:
        text = span.get("text", "")
        for word_match in _WORD_RE.finditer(text):
            word = word_match.group()
            if len(word) < 2:
                continue

            scripts: set[str] = set()
            suspect_chars: list[str] = []

            for ch in word:
                s = _unicode_script(ch)
                if s != "Neutral":
                    scripts.add(s)
                if ch in _SUSPICIOUS_LOOKALIKES:
                    suspect_chars.append(f"{ch!r}(U+{ord(ch):04X})")

            # Only flag if multiple non-neutral scripts AND suspicious chars present
            non_neutral = scripts - {"Neutral", "Other"}
            if len(non_neutral) >= 2 and suspect_chars:
                desc = (
                    f"Word {word!r} mixes scripts {non_neutral} "
                    f"with suspected homoglyphs: {', '.join(suspect_chars)}"
                )
                signals.append({
                    "signal_type":   "homoglyph_substitution",
                    "severity":      "high",
                    "page":          span["page"],
                    "bbox":          span.get("bbox"),
                    "description":   desc,
                    "evidence_text": _snippet(text),
                })
                break   # one signal per span is enough

    return signals


# ─────────────────────────────────────────────────────────────────────────────
# 3. HIDDEN-TEXT DETECTOR (near-white text on white background)
# ─────────────────────────────────────────────────────────────────────────────
# Uses Euclidean distance in RGB space rather than exact #FFFFFF match.
# Default background assumed white; configurable.

def _rgb_distance(c1: tuple[int, int, int], c2: tuple[int, int, int]) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(c1, c2)))


def detect_hidden_text(
    spans: list[dict],
    background_color: tuple[int, int, int] = (255, 255, 255),
    threshold: int = 30,
) -> list[SignalDict]:
    """
    Flag text whose colour is indistinguishable from the background
    using Euclidean distance in RGB space.

    threshold=30 means the colour vector is within a sphere of radius 30
    around the background in the 0-255 cube.
    Max possible distance ≈ 441.7 (black on white).

    Severity:
      HIGH   — distance < 10   (essentially invisible)
      MEDIUM — distance 10-30  (visible only on coloured backgrounds)
    """
    signals: list[SignalDict] = []

    for span in spans:
        color = span.get("font_color")
        if color is None:
            continue
        text = span.get("text", "").strip()
        if not text:
            continue

        dist = _rgb_distance(tuple(color), background_color)
        if dist < threshold:
            severity = "high" if dist < 10 else "medium"
            desc = (
                f"Text colour RGB{tuple(color)} is {dist:.1f} units from "
                f"background RGB{background_color} (threshold {threshold}). "
                "Text is effectively invisible."
            )
            signals.append({
                "signal_type":   "hidden_text",
                "severity":      severity,
                "page":          span["page"],
                "bbox":          span.get("bbox"),
                "description":   desc,
                "evidence_text": _snippet(text),
            })

    return signals


# ─────────────────────────────────────────────────────────────────────────────
# 4. OFF-PAGE / ZERO-FONT-SIZE DETECTOR
# ─────────────────────────────────────────────────────────────────────────────

def detect_offpage_or_zero_size(
    spans: list[dict],
    page_dims: list[dict],
    hidden_size_threshold: float = 1.0,
) -> list[SignalDict]:
    """
    Flag spans that are:
      a) Rendered with font-size ≤ hidden_size_threshold (pt) — invisible to
         the human reader but parsed by ATS.
      b) Positioned outside the visible page area (negative coords or beyond
         the page width/height) — content hidden off-canvas.

    Severity:
      HIGH   — font-size 0 or outside page bounds
      MEDIUM — font-size > 0 but ≤ threshold
    """
    # Build a page_num → dimensions lookup
    dim_map: dict[int, dict] = {d["page"]: d for d in page_dims}
    signals: list[SignalDict] = []

    for span in spans:
        text = span.get("text", "").strip()
        if not text:
            continue

        page = span["page"]
        font_size: float = span.get("font_size", 12.0)
        bbox = span.get("bbox")

        # ── a. Zero / tiny font ───────────────────────────────────────────
        if font_size <= hidden_size_threshold:
            severity = "high" if font_size <= 0 else "medium"
            desc = (
                f"Font size {font_size}pt is at or below the hidden-text "
                f"threshold ({hidden_size_threshold}pt)."
            )
            signals.append({
                "signal_type":   "zero_or_tiny_font",
                "severity":      severity,
                "page":          page,
                "bbox":          bbox,
                "description":   desc,
                "evidence_text": _snippet(text),
            })
            continue  # no need to also check position for same span

        # ── b. Off-page position ──────────────────────────────────────────
        if bbox is None:
            continue

        dims = dim_map.get(page)
        if dims is None:
            continue

        x0, y0, x1, y1 = bbox
        page_w: float = dims["width"]
        page_h: float = dims["height"]

        off_left   = x1 < 0
        off_right  = x0 > page_w
        off_top    = y1 < 0
        off_bottom = y0 > page_h

        if off_left or off_right or off_top or off_bottom:
            direction = ", ".join(filter(None, [
                "left"   if off_left   else "",
                "right"  if off_right  else "",
                "top"    if off_top    else "",
                "bottom" if off_bottom else "",
            ]))
            desc = (
                f"Span bbox {[round(v,1) for v in bbox]} is entirely off "
                f"the {page_w}×{page_h}pt page (off: {direction})."
            )
            signals.append({
                "signal_type":   "offpage_text",
                "severity":      "high",
                "page":          page,
                "bbox":          bbox,
                "description":   desc,
                "evidence_text": _snippet(text),
            })

    return signals


# ─────────────────────────────────────────────────────────────────────────────
# 5. TIMELINE INCONSISTENCY DETECTOR
# ─────────────────────────────────────────────────────────────────────────────

# Regex for common resume date-range patterns, e.g.:
#   "Jan 2020 – Mar 2022"   "2019–Present"   "June 2018 to Current"
_DATE_RANGE_RE = re.compile(
    r"""
    (?P<start>
        (?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|
           Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|
           Dec(?:ember)?)
        \s*\.?\s*\d{4}
        |
        \d{4}                     # bare year
    )
    \s*
    (?:–|—|−|-{1,2}|to|through|until)   # separator
    \s*
    (?P<end>
        (?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|
           Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|
           Dec(?:ember)?)
        \s*\.?\s*\d{4}
        |
        \d{4}
        |
        (?:Present|Current|Now|Ongoing|Today)
    )
    """,
    re.VERBOSE | re.IGNORECASE,
)

_TODAY = date.today()


def _parse_date_fuzzy(raw: str) -> date | None:
    """Parse a date string; returns None if unparseable."""
    raw = raw.strip()
    if re.match(r"(?:Present|Current|Now|Ongoing|Today)", raw, re.IGNORECASE):
        return _TODAY
    # Bare year → Jan 1 of that year
    if re.fullmatch(r"\d{4}", raw):
        return date(int(raw), 1, 1)
    try:
        return du_parser.parse(raw, default=datetime(2000, 1, 1)).date()
    except Exception:  # noqa: BLE001
        return None


def extract_date_ranges(spans: list[dict]) -> list[dict]:
    """
    Scan all text spans for date-range patterns and return a list of:
    {
        "start": date,
        "end":   date,
        "raw":   str,       # original matched text
        "page":  int,
        "bbox":  tuple | None,
    }
    """
    ranges: list[dict] = []
    full_text_per_page: dict[int, tuple[str, int | None]] = {}

    # Concatenate spans per page so cross-span date ranges are caught
    page_texts: dict[int, list[str]] = {}
    for span in spans:
        page_texts.setdefault(span["page"], []).append(span.get("text", ""))

    for page_num, parts in page_texts.items():
        text = " ".join(parts)
        for m in _DATE_RANGE_RE.finditer(text):
            start = _parse_date_fuzzy(m.group("start"))
            end   = _parse_date_fuzzy(m.group("end"))
            if start and end:
                ranges.append({
                    "start": start,
                    "end":   end,
                    "raw":   m.group(),
                    "page":  page_num,
                    "bbox":  None,   # page-level, not span-level
                })

    return ranges


def detect_timeline_issues(parsed_ranges: list[dict]) -> list[SignalDict]:
    """
    Given a list of date ranges (from `extract_date_ranges`), detect:

    a) END before START — impossible date order.
    b) Future START date — job started after today.
    c) Overlapping concurrent jobs — two ranges that overlap by more than
       a configurable grace period (1 month by default).

    Severity:
      HIGH   — end < start, future start
      MEDIUM — overlapping jobs (could be consulting/part-time)
    """
    signals: list[SignalDict] = []

    # ── a. Individual range sanity checks ────────────────────────────────────
    for r in parsed_ranges:
        start: date = r["start"]
        end:   date = r["end"]
        raw:   str  = r["raw"]
        page:  int  = r["page"]

        if end < start:
            signals.append({
                "signal_type":   "timeline_end_before_start",
                "severity":      "high",
                "page":          page,
                "bbox":          r.get("bbox"),
                "description":   (
                    f"Employment end date ({end}) precedes start date ({start}). "
                    f"Original text: {raw!r}"
                ),
                "evidence_text": raw,
            })

        if start > _TODAY:
            signals.append({
                "signal_type":   "timeline_future_start",
                "severity":      "high",
                "page":          page,
                "bbox":          r.get("bbox"),
                "description":   (
                    f"Employment start date ({start}) is in the future. "
                    f"Original text: {raw!r}"
                ),
                "evidence_text": raw,
            })

    # ── b. Overlap detection (O(n²) — n is typically < 20 for a resume) ────
    valid = [r for r in parsed_ranges if r["end"] >= r["start"]]
    valid.sort(key=lambda r: r["start"])
    grace = relativedelta(months=1)   # allow 1-month overlap (job transitions)

    for i in range(len(valid)):
        for j in range(i + 1, len(valid)):
            a, b = valid[i], valid[j]
            # b starts before a ends (with grace)
            overlap_start = b["start"]
            overlap_end   = a["end"]
            if overlap_start < overlap_end:
                # Calculate overlap duration
                overlap_months = (
                    (overlap_end.year - overlap_start.year) * 12
                    + (overlap_end.month - overlap_start.month)
                )
                if overlap_months > 1:   # more than grace month
                    desc = (
                        f"Overlapping employment periods: "
                        f"{a['raw']!r} (ends {a['end']}) and "
                        f"{b['raw']!r} (starts {b['start']}). "
                        f"Overlap ≈ {overlap_months} month(s)."
                    )
                    signals.append({
                        "signal_type":   "timeline_overlap",
                        "severity":      "medium",
                        "page":          max(a["page"], b["page"]),
                        "bbox":          None,
                        "description":   desc,
                        "evidence_text": f"{a['raw']} / {b['raw']}",
                    })

    return signals


# ─────────────────────────────────────────────────────────────────────────────
# Aggregator
# ─────────────────────────────────────────────────────────────────────────────

def run_all_detectors(
    spans: list[dict],
    page_dims: list[dict],
    background_color: tuple[int, int, int] = (255, 255, 255),
    hidden_text_threshold: int = 30,
    hidden_size_threshold: float = 1.0,
) -> list[SignalDict]:
    """
    Run every detector and return the combined signal list.
    Adding a new detector in Phase 3+ only requires registering it here.
    """
    signals: list[SignalDict] = []
    signals.extend(detect_zero_width_chars(spans))
    signals.extend(detect_homoglyphs(spans))
    signals.extend(detect_hidden_text(spans, background_color, hidden_text_threshold))
    signals.extend(detect_offpage_or_zero_size(spans, page_dims, hidden_size_threshold))

    date_ranges = extract_date_ranges(spans)
    signals.extend(detect_timeline_issues(date_ranges))

    return signals


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _snippet(text: str, max_len: int = 200) -> str:
    """Truncate evidence text for storage."""
    text = text.replace("\n", " ")
    return text[:max_len] + ("…" if len(text) > max_len else "")
