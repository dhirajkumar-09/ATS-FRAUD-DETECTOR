"""
SQLAlchemy ORM models.

Tables
------
Resume        – one row per uploaded PDF
ScanResult    – one row per completed scan run (linked 1-to-1 with Resume)
FraudSignal   – one row per detected fraud event (linked many-to-1 with ScanResult)
TextSpan      – raw extracted spans stored as JSON for debugging / re-runs
"""
import json
from datetime import datetime, timezone

from sqlalchemy import (
    Column, DateTime, Float, ForeignKey, Integer, String, Text
)
from sqlalchemy.orm import relationship

from app.database import Base


# ── helpers ─────────────────────────────────────────────────────────────────
def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Resume ───────────────────────────────────────────────────────────────────
class Resume(Base):
    __tablename__ = "resumes"

    id          = Column(Integer, primary_key=True, index=True)
    filename    = Column(String(512), nullable=False)
    file_path   = Column(String(1024), nullable=False)
    sha256      = Column(String(64), nullable=False, index=True)
    uploaded_at = Column(DateTime, default=_utcnow)
    page_count  = Column(Integer, default=0)

    scan_result = relationship("ScanResult", back_populates="resume", uselist=False)


# ── ScanResult ────────────────────────────────────────────────────────────────
class ScanResult(Base):
    __tablename__ = "scan_results"

    id             = Column(Integer, primary_key=True, index=True)
    resume_id      = Column(Integer, ForeignKey("resumes.id"), nullable=False, unique=True)
    scanned_at     = Column(DateTime, default=_utcnow)
    status         = Column(String(32), default="pending")   # pending | done | error
    error_message  = Column(Text, nullable=True)

    # Aggregate counts (denormalised for quick API responses)
    total_signals  = Column(Integer, default=0)
    high_count     = Column(Integer, default=0)
    medium_count   = Column(Integer, default=0)
    low_count      = Column(Integer, default=0)

    # Scores set in later phases
    true_match_score  = Column(Float, nullable=True)
    ai_content_score  = Column(Float, nullable=True)

    resume  = relationship("Resume", back_populates="scan_result")
    signals = relationship("FraudSignal", back_populates="scan_result",
                           cascade="all, delete-orphan")
    spans   = relationship("TextSpan", back_populates="scan_result",
                           cascade="all, delete-orphan")


# ── FraudSignal ────────────────────────────────────────────────────────────────
class FraudSignal(Base):
    """One detected anomaly: type, where on the page, how severe."""
    __tablename__ = "fraud_signals"

    id             = Column(Integer, primary_key=True, index=True)
    scan_result_id = Column(Integer, ForeignKey("scan_results.id"), nullable=False)

    # Detection metadata
    signal_type  = Column(String(64),  nullable=False)   # e.g. "zero_width_chars"
    severity     = Column(String(16),  nullable=False)   # high | medium | low
    page         = Column(Integer,     nullable=False)   # 1-indexed
    description  = Column(Text,        nullable=False)

    # Bounding box as individual floats (pixels, PDF-space)
    bbox_x0 = Column(Float, nullable=True)
    bbox_y0 = Column(Float, nullable=True)
    bbox_x1 = Column(Float, nullable=True)
    bbox_y1 = Column(Float, nullable=True)

    # Raw snippet of offending text (truncated to 500 chars)
    evidence_text = Column(Text, nullable=True)

    scan_result = relationship("ScanResult", back_populates="signals")

    @property
    def bbox(self):
        return (self.bbox_x0, self.bbox_y0, self.bbox_x1, self.bbox_y1)


# ── TextSpan ─────────────────────────────────────────────────────────────────
class TextSpan(Base):
    """
    Stores raw extracted text spans as JSON blobs.
    Each row = one PDF page's worth of spans to avoid huge single rows.
    """
    __tablename__ = "text_spans"

    id             = Column(Integer, primary_key=True, index=True)
    scan_result_id = Column(Integer, ForeignKey("scan_results.id"), nullable=False)
    page           = Column(Integer, nullable=False)   # 1-indexed
    spans_json     = Column(Text, nullable=False)      # JSON array of span dicts

    scan_result = relationship("ScanResult", back_populates="spans")

    def set_spans(self, spans: list[dict]) -> None:
        self.spans_json = json.dumps(spans)

    def get_spans(self) -> list[dict]:
        return json.loads(self.spans_json)
