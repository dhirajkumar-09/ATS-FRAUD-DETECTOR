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
            
        paragraphs = (ai_content or {}).get("paragraph_ai_breakdown", [])
        if paragraphs:
            most_suspicious = max(paragraphs, key=lambda p: p.get("ai_score", 0), default=None)
            if most_suspicious and most_suspicious.get("ai_score", 0) >= 70:
                snippet = most_suspicious.get("text_snippet", "")[:40].replace('\n', ' ').strip()
                factors.append(
                    f"A paragraph on page {most_suspicious.get('page', 1)} starting with '{snippet}...' "
                    f"scores {most_suspicious['ai_score']:.1f}% likely AI-generated."
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

    forensic_risk = trust_score.get("forensic_risk_score")
    risk_text = f" Forensic Risk Score: {forensic_risk}/100." if forensic_risk is not None else ""

    summary = (
        f"Trust Score: {score:.1f}/100 ({label}).{risk_text} "
        "Score represents detected document-risk indicators according to our forensic scoring model. "
        + (" ".join(factors[:2]))
    )
    
    font_sub_flag = any(s.get("signal_type") == "font_substitution" for s in signals)
    if font_sub_flag:
        factors.insert(0, "This resume uses a manipulated font mapping to hide keywords from human readers while exposing them to ATS text extraction — a deliberate deception technique.")

    limitations = (
        "Forensic Note: Fraud signals reflect deterministic document structure anomalies (Unicode codepoints, "
        "color vectors, content streams). AI-content detection is probabilistic and should not be used as the sole "
        "basis for rejecting a candidate."
    )
    if font_sub_flag:
        limitations += " Additionally, Font Substitution detection currently uses a heuristic based on high ATS keyword density in subset fonts; true CMap validation is a best-effort approximation."

    return {
        "verdict_title": verdict_title,
        "recommendation": recommendation,
        "summary": summary,
        "key_factors": factors,
        "limitations_disclaimer": limitations,
    }
