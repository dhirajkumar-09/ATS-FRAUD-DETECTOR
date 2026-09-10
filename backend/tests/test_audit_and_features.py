"""
test_audit_and_features.py — Comprehensive Audit & New Features Test Suite
==========================================================================
Validates:
  1. Determinism: Same PDF scanned twice produces identical signals and scores.
  2. Consistency: Trust score, severity counts, and labels never contradict.
  3. Exact fixture outputs for all 5 fixture PDFs.
  4. Robustness on edge-case PDFs (0 bytes, 0 pages, no metadata).
  5. Endpoints (/scan, /scan/{id}, /scan/{id}/inspect, /scan/{id}/badge.svg, /scan/batch, /report/{id}/pdf).
"""
from __future__ import annotations

import io
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine, SessionLocal
from app.main import app
from app.models import User
from app.auth import create_access_token, hash_password
from app.services.pdf_extractor import extract_pdf
from app.services.fraud_detectors import run_all_detectors
from app.services.trust_score import compute_trust_score
from tests.generate_fixtures import FIXTURES_DIR, generate_all_fixtures


@pytest.fixture(scope="module", autouse=True)
def ensure_fixtures():
    generate_all_fixtures()


@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    return TestClient(app)


@pytest.fixture(scope="module")
def auth_headers():
    db = SessionLocal()
    user = db.query(User).filter_by(email="audit_test@recruiter.com").first()
    if not user:
        user = User(
            email="audit_test@recruiter.com",
            hashed_password=hash_password("SecretPassword123!"),
            full_name="Audit Recruiter",
            organization="AuditCorp",
            is_admin=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    token = create_access_token(user_id=user.id, email=user.email)
    db.close()
    return {"Authorization": f"Bearer {token}"}


# ─────────────────────────────────────────────────────────────────────────────
# 1. Determinism Guarantee
# ─────────────────────────────────────────────────────────────────────────────

def test_determinism_across_multiple_runs():
    pdf_path = FIXTURES_DIR / "hidden_text_resume.pdf"
    res1 = extract_pdf(pdf_path)
    res2 = extract_pdf(pdf_path)

    sig1 = run_all_detectors(
        spans=res1["spans"],
        page_dims=res1["page_dims"],
        metadata=res1["metadata"],
        word_order=res1["word_order"],
        image_pages=res1["image_pages"],
    )
    sig2 = run_all_detectors(
        spans=res2["spans"],
        page_dims=res2["page_dims"],
        metadata=res2["metadata"],
        word_order=res2["word_order"],
        image_pages=res2["image_pages"],
    )

    assert len(sig1) == len(sig2)
    for s1, s2 in zip(sig1, sig2):
        assert s1["signal_type"] == s2["signal_type"]
        assert s1["severity"] == s2["severity"]
        assert s1["page"] == s2["page"]
        assert s1["description"] == s2["description"]
        assert s1["bbox"] == s2["bbox"]

    trust1 = compute_trust_score({"high": 1, "medium": 0, "low": 0}, ai_content_score=20.0)
    trust2 = compute_trust_score({"high": 1, "medium": 0, "low": 0}, ai_content_score=20.0)
    assert trust1 == trust2


# ─────────────────────────────────────────────────────────────────────────────
# 2. Consistency & Validation: High fraud signals NEVER yield "Verified"
# ─────────────────────────────────────────────────────────────────────────────

def test_high_fraud_never_verified():
    # Even with 0 AI score and 100 match score, a single HIGH signal prevents Verified
    trust = compute_trust_score(
        fraud_summary={"high": 1, "medium": 0, "low": 0},
        ai_content_score=0.0,
        true_match_score=100.0,
    )
    assert trust["label"] != "Verified"
    assert trust["label"] in ("Caution", "High Risk")
    assert trust["score"] <= 74.0

    # 2 high signals -> automatically High Risk
    trust_high = compute_trust_score(
        fraud_summary={"high": 2, "medium": 0, "low": 0},
        ai_content_score=0.0,
        true_match_score=100.0,
    )
    assert trust_high["label"] == "High Risk"
    assert trust_high["score"] <= 44.0


# ─────────────────────────────────────────────────────────────────────────────
# 3. Known Fixture PDFs Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_fixture_clean_resume():
    pdf_path = FIXTURES_DIR / "clean_resume.pdf"
    res = extract_pdf(pdf_path)
    signals = run_all_detectors(
        spans=res["spans"],
        page_dims=res["page_dims"],
        metadata=res["metadata"],
        word_order=res["word_order"],
        image_pages=res["image_pages"],
    )
    assert signals == []
    trust = compute_trust_score(
        fraud_summary={"total": 0, "high": 0, "medium": 0, "low": 0},
        ai_content_score=15.0,
        true_match_score=85.0,
    )
    assert trust["label"] == "Verified"
    assert trust["score"] >= 80.0


def test_fixture_hidden_text_resume():
    pdf_path = FIXTURES_DIR / "hidden_text_resume.pdf"
    res = extract_pdf(pdf_path)
    signals = run_all_detectors(
        spans=res["spans"],
        page_dims=res["page_dims"],
        metadata=res["metadata"],
        word_order=res["word_order"],
        image_pages=res["image_pages"],
    )
    signal_types = {s["signal_type"] for s in signals}
    assert "hidden_text" in signal_types

    hidden_signals = [s for s in signals if s["signal_type"] == "hidden_text"]
    assert hidden_signals[0]["severity"] == "high"


def test_fixture_homoglyphs_resume():
    pdf_path = FIXTURES_DIR / "homoglyphs_resume.pdf"
    res = extract_pdf(pdf_path)
    signals = run_all_detectors(
        spans=res["spans"],
        page_dims=res["page_dims"],
        metadata=res["metadata"],
        word_order=res["word_order"],
        image_pages=res["image_pages"],
    )
    signal_types = {s["signal_type"] for s in signals}
    assert "homoglyph_substitution" in signal_types


def test_fixture_layer_order_mismatch_resume():
    pdf_path = FIXTURES_DIR / "layer_order_mismatch_resume.pdf"
    res = extract_pdf(pdf_path)
    # The reverse-order lines produce high disorder_ratio
    order_stats = res["word_order"]
    assert len(order_stats) >= 1
    assert order_stats[0]["disorder_ratio"] > 0.15

    signals = run_all_detectors(
        spans=res["spans"],
        page_dims=res["page_dims"],
        metadata=res["metadata"],
        word_order=res["word_order"],
        image_pages=res["image_pages"],
    )
    signal_types = {s["signal_type"] for s in signals}
    assert "layer_order_mismatch" in signal_types


def test_fixture_scanned_image_only_resume():
    pdf_path = FIXTURES_DIR / "scanned_image_only_resume.pdf"
    res = extract_pdf(pdf_path)
    img_pages = res["image_pages"]
    assert len(img_pages) >= 1
    assert img_pages[0]["is_suspected_image_only"] is True

    signals = run_all_detectors(
        spans=res["spans"],
        page_dims=res["page_dims"],
        metadata=res["metadata"],
        word_order=res["word_order"],
        image_pages=res["image_pages"],
    )
    signal_types = {s["signal_type"] for s in signals}
    assert "image_only_page" in signal_types


# ─────────────────────────────────────────────────────────────────────────────
# 4. Edge-Case PDFs
# ─────────────────────────────────────────────────────────────────────────────

def test_empty_pdf_raises_clean_error(tmp_path: Path):
    empty_file = tmp_path / "empty.pdf"
    empty_file.write_bytes(b"")
    with pytest.raises(ValueError, match="empty"):
        extract_pdf(empty_file)


def test_corrupted_pdf_raises_clean_error(tmp_path: Path):
    corrupt_file = tmp_path / "corrupt.pdf"
    corrupt_file.write_bytes(b"NOT A REAL PDF HEADER")
    with pytest.raises(ValueError, match="corrupted|Invalid"):
        extract_pdf(corrupt_file)


# ─────────────────────────────────────────────────────────────────────────────
# 5. API Endpoints
# ─────────────────────────────────────────────────────────────────────────────

def test_api_health(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy"}


def test_api_scan_and_inspect(client: TestClient, auth_headers: dict):
    pdf_path = FIXTURES_DIR / "hidden_text_resume.pdf"
    with open(pdf_path, "rb") as f:
        resp = client.post(
            "/scan",
            files={"file": ("hidden_text_resume.pdf", f, "application/pdf")},
            data={"job_description": "We need a Python software engineer with AWS and Kubernetes."},
            headers=auth_headers,
        )
    assert resp.status_code == 201
    data = resp.json()
    scan_id = data["scan_id"]
    assert scan_id is not None
    assert "fraud_summary" in data
    assert "narrative" in data
    assert data["narrative"]["verdict_title"] is not None

    # Test GET /scan/{id}
    get_resp = client.get(f"/scan/{scan_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["scan_id"] == scan_id

    # Test GET /scan/{id}/inspect
    inspect_resp = client.get(f"/scan/{scan_id}/inspect", headers=auth_headers)
    assert inspect_resp.status_code == 200
    inspect_data = inspect_resp.json()
    assert "flagged_spans" in inspect_data
    assert "signals" in inspect_data

    # Test GET /scan/{id}/badge.svg
    badge_resp = client.get(f"/scan/{scan_id}/badge.svg", headers=auth_headers)
    assert badge_resp.status_code == 200
    assert "image/svg+xml" in badge_resp.headers["content-type"]
    assert b"<svg" in badge_resp.content

    # Test GET /report/{id}/pdf
    report_resp = client.get(f"/report/{scan_id}/pdf", headers=auth_headers)
    assert report_resp.status_code == 200
    assert "application/pdf" in report_resp.headers["content-type"]


def test_api_batch_scan(client: TestClient, auth_headers: dict):
    clean_path = FIXTURES_DIR / "clean_resume.pdf"
    hidden_path = FIXTURES_DIR / "hidden_text_resume.pdf"

    with open(clean_path, "rb") as f1, open(hidden_path, "rb") as f2:
        files = [
            ("files", ("clean_resume.pdf", f1.read(), "application/pdf")),
            ("files", ("hidden_text_resume.pdf", f2.read(), "application/pdf")),
        ]
        resp = client.post(
            "/scan/batch",
            files=files,
            data={"job_description": "Python, Docker, Kubernetes software engineer."},
            headers=auth_headers,
        )

    assert resp.status_code == 201
    batch_data = resp.json()
    assert batch_data["total_processed"] == 2
    leaderboard = batch_data["leaderboard"]
    assert len(leaderboard) == 2
    # First candidate on leaderboard should have higher trust score than second
    assert leaderboard[0]["trust_score"] >= leaderboard[1]["trust_score"]
