"""Database connection and session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from ..config import DATABASE_URL
from .models import Base

# Create SQLite engine with special settings for FastAPI
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite-specific: allow multi-threaded access
    poolclass=StaticPool,  # Use static pool for consistent connections
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Session:
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
