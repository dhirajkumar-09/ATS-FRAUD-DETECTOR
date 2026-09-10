"""
trust_score.py — Phase 5, Feature 4
======================================
Converts the raw Green/Red-style fraud signal counts, the AI-content score,
and (when available) the True Match Score into a single composite
0-100 "Trust Score" with a Verified / Caution / High Risk badge — a
judge-friendly, one-glance verdict. The full detail tables remain available
for anyone who wants to drill in.

Public API
----------
    compute_trust_score(
        fraud_summary: dict,           # {"high", "medium", "low", ...}
        ai_content_score: float | None,
        true_match_score: float | None,
    ) -> dict
        {
            "score":   float,          # 0-100, higher = more trustworthy
            "label":   str,            # "Verified" | "Caution" | "High Risk"
            "emoji":   str,            # 🟢 | 🟡 | 🔴
            "color":   str,            # CSS variable name for the frontend
            "breakdown": {
                "fraud_component":  float,  # 0-100 (100 = no fraud signals)
                "integrity_component": float,  # 0-100 (100 = looks human-written)
                "match_component":  float | None,  # 0-100, None if no JD given
            },
            "weights": {...},
        }

Weighting rationale
--------------------
- Fraud signals are the strongest evidence of deliberate manipulation, so
  they dominate the score (60%).
- The AI-content score feeds an "integrity" component — heavily AI-generated
  content isn't fraud by itself, but it reduces confidence that the resume
  reflects the candidate's own authentic experience (25%).
- True Match Score reflects genuine job-fit, not honesty — it gets a light
  weight (15%) and is excluded from the blend entirely when no job
  description was supplied, so the score never penalises resumes for a
  feature the recruiter didn't opt into.
"""
from __future__ import annotations

from typing import Any

_WEIGHT_FRAUD = 0.60
_WEIGHT_INTEGRITY = 0.25
_WEIGHT_MATCH = 0.15

# Per-signal penalty applied to the 0-100 fraud component.
_HIGH_PENALTY = 18.0
_MEDIUM_PENALTY = 8.0
_LOW_PENALTY = 3.0

_VERIFIED_THRESHOLD = 75.0
_CAUTION_THRESHOLD = 45.0


def _fraud_component(fraud_summary: dict[str, Any]) -> float:
    """100 = no fraud signals at all; degrades with each signal, floor 0."""
    high   = fraud_summary.get("high", 0)
    medium = fraud_summary.get("medium", 0)
    low    = fraud_summary.get("low", 0)

    penalty = high * _HIGH_PENALTY + medium * _MEDIUM_PENALTY + low * _LOW_PENALTY
    return max(0.0, 100.0 - penalty)


def _integrity_component(ai_content_score: float | None) -> float:
    """
    100 = confidently human-written, 0 = confidently AI-written.
    ai_content_score is already 0 (human) .. 100 (AI), so just invert it.
    None (score unavailable) is treated as neutral (70) rather than
    penalising resumes when the AI detector had too little text to judge.
    """
    if ai_content_score is None:
        return 70.0
    return max(0.0, 100.0 - float(ai_content_score))


def _match_component(true_match_score: float | None) -> float | None:
    if true_match_score is None:
        return None
    return max(0.0, min(100.0, float(true_match_score)))


def _label_for(score: float, high_count: int = 0) -> tuple[str, str, str]:
    # Critical consistency rule: A resume with high-severity fraud signals
    # must NEVER be labeled "Verified", and 2+ high signals must be "High Risk".
    if high_count >= 2:
        return "High Risk", "🔴", "--crimson"
    if high_count == 1:
        if score >= _CAUTION_THRESHOLD:
            return "Caution", "🟡", "--amber"
        return "High Risk", "🔴", "--crimson"

    if score >= _VERIFIED_THRESHOLD:
        return "Verified", "🟢", "--teal"
    if score >= _CAUTION_THRESHOLD:
        return "Caution", "🟡", "--amber"
    return "High Risk", "🔴", "--crimson"


def compute_trust_score(
    fraud_summary: dict[str, Any],
    ai_content_score: float | None,
    true_match_score: float | None = None,
) -> dict[str, Any]:
    high_count = int(fraud_summary.get("high", 0))
    fraud_c = _fraud_component(fraud_summary)
    integrity_c = _integrity_component(ai_content_score)
    match_c = _match_component(true_match_score)

    if match_c is None:
        # Re-normalise fraud/integrity weights to 100% when no JD was given,
        # so the absence of an optional feature never drags the score down.
        w_fraud = _WEIGHT_FRAUD / (_WEIGHT_FRAUD + _WEIGHT_INTEGRITY)
        w_integrity = _WEIGHT_INTEGRITY / (_WEIGHT_FRAUD + _WEIGHT_INTEGRITY)
        score = fraud_c * w_fraud + integrity_c * w_integrity
    else:
        score = (
            fraud_c * _WEIGHT_FRAUD
            + integrity_c * _WEIGHT_INTEGRITY
            + match_c * _WEIGHT_MATCH
        )

    # Consistency enforcement: cap numeric score so it agrees with label
    if high_count >= 2:
        score = min(score, 44.0)
    elif high_count == 1:
        score = min(score, 74.0)

    score = round(max(0.0, min(100.0, score)), 1)
    label, emoji, color = _label_for(score, high_count=high_count)

    return {
        "score": score,
        "label": label,
        "emoji": emoji,
        "color": color,
        "breakdown": {
            "fraud_component":     round(fraud_c, 1),
            "integrity_component": round(integrity_c, 1),
            "match_component":     round(match_c, 1) if match_c is not None else None,
        },
        "weights": {
            "fraud": _WEIGHT_FRAUD,
            "integrity": _WEIGHT_INTEGRITY,
            "match": _WEIGHT_MATCH if match_c is not None else 0.0,
        },
    }