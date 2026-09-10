"""
forensic_narrative.py — Explainability & Forensic Audit Narrative
================================================================
Generates plain-English, executive summaries explaining exactly *why*
a resume received its Trust Score, what fraud signals were found,
and how AI content / job-match factors influenced the verdict.
"""
from __future__ import annotations

from typing import Any


def generate_score_narrative(
    fraud_summary: dict[str, Any],
    ai_content: dict[str, Any] | None,
    true_match: dict[str, Any] | None,
    trust_score: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Synthesise a multi-point forensic briefing for recruiters.

    Returns
    -------
    {
        "verdict_title": str,
        "recommendation": str,
        "summary": str,
        "key_factors": list[str],
        "limitations_disclaimer": str,
    }
    """
    trust_score = trust_score or {}
    score = trust_score.get("score", 0.0)
    label = trust_score.get("label", "Unknown")

    total_signals = fraud_summary.get("total", 0)
    high_count = fraud_summary.get("high", 0)
    medium_count = fraud_summary.get("medium", 0)
    low_count = fraud_summary.get("low", 0)
    signals = fraud_summary.get("signals", [])

    factors: list[str] = []

    # 1. Fraud signal narration
    if high_count > 0:
        high_types = sorted({s.get("signal_type", "unknown") for s in signals if s.get("severity") == "high"})
        type_names = ", ".join(t.replace("_", " ") for t in high_types)
        factors.append(
            f"Detected {high_count} HIGH-severity manipulation signal(s) ({type_names}). "
            "Deliberate ATS-evasion techniques automatically disqualify the candidate from Verified status."
        )
    elif medium_count > 0:
        med_types = sorted({s.get("signal_type", "unknown") for s in signals if s.get("severity") == "medium"})
        type_names = ", ".join(t.replace("_", " ") for t in med_types)
        factors.append(
            f"Identified {medium_count} MEDIUM-severity anomaly signal(s) ({type_names}) "
            "suggesting non-standard document formatting or timeline overlaps."
        )
    elif total_signals == 0:
        factors.append(
            "Zero ATS manipulation signals detected: no hidden text, zero-width spaces, "
            "homoglyphs, off-page text, or scrambled content stream layers."
        )

    # 2. AI Content narration
    ai_score = (ai_content or {}).get("score")
    if ai_score is not None:
        backend = (ai_content or {}).get("backend", "heuristic")
        if ai_score >= 70:
            factors.append(
                f"AI Content Index is elevated at {ai_score:.1f}/100 ({backend} analysis). "
                "The text exhibits high syntactic uniformity and repetitive phrasing typical of synthetic LLM generation."
            )
        elif ai_score >= 40:
            factors.append(
                f"AI Content Index is moderate at {ai_score:.1f}/100. "
                "Document shows signs of AI-assisted drafting or heavy templating."
            )
        else:
            factors.append(
                f"AI Content Index is low ({ai_score:.1f}/100), consistent with natural, human-authored writing."
            )

    # 3. Match score narration
    if true_match:
        match_score = true_match.get("score", 0.0)
        matched_skills = true_match.get("matched_skills", [])
        missing_skills = true_match.get("missing_skills", [])
        if matched_skills:
            top_matched = ", ".join(matched_skills[:5])
            factors.append(f"Demonstrated alignment on {len(matched_skills)} required skill(s): {top_matched}.")
        if missing_skills:
            top_missing = ", ".join(missing_skills[:4])
            factors.append(f"Missing {len(missing_skills)} key skill(s) requested in JD: {top_missing}.")
        factors.append(f"True Match Score: {match_score:.1f}/100 after stripping fraudulent keywords.")
    else:
        factors.append("Job description fit was not evaluated (no JD provided). Score reflects pure document authenticity.")

    # Recommendation
    if label == "High Risk":
        verdict_title = "HIGH RISK — Suspected ATS Evasion / Document Tampering"
        recommendation = (
            "Flag for recruiter review. Deliberate anomalies detected that may have been designed "
            "to artificially inflate search relevance. Conduct a live technical interview or request original source documents."
        )
    elif label == "Caution":
        verdict_title = "CAUTION — Review Formatting & Experience Timelines"
        recommendation = (
            "Manual review recommended. Document contains layout, metadata, or timeline inconsistencies "
            "that warrant brief verification before advancing."
        )
    else:
        verdict_title = "VERIFIED — Authentic Candidate Dossier"
        recommendation = (
            "Clear to proceed. Document shows high structural integrity, genuine authorship patterns, "
            "and absence of ATS manipulation tactics."
        )

    summary = (
        f"Candidate received a composite Trust Score of {score:.1f}/100 ({label}). "
        + (" ".join(factors[:2]))
    )

    limitations = (
        "Forensic Note: Fraud signals reflect deterministic document structure anomalies (Unicode codepoints, "
        "color vectors, content streams). AI-content scoring is heuristic and probabilistic — treat elevated AI scores "
        "as an investigative signal rather than absolute proof of authorship."
    )

    return {
        "verdict_title": verdict_title,
        "recommendation": recommendation,
        "summary": summary,
        "key_factors": factors,
        "limitations_disclaimer": limitations,
    }
