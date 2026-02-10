"""Database connection and session management."""

from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

from ..config import DATABASE_URL
from .models import Base

# Create SQLite engine with NullPool for better concurrent request handling
# NullPool doesn't pool connections, creating new ones per request (safer for SQLite)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite-specific: allow multi-threaded access
    poolclass=NullPool,  # No connection pooling for SQLite (safest under concurrent ASGI)
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """Dependency for FastAPI to inject database sessions.

    Usage in endpoints:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all tables in database."""
    Base.metadata.create_all(bind=engine)

    # Enable WAL mode for SQLite to handle concurrent writes better
    with engine.begin() as connection:
        connection.execute(text("PRAGMA journal_mode=WAL;"))
        connection.execute(text("PRAGMA synchronous=NORMAL;"))
        connection.execute(text("PRAGMA cache_size=10000;"))
