"""
risk_config.py — Explainable Risk-Scoring Configuration
=========================================================
All per-category risk point allocations live here.
They can be overridden via environment variables so tuning
never requires a code change.

Category totals must sum to ≤ 100 (the max possible risk score).

Usage
-----
    from app.services.risk_config import RISK_WEIGHTS, TOTAL_MAX
    pts = RISK_WEIGHTS["hidden_text"]   # → 25

Environment variables (all optional)
-------------------------------------
    RISK_WEIGHT_HIDDEN_TEXT       default 25
    RISK_WEIGHT_ZERO_WIDTH        default 15
    RISK_WEIGHT_HOMOGLYPH         default 15
    RISK_WEIGHT_OFFPAGE           default 15
    RISK_WEIGHT_FONT_ANOMALY      default 10
    RISK_WEIGHT_METADATA          default 10
    RISK_WEIGHT_PROMPT_INJECTION  default 10
"""
from __future__ import annotations

import os

def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (ValueError, TypeError):
        return default


RISK_WEIGHTS: dict[str, int] = {
    # Category key          Env-var override                   Default
    "hidden_text":          _env_int("RISK_WEIGHT_HIDDEN_TEXT",       25),
    "zero_width_chars":     _env_int("RISK_WEIGHT_ZERO_WIDTH",         15),
    "homoglyph":            _env_int("RISK_WEIGHT_HOMOGLYPH",          15),
    "offpage":              _env_int("RISK_WEIGHT_OFFPAGE",            15),
    "font_anomaly":         _env_int("RISK_WEIGHT_FONT_ANOMALY",       10),
    "metadata":             _env_int("RISK_WEIGHT_METADATA",           10),
    "prompt_injection":     _env_int("RISK_WEIGHT_PROMPT_INJECTION",   10),
}

# Hard cap — individual category scores are prorated if they exceed their
# allocation; the total is further capped at TOTAL_MAX.
TOTAL_MAX: int = 100

# Maps signal_type strings (from fraud_detectors) to category keys above.
# Any signal_type not listed here contributes 0 risk points.
SIGNAL_CATEGORY_MAP: dict[str, str] = {
    # Hidden / invisible text
    "hidden_text":                  "hidden_text",
    "zero_or_tiny_font":            "hidden_text",

    # Zero-width Unicode
    "zero_width_chars":             "zero_width_chars",

    # Homoglyph / mixed script
    "homoglyph_substitution":       "homoglyph",

    # Off-page / abnormal position
    "offpage_text":                 "offpage",

    # Font / rendering anomaly
    "font_substitution":            "font_anomaly",
    "layer_order_mismatch":         "font_anomaly",
    "image_only_page":              "font_anomaly",

    # PDF metadata / structure
    "metadata_generic_builder_tool":"metadata",
    "metadata_rapid_edit_window":   "metadata",
    "metadata_mod_before_creation": "metadata",
    "metadata_stripped":            "metadata",

    # Prompt injection
    "prompt_injection":             "prompt_injection",

    # Timeline issues contribute to overall trust via severity but are not
    # mapped to a forensic risk category (they are a content issue, not a
    # document manipulation issue).  Assign 0 by leaving them unmapped.
}


def compute_risk_score(signals: list[dict]) -> dict:
    """
    Aggregate per-signal risk points into a category breakdown and total.

    Each signal already has a ``risk_points`` field set by the detector.
    We sum by category, cap each category at its configured maximum, then
    cap the total at TOTAL_MAX.

    Returns
    -------
    {
        "total":       int,              # 0–100
        "breakdown": {
            "hidden_text":       int,   # 0–25
            "zero_width_chars":  int,   # 0–15
            "homoglyph":         int,   # 0–15
            "offpage":           int,   # 0–15
            "font_anomaly":      int,   # 0–10
            "metadata":          int,   # 0–10
            "prompt_injection":  int,   # 0–10
        }
    }
    """
    # Accumulate raw points by category (uncapped)
    raw: dict[str, int] = {k: 0 for k in RISK_WEIGHTS}

    for sig in signals:
        cat = SIGNAL_CATEGORY_MAP.get(sig.get("signal_type", ""))
        if cat is None:
            continue
        raw[cat] += sig.get("risk_points", 0)

    # Cap each category at its configured max
    breakdown: dict[str, int] = {
        cat: min(pts, RISK_WEIGHTS[cat]) for cat, pts in raw.items()
    }

    total = min(sum(breakdown.values()), TOTAL_MAX)

    return {
        "total":     total,
        "breakdown": breakdown,
    }
