"""
resume_validator.py
====================
Rejects PDFs that clearly aren't resumes before running fraud detection.
"""
from __future__ import annotations
import re
from typing import Any

_SECTION_KEYWORDS: tuple[str, ...] = (
    "experience", "work experience", "employment", "employment history",
    "education", "skills", "technical skills", "core competencies",
    "projects", "certification", "certifications", "objective",
    "summary", "profile", "achievements", "publications", "internship",
    "career", "qualifications", "responsibilities", "curriculum vitae",
    "resume", "references", "languages", "awards", "volunteer",
)

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"(\+?\d[\d\-\s()]{8,}\d)")

MIN_SCORE = 2          # must match ≥2 resume indicators (keywords + contact signals)
MIN_WORDS_TO_JUDGE = 15


def score_resume_likelihood(text: str) -> dict[str, Any]:
    lowered = text.lower()
    matched = [kw for kw in _SECTION_KEYWORDS if kw in lowered]
    has_email = bool(_EMAIL_RE.search(text))
    has_phone = bool(_PHONE_RE.search(text))
    word_count = len(re.findall(r"\b[a-zA-Z]+\b", text))

    score = min(len(matched), 4)
    score += 1 if has_email else 0
    score += 1 if has_phone else 0

    return {
        "score": score, "matched_keywords": matched,
        "has_email": has_email, "has_phone": has_phone,
        "word_count": word_count,
    }


def is_likely_resume(text: str) -> tuple[bool, dict[str, Any]]:
    details = score_resume_likelihood(text)
    if details["word_count"] < MIN_WORDS_TO_JUDGE:
        details["reason"] = "insufficient_text_defer_to_ocr"
        return True, details
    passed = details["score"] >= MIN_SCORE
    details["reason"] = "heuristic_score_pass" if passed else "heuristic_score_fail"
    return passed, details