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

