import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db, Base
from app.models import User, Resume, ScanResult
from app.auth import hash_password, create_access_token

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(bind=engine)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_data():
    app.dependency_overrides[get_db] = override_get_db
    db = TestingSessionLocal()
    for tbl in reversed(Base.metadata.sorted_tables):
        db.execute(tbl.delete())
    db.commit()

    # User A
    user_a = User(
        email="recruiter_a@test.com",
        hashed_password=hash_password("password123"),
        organization="OrgA",
        is_admin=True,
    )
    # User B
    user_b = User(
        email="recruiter_b@test.com",
        hashed_password=hash_password("password123"),
        organization="OrgB",
        is_admin=True,
    )
    db.add_all([user_a, user_b])
    db.commit()

    # Scans for User A (3 scans: 2 Verified, 1 High Risk)
    res_a1 = Resume(owner_id=user_a.id, filename="resume_a1.pdf", file_path="/fake/1.pdf", sha256="hash1", page_count=1)
    res_a2 = Resume(owner_id=user_a.id, filename="resume_a2.pdf", file_path="/fake/2.pdf", sha256="hash2", page_count=2)
    res_a3 = Resume(owner_id=user_a.id, filename="resume_a3.pdf", file_path="/fake/3.pdf", sha256="hash3", page_count=1)
    db.add_all([res_a1, res_a2, res_a3])
    db.commit()

    scan_a1 = ScanResult(
        resume_id=res_a1.id,
        status="done",
        trust_score=92.0,
        trust_label="Verified",
        ai_content_score=10.0,
        true_match_score=85.0,
        total_signals=0,
        high_count=0,
        medium_count=0,
        low_count=0,
        scanned_at=datetime(2026, 1, 10, 10, 0, 0, tzinfo=timezone.utc),
    )
    scan_a2 = ScanResult(
        resume_id=res_a2.id,
        status="done",
        trust_score=88.0,
        trust_label="Verified",
        ai_content_score=20.0,
        true_match_score=75.0,
        total_signals=1,
        high_count=0,
        medium_count=1,
        low_count=0,
        scanned_at=datetime(2026, 1, 11, 10, 0, 0, tzinfo=timezone.utc),
    )
    scan_a3 = ScanResult(
        resume_id=res_a3.id,
        status="done",
        trust_score=35.0,
        trust_label="High Risk",
        ai_content_score=85.0,
        true_match_score=40.0,
        total_signals=3,
        high_count=2,
        medium_count=1,
        low_count=0,
        scanned_at=datetime(2026, 1, 12, 10, 0, 0, tzinfo=timezone.utc),
    )
    db.add_all([scan_a1, scan_a2, scan_a3])

    # Scan for User B
    res_b = Resume(owner_id=user_b.id, filename="resume_b.pdf", file_path="/fake/b.pdf", sha256="hashb", page_count=1)
    db.add(res_b)
    db.commit()

    scan_b = ScanResult(
        resume_id=res_b.id,
        status="done",
        trust_score=50.0,
        trust_label="Caution",
        ai_content_score=45.0,
        true_match_score=60.0,
        total_signals=2,
        high_count=1,
        medium_count=1,
        low_count=0,
        scanned_at=datetime(2026, 1, 12, 12, 0, 0, tzinfo=timezone.utc),
    )
    db.add(scan_b)
    db.commit()


def get_token(email: str = "recruiter_a@test.com") -> dict:
    res = client.post("/auth/login", data={"username": email, "password": "password123"})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_get_scan_history_success():
    headers = get_token("recruiter_a@test.com")
    res = client.get("/scan", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["total"] == 3
    assert len(data["items"]) == 3
    # Ordered by scanned_at desc: scan_a3 is newest
    assert data["items"][0]["filename"] == "resume_a3.pdf"
    assert data["items"][0]["trust_label"] == "High Risk"

    # Verify summary
    summary = data["summary"]
    assert summary["total_scans"] == 3
    assert summary["counts_by_label"]["Verified"] == 2
    assert summary["counts_by_label"]["High Risk"] == 1
    assert summary["counts_by_label"]["Caution"] == 0
    # Average: (92 + 88 + 35) / 3 = 71.7
    assert summary["average_trust_score"] == 71.7


def test_get_scan_history_pagination():
    headers = get_token("recruiter_a@test.com")
    res = client.get("/scan?limit=2&offset=1", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["limit"] == 2
    assert data["offset"] == 1
    # 2nd newest is scan_a2
    assert data["items"][0]["filename"] == "resume_a2.pdf"


def test_get_scan_history_filter_trust_label():
    headers = get_token("recruiter_a@test.com")
    res = client.get("/scan?trust_label=Verified", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["total"] == 2
    assert len(data["items"]) == 2
    for item in data["items"]:
        assert item["trust_label"] == "Verified"

    # Overall summary still reflects all 3 scans of User A
    assert data["summary"]["total_scans"] == 3


def test_get_scan_history_user_isolation():
    # User B should only see their 1 scan
    headers_b = get_token("recruiter_b@test.com")
    res_b = client.get("/scan", headers=headers_b)
    assert res_b.status_code == 200
    data_b = res_b.json()

    assert data_b["total"] == 1
    assert data_b["items"][0]["filename"] == "resume_b.pdf"
    assert data_b["summary"]["total_scans"] == 1
    assert data_b["summary"]["counts_by_label"]["Caution"] == 1
