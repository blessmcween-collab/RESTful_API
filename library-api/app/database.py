"""Database engine, session factory and FastAPI dependency."""
import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# SQLite by default. For PostgreSQL set e.g.
#   DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/library
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./library.db")

# SQLite connections can't be shared across threads by default; FastAPI runs
# sync endpoints in a thread pool, so we relax that check for SQLite only.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Base class for all ORM models."""


def get_db() -> Generator[Session, None, None]:
    """Yield a database session per request and always close it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
