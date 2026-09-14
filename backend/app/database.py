"""
SQLAlchemy engine + session factory.
Import `SessionLocal` in routers/services; `engine` is used at startup.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import DATABASE_URL

# connect_args only needed for SQLite (disables thread check so FastAPI works)
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


def init_db():
    """Ensure all tables and columns are created cleanly on startup."""
    Base.metadata.create_all(bind=engine)
    if DATABASE_URL.startswith("sqlite"):
        try:
            with engine.connect() as conn:
                from sqlalchemy import text
                res = conn.execute(text("PRAGMA table_info(scan_results)"))
                existing_cols = {row[1] for row in res.fetchall()}
                if existing_cols:
                    if "trust_score" not in existing_cols:
                        conn.execute(text("ALTER TABLE scan_results ADD COLUMN trust_score FLOAT"))
                    if "trust_label" not in existing_cols:
                        conn.execute(text("ALTER TABLE scan_results ADD COLUMN trust_label VARCHAR(16)"))
                    if "share_token" not in existing_cols:
                        conn.execute(text("ALTER TABLE scan_results ADD COLUMN share_token VARCHAR(64)"))
                    if "share_token_created_at" not in existing_cols:
                        conn.execute(text("ALTER TABLE scan_results ADD COLUMN share_token_created_at DATETIME"))
                    # Phase 7 — Explainable Risk Engine
                    if "forensic_risk_score" not in existing_cols:
                        conn.execute(text("ALTER TABLE scan_results ADD COLUMN forensic_risk_score FLOAT"))
                    conn.commit()

                # fraud_signals explainability columns
                res_fs = conn.execute(text("PRAGMA table_info(fraud_signals)"))
                fs_cols = {row[1] for row in res_fs.fetchall()}
                if fs_cols:
                    for col_def in [
                        ("risk_points",       "INTEGER"),
                        ("evidence_strength", "VARCHAR(16)"),
                        ("confidence",        "VARCHAR(8)"),
                        ("remediation",       "TEXT"),
                        ("evidence_json",     "TEXT"),
                    ]:
                        if col_def[0] not in fs_cols:
                            conn.execute(text(
                                f"ALTER TABLE fraud_signals ADD COLUMN {col_def[0]} {col_def[1]}"
                            ))
                    conn.commit()

                res2 = conn.execute(text("PRAGMA table_info(org_settings)"))
                org_cols = {row[1] for row in res2.fetchall()}
                if org_cols:
                    if "candidate_transparency_enabled" not in org_cols:
                        conn.execute(text(
                            "ALTER TABLE org_settings ADD COLUMN candidate_transparency_enabled BOOLEAN DEFAULT 0"
                        ))
                    conn.commit()
        except Exception:
            pass


def get_db():
    """FastAPI dependency: yields a DB session and ensures it is closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()