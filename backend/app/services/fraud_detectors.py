"""
fraud_detectors.py — Phase 2 + Explainable Risk Engine
=======================================================
Seven independent, pure fraud-detection functions.
Each returns a list of SignalDict — no database, no I/O, fully unit-testable.

SignalDict schema (extended)
----------------------------
{
    "signal_type":       str,    # snake_case identifier
    "severity":          str,    # "high" | "medium" | "low"
    "page":              int,    # 1-indexed
    "bbox":              tuple[float, float, float, float] | None,
    "description":       str,    # human-readable explanation
    "evidence_text":     str | None,   # up to 200 chars of offending text
    # ── New explainability fields ────────────────────────────────────────────
    "risk_points":       int,    # points contributed toward category max
    "evidence_strength": str,    # DEFINITIVE | STRONG | MODERATE | WEAK | PROBABILISTIC
    "confidence":        str,    # "high" | "medium" | "low"
    "remediation":       str,    # advice shown in UI
    # ── Optional structured evidence (present where applicable) ─────────────
    "evidence":          dict | None,   # raw triggering values from PDF
}

Evidence Strength taxonomy
--------------------------
DEFINITIVE   — The character / object is unambiguously present in the PDF
               (e.g. an actual zero-width codepoint was extracted).
STRONG       — The technical measurement strongly indicates manipulation
               (e.g. text colour RGB distance < 10 from background).
MODERATE     — The measurement is unusual but has innocent explanations
               (e.g. layer-order scrambling, slightly small font).
WEAK         — The signal is informational only and rarely indicates fraud
               (e.g. metadata from a known free resume-builder tool).
PROBABILISTIC— The signal is inherently statistical and model-dependent
               (used exclusively for AI-content detection outputs).
"""
from __future__ import annotations

import math
import re
import unicodedata
from datetime import date, datetime
from typing import Any

from dateutil import parser as du_parser
from dateutil.relativedelta import relativedelta

from app.services.risk_config import RISK_WEIGHTS, SIGNAL_CATEGORY_MAP, compute_risk_score  # noqa: F401 (re-exported)

# ── Type alias ────────────────────────────────────────────────────────────────
SignalDict = dict[str, Any]


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _snippet(text: str, max_len: int = 200) -> str:
    """Truncate evidence text for storage."""
    text = text.replace("\n", " ")
    return text[:max_len] + ("…" if len(text) > max_len else "")


def _scale_risk(category: str, severity: str) -> int:
    """
    Return risk points for a single signal occurrence, prorated by severity.
    HIGH → 100% of category max
    MEDIUM → 50% of category max
    LOW → 25% of category max
    """
    max_pts = RISK_WEIGHTS.get(category, 0)
    factor = {"high": 1.0, "medium": 0.5, "low": 0.25}.get(severity, 0.5)
    return max(1, round(max_pts * factor))


# ─────────────────────────────────────────────────────────────────────────────
# 0a. PDF LAYER-ORDER FORENSICS
# ─────────────────────────────────────────────────────────────────────────────
_LAYER_ORDER_HIGH_THRESHOLD = 0.30
_LAYER_ORDER_MEDIUM_THRESHOLD = 0.15


def detect_layer_order_mismatch(word_order: list[dict] | None) -> list[SignalDict]:
    """
    Flag pages where the PDF's internal text-extraction order diverges
    sharply from top-to-bottom/left-to-right visual reading order.

    Severity:
      HIGH   — disorder_ratio > 0.30 (heavily scrambled)
      MEDIUM — disorder_ratio > 0.15 (partially scrambled)

    Evidence strength: MODERATE
    Category: font_anomaly
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
            "signal_type":       "layer_order_mismatch",
            "severity":          severity,
            "page":              page_stat["page"],
            "bbox":              None,
            "description":       desc,
            "evidence_text":     _snippet(sample),
            "risk_points":       _scale_risk("font_anomaly", severity),
            "evidence_strength": "MODERATE",
            "confidence":        "medium",
            "remediation":       (
                "Layer-order scrambling alone is not proof of fraud — some PDF "
                "generators produce non-sequential content streams. Verify the "
                "visual layout matches the extracted text."
            ),
            "evidence": {
                "disorder_ratio": round(ratio, 4),
                "word_count":     page_stat.get("word_count", 0),
            },
        })

    return signals


# ─────────────────────────────────────────────────────────────────────────────
# 0b. METADATA FORENSICS
# ─────────────────────────────────────────────────────────────────────────────
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
    Cross-check PDF metadata against expected values for a genuine resume.

    Signals raised:
      - metadata_generic_builder_tool (MEDIUM/WEAK)
      - metadata_rapid_edit_window (MEDIUM/WEAK)
      - metadata_mod_before_creation (LOW/WEAK)
      - metadata_stripped (LOW/WEAK)

    Evidence strength: WEAK
    Category: metadata
    IMPORTANT: Metadata differences are NEVER proof of fraud on their own.
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
            "signal_type":       "metadata_generic_builder_tool",
            "severity":          "medium",
            "page":              1,
            "bbox":              None,
            "description":       (
                f"Document metadata identifies the authoring tool as "
                f"{creator or producer!r}, matching known free/instant resume "
                f"builder '{matched_tool}'. Not disqualifying on its own, but "
                f"worth weighing against claimed seniority/experience."
            ),
            "evidence_text":     f"Creator={creator!r} Producer={producer!r}",
            "risk_points":       _scale_risk("metadata", "medium"),
            "evidence_strength": "WEAK",
            "confidence":        "high",
            "remediation":       (
                "Many legitimate candidates use free resume builders. "
                "Verify claimed experience through interview and references "
                "rather than relying on tooling metadata."
            ),
            "evidence": {
                "creator":       creator,
                "producer":      producer,
                "matched_tool":  matched_tool,
            },
        })

    created  = _parse_pdf_date(metadata.get("creationDate"))
    modified = _parse_pdf_date(metadata.get("modDate"))

    if created and modified:
        gap = modified - created
        gap_minutes = gap.total_seconds() / 60.0

        if 0 < gap_minutes < 120:
            signals.append({
                "signal_type":       "metadata_rapid_edit_window",
                "severity":          "medium",
                "page":              1,
                "bbox":              None,
                "description":       (
                    f"File was created and last modified only "
                    f"{gap_minutes:.0f} minute(s) apart — consistent "
                    f"with a resume rapidly assembled/edited right before "
                    f"submission rather than a maintained, long-standing document."
                ),
                "evidence_text":     (
                    f"CreationDate={metadata.get('creationDate')!r} "
                    f"ModDate={metadata.get('modDate')!r}"
                ),
                "risk_points":       _scale_risk("metadata", "medium"),
                "evidence_strength": "WEAK",
                "confidence":        "medium",
                "remediation":       (
                    "A short edit window may simply reflect a candidate who "
                    "saved once after final tweaks. Consider alongside other signals."
                ),
                "evidence": {
                    "creation_date":  metadata.get("creationDate"),
                    "mod_date":       metadata.get("modDate"),
                    "gap_minutes":    round(gap_minutes, 1),
                },
            })

        if gap.total_seconds() < 0:
            signals.append({
                "signal_type":       "metadata_mod_before_creation",
                "severity":          "low",
                "page":              1,
                "bbox":              None,
                "description":       (
                    "Document's ModDate is earlier than its CreationDate — "
                    "an internal inconsistency that can indicate manual "
                    "metadata tampering."
                ),
                "evidence_text":     (
                    f"CreationDate={metadata.get('creationDate')!r} "
                    f"ModDate={metadata.get('modDate')!r}"
                ),
                "risk_points":       _scale_risk("metadata", "low"),
                "evidence_strength": "WEAK",
                "confidence":        "medium",
                "remediation":       (
                    "Metadata timestamp reversal can occur with some PDF editors. "
                    "It is a weak signal and should not be used in isolation."
                ),
                "evidence": {
                    "creation_date": metadata.get("creationDate"),
                    "mod_date":      metadata.get("modDate"),
                },
            })

    if not creator and not producer and not metadata.get("creationDate"):
        signals.append({
            "signal_type":       "metadata_stripped",
            "severity":          "low",
            "page":              1,
            "bbox":              None,
            "description":       (
                "No creator/producer/creation-date metadata present at all. "
                "This can be entirely innocent, but it can also indicate "
                "metadata was deliberately stripped to hide the authoring tool."
            ),
            "evidence_text":     None,
            "risk_points":       _scale_risk("metadata", "low"),
            "evidence_strength": "WEAK",
            "confidence":        "low",
            "remediation":       (
                "Stripped metadata is common in privacy-conscious exports. "
                "Treat as a very weak supporting signal only."
            ),
            "evidence":          None,
        })

    return signals


# ─────────────────────────────────────────────────────────────────────────────
# 0c. IMAGE-ONLY PAGE DETECTION
# ─────────────────────────────────────────────────────────────────────────────

def detect_image_only_pages(image_pages: list[dict] | None) -> list[SignalDict]:
    """
    Flag pages that are visually dominated by a large embedded image yet
    contain almost no extractable text.

    Evidence strength: STRONG
    Category: font_anomaly
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
            "signal_type":       "image_only_page",
            "severity":          "high",
            "page":              page_stat["page"],
            "bbox":              None,
            "description":       desc,
            "evidence_text":     None,
            "risk_points":       _scale_risk("font_anomaly", "high"),
            "evidence_strength": "STRONG",
            "confidence":        "high",
            "remediation":       (
                "Run OCR on this page to recover the actual text content "
                "before making a hiring decision."
            ),
            "evidence": {
                "image_area_ratio":  round(page_stat.get("image_area_ratio", 0), 4),
                "text_char_count":   page_stat.get("text_char_count", 0),
            },
        })

    return signals


# ─────────────────────────────────────────────────────────────────────────────
# 1. ZERO-WIDTH CHARACTER DETECTOR
# ─────────────────────────────────────────────────────────────────────────────
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

    Returns per-span signals with full Unicode evidence (code point,
    character name, occurrence count, surrounding context).

    Severity: HIGH — deliberate manipulation, invisible to human reviewers.
    Evidence strength: DEFINITIVE
    Category: zero_width_chars
    """
    signals: list[SignalDict] = []

    for span in spans:
        text = span.get("text", "")
        matches = list(_ZW_PATTERN.finditer(text))
        if not matches:
            continue

        # Build per-character evidence
        char_details: list[dict] = []
        seen_codepoints: set[str] = set()
        for m in matches:
            ch = m.group()
            cp = f"U+{ord(ch):04X}"
            name = _ZERO_WIDTH_CHARS.get(ch, unicodedata.name(ch, "UNKNOWN"))
            # Surrounding context (±20 chars, sanitised)
            start = max(0, m.start() - 20)
            end   = min(len(text), m.end() + 20)
            context = repr(text[start:end])

            if cp not in seen_codepoints:
                char_details.append({
                    "character":   repr(ch),
                    "codepoint":   cp,
                    "name":        name,
                    "context":     context,
                })
                seen_codepoints.add(cp)

        char_names = ", ".join(d["name"] for d in char_details)
        description = (
            f"Found {len(matches)} invisible character(s) in span on page {span['page']}: "
            + char_names
            + ". These characters are invisible to human readers but are parsed "
            "by ATS keyword scanners, and can be used to insert hidden keywords."
        )

        signals.append({
            "signal_type":       "zero_width_chars",
            "severity":          "high",
            "page":              span["page"],
            "bbox":              span.get("bbox"),
            "description":       description,
            "evidence_text":     _snippet(text),
            "risk_points":       _scale_risk("zero_width_chars", "high"),
            "evidence_strength": "DEFINITIVE",
            "confidence":        "high",
            "remediation":       (
                "Remove all invisible Unicode control characters from the "
                "document. Search-and-replace in the original source file "
                "(not just the PDF) to eliminate the characters at the root."
            ),
            "evidence": {
                "occurrence_count":   len(matches),
                "unique_codepoints":  len(seen_codepoints),
                "characters":         char_details,
                "page":               span["page"],
                "bbox":               span.get("bbox"),
            },
        })

    return signals


# ─────────────────────────────────────────────────────────────────────────────
# 2. HOMOGLYPH DETECTOR
# ─────────────────────────────────────────────────────────────────────────────

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
    Greek codepoints.

    IMPORTANT: Do not flag legitimate multilingual resumes. Mixed-script
    anomalies are indicators when a primarily-Latin-script word contains a
    single Cyrillic/Greek lookalike — not when the document legitimately
    uses multiple scripts.

    Severity: HIGH — intentional character substitution when confirmed.
    Evidence strength: STRONG
    Category: homoglyph
    """
    signals: list[SignalDict] = []

    for span in spans:
        text = span.get("text", "")
        for word_match in _WORD_RE.finditer(text):
            word = word_match.group()
            if len(word) < 2:
                continue

            scripts: set[str] = set()
            suspect_chars: list[dict] = []

            for ch in word:
                s = _unicode_script(ch)
                if s != "Neutral":
                    scripts.add(s)
                if ch in _SUSPICIOUS_LOOKALIKES:
                    suspect_chars.append({
                        "character":       repr(ch),
                        "codepoint":       f"U+{ord(ch):04X}",
                        "detected_script": _unicode_script(ch),
                        "expected_script": "Latin",
                        "position_in_word": word.index(ch),
                    })

            # Only flag if MULTIPLE non-neutral scripts AND suspicious chars present
            # This avoids false-positives on legitimate multilingual content
            non_neutral = scripts - {"Neutral", "Other"}
            if len(non_neutral) >= 2 and suspect_chars:
                scripts_list = sorted(non_neutral)
                desc = (
                    f"Word {word!r} on page {span['page']} mixes scripts "
                    f"{scripts_list} with suspected homoglyphs: "
                    + ", ".join(
                        f"{c['character']}({c['codepoint']})" for c in suspect_chars
                    )
                    + ". Visually similar Unicode characters can alter machine-readable "
                    "text while appearing identical to a human reader."
                )
                signals.append({
                    "signal_type":       "homoglyph_substitution",
                    "severity":          "high",
                    "page":              span["page"],
                    "bbox":              span.get("bbox"),
                    "description":       desc,
                    "evidence_text":     _snippet(text),
                    "risk_points":       _scale_risk("homoglyph", "high"),
                    "evidence_strength": "STRONG",
                    "confidence":        "high",
                    "remediation":       (
                        "Replace the flagged characters with their standard Latin "
                        "equivalents in the source document. Use a Unicode inspector "
                        "to verify all characters in key terms (name, skills, company names)."
                    ),
                    "evidence": {
                        "word":              word,
                        "scripts_found":     scripts_list,
                        "suspect_chars":     suspect_chars,
                        "page":              span["page"],
                        "bbox":              span.get("bbox"),
                    },
                })
                break   # one signal per span is enough

    return signals


# ─────────────────────────────────────────────────────────────────────────────
# 3. HIDDEN-TEXT DETECTOR (near-white text on white background)
# ─────────────────────────────────────────────────────────────────────────────

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

    Classification:
      HIGH   — distance < 10   (essentially invisible)  → DEFINITIVE
      MEDIUM — distance 10-30  (barely visible)          → STRONG

    Evidence strength: DEFINITIVE (dist<10) | STRONG (10-30)
    Category: hidden_text
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
            strength = "DEFINITIVE" if dist < 10 else "STRONG"
            desc = (
                f"Text colour RGB{tuple(color)} is {dist:.1f} units from "
                f"background RGB{background_color} (threshold {threshold}). "
                "Text is effectively invisible to a human reader but "
                "fully parseable by ATS keyword scanners."
            )
            signals.append({
                "signal_type":       "hidden_text",
                "severity":          severity,
                "page":              span["page"],
                "bbox":              span.get("bbox"),
                "description":       desc,
                "evidence_text":     _snippet(text),
                "risk_points":       _scale_risk("hidden_text", severity),
                "evidence_strength": strength,
                "confidence":        "high",
                "remediation":       (
                    "Remove or make visible any text that shares the document's "
                    "background colour. White or near-white text on a white "
                    "background is a classic ATS keyword-stuffing technique."
                ),
                "evidence": {
                    "text_color_rgb":        list(color),
                    "background_color_rgb":  list(background_color),
                    "rgb_distance":          round(dist, 2),
                    "threshold":             threshold,
                    "font_size":             span.get("font_size"),
                    "page":                  span["page"],
                    "bbox":                  span.get("bbox"),
                },
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

    Normal margin text and legitimate small-print are NOT flagged here —
    the font threshold is very tight (≤ 1pt by default, configurable).

    Severity:
      HIGH   — font-size 0 or outside page bounds
      MEDIUM — font-size > 0 but ≤ threshold

    Category:
      hidden_text  (tiny font)
      offpage      (off-canvas text)

    Evidence strength: DEFINITIVE (off-page) | STRONG (tiny font)
    """
    dim_map: dict[int, dict] = {d["page"]: d for d in page_dims}
    signals: list[SignalDict] = []

    for span in spans:
        text = span.get("text", "").strip()
        if not text:
            continue

        page = span["page"]
        font_size: float = span.get("font_size", 12.0)
        bbox = span.get("bbox")

        # ── a. Zero / tiny font ──────────────────────────────────────────────
        if font_size <= hidden_size_threshold:
            severity = "high" if font_size <= 0 else "medium"
            strength = "DEFINITIVE" if font_size <= 0 else "STRONG"
            desc = (
                f"Font size {font_size}pt is at or below the hidden-text "
                f"threshold ({hidden_size_threshold}pt). Text is effectively "
                "invisible to a human reader but extracted by ATS parsers."
            )
            signals.append({
                "signal_type":       "zero_or_tiny_font",
                "severity":          severity,
                "page":              page,
                "bbox":              bbox,
                "description":       desc,
                "evidence_text":     _snippet(text),
                "risk_points":       _scale_risk("hidden_text", severity),
                "evidence_strength": strength,
                "confidence":        "high",
                "remediation":       (
                    f"All visible text should be at least 6pt. Font size "
                    f"{font_size}pt is below the minimum legible threshold. "
                    "Remove or resize this text."
                ),
                "evidence": {
                    "font_size":             font_size,
                    "hidden_size_threshold": hidden_size_threshold,
                    "page":                  page,
                    "bbox":                  bbox,
                },
            })
            continue  # no need to also check position for same span

        # ── b. Off-page position ─────────────────────────────────────────────
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

            # Calculate distance outside boundary
            dist_outside = max(
                -x1 if off_left else 0,
                x0 - page_w if off_right else 0,
                -y1 if off_top else 0,
                y0 - page_h if off_bottom else 0,
            )

            desc = (
                f"Span bbox {[round(v,1) for v in bbox]} is entirely off "
                f"the {page_w:.0f}×{page_h:.0f}pt page (off: {direction}). "
                f"Distance outside boundary: {dist_outside:.1f}pt. "
                "Off-page text is invisible to human readers but may be "
                "extracted by some ATS parsers."
            )
            signals.append({
                "signal_type":       "offpage_text",
                "severity":          "high",
                "page":              page,
                "bbox":              bbox,
                "description":       desc,
                "evidence_text":     _snippet(text),
                "risk_points":       _scale_risk("offpage", "high"),
                "evidence_strength": "DEFINITIVE",
                "confidence":        "high",
                "remediation":       (
                    "Remove all text objects positioned outside the page "
                    "boundaries. Off-page text is a well-known ATS evasion "
                    "technique and should not appear in a legitimate resume."
                ),
                "evidence": {
                    "bbox":                list(bbox),
                    "page_width":          page_w,
                    "page_height":         page_h,
                    "off_directions":      direction,
                    "distance_outside_pt": round(dist_outside, 2),
                    "page":                page,
                },
            })

    return signals


# ─────────────────────────────────────────────────────────────────────────────
# 5. TIMELINE INCONSISTENCY DETECTOR
# ─────────────────────────────────────────────────────────────────────────────

# Regex for common resume date-range patterns, e.g.:
#   "Jan 2020 – Mar 2022"   "2019–Present"   "June 2018 to Current"
#
# FIX (crash bug): added (?<!\d) / (?!\d) guards around the bare 4-digit
# year branches so a substring like "0000" inside a phone number
# ("+91-90000-00000") or pincode can no longer be mistaken for a year.
# Without these lookarounds, \d{4} happily matches the last 4 digits of
# any longer digit run, which previously produced raw="0000" and crashed
# downstream in _parse_date_fuzzy with `ValueError: year 0 is out of range`.
_DATE_RANGE_RE = re.compile(
    r"""
    (?P<start>
        (?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|
           Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|
           Dec(?:ember)?)
        \s*\.?\s*\d{4}
        |
        (?<!\d)\d{4}(?!\d)        # bare year — not part of a longer digit run
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
        (?<!\d)\d{4}(?!\d)        # bare year — not part of a longer digit run
        |
        (?:Present|Current|Now|Ongoing|Today)
    )
    """,
    re.VERBOSE | re.IGNORECASE,
)

_TODAY = date.today()

# FIX (crash bug): reasonable bounds for a resume date — anything outside
# this range is almost certainly a mis-parsed phone number, ID, or OCR
# artifact rather than a genuine employment year, so we discard it instead
# of trying to construct an out-of-range `date()` object.
_MIN_VALID_YEAR = 1950
_MAX_VALID_YEAR_OFFSET = 1  # allow up to 1 year in the future (ref_date.year + 1)


def _parse_date_fuzzy(raw: str, ref_date: date | None = None) -> date | None:
    """
    Parse a date string; returns None if unparseable OR if the resulting
    year falls outside a sane resume-date range (1950 .. today+1).

    This is the fix for the production crash:
        File "fraud_detectors.py", line 613, in _parse_date_fuzzy
            return date(int(raw), 1, 1)
        ValueError: year 0 is out of range

    That happened because the old regex could match "0000" out of a phone
    number, and `date(0, 1, 1)` is not a valid Python date. Now any
    out-of-range or garbage year is simply treated as "not a date" (None)
    instead of raising.
    """
    raw = raw.strip()
    target_today = ref_date or date.today()
    max_valid_year = target_today.year + _MAX_VALID_YEAR_OFFSET

    if re.match(r"(?:Present|Current|Now|Ongoing|Today)", raw, re.IGNORECASE):
        return target_today

    # Bare year → Jan 1 of that year
    if re.fullmatch(r"\d{4}", raw):
        year = int(raw)
        if year < _MIN_VALID_YEAR or year > max_valid_year:
            return None
        return date(year, 1, 1)

    try:
        parsed = du_parser.parse(raw, default=datetime(2000, 1, 1)).date()
    except Exception:  # noqa: BLE001
        return None

    if parsed.year < _MIN_VALID_YEAR or parsed.year > max_valid_year:
        return None

    return parsed


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

    Note: Timeline signals are content-based, not document-manipulation signals.
    They contribute 0 risk points to the forensic score but affect the overall
    trust label through the fraud component.
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
                "signal_type":       "timeline_end_before_start",
                "severity":          "high",
                "page":              page,
                "bbox":              r.get("bbox"),
                "description":       (
                    f"Employment end date ({end}) precedes start date ({start}). "
                    f"Original text: {raw!r}"
                ),
                "evidence_text":     raw,
                "risk_points":       0,   # content issue, not document manipulation
                "evidence_strength": "STRONG",
                "confidence":        "high",
                "remediation":       "Verify the employment dates against primary sources.",
                "evidence": {
                    "start_date": str(start),
                    "end_date":   str(end),
                    "raw_text":   raw,
                },
            })

        if start > target_today:
            signals.append({
                "signal_type":       "timeline_future_start",
                "severity":          "high",
                "page":              page,
                "bbox":              r.get("bbox"),
                "description":       (
                    f"Employment start date ({start}) is in the future. "
                    f"Original text: {raw!r}"
                ),
                "evidence_text":     raw,
                "risk_points":       0,   # content issue, not document manipulation
                "evidence_strength": "STRONG",
                "confidence":        "high",
                "remediation":       "Verify employment start date is not a typo.",
                "evidence": {
                    "start_date":  str(start),
                    "today":       str(target_today),
                    "raw_text":    raw,
                },
            })

    # ── b. Overlap detection ─────────────────────────────────────────────────
    valid = [r for r in parsed_ranges if r["end"] >= r["start"]]
    valid.sort(key=lambda r: (r["start"], r["end"], r["page"]))
    grace = relativedelta(months=1)   # allow 1-month overlap (job transitions)

    for i in range(len(valid)):
        for j in range(i + 1, len(valid)):
            a, b = valid[i], valid[j]
            overlap_start = b["start"]
            overlap_end   = a["end"]
            if overlap_start < overlap_end:
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
                        "signal_type":       "timeline_overlap",
                        "severity":          "medium",
                        "page":              max(a["page"], b["page"]),
                        "bbox":              None,
                        "description":       desc,
                        "evidence_text":     f"{a['raw']} / {b['raw']}",
                        "risk_points":       0,   # content issue, not manipulation
                        "evidence_strength": "MODERATE",
                        "confidence":        "medium",
                        "remediation":       (
                            "Overlapping employment dates may indicate consulting "
                            "or part-time work. Ask the candidate to clarify "
                            "the employment arrangement."
                        ),
                        "evidence": {
                            "period_a":       a["raw"],
                            "period_b":       b["raw"],
                            "overlap_months": overlap_months,
                        },
                    })

    return signals


# ─────────────────────────────────────────────────────────────────────────────
# FONT SUBSTITUTION DETECTOR
# ─────────────────────────────────────────────────────────────────────────────

def detect_font_substitution(font_glyph_anomalies: list[dict] | None) -> list[SignalDict]:
    """
    Catch resumes where an embedded custom/subset font remaps character codes
    so that the text looks like one thing visually but the underlying Unicode
    encodes different characters (e.g., invisible ATS keyword stuffing).

    An unusual font alone must NOT be treated as fraud — this detector is
    triggered only when font_glyph_anomalies are explicitly detected by the
    PDF extractor.

    Evidence strength: MODERATE (supporting signal; requires visual verification)
    Category: font_anomaly
    """
    signals: list[SignalDict] = []
    if not font_glyph_anomalies:
        return signals

    for anomaly in font_glyph_anomalies:
        text = anomaly.get("suspected_extracted_text", "")
        font_name = anomaly.get("font_name", "")
        signals.append({
            "signal_type":       "font_substitution",
            "severity":          "high",
            "page":              anomaly.get("page", 1),
            "bbox":              anomaly.get("span_bbox"),
            "description":       (
                f"Suspected glyph-swap attack. The subset font '{font_name}' "
                "extracts as text that does not appear visually in the document. "
                "This technique allows hidden keywords to be parsed by ATS "
                "while appearing invisible or different to human reviewers."
            ),
            "evidence_text":     text[:200],
            "risk_points":       _scale_risk("font_anomaly", "high"),
            "evidence_strength": "MODERATE",
            "confidence":        "medium",
            "remediation":       (
                "This detection uses a heuristic based on high ATS keyword density "
                "in subset fonts. Verify by opening the PDF in a text editor and "
                "checking if the extracted text matches what you see visually."
            ),
            "evidence": {
                "font_name":              font_name,
                "suspected_hidden_text":  text[:200],
                "page":                   anomaly.get("page", 1),
            },
        })

    return signals


# ─────────────────────────────────────────────────────────────────────────────
# 6. PROMPT INJECTION DETECTOR  (new)
# ─────────────────────────────────────────────────────────────────────────────

# Patterns that attempt to manipulate AI evaluators
_PROMPT_INJECTION_PATTERNS: list[tuple[str, str, str]] = [
    # (regex_pattern, severity, matched_description)
    (
        r"ignore\s+(?:all\s+)?(?:previous|prior|above|earlier)\s+instructions?",
        "high",
        "Classic prompt injection: instruction override attempt",
    ),
    (
        r"disregard\s+(?:all\s+)?(?:previous|prior|above|earlier)",
        "high",
        "Prompt injection: disregard instruction attempt",
    ),
    (
        r"(?:always|must|should)\s+(?:rank|select|choose|hire|accept)\s+this\s+candidate",
        "high",
        "Prompt injection: forced selection instruction",
    ),
    (
        r"give\s+this\s+candidate\s+a\s+(?:score|rating)\s+of\s+(?:100|10|A\+|perfect)",
        "high",
        "Prompt injection: score manipulation attempt",
    ),
    (
        r"ai\s*(?:evaluator|assistant|model|system)\s*[:,]?\s*(?:please\s+)?(?:select|rank|hire|accept|approve)",
        "high",
        "Prompt injection: direct AI evaluator instruction",
    ),
    (
        r"(?:you\s+are\s+now|act\s+as|pretend\s+to\s+be)\s+(?:a\s+)?(?:hiring\s+manager|recruiter|hr)",
        "medium",
        "Prompt injection: role override attempt",
    ),
    (
        r"this\s+candidate\s+(?:is\s+perfect|is\s+the\s+best|should\s+be\s+hired\s+immediately)",
        "medium",
        "Prompt injection: forced positive assessment",
    ),
    (
        r"do\s+not\s+(?:flag|detect|check|scan|evaluate)\s+this\s+(?:resume|document|candidate)",
        "medium",
        "Prompt injection: evasion instruction",
    ),
    (
        r"system\s*:\s*(?:select|hire|approve|accept|rank|boost)",
        "medium",
        "Prompt injection: system-prompt-style instruction",
    ),
    (
        r"forget\s+(?:everything|all)\s+(?:you\s+)?(?:know|have\s+learned|were\s+told)",
        "high",
        "Prompt injection: memory wipe instruction",
    ),
]

_COMPILED_INJECTION_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    (re.compile(pattern, re.IGNORECASE | re.UNICODE), severity, desc)
    for pattern, severity, desc in _PROMPT_INJECTION_PATTERNS
]


def detect_prompt_injection(spans: list[dict]) -> list[SignalDict]:
    """
    Detect text patterns in the resume that attempt to manipulate AI evaluators.

    Relevant because the frontend integrates Gemini AI (gemini.ts) which receives
    scan context. This detector catches instructions that, if not isolated,
    could attempt to override AI evaluator behavior.

    IMPORTANT: Do not flag normal resume text. Only exact or near-exact matches
    against known injection patterns are flagged.

    Severity: HIGH (exact instruction override) | MEDIUM (softer manipulation)
    Evidence strength: STRONG (exact match) | MODERATE (pattern match)
    Category: prompt_injection
    """
    signals: list[SignalDict] = []

    # Deduplicate: track (pattern, page) pairs to avoid repeated signals
    seen: set[tuple[str, int]] = set()

    for span in spans:
        text = span.get("text", "")
        if not text.strip():
            continue

        for pattern, severity, match_desc in _COMPILED_INJECTION_PATTERNS:
            m = pattern.search(text)
            if not m:
                continue

            key = (match_desc, span["page"])
            if key in seen:
                continue
            seen.add(key)

            matched_text = m.group()
            strength = "STRONG" if severity == "high" else "MODERATE"

            desc = (
                f"Potential prompt injection instruction detected on page {span['page']}: "
                f"{match_desc}. Suspicious instruction: {matched_text!r}. "
                "This type of text may attempt to manipulate AI evaluators "
                "processing this resume."
            )
            signals.append({
                "signal_type":       "prompt_injection",
                "severity":          severity,
                "page":              span["page"],
                "bbox":              span.get("bbox"),
                "description":       desc,
                "evidence_text":     _snippet(text),
                "risk_points":       _scale_risk("prompt_injection", severity),
                "evidence_strength": strength,
                "confidence":        "medium",
                "remediation":       (
                    "The flagged text appears to be an instruction targeting AI "
                    "processing systems. If this was not intentional, remove it. "
                    "If detected in white/hidden text, this is a deliberate attempt "
                    "to manipulate AI evaluators."
                ),
                "evidence": {
                    "matched_text":   matched_text,
                    "pattern_reason": match_desc,
                    "page":           span["page"],
                    "bbox":           span.get("bbox"),
                    "full_span":      _snippet(text, 300),
                },
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
    font_glyph_anomalies: list[dict] | None = None,
    reference_date: date | None = None,
) -> list[SignalDict]:
    """
    Run every detector and return the combined signal list in deterministic order.
    Adding a new detector only requires registering it here.

    All returned signals now include `risk_points`, `evidence_strength`,
    `confidence`, `remediation`, and `evidence` fields for the explainability UI.
    """
    signals: list[SignalDict] = []
    signals.extend(detect_zero_width_chars(spans))
    signals.extend(detect_homoglyphs(spans))
    signals.extend(detect_hidden_text(spans, background_color, hidden_text_threshold))
    signals.extend(detect_offpage_or_zero_size(spans, page_dims, hidden_size_threshold))
    signals.extend(detect_prompt_injection(spans))

    # FIX (crash bug): wrapped in try/except so a future edge case in date
    # parsing degrades gracefully (skips just the timeline signals) instead
    # of taking down the entire /scan request with a 500 error. Every other
    # detector's results still reach the user even if this one misbehaves.
    try:
        date_ranges = extract_date_ranges(spans, ref_date=reference_date)
        signals.extend(detect_timeline_issues(date_ranges, ref_date=reference_date))
    except Exception:  # noqa: BLE001
        pass

    # ── Phase 5 additions ────────────────────────────────────────────────────
    signals.extend(detect_layer_order_mismatch(word_order))
    signals.extend(detect_metadata_red_flags(metadata))
    signals.extend(detect_image_only_pages(image_pages))
    signals.extend(detect_font_substitution(font_glyph_anomalies))

    # ── Deterministic sorting ─────────────────────────────────────────────────
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