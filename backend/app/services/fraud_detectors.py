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
# 0a. PDF LAYER-ORDER FORENSICS  (Feature 1)
# ─────────────────────────────────────────────────────────────────────────────
# Consumes `word_order` produced by pdf_extractor._compute_word_order_signal():
# [{"page", "word_count", "disorder_ratio", "sample_words"}, ...]
#
# disorder_ratio close to 0   → extraction order ≈ visual reading order (normal)
# disorder_ratio high         → underlying content-stream order is scrambled
#                                relative to what a human sees — a hallmark of
#                                deliberately reordered/stuffed PDF content
#                                meant to confuse ATS parsers while looking
#                                normal to a human reviewer.
_LAYER_ORDER_HIGH_THRESHOLD = 0.30
_LAYER_ORDER_MEDIUM_THRESHOLD = 0.15


def detect_layer_order_mismatch(word_order: list[dict] | None) -> list[SignalDict]:
    """
    Flag pages where the PDF's internal text-extraction order diverges
    sharply from top-to-bottom/left-to-right visual reading order.

    Severity:
      HIGH   — disorder_ratio > 0.30 (heavily scrambled)
      MEDIUM — disorder_ratio > 0.15 (partially scrambled)
    """
    signals: list[SignalDict] = []
    if not word_order:
        return signals

    for page_stat in word_order:
        ratio = page_stat.get("disorder_ratio", 0.0)
        if ratio <= _LAYER_ORDER_MEDIUM_THRESHOLD:
            continue

        severity = "high" if ratio > _LAYER_ORDER_HIGH_THRESHOLD else "medium"
        sample = ", ".join(page_stat.get("sample_words", [])[:12])
        desc = (
            f"Underlying PDF text order diverges {ratio:.0%} from visual reading "
            f"order across {page_stat.get('word_count', 0)} words — text may have "
            f"been deliberately reordered in the content stream to confuse ATS "
            f"parsers while still looking normal to a human reader."
        )
        signals.append({
            "signal_type":   "layer_order_mismatch",
            "severity":      severity,
            "page":          page_stat["page"],
            "bbox":          None,
            "description":   desc,
            "evidence_text": _snippet(sample),
        })

    return signals


# ─────────────────────────────────────────────────────────────────────────────
# 0b. METADATA FORENSICS  ("Digital Fingerprint" check — Feature 2)
# ─────────────────────────────────────────────────────────────────────────────
# Consumes the `metadata` dict returned by pdf_extractor._extract_metadata().
_GENERIC_BUILDER_TOOLS: tuple[str, ...] = (
    "canva", "zety", "resume.io", "resumeio", "resume genius", "resumegenius",
    "novoresume", "kickresume", "resumonk", "enhancv", "standard resume",
    "resumemaker", "resume-now", "resumebuild", "cvmaker", "myperfectresume",
    "visualcv", "docs.google.com", "google docs",
)

_PDF_DATE_RE = re.compile(
    r"D:(?P<Y>\d{4})(?P<m>\d{2})(?P<d>\d{2})"
    r"(?P<H>\d{2})?(?P<M>\d{2})?(?P<S>\d{2})?"
)


def _parse_pdf_date(raw: str | None) -> datetime | None:
    """Parse a PDF-format date string like 'D:20240115120000+00'00''."""
    if not raw:
        return None
    m = _PDF_DATE_RE.match(raw)
    if not m:
        return None
    g = m.groupdict(default="0")
    try:
        return datetime(
            int(g["Y"]), int(g["m"]), int(g["d"]),
            int(g["H"] or 0), int(g["M"] or 0), int(g["S"] or 0),
        )
    except ValueError:
        return None


def detect_metadata_red_flags(metadata: dict[str, str] | None) -> list[SignalDict]:
    """
    Cross-check PDF metadata (Creator/Producer software, creation vs.
    modification timestamps) against what a "professionally authored, stable
    resume" would look like.

    Signals raised:
      - metadata_generic_builder_tool (MEDIUM): Producer/Creator matches a
        known free/instant resume-builder template tool.
      - metadata_rapid_edit_window (MEDIUM): ModDate is only minutes/hours
        after CreationDate yet the file was generated very recently —
        consistent with a resume assembled and tweaked in a rush right
        before submission rather than a maintained personal document.
      - metadata_stripped (LOW): No creation/producer info at all, which can
        indicate metadata was deliberately scrubbed to hide the tool of
        origin.
    """
    signals: list[SignalDict] = []
    if metadata is None:
        return signals

    creator  = (metadata.get("creator")  or "").strip()
    producer = (metadata.get("producer") or "").strip()
    combined = f"{creator} {producer}".lower()

    matched_tool = next((t for t in _GENERIC_BUILDER_TOOLS if t in combined), None)
    if matched_tool:
        signals.append({
            "signal_type":   "metadata_generic_builder_tool",
            "severity":      "medium",
            "page":          1,
            "bbox":          None,
            "description":   (
                f"Document metadata identifies the authoring tool as "
                f"{creator or producer!r}, matching known free/instant resume "
                f"builder '{matched_tool}'. Not disqualifying on its own, but "
                f"worth weighing against claimed seniority/experience."
            ),
            "evidence_text": f"Creator={creator!r} Producer={producer!r}",
        })

    created  = _parse_pdf_date(metadata.get("creationDate"))
    modified = _parse_pdf_date(metadata.get("modDate"))

    if created and modified:
        gap = modified - created
        gap_minutes = gap.total_seconds() / 60.0

        # Rushed-together red flag: created & last edited within the same
        # short window — consistent with a resume assembled/tweaked right before submission
        if 0 < gap_minutes < 120:
            signals.append({
                "signal_type":   "metadata_rapid_edit_window",
                "severity":      "medium",
                "page":          1,
                "bbox":          None,
                "description":   (
                    f"File was created and last modified only "
                    f"{gap_minutes:.0f} minute(s) apart — consistent "
                    f"with a resume rapidly assembled/edited right before "
                    f"submission rather than a maintained, long-standing document."
                ),
                "evidence_text": (
                    f"CreationDate={metadata.get('creationDate')!r} "
                    f"ModDate={metadata.get('modDate')!r}"
                ),
            })

        if gap.total_seconds() < 0:
            signals.append({
                "signal_type":   "metadata_mod_before_creation",
                "severity":      "low",
                "page":          1,
                "bbox":          None,
                "description":   (
                    "Document's ModDate is earlier than its CreationDate — "
                    "an internal inconsistency that can indicate manual "
                    "metadata tampering."
                ),
                "evidence_text": (
                    f"CreationDate={metadata.get('creationDate')!r} "
                    f"ModDate={metadata.get('modDate')!r}"
                ),
            })

    if not creator and not producer and not metadata.get("creationDate"):
        signals.append({
            "signal_type":   "metadata_stripped",
            "severity":      "low",
            "page":          1,
            "bbox":          None,
            "description":   (
                "No creator/producer/creation-date metadata present at all. "
                "This can be entirely innocent, but it can also indicate "
                "metadata was deliberately stripped to hide the authoring tool."
            ),
            "evidence_text": None,
        })

    return signals


# ─────────────────────────────────────────────────────────────────────────────
# 0c. IMAGE-ONLY PAGE DETECTION  (OCR-bypass check — Feature 3)
# ─────────────────────────────────────────────────────────────────────────────
# Consumes `image_pages` produced by pdf_extractor._compute_image_page_stats():
# [{"page", "text_char_count", "image_area_ratio", "is_suspected_image_only"}, ...]

def detect_image_only_pages(image_pages: list[dict] | None) -> list[SignalDict]:
    """
    Flag pages that are visually dominated by a large embedded image yet
    contain almost no extractable text — a common trick to defeat
    text-based fraud/keyword scanners entirely, since the "text" a human
    sees is actually a picture.

    Severity: HIGH — this fully defeats naive text extraction.
    """
    signals: list[SignalDict] = []
    if not image_pages:
        return signals

    for page_stat in image_pages:
        if not page_stat.get("is_suspected_image_only"):
            continue

        desc = (
            f"Page {page_stat['page']} is ~"
            f"{page_stat['image_area_ratio']:.0%} covered by embedded "
            f"image(s) but has only {page_stat['text_char_count']} "
            f"extractable text character(s) — this page may be a scanned/"
            f"flattened image standing in for real text, which would let it "
            f"bypass any text-based ATS or fraud scan entirely. Run OCR to "
            f"recover and re-check the actual content."
        )
        signals.append({
            "signal_type":   "image_only_page",
            "severity":      "high",
            "page":          page_stat["page"],
            "bbox":          None,
            "description":   desc,
            "evidence_text": None,
        })

    return signals


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
                    f"Word {word!r} mixes scripts {sorted(non_neutral)} "
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


def _parse_date_fuzzy(raw: str, ref_date: date | None = None) -> date | None:
    """Parse a date string; returns None if unparseable."""
    raw = raw.strip()
    target_today = ref_date or date.today()
    if re.match(r"(?:Present|Current|Now|Ongoing|Today)", raw, re.IGNORECASE):
        return target_today
    # Bare year → Jan 1 of that year
    if re.fullmatch(r"\d{4}", raw):
        return date(int(raw), 1, 1)
    try:
        return du_parser.parse(raw, default=datetime(2000, 1, 1)).date()
    except Exception:  # noqa: BLE001
        return None


def extract_date_ranges(spans: list[dict], ref_date: date | None = None) -> list[dict]:
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
            start = _parse_date_fuzzy(m.group("start"), ref_date)
            end   = _parse_date_fuzzy(m.group("end"), ref_date)
            if start and end:
                ranges.append({
                    "start": start,
                    "end":   end,
                    "raw":   m.group(),
                    "page":  page_num,
                    "bbox":  None,   # page-level, not span-level
                })

    return ranges


def detect_timeline_issues(parsed_ranges: list[dict], ref_date: date | None = None) -> list[SignalDict]:
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
    target_today = ref_date or date.today()

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

        if start > target_today:
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
    valid.sort(key=lambda r: (r["start"], r["end"], r["page"]))
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
    metadata: dict[str, str] | None = None,
    word_order: list[dict] | None = None,
    image_pages: list[dict] | None = None,
    reference_date: date | None = None,
) -> list[SignalDict]:
    """
    Run every detector and return the combined signal list in deterministic order.
    Adding a new detector only requires registering it here.

    `metadata`, `word_order`, and `image_pages` are optional (Phase 5) — pass
    them from pdf_extractor.extract_pdf()'s return dict to enable the
    metadata-forensics, layer-order, and image-only-page detectors.
    """
    signals: list[SignalDict] = []
    signals.extend(detect_zero_width_chars(spans))
    signals.extend(detect_homoglyphs(spans))
    signals.extend(detect_hidden_text(spans, background_color, hidden_text_threshold))
    signals.extend(detect_offpage_or_zero_size(spans, page_dims, hidden_size_threshold))

    date_ranges = extract_date_ranges(spans, ref_date=reference_date)
    signals.extend(detect_timeline_issues(date_ranges, ref_date=reference_date))

    # ── Phase 5 additions ───────────────────────────────────────────────────
    signals.extend(detect_layer_order_mismatch(word_order))
    signals.extend(detect_metadata_red_flags(metadata))
    signals.extend(detect_image_only_pages(image_pages))

    # ── Deterministic sorting ───────────────────────────────────────────────
    # Sort order: page (ascending), severity (high -> medium -> low),
    # signal_type (alphabetical), bbox coordinates, and description.
    _sev_rank = {"high": 0, "medium": 1, "low": 2}
    signals.sort(
        key=lambda s: (
            s.get("page", 1),
            _sev_rank.get(s.get("severity", "low"), 3),
            s.get("signal_type", ""),
            tuple(s.get("bbox") or (0.0, 0.0, 0.0, 0.0)),
            s.get("description", ""),
        )
    )

    return signals



# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _snippet(text: str, max_len: int = 200) -> str:
    """Truncate evidence text for storage."""
    text = text.replace("\n", " ")
    return text[:max_len] + ("…" if len(text) > max_len else "")