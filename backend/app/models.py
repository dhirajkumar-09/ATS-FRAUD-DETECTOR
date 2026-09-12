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
    Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
)
from sqlalchemy.orm import relationship

from app.database import Base


# ── helpers ─────────────────────────────────────────────────────────────────
def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── User ─────────────────────────────────────────────────────────────────────
class User(Base):
    """A recruiter account. Owns resumes/scans and belongs to an organization."""
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    email           = Column(String(320), nullable=False, unique=True, index=True)
    hashed_password = Column(String(128), nullable=False)
    full_name       = Column(String(256), nullable=True)
    organization    = Column(String(256), nullable=False, index=True)
    is_admin        = Column(Boolean, default=False)  # can edit org-level thresholds
    created_at      = Column(DateTime, default=_utcnow)

    resumes = relationship("Resume", back_populates="owner")


# ── OrgSettings ───────────────────────────────────────────────────────────────
class OrgSettings(Base):
    """
    Per-organization overrides for fraud-detection thresholds.
    One row per `organization` string; falls back to app.config defaults
    when no row exists yet.
    """
    __tablename__ = "org_settings"

    id                  = Column(Integer, primary_key=True, index=True)
    organization        = Column(String(256), nullable=False, unique=True, index=True)
    near_white_threshold = Column(Integer, nullable=True)   # None → use config default
    hidden_font_size_pt  = Column(Float, nullable=True)     # None → use config default
    candidate_transparency_enabled = Column(Boolean, default=False)
    updated_at          = Column(DateTime, default=_utcnow, onupdate=_utcnow)


# ── Resume ───────────────────────────────────────────────────────────────────
class Resume(Base):
    __tablename__ = "resumes"

    id          = Column(Integer, primary_key=True, index=True)
    owner_id    = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    filename    = Column(String(512), nullable=False)
    file_path   = Column(String(1024), nullable=False)
    sha256      = Column(String(64), nullable=False, index=True)
    uploaded_at = Column(DateTime, default=_utcnow)
    page_count  = Column(Integer, default=0)

    owner       = relationship("User", back_populates="resumes")
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

    # Phase 5 — composite Trust Score badge
    trust_score  = Column(Float, nullable=True)   # 0-100
    trust_label  = Column(String(32), nullable=True)   # Verified | Caution | High Risk

    # Share link fields
    share_token  = Column(String(64), unique=True, nullable=True, index=True)
    share_token_created_at = Column(DateTime, nullable=True)

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


# ── DuplicateMatch ─────────────────────────────────────────────────────────────
class DuplicateMatch(Base):
    """Stores near-duplicate template reuse matches across resumes."""
    __tablename__ = "duplicate_matches"

    id               = Column(Integer, primary_key=True, index=True)
    scan_result_id_a = Column(Integer, ForeignKey("scan_results.id"), nullable=False, index=True)
    scan_result_id_b = Column(Integer, ForeignKey("scan_results.id"), nullable=False, index=True)
    similarity_score = Column(Float, nullable=False)
    organization     = Column(String(256), nullable=False, index=True)
    detected_at      = Column(DateTime, default=_utcnow)

    scan_a = relationship("ScanResult", foreign_keys=[scan_result_id_a])
    scan_b = relationship("ScanResult", foreign_keys=[scan_result_id_b])


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