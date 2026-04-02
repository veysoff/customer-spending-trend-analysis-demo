"""Database connection and session management."""

from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

from ..config import DATABASE_URL
from .models import Base

# Detect database dialect for SQLite-specific configuration
_is_sqlite = DATABASE_URL.startswith("sqlite")

# Create engine with dialect-specific configuration
# SQLite: NullPool for better concurrent ASGI handling, check_same_thread=False for multi-threaded access
# PostgreSQL: Default pool (QueuePool), standard connection args
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    poolclass=NullPool if _is_sqlite else None,  # None → SQLAlchemy default (QueuePool for PostgreSQL)
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
    # These PRAGMA statements are SQLite-specific and should not run on other databases
    if _is_sqlite:
        with engine.begin() as connection:
            connection.execute(text("PRAGMA journal_mode=WAL;"))
            connection.execute(text("PRAGMA synchronous=NORMAL;"))
            connection.execute(text("PRAGMA cache_size=10000;"))
