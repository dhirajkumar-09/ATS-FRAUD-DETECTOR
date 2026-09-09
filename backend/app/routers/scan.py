"""
routers/scan.py
===============
POST /scan   — upload a PDF, extract spans, persist, return scan_id + summary
GET  /scan/{scan_id} — retrieve full scan result with all stored spans
"""
from __future__ import annotations

import logging
import re
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import MAX_UPLOAD_BYTES, UPLOAD_DIR
from app.database import get_db
from app.models import FraudSignal, Resume, ScanResult, TextSpan
from app.services.ai_content_detector import compute_ai_score
from app.services.fraud_detectors import run_all_detectors
from app.services.match_scorer import compute_true_match_score, spans_to_clean_text
from app.services.pdf_extractor import extract_pdf

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scan", tags=["scan"])


# ─────────────────────────────────────────────────────────────────────────────
# POST /scan
# ─────────────────────────────────────────────────────────────────────────────

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_scan(
    file: UploadFile = File(..., description="Resume PDF to scan"),
    job_description: Optional[str] = Form(
        None,
        description="Job description text (optional). Enables True Match Score.",
    ),
    db: Session = Depends(get_db),
):
    """
    Upload a PDF resume. Runs:
      - Phase 1: PDF extraction (text spans, metadata)
      - Phase 2: Fraud detection (all 5 detectors)
      - Phase 3: AI content score + True Match Score (if job_description provided)

    Returns
    -------
    scan_id, sha256, page_count, fraud_summary, AI score, match score,
    and the first 10 spans for quick verification.
    """
    # ── 1. Validate content type ──────────────────────────────────────────
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are accepted.",
        )

    # ── 2. Save upload to disk (stream to temp file first to check size) ──
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp_path = Path(tmp.name)
        total_bytes = 0
        chunk_size = 64 * 1024   # 64 KB

        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > MAX_UPLOAD_BYTES:
                tmp_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File exceeds the {MAX_UPLOAD_BYTES // (1024*1024)} MB limit.",
                )
            tmp.write(chunk)

    # ── 3. Extract PDF ────────────────────────────────────────────────────
    try:
        extracted = extract_pdf(tmp_path)
    except Exception as exc:
        tmp_path.unlink(missing_ok=True)
        logger.exception("PDF extraction failed")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not parse PDF: {exc}",
        ) from exc

    # ── 4. Persist the file with sha256-based filename ────────────────────
    sha256 = extracted["sha256"]
    dest_path = UPLOAD_DIR / f"{sha256}.pdf"
    shutil.move(str(tmp_path), str(dest_path))

    # ── 5. Create / reuse Resume row (idempotent on same sha256) ──────────
    resume = db.query(Resume).filter_by(sha256=sha256).first()
    if resume is None:
        resume = Resume(
            filename=file.filename or "unknown.pdf",
            file_path=str(dest_path),
            sha256=sha256,
            page_count=extracted["page_count"],
        )
        db.add(resume)
        db.flush()   # get resume.id

    # ── 6. Create ScanResult ──────────────────────────────────────────────
    scan = ScanResult(
        resume_id=resume.id,
        status="processing",
    )
    db.add(scan)
    db.flush()

    # ── 7. Store spans per page ───────────────────────────────────────────
    pages_seen: dict[int, list[dict]] = {}
    for span in extracted["spans"]:
        pages_seen.setdefault(span["page"], []).append(span)

    for page_num, page_spans in pages_seen.items():
        ts = TextSpan(scan_result_id=scan.id, page=page_num)
        ts.set_spans(page_spans)
        db.add(ts)

    # ── 8. Run detectors (Phase 1: all return [] stubs) ───────────────────
    signals = run_all_detectors(
        spans=extracted["spans"],
        page_dims=extracted["page_dims"],
    )

    severity_counts = {"high": 0, "medium": 0, "low": 0}
    for sig in signals:
        bbox = sig.get("bbox")
        fs = FraudSignal(
            scan_result_id=scan.id,
            signal_type=sig["signal_type"],
            severity=sig["severity"],
            page=sig["page"],
            description=sig["description"],
            evidence_text=sig.get("evidence_text"),
            bbox_x0=bbox[0] if bbox else None,
            bbox_y0=bbox[1] if bbox else None,
            bbox_x1=bbox[2] if bbox else None,
            bbox_y1=bbox[3] if bbox else None,
        )
        db.add(fs)
        severity_counts[sig["severity"]] = severity_counts.get(sig["severity"], 0) + 1

    scan.total_signals = len(signals)
    scan.high_count    = severity_counts["high"]
    scan.medium_count  = severity_counts["medium"]
    scan.low_count     = severity_counts["low"]
    scan.status        = "done"

    db.commit()

    # ── 9. Phase 3 — build clean text (strip HIGH-severity fraudulent spans) ─
    high_signal_types = {
        "zero_width_chars", "hidden_text", "zero_or_tiny_font",
        "offpage_text", "homoglyph_substitution",
    }
    high_bboxes: list[tuple] = [
        sig["bbox"] for sig in signals
        if sig["severity"] == "high" and sig.get("bbox")
    ]

    def _is_clean(span: dict) -> bool:
        """True if this span is not covered by a HIGH-severity signal bbox."""
        sb = span.get("bbox")
        if sb is None:
            return True
        for hb in high_bboxes:
            # Overlap check: rectangles overlap if they share area
            if sb[0] < hb[2] and sb[2] > hb[0] and sb[1] < hb[3] and sb[3] > hb[1]:
                return False
        return True

    clean_spans = [s for s in extracted["spans"] if _is_clean(s)]
    all_spans   = extracted["spans"]
    clean_text  = " ".join(s.get("text", "") for s in clean_spans)
    total_words = len(re.findall(r"\b[a-zA-Z]+\b",
                                  " ".join(s.get("text","") for s in all_spans)))
    clean_words = len(re.findall(r"\b[a-zA-Z]+\b", clean_text))
    flagged_words = max(0, total_words - clean_words)

    # ── 10. AI content score ──────────────────────────────────────────────────
    ai_result = compute_ai_score(clean_text)
    scan.ai_content_score = ai_result["score"]

    # ── 11. True Match Score (only if JD provided) ───────────────────────────
    match_result: dict | None = None
    if job_description and job_description.strip():
        match_result = compute_true_match_score(clean_text, job_description)
        scan.true_match_score = match_result["score"]

    db.commit()

    # ── 12. Return summary ────────────────────────────────────────────────────
    response: dict = {
        "scan_id":    scan.id,
        "resume_id":  resume.id,
        "sha256":     sha256,
        "filename":   resume.filename,
        "page_count": extracted["page_count"],
        "span_count": len(extracted["spans"]),
        "page_dims":  extracted["page_dims"],
        "metadata":   extracted["metadata"],
        "fraud_summary": {
            "total":  scan.total_signals,
            "high":   scan.high_count,
            "medium": scan.medium_count,
            "low":    scan.low_count,
            "signals": [
                {
                    "signal_type": s["signal_type"],
                    "severity":    s["severity"],
                    "page":        s["page"],
                    "description": s["description"],
                    "evidence_text": s.get("evidence_text"),
                    "bbox": list(s["bbox"]) if s.get("bbox") else None,
                }
                for s in signals
            ],
        },
        "ai_content": {
            **ai_result,
            "clean_word_count":   clean_words,
            "flagged_word_count": flagged_words,
        },
        "true_match":  match_result,   # None if no JD provided
        "sample_spans": _serialise_spans(extracted["spans"][:10]),
    }
    return response



# ─────────────────────────────────────────────────────────────────────────────
# GET /scan/{scan_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{scan_id}")
def get_scan(scan_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a completed scan result including all stored spans and signals.
    """
    scan: ScanResult | None = db.query(ScanResult).filter_by(id=scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found.")

    all_spans: list[dict] = []
    for ts in scan.spans:
        all_spans.extend(ts.get_spans())

    signals_out = [
        {
            "id":          sig.id,
            "signal_type": sig.signal_type,
            "severity":    sig.severity,
            "page":        sig.page,
            "bbox":        sig.bbox,
            "description": sig.description,
            "evidence_text": sig.evidence_text,
        }
        for sig in scan.signals
    ]

    return {
        "scan_id":    scan.id,
        "resume_id":  scan.resume_id,
        "status":     scan.status,
        "scanned_at": scan.scanned_at.isoformat() if scan.scanned_at else None,
        "fraud_summary": {
            "total":  scan.total_signals,
            "high":   scan.high_count,
            "medium": scan.medium_count,
            "low":    scan.low_count,
        },
        "signals":     signals_out,
        "span_count":  len(all_spans),
        "spans":       _serialise_spans(all_spans),
        "true_match_score": scan.true_match_score,
        "ai_content_score": scan.ai_content_score,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _serialise_spans(spans: list[dict]) -> list[dict]:
    """Make span dicts fully JSON-serialisable (tuples → lists)."""
    out = []
    for s in spans:
        out.append({
            **s,
            "font_color": list(s["font_color"]) if s.get("font_color") else None,
            "bbox":       list(s["bbox"])       if s.get("bbox")       else None,
        })
    return out
