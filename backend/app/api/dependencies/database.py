from typing import Generator
from sqlalchemy.orm import Session
from app.db.session import get_db as _get_db


def get_db() -> Generator[Session, None, None]:
    """
    Thin wrapper around the core DB dependency.

    This delegates to app.db.session.get_db so it always sees the
    up-to-date SessionLocal initialized by init_db().
    """
    yield from _get_db()
