import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.database import get_db, Base
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from app.models import User, OrgSettings, Resume, ScanResult, FraudSignal
from app.auth import hash_password
import json

# Setup test DB
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(bind=engine)

from sqlalchemy.orm import sessionmaker

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
    # Clear db
    for tbl in reversed(Base.metadata.sorted_tables):
        db.execute(tbl.delete())
    db.commit()

    # Create admin user
    user = User(
        email="admin@test.com",
        hashed_password=hash_password("testpass"),
        organization="TestOrg",
        is_admin=True
    )
    db.add(user)
    db.commit()

    # Create resume and scan result
    resume = Resume(owner_id=user.id, filename="test.pdf", file_path="/fake/path", sha256="dummy", page_count=1)
    db.add(resume)
    db.commit()

    scan = ScanResult(
        resume_id=resume.id,
        status="done",
        trust_score=80.0,
        trust_label="Caution",
        ai_content_score=20.0,
        true_match_score=90.0,
        high_count=1,
    )
    db.add(scan)
    db.commit()

    sig = FraudSignal(
        scan_result_id=scan.id,
        signal_type="hidden_text",
        severity="high",
        page=1,
        bbox_x0=10, bbox_y0=10, bbox_x1=20, bbox_y1=20,
        description="Hidden stuff",
        evidence_text="secret text"
    )
    db.add(sig)
    db.commit()
    db.close()
    yield
    app.dependency_overrides.clear()

def get_auth_headers():
    res = client.post("/auth/login", data={"username": "admin@test.com", "password": "testpass"})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_org_setting_defaults_false():
    headers = get_auth_headers()
    res = client.get("/auth/org-settings", headers=headers)
    assert res.status_code == 200
    assert res.json()["candidate_transparency_enabled"] is False

def test_share_link_fails_when_disabled():
    headers = get_auth_headers()
    # Assume scan id is 1
    res = client.post("/scan/1/share-link", headers=headers)
    assert res.status_code == 403
    assert "Candidate Transparency Mode is not enabled" in res.json()["detail"]

def test_share_link_success_when_enabled():
    headers = get_auth_headers()
    
    # Enable setting
    client.put("/auth/org-settings", json={"candidate_transparency_enabled": True}, headers=headers)
    
    # Generate link
    res = client.post("/scan/1/share-link", headers=headers)
    assert res.status_code == 200
    token = res.json()["share_token"]
    assert token is not None

    # Fetch public endpoint
    pub_res = client.get(f"/scan/public/{token}")
    assert pub_res.status_code == 200
    data = pub_res.json()
    
    # Assert reduced fields
    assert "trust_score" in data
    assert "ai_content_score" in data
    assert "filename" in data
    assert "narrative" in data
    assert "summary" in data["narrative"]
    
    # Assert internals are stripped
    assert "signals" not in data
    assert "spans" not in data
    response_str = json.dumps(data)
    assert "bbox" not in response_str
    assert "evidence_text" not in response_str
    assert "secret text" not in response_str

    # Revoke link
    client.delete("/scan/1/share-link", headers=headers)
    
    # Fetch public endpoint again
    pub_res2 = client.get(f"/scan/public/{token}")
    assert pub_res2.status_code == 404
