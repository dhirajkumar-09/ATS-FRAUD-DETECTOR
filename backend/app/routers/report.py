"""
routers/report.py — Phase 4
==============================
GET /report/{scan_id}/pdf — build (or reuse a cached) forensic evidence PDF
and return it as a download.
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import REPORTS_DIR
from app.database import get_db
from app.models import ScanResult, User
from app.services.forensic_report import generate_forensic_report

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/report", tags=["report"])


@router.get("/{scan_id}/pdf")
def download_report(
    scan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Download the forensic evidence PDF for a completed scan.

    If the report was already generated for this scan, the cached file on
    disk is returned immediately. Otherwise it's built on the fly from the
    scan's stored signals + the original PDF, then cached for next time.
    """
    scan: ScanResult | None = db.query(ScanResult).filter_by(id=scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found.")
    if scan.resume.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="This scan belongs to another account.")

    if scan.status != "done":
        raise HTTPException(
            status_code=409,
            detail=f"Scan {scan_id} is not finished yet (status: {scan.status}).",
        )

    resume = scan.resume
    original_pdf_path = Path(resume.file_path)
    if not original_pdf_path.exists():
        raise HTTPException(
            status_code=410,
            detail="Original PDF for this scan is no longer available on disk.",
        )

    report_path = REPORTS_DIR / f"scan_{scan_id}_forensic_report.pdf"

    # Reuse a cached report if one already exists for this scan
    if not report_path.exists():
        scan_result = _build_scan_result_dict(scan, resume)
        try:
            generate_forensic_report(
                scan_result=scan_result,
                original_pdf_path=original_pdf_path,
                output_path=report_path,
            )
        except Exception as exc:
            logger.exception("Forensic report generation failed for scan %s", scan_id)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate forensic report: {exc}",
            ) from exc

    return FileResponse(
        path=report_path,
        media_type="application/pdf",
        filename=f"ats_fraud_report_scan_{scan_id}.pdf",
    )


def _build_scan_result_dict(scan: ScanResult, resume) -> dict:
    """Shape ORM rows into the dict forensic_report.generate_forensic_report expects."""
    signals = [
        {
            "signal_type": sig.signal_type,
            "severity": sig.severity,
            "page": sig.page,
            "description": sig.description,
            "evidence_text": sig.evidence_text,
            "bbox": sig.bbox if all(v is not None for v in sig.bbox) else None,
        }
        for sig in scan.signals
    ]

    return {
        "scan_id": scan.id,
        "filename": resume.filename,
        "sha256": resume.sha256,
        "page_count": resume.page_count,
        "scanned_at": scan.scanned_at.isoformat() if scan.scanned_at else None,
        "fraud_summary": {
            "total": scan.total_signals,
            "high": scan.high_count,
            "medium": scan.medium_count,
            "low": scan.low_count,
            "signals": signals,
        },
        "ai_content_score": scan.ai_content_score,
        "true_match_score": scan.true_match_score,
    }