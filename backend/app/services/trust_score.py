"""
trust_score.py — Explainable Trust Score Engine
=================================================
Converts the raw fraud signals, the AI-content score,
and (when available) the True Match Score into:

  1. A forensic_risk_score (0-100) — pure document-forensic evidence
     computed from per-signal risk_points via risk_config.py
  2. A composite trust_score (0-100) — the blended recruiter-facing score

Formula
-------
  forensic_risk_score  = sum of detected risk points (capped at 100)
  fraud_component      = 100 − forensic_risk_score
  trust_score          = fraud_component×0.60 + integrity×0.25 + match×0.15

  (When no JD is supplied, fraud/integrity weights are re-normalised to 100%:
   trust_score = fraud_component×0.706 + integrity×0.294)

Wording rules (enforced in narrative/UI, not here)
--------------------------------------------------
- "Trust Score: 78/100"   ← correct
- "Score represents detected document-risk indicators per our forensic model."
- NEVER "78% probability the resume is genuine"

Public API
----------
    compute_trust_score(
        fraud_summary: dict,
        ai_content_score: float | None,
        true_match_score: float | None,
        signals: list[dict] | None,   # ← NEW: needed for risk point aggregation
    ) -> dict
        {
            "score":                float,   # 0-100
            "forensic_risk_score":  int,     # 0-100  ← NEW
            "risk_breakdown":       dict,    # per-category breakdown  ← NEW
            "label":                str,
            "emoji":                str,
            "color":                str,
            "breakdown": {
                "fraud_component":    float,
                "integrity_component": float,
                "match_component":    float | None,
            },
            "weights": {...},
        }
"""
from __future__ import annotations

from typing import Any

from app.services.risk_config import compute_risk_score

_WEIGHT_FRAUD     = 0.60
_WEIGHT_INTEGRITY = 0.25
_WEIGHT_MATCH     = 0.15

_VERIFIED_THRESHOLD = 75.0
_CAUTION_THRESHOLD  = 45.0


def _fraud_component(
    fraud_summary: dict[str, Any],
    signals: list[dict] | None,
) -> tuple[float, int, dict]:
    """
    Compute the fraud component (0-100, 100 = no fraud signals) using
    the new risk-point model.

    Returns
    -------
    (fraud_component_score, forensic_risk_score, risk_breakdown)
    """
    if signals:
        risk = compute_risk_score(signals)
        forensic_risk = risk["total"]
        breakdown     = risk["breakdown"]
    else:
        # Legacy fallback: use severity counts if no signals list provided
        high   = fraud_summary.get("high", 0)
        medium = fraud_summary.get("medium", 0)
        low    = fraud_summary.get("low", 0)
        forensic_risk = min(100, high * 18 + medium * 8 + low * 3)
        breakdown     = {}

    fraud_component = max(0.0, 100.0 - forensic_risk)
    return fraud_component, forensic_risk, breakdown


def _integrity_component(ai_content_score: float | None) -> float:
    """
    100 = confidently human-written, 0 = confidently AI-written.
    ai_content_score is already 0 (human) .. 100 (AI), so just invert it.
    None (score unavailable) is treated as neutral (70).
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
    signals: list[dict] | None = None,
) -> dict[str, Any]:
    """
    Compute the composite Trust Score and the new Forensic Risk Score.

    Parameters
    ----------
    fraud_summary:    dict with "high", "medium", "low", "total" keys
    ai_content_score: 0-100 AI likelihood score (None → neutral 70)
    true_match_score: 0-100 job-match score (None → excluded from blend)
    signals:          full signal list from run_all_detectors() — enables
                      the new per-category risk-point calculation.
                      Falls back to severity-count penalties if None.
    """
    high_count = int(fraud_summary.get("high", 0))
    fraud_c, forensic_risk, risk_breakdown = _fraud_component(fraud_summary, signals)
    integrity_c = _integrity_component(ai_content_score)
    match_c     = _match_component(true_match_score)

    if match_c is None:
        # Re-normalise fraud/integrity weights to 100% when no JD was given
        w_fraud     = _WEIGHT_FRAUD / (_WEIGHT_FRAUD + _WEIGHT_INTEGRITY)
        w_integrity = _WEIGHT_INTEGRITY / (_WEIGHT_FRAUD + _WEIGHT_INTEGRITY)
        score = fraud_c * w_fraud + integrity_c * w_integrity
    else:
        score = (
            fraud_c     * _WEIGHT_FRAUD
            + integrity_c * _WEIGHT_INTEGRITY
            + match_c     * _WEIGHT_MATCH
        )

    # Consistency enforcement: cap numeric score so it agrees with label
    if high_count >= 2:
        score = min(score, 44.0)
    elif high_count == 1:
        score = min(score, 74.0)

    score = round(max(0.0, min(100.0, score)), 1)
    label, emoji, color = _label_for(score, high_count=high_count)

    return {
        "score":               score,
        "forensic_risk_score": forensic_risk,
        "risk_breakdown":      risk_breakdown,
        "label":               label,
        "emoji":               emoji,
        "color":               color,
        "breakdown": {
            "fraud_component":      round(fraud_c, 1),
            "integrity_component":  round(integrity_c, 1),
            "match_component":      round(match_c, 1) if match_c is not None else None,
        },
        "weights": {
            "fraud":     _WEIGHT_FRAUD,
            "integrity": _WEIGHT_INTEGRITY,
            "match":     _WEIGHT_MATCH if match_c is not None else 0.0,
        },
    }