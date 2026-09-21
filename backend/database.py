"""
database.py
-----------
Creates the SQLite engine and session factory, and initialises all tables on
startup. Import `get_db` in routers to obtain a per-request DB session.
"""

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# ── Resolve database path ──────────────────────────────────────────────────────
# Default: <repo-root>/db/interviewsense.db
# Override by setting DATABASE_URL in the environment / .env file.
_DB_DIR = Path(__file__).resolve().parent.parent / "db"
_DB_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{_DB_DIR / 'interviewsense.db'}",
)

# ── SQLAlchemy engine ──────────────────────────────────────────────────────────
# connect_args={"check_same_thread": False} is required for SQLite when used
# with FastAPI's async request handling (multiple threads share one connection).
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,  # Set True to log all SQL statements during development
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ── Declarative base ───────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """All ORM models inherit from this base."""
    pass


# ── Table initialisation ───────────────────────────────────────────────────────
def init_db() -> None:
    """Create all tables defined in db_models if they don't already exist."""
    # Import models so SQLAlchemy registers them against Base.metadata
    from backend.models import db_models  # noqa: F401
    Base.metadata.create_all(bind=engine)


# ── Dependency for FastAPI routes ──────────────────────────────────────────────
def get_db():
    """
    Yield a database session and ensure it is closed after the request.

    Usage in a router::

        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
