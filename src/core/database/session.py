from __future__ import annotations

from pathlib import Path
from sqlmodel import Session, SQLModel, create_engine

# Import entities so SQLModel knows about the tables
from .entities import FOAEntity

DEFAULT_DB_PATH = Path("foa_data.db")
engine = create_engine(f"sqlite:///{DEFAULT_DB_PATH}")


def init_db():
    """Create database tables if they don't exist."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Returns a new SQLModel session."""
    return Session(engine)
