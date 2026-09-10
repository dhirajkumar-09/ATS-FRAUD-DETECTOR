"""
test_auth.py — Auth Endpoint Tests
====================================
Covers the /auth/register and /auth/login endpoints.
Follows the same fixture/style pattern as test_audit_and_features.py.

Tests:
  1. Successful registration returns 201 + token
  2. Successful login returns 200 + token
  3. Login with wrong password returns 401
  4. Duplicate-email registration returns 409 (not a 500)
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    return TestClient(app)


# Unique email prefix for this test module to avoid conflicts with other test
# modules that share the same SQLite database.
_EMAIL_BASE = "auth_test_user_{}@recruiter-tests.com"
_REGISTER_EMAIL = _EMAIL_BASE.format("primary")
_PASSWORD = "S3cur3P@ssword!"
_ORG = "AuthTestCorp"


# ─────────────────────────────────────────────────────────────────────────────
# 1. Successful registration
# ─────────────────────────────────────────────────────────────────────────────

def test_register_success(client: TestClient):
    """POST /auth/register with valid data should return 201 + a bearer token."""
    resp = client.post(
        "/auth/register",
        json={
            "email": _REGISTER_EMAIL,
            "password": _PASSWORD,
            "full_name": "Test Recruiter",
            "organization": _ORG,
        },
    )
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["email"] == _REGISTER_EMAIL
    assert data["organization"] == _ORG
    assert isinstance(data["user_id"], int)
    assert data["is_admin"] is True  # first registrant in a new org → auto-admin


# ─────────────────────────────────────────────────────────────────────────────
# 2. Successful login
# ─────────────────────────────────────────────────────────────────────────────

def test_login_success(client: TestClient):
    """
    POST /auth/login (OAuth2 form body: username=email, password) should
    return 200 + a bearer token for valid credentials.
    """
    resp = client.post(
        "/auth/login",
        data={
            "username": _REGISTER_EMAIL,
            "password": _PASSWORD,
        },
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["email"] == _REGISTER_EMAIL

    # Verify the token actually works on a protected endpoint (GET /auth/me)
    token = data["access_token"]
    me_resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == _REGISTER_EMAIL


# ─────────────────────────────────────────────────────────────────────────────
# 3. Login with wrong password → 401
# ─────────────────────────────────────────────────────────────────────────────

def test_login_wrong_password(client: TestClient):
    """
    POST /auth/login with the correct email but wrong password must return
    HTTP 401 (routers/auth.py raises HTTP_401_UNAUTHORIZED on mismatch).
    It must NOT return 500 (i.e., the error path is handled cleanly).
    """
    resp = client.post(
        "/auth/login",
        data={
            "username": _REGISTER_EMAIL,
            "password": "TotallyWrongPassword999!",
        },
    )
    assert resp.status_code == 401, (
        f"Expected 401 for wrong password, got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    assert "detail" in body
    assert "password" in body["detail"].lower() or "incorrect" in body["detail"].lower()


# ─────────────────────────────────────────────────────────────────────────────
# 4. Duplicate-email registration → 409, not 500
# ─────────────────────────────────────────────────────────────────────────────

def test_duplicate_email_register(client: TestClient):
    """
    Registering a second account with the same email must return HTTP 409
    (Conflict) with a clear error message — never a 500 or an unhandled
    IntegrityError.
    """
    resp = client.post(
        "/auth/register",
        json={
            "email": _REGISTER_EMAIL,  # same email as test_register_success
            "password": "AnotherP@ss1!",
            "full_name": "Duplicate User",
            "organization": _ORG,
        },
    )
    assert resp.status_code == 409, (
        f"Expected 409 Conflict for duplicate email, got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    assert "detail" in body
    assert "email" in body["detail"].lower() or "already exists" in body["detail"].lower()
