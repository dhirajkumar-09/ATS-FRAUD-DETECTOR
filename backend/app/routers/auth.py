"""
routers/auth.py — Phase 5
==========================
POST /auth/register     — create a recruiter account, returns a JWT
POST /auth/login        — OAuth2 password flow, returns a JWT
GET  /auth/me           — current user's profile
GET  /auth/org-settings — this user's org threshold overrides
PUT  /auth/org-settings — update org threshold overrides (admin only)

The first user to register for a given `organization` string is auto-promoted
to admin for that org, so there's always someone who can manage thresholds
without needing a separate bootstrap step.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    require_admin,
    verify_password,
)
from app.database import get_db
from app.models import OrgSettings, User

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Schemas ──────────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = None
    organization: str = Field(min_length=1, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str
    organization: str
    is_admin: bool


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str | None
    organization: str
    is_admin: bool


class OrgSettingsIn(BaseModel):
    near_white_threshold: int | None = None
    hidden_font_size_pt: float | None = None
    candidate_transparency_enabled: bool | None = None


class OrgSettingsOut(BaseModel):
    organization: str
    near_white_threshold: int | None
    hidden_font_size_pt: float | None
    candidate_transparency_enabled: bool


# ── Register ─────────────────────────────────────────────────────────────────
@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter_by(email=payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    # First registrant for a new organization becomes its admin.
    org_has_members = db.query(User).filter_by(organization=payload.organization).first() is not None

    user = User(
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        organization=payload.organization,
        is_admin=not org_has_members,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.email)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        email=user.email,
        organization=user.organization,
        is_admin=user.is_admin,
    )


# ── Login ────────────────────────────────────────────────────────────────────
@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2PasswordRequestForm's `username` field carries the email.
    user = db.query(User).filter_by(email=form_data.username.lower()).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(user.id, user.email)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        email=user.email,
        organization=user.organization,
        is_admin=user.is_admin,
    )


# ── Current user ───────────────────────────────────────────────────────────────
@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


# ── Org settings ─────────────────────────────────────────────────────────────
@router.get("/org-settings", response_model=OrgSettingsOut)
def get_org_settings(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    settings = db.query(OrgSettings).filter_by(organization=current_user.organization).first()
    if settings is None:
        # No overrides saved yet - report nulls, meaning "use app defaults".
        return OrgSettingsOut(
            organization=current_user.organization,
            near_white_threshold=None,
            hidden_font_size_pt=None,
            candidate_transparency_enabled=False,
        )
    return OrgSettingsOut(
        organization=settings.organization,
        near_white_threshold=settings.near_white_threshold,
        hidden_font_size_pt=settings.hidden_font_size_pt,
        candidate_transparency_enabled=settings.candidate_transparency_enabled,
    )


@router.put("/org-settings", response_model=OrgSettingsOut)
def update_org_settings(
    payload: OrgSettingsIn,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    settings = db.query(OrgSettings).filter_by(organization=current_user.organization).first()
    if settings is None:
        settings = OrgSettings(organization=current_user.organization)
        db.add(settings)

    settings.near_white_threshold = payload.near_white_threshold
    settings.hidden_font_size_pt = payload.hidden_font_size_pt
    if payload.candidate_transparency_enabled is not None:
        settings.candidate_transparency_enabled = payload.candidate_transparency_enabled
        
    db.commit()
    db.refresh(settings)

    return OrgSettingsOut(
        organization=settings.organization,
        near_white_threshold=settings.near_white_threshold,
        hidden_font_size_pt=settings.hidden_font_size_pt,
        candidate_transparency_enabled=settings.candidate_transparency_enabled,
    )