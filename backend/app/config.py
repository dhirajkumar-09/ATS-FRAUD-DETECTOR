"""
Central configuration for ATS Fraud Detector backend.
All environment-sensitive values live here; import from this module
rather than reading os.environ scattered across the codebase.
"""
import os
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR: Path = Path(__file__).resolve().parent.parent
UPLOAD_DIR: Path = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

REPORTS_DIR: Path = BASE_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

# ── Database ────────────────────────────────────────────────────────────────
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{BASE_DIR / 'ats_fraud.db'}"
)

# ── PDF Extraction ──────────────────────────────────────────────────────────
# Maximum upload size in bytes (default 20 MB)
MAX_UPLOAD_BYTES: int = int(os.getenv("MAX_UPLOAD_BYTES", 20 * 1024 * 1024))

# ── Fraud detection thresholds (can be overridden via env vars) ─────────────
# RGB Euclidean-distance threshold below which text is considered "near-white"
NEAR_WHITE_THRESHOLD: int = int(os.getenv("NEAR_WHITE_THRESHOLD", 30))

# Font size (pt) at or below which text is treated as "hidden"
HIDDEN_FONT_SIZE_PT: float = float(os.getenv("HIDDEN_FONT_SIZE_PT", 1.0))

# ── AI detector ─────────────────────────────────────────────────────────────
AI_DETECTOR_MODEL: str = os.getenv("AI_DETECTOR_MODEL", "distilgpt2")

# ── Auth (Phase 5) ────────────────────────────────────────────────────────────
# IMPORTANT: set JWT_SECRET_KEY yourself in production — this default is only
# for local dev and is intentionally obvious so nobody mistakes it for secure.
JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "dev-only-change-me-before-deploying")
JWT_ALGORITHM: str = "HS256"
JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", 60 * 24))  # 24h

# ── App metadata ─────────────────────────────────────────────────────────────
APP_TITLE: str = "ATS Fraud Detector"
APP_VERSION: str = "0.1.0"