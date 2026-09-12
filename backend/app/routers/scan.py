"""
routers/scan.py
===============
POST /scan            — upload a PDF, extract spans, persist, return scan_id + summary + narrative
POST /scan/batch      — upload multiple PDF resumes, returning a ranked leaderboard
GET  /scan/{scan_id}  — retrieve full scan result with all stored spans and narrative
GET  /scan/{scan_id}/inspect — forensic side-by-side span inspector
GET  /scan/{scan_id}/badge.svg — shareable SVG trust badge
"""
from __future__ import annotations

import logging
import re
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import HIDDEN_FONT_SIZE_PT, MAX_UPLOAD_BYTES, NEAR_WHITE_THRESHOLD, PLAGIARISM_SIMILARITY_THRESHOLD, UPLOAD_DIR
from app.database import get_db
from app.models import FraudSignal, OrgSettings, Resume, ScanResult, TextSpan, User, DuplicateMatch
from app.services.ai_content_detector import compute_ai_score
from app.services.badge_generator import generate_trust_badge_svg
from app.services.forensic_narrative import generate_score_narrative
from app.services.fraud_detectors import run_all_detectors
from app.services.match_scorer import compute_true_match_score, compute_pairwise_similarity, spans_to_clean_text
from app.services.ocr_helper import ocr_page_text
from app.services.pdf_extractor import extract_pdf
from app.services.trust_score import compute_trust_score
from app.services.resume_validator import is_likely_resume

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scan", tags=["scan"])


# ─────────────────────────────────────────────────────────────────────────────
# Helper: core scan processing logic
# ─────────────────────────────────────────────────────────────────────────────

def _execute_pdf_scan(
    tmp_path: Path,
    original_filename: str,
    job_description: Optional[str],
    current_user: User,
    db: Session,
) -> dict:
    # ── Extract PDF ──────────────────────────────────────────────────────────
    try:
        extracted = extract_pdf(tmp_path)
    except Exception as exc:
        tmp_path.unlink(missing_ok=True)
        logger.exception("PDF extraction failed for %s", original_filename)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not parse PDF: {exc}",
        ) from exc

    # ── Resume validation ─────────────────────────────────────────────────────
    full_text = " ".join(s.get("text", "") for s in extracted.get("spans", []))
    is_resume, _val_details = is_likely_resume(full_text)
    if not is_resume:
        tmp_path.unlink(missing_ok=True)
        logger.info(
            "Rejected non-resume upload '%s' (validator: %s)",
            original_filename, _val_details,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This doesn't look like a resume.",
        )

    # ── Persist file with sha256 filename ────────────────────────────────────
    sha256 = extracted["sha256"]
    dest_path = UPLOAD_DIR / f"{sha256}.pdf"
    if not dest_path.exists():
        shutil.move(str(tmp_path), str(dest_path))
    else:
        tmp_path.unlink(missing_ok=True)

    # ── Create / reuse Resume row ────────────────────────────────────────────
    resume = (
        db.query(Resume)
        .filter_by(sha256=sha256, owner_id=current_user.id)
        .first()
    )
    if resume is None:
        resume = Resume(
            owner_id=current_user.id,
            filename=original_filename,
            file_path=str(dest_path),
            sha256=sha256,
            page_count=extracted["page_count"],
        )
        db.add(resume)
        db.flush()

    # ── Create or reuse ScanResult (idempotent / handles rescan) ─────────────
    if resume.scan_result:
        scan = resume.scan_result
        scan.status = "processing"
        db.query(FraudSignal).filter_by(scan_result_id=scan.id).delete()
        db.query(TextSpan).filter_by(scan_result_id=scan.id).delete()
        db.flush()
    else:
        scan = ScanResult(
            resume_id=resume.id,
            status="processing",
        )
        db.add(scan)
        db.flush()


    # ── Store spans per page ─────────────────────────────────────────────────
    pages_seen: dict[int, list[dict]] = {}
    for span in extracted["spans"]:
        pages_seen.setdefault(span["page"], []).append(span)

    for page_num, page_spans in pages_seen.items():
        ts = TextSpan(scan_result_id=scan.id, page=page_num)
        ts.set_spans(page_spans)
        db.add(ts)

    # ── Run detectors with org overrides ─────────────────────────────────────
    org_settings = (
        db.query(OrgSettings)
        .filter_by(organization=current_user.organization)
        .first()
    )
    near_white = (
        org_settings.near_white_threshold
        if org_settings and org_settings.near_white_threshold is not None
        else NEAR_WHITE_THRESHOLD
    )
    hidden_size = (
        org_settings.hidden_font_size_pt
        if org_settings and org_settings.hidden_font_size_pt is not None
        else HIDDEN_FONT_SIZE_PT
    )
    signals = run_all_detectors(
        spans=extracted["spans"],
        page_dims=extracted["page_dims"],
        hidden_text_threshold=near_white,
        hidden_size_threshold=hidden_size,
        metadata=extracted.get("metadata"),
        word_order=extracted.get("word_order"),
        image_pages=extracted.get("image_pages"),
        font_glyph_anomalies=extracted.get("font_glyph_anomalies"),
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

    # ── Build clean text (strip HIGH-severity manipulation spans) ─────────────
    high_bboxes: list[tuple] = [
        sig["bbox"] for sig in signals
        if sig["severity"] == "high" and sig.get("bbox")
    ]

    def _is_clean(span: dict) -> bool:
        sb = span.get("bbox")
        if sb is None:
            return True
        for hb in high_bboxes:
            if sb[0] < hb[2] and sb[2] > hb[0] and sb[1] < hb[3] and sb[3] > hb[1]:
                return False
        return True

    clean_spans = [s for s in extracted["spans"] if _is_clean(s)]
    all_spans   = extracted["spans"]
    
    # Reconstruct text grouping by block_no to preserve paragraphs
    paragraphs = []
    current_block = []
    current_block_no = None
    for s in clean_spans:
        b_no = s.get("block_no")
        if b_no != current_block_no:
            if current_block:
                paragraphs.append(" ".join(current_block))
            current_block = []
            current_block_no = b_no
        current_block.append(s.get("text", ""))
    if current_block:
        paragraphs.append(" ".join(current_block))
    
    clean_text = "\n\n".join(paragraphs)
    
    total_words = len(re.findall(r"\b[a-zA-Z]+\b", " ".join(s.get("text", "") for s in all_spans)))
    clean_words = len(re.findall(r"\b[a-zA-Z]+\b", clean_text))
    flagged_words = max(0, total_words - clean_words)

    # ── AI content score ─────────────────────────────────────────────────────
    from app.services.ai_content_detector import compute_ai_score, compute_paragraph_ai_scores
    ai_result = compute_ai_score(clean_text)
    ai_result["paragraph_ai_breakdown"] = compute_paragraph_ai_scores(clean_spans)
    scan.ai_content_score = ai_result["score"]

    # ── True Match Score ─────────────────────────────────────────────────────
    match_result: dict | None = None
    if job_description and job_description.strip():
        match_result = compute_true_match_score(clean_text, job_description)
        scan.true_match_score = match_result["score"]

    # ── OCR recovery on suspected image-only pages ───────────────────────────
    image_pages = extracted.get("image_pages", [])
    ocr_results: list[dict] = []
    for page_stat in image_pages:
        if not page_stat.get("is_suspected_image_only"):
            continue
        ocr = ocr_page_text(dest_path, page_stat["page"])
        ocr_results.append({"page": page_stat["page"], **ocr})

    # ── Trust Score badge ────────────────────────────────────────────────────
    fraud_summary_for_score = {
        "total": scan.total_signals,
        "high": scan.high_count,
        "medium": scan.medium_count,
        "low": scan.low_count,
        "signals": signals,
    }
    trust = compute_trust_score(
        fraud_summary=fraud_summary_for_score,
        ai_content_score=scan.ai_content_score,
        true_match_score=scan.true_match_score,
    )
    scan.trust_score = trust["score"]
    scan.trust_label = trust["label"]
    db.commit()

    # ── Explainability Narrative ─────────────────────────────────────────────
    narrative = generate_score_narrative(
        fraud_summary=fraud_summary_for_score,
        ai_content=ai_result,
        true_match=match_result,
        trust_score=trust,
    )

    return {
        "scan_id":    scan.id,
        "share_token": scan.share_token,
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
        "true_match":  match_result,
        "sample_spans": _serialise_spans(extracted["spans"][:10]),
        "trust_score":  trust,
        "narrative":    narrative,
        "word_order":   extracted.get("word_order", []),
        "image_pages":  image_pages,
        "ocr_results":  ocr_results,
        "clean_text":   clean_text,
    }


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
    current_user: User = Depends(get_current_user),
):
    """
    Upload a PDF resume. Runs extraction, fraud detection, AI content analysis,
    job matching, trust scoring, and explainability narrative generation.
    """
    filename = file.filename or "unknown.pdf"
    is_pdf = filename.lower().endswith(".pdf") or file.content_type in ("application/pdf", "application/octet-stream")
    if not is_pdf:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are accepted.",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp_path = Path(tmp.name)
        total_bytes = 0
        chunk_size = 64 * 1024

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

    if total_bytes == 0:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded PDF file is empty (0 bytes).",
        )

    return _execute_pdf_scan(
        tmp_path=tmp_path,
        original_filename=filename,
        job_description=job_description,
        current_user=current_user,
        db=db,
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /scan/batch  (Feature: Multi-file leaderboard)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/batch", status_code=status.HTTP_201_CREATED)
async def create_batch_scan(
    files: list[UploadFile] = File(..., description="Multiple resume PDFs to scan"),
    job_description: Optional[str] = Form(
        None,
        description="Job description text for ranking all candidates.",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload multiple resume PDFs simultaneously.
    Returns a sortable leaderboard of candidates ranked by Trust Score.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided in batch upload.")

    results: list[dict] = []
    errors: list[dict] = []
    batch_texts: dict[int, str] = {}

    for file in files:
        fname = file.filename or "unknown.pdf"
        if not (fname.lower().endswith(".pdf") or file.content_type in ("application/pdf", "application/octet-stream")):
            errors.append({"filename": fname, "error": "Not a PDF file"})
            continue

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp_path = Path(tmp.name)
            total_bytes = 0
            while True:
                chunk = await file.read(64 * 1024)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > MAX_UPLOAD_BYTES:
                    break
                tmp.write(chunk)

        if total_bytes == 0 or total_bytes > MAX_UPLOAD_BYTES:
            tmp_path.unlink(missing_ok=True)
            err_msg = "Empty file (0 bytes)" if total_bytes == 0 else "File exceeds size limit"
            errors.append({"filename": fname, "error": err_msg})
            continue

        try:
            scan_out = _execute_pdf_scan(
                tmp_path=tmp_path,
                original_filename=fname,
                job_description=job_description,
                current_user=current_user,
                db=db,
            )
            batch_texts[scan_out["scan_id"]] = scan_out["clean_text"]
            results.append({
                "scan_id": scan_out["scan_id"],
                "filename": scan_out["filename"],
                "sha256": scan_out["sha256"],
                "page_count": scan_out["page_count"],
                "trust_score": scan_out["trust_score"]["score"],
                "trust_label": scan_out["trust_score"]["label"],
                "trust_emoji": scan_out["trust_score"]["emoji"],
                "high_fraud_signals": scan_out["fraud_summary"]["high"],
                "total_fraud_signals": scan_out["fraud_summary"]["total"],
                "ai_content_score": scan_out["ai_content"]["score"],
                "true_match_score": scan_out["true_match"]["score"] if scan_out.get("true_match") else None,
                "summary": scan_out["narrative"]["summary"],
            })
        except Exception as exc:
            logger.warning("Batch scan failed for %s: %s", fname, exc)
            errors.append({"filename": fname, "error": str(exc)})

    # ── Plagiarism / Duplicate Template Fingerprinting ──────────────────────
    duplicate_matches_out = []
    if len(batch_texts) > 1:
        matches = compute_pairwise_similarity(batch_texts, threshold=PLAGIARISM_SIMILARITY_THRESHOLD)
        
        affected_scan_ids = set()
        for match in matches:
            id_a = match["id_a"]
            id_b = match["id_b"]
            
            # Persist to DB
            dup_match = DuplicateMatch(
                scan_result_id_a=id_a,
                scan_result_id_b=id_b,
                similarity_score=match["similarity_score"],
                organization=current_user.organization
            )
            db.add(dup_match)
            
            # Create fraud signals for both
            for target_id in (id_a, id_b):
                other_id = id_b if target_id == id_a else id_a
                # Find the filename of the other candidate for a better description
                other_filename = next((r["filename"] for r in results if r["scan_id"] == other_id), "another candidate")
                
                fs = FraudSignal(
                    scan_result_id=target_id,
                    signal_type="duplicate_template",
                    severity="high",
                    page=1,
                    description=f"Near-duplicate template or copy-pasted content detected. {match['similarity_score']}% similarity with {other_filename}.",
                    evidence_text=" | ".join(match["shared_phrases"])
                )
                db.add(fs)
                affected_scan_ids.add(target_id)
                
            duplicate_matches_out.append({
                "scan_id_a": id_a,
                "scan_id_b": id_b,
                "similarity_score": match["similarity_score"],
                "shared_phrases": match["shared_phrases"]
            })
            
        if matches:
            db.commit()
            
            # Re-compute trust score for affected scans
            for s_id in affected_scan_ids:
                scan = db.query(ScanResult).filter_by(id=s_id).first()
                if not scan:
                    continue
                
                scan.total_signals += 1
                scan.high_count += 1
                
                fraud_summary_for_score = {
                    "total": scan.total_signals,
                    "high": scan.high_count,
                    "medium": scan.medium_count,
                    "low": scan.low_count,
                    "signals": []
                }
                trust = compute_trust_score(
                    fraud_summary=fraud_summary_for_score,
                    ai_content_score=scan.ai_content_score,
                    true_match_score=scan.true_match_score
                )
                scan.trust_score = trust["score"]
                scan.trust_label = trust["label"]
                
                for r in results:
                    if r["scan_id"] == s_id:
                        r["trust_score"] = trust["score"]
                        r["trust_label"] = trust["label"]
                        r["trust_emoji"] = trust["emoji"]
                        r["high_fraud_signals"] = scan.high_count
                        r["total_fraud_signals"] = scan.total_signals
                        break
            db.commit()

    # Sort leaderboard by Trust Score descending, then match score descending
    results.sort(key=lambda r: (r["trust_score"], r.get("true_match_score") or 0.0), reverse=True)

    return {
        "total_submitted": len(files),
        "total_processed": len(results),
        "total_failed": len(errors),
        "leaderboard": results,
        "errors": errors,
        "duplicate_matches": duplicate_matches_out,
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /scan/{scan_id}
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{scan_id}")
def get_scan(
    scan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve a completed scan result including all stored spans, signals, and narrative.
    """
    scan: ScanResult | None = db.query(ScanResult).filter_by(id=scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found.")
    if scan.resume.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="This scan belongs to another account.")

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

    fraud_summary = {
        "total":  scan.total_signals,
        "high":   scan.high_count,
        "medium": scan.medium_count,
        "low":    scan.low_count,
        "signals": signals_out,
    }

    trust_dict = {
        "score": scan.trust_score,
        "label": scan.trust_label,
        "emoji": {"Verified": "🟢", "Caution": "🟡", "High Risk": "🔴"}.get(scan.trust_label, ""),
    }

    high_bboxes = [sig.bbox for sig in scan.signals if sig.severity == "high" and sig.bbox]
    def _is_clean(span: dict) -> bool:
        sb = span.get("bbox")
        if sb is None: return True
        for hb in high_bboxes:
            if sb[0] < hb[2] and sb[2] > hb[0] and sb[1] < hb[3] and sb[3] > hb[1]:
                return False
        return True
    
    clean_spans = [s for s in all_spans if _is_clean(s)]
    from app.services.ai_content_detector import compute_paragraph_ai_scores
    breakdown = compute_paragraph_ai_scores(clean_spans)
    
    ai_content = {
        "score": scan.ai_content_score,
        "paragraph_ai_breakdown": breakdown
    }

    narrative = generate_score_narrative(
        fraud_summary=fraud_summary,
        ai_content=ai_content,
        true_match={"score": scan.true_match_score} if scan.true_match_score is not None else None,
        trust_score=trust_dict,
    )

    return {
        "scan_id":    scan.id,
        "resume_id":  scan.resume_id,
        "filename":   scan.resume.filename,
        "status":     scan.status,
        "scanned_at": scan.scanned_at.isoformat() if scan.scanned_at else None,
        "fraud_summary": fraud_summary,
        "signals":     signals_out,
        "ai_content_score": scan.ai_content_score,
        "ai_content":  ai_content,
        "true_match_score": scan.true_match_score,
        "trust_score": scan.trust_score,
        "trust_label": scan.trust_label,
        "span_count":  len(all_spans),
        "spans":       _serialise_spans(all_spans),
        "narrative":   narrative,
        "share_token": scan.share_token,
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /scan/{scan_id}/inspect  (Feature: Side-by-side span inspector)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{scan_id}/inspect")
def inspect_scan(
    scan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns flagged spans mapped directly to their matching fraud signals
    to drive the interactive side-by-side before/after inspector.
    """
    scan: ScanResult | None = db.query(ScanResult).filter_by(id=scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found.")
    if scan.resume.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="This scan belongs to another account.")

    all_spans: list[dict] = []
    for ts in scan.spans:
        all_spans.extend(ts.get_spans())

    signals = [
        {
            "id": sig.id,
            "signal_type": sig.signal_type,
            "severity": sig.severity,
            "page": sig.page,
            "bbox": sig.bbox,
            "description": sig.description,
            "evidence_text": sig.evidence_text,
        }
        for sig in scan.signals
    ]

    flagged_spans = []
    clean_spans = []

    for span in all_spans:
        sb = span.get("bbox")
        matching = []
        if sb:
            for sig in signals:
                if sig["page"] == span.get("page") and sig.get("bbox"):
                    hb = sig["bbox"]
                    if hb and all(v is not None for v in hb):
                        if sb[0] < hb[2] and sb[2] > hb[0] and sb[1] < hb[3] and sb[3] > hb[1]:
                            matching.append(sig)
        if matching:
            flagged_spans.append({**span, "matching_signals": matching})
        else:
            clean_spans.append(span)

    return {
        "scan_id": scan.id,
        "filename": scan.resume.filename,
        "page_count": scan.resume.page_count,
        "total_spans": len(all_spans),
        "flagged_span_count": len(flagged_spans),
        "clean_span_count": len(clean_spans),
        "signals": signals,
        "flagged_spans": _serialise_spans(flagged_spans),
        "sample_clean_spans": _serialise_spans(clean_spans[:30]),
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /scan/{scan_id}/badge.svg  (Feature: Shareable SVG Trust Badge)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{scan_id}/badge.svg")
def get_scan_badge(
    scan_id: int,
    db: Session = Depends(get_db),
):
    """
    Generate and serve a crisp SVG Trust Badge for embedding in recruiter portfolios.
    This endpoint is public so the SVG can be rendered anywhere via an <img> tag.
    """
    scan: ScanResult | None = db.query(ScanResult).filter_by(id=scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found.")

    svg_content = generate_trust_badge_svg(
        score=scan.trust_score or 0.0,
        label=scan.trust_label or "Caution",
    )
    return Response(
        content=svg_content,
        media_type="image/svg+xml",
        headers={"Cache-Control": "max-age=3600"},
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /scan/{scan_id}/share-link
# ─────────────────────────────────────────────────────────────────────────────
import secrets
from datetime import datetime, timezone

@router.post("/{scan_id}/share-link")
def create_share_link(
    scan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scan: ScanResult | None = db.query(ScanResult).filter_by(id=scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found.")
    if scan.resume.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized.")

    org_settings = db.query(OrgSettings).filter_by(organization=current_user.organization).first()
    if not org_settings or not org_settings.candidate_transparency_enabled:
        raise HTTPException(
            status_code=403, 
            detail="Candidate Transparency Mode is not enabled for your organization. Please enable it in Settings first."
        )

    if not scan.share_token:
        scan.share_token = secrets.token_urlsafe(32)
        scan.share_token_created_at = datetime.now(timezone.utc)
        db.commit()

    # We return just the token string, frontend will construct the URL
    return {"share_token": scan.share_token}


# ─────────────────────────────────────────────────────────────────────────────
# DELETE /scan/{scan_id}/share-link
# ─────────────────────────────────────────────────────────────────────────────
@router.delete("/{scan_id}/share-link")
def revoke_share_link(
    scan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scan: ScanResult | None = db.query(ScanResult).filter_by(id=scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found.")
    if scan.resume.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized.")

    scan.share_token = None
    scan.share_token_created_at = None
    db.commit()
    return {"status": "revoked"}


# ─────────────────────────────────────────────────────────────────────────────
# GET /scan/public/{share_token}
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/public/{share_token}")
def get_public_scan_result(share_token: str, db: Session = Depends(get_db)):
    """
    Candidate-facing public endpoint. 
    NO AUTHENTICATION REQUIRED (rate limiting TODO).
    Returns a highly redacted view: no bboxes, no evidence strings, no raw spans.
    """
    scan: ScanResult | None = db.query(ScanResult).filter_by(share_token=share_token).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Invalid or expired share link.")

    fraud_summary = {
        "total": scan.total_signals,
        "high": scan.high_count,
        "medium": scan.medium_count,
        "low": scan.low_count,
    }

    trust_dict = {
        "score": scan.trust_score,
        "label": scan.trust_label,
        "emoji": {"Verified": "🟢", "Caution": "🟡", "High Risk": "🔴"}.get(scan.trust_label, ""),
    }

    ai_content = {
        "score": scan.ai_content_score
    }

    # Generate the standard plain-language narrative
    narrative = generate_score_narrative(
        fraud_summary=fraud_summary,
        ai_content=ai_content,
        true_match={"score": scan.true_match_score} if scan.true_match_score is not None else None,
        trust_score=trust_dict,
    )

    return {
        "filename": scan.resume.filename,
        "scanned_at": scan.scanned_at.isoformat() if scan.scanned_at else None,
        "trust_score": scan.trust_score,
        "trust_label": scan.trust_label,
        "ai_content_score": scan.ai_content_score,
        "true_match_score": scan.true_match_score,
        "narrative": {
            "summary": narrative.get("summary", ""),
            "key_factors": narrative.get("key_factors", []),
            "recommendation": narrative.get("recommendation", ""),
            "limitations_disclaimer": "This is an automated forensic summary shared by the hiring organization. Contact them directly with questions."
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _serialise_spans(spans: list[dict]) -> list[dict]:
    """Make span dicts fully JSON-serialisable (tuples → lists)."""
    out = []
    for s in spans:
        item = {**s}
        if item.get("font_color") is not None:
            item["font_color"] = list(item["font_color"])
        if item.get("bbox") is not None:
            item["bbox"] = list(item["bbox"])
        out.append(item)
    return out