
Auth · PY
"""
auth.py — Phase 5
==================
Password hashing (bcrypt directly, no passlib — sidesteps the passlib/bcrypt
version-pinning issues that trip up fresh installs) and JWT issuing/verifying
for the recruiter-account system.
 
Public API
----------
    hash_password(password) -> str
    verify_password(password, hashed) -> bool
    create_access_token(user_id, email) -> str
    get_current_user  — FastAPI dependency, injects the authenticated User
"""
from __future__ import annotations
 
from datetime import datetime, timedelta, timezone
 
import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
 
from app.config import JWT_ALGORITHM, JWT_EXPIRE_MINUTES, JWT_SECRET_KEY
from app.database import get_db
from app.models import User
 
# tokenUrl is just what shows up in the Swagger "Authorize" dialog;
# the actual login endpoint lives in routers/auth.py
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=True)
 
 
# ── Password hashing ──────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
 
 
def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False
 
 
# ── JWT ────────────────────────────────────────────────────────────────────────
def create_access_token(user_id: int, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "email": email, "exp": expire}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
 
 
def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
 
 
# ── FastAPI dependency ──────────────────────────────────────────────────────────
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = _decode_token(token)
    user_id = payload.get("sub")
    user = db.query(User).filter_by(id=int(user_id)).first() if user_id else None
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
 
 
def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an organization admin can do this.",
        )
    return current_user
 
