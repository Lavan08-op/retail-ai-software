"""SQLAlchemy engine/session setup. WAL mode is enabled here, once, so
every consumer of this module gets it automatically — no one else should be
opening a raw sqlite3 connection by hand.

Two session factories are exposed on purpose:
- SessionWriter: used ONLY by storage/writer.py. Nothing else should import
  this.
- SessionReader: used by PySide6, Streamlit, and any read-only service code.
  Connections from this factory get PRAGMA query_only = ON as a real
  enforcement mechanism, not just a naming convention.
"""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

DB_PATH = Path(os.environ.get("RETAIL_AI_DB_PATH", "data/retail_ai.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

_DB_URL = f"sqlite:///{DB_PATH}"

# Single engine, shared by both session factories — SQLite WAL mode is a
# property of the database file, not the connection, but we still set the
# PRAGMA on every new connection to be explicit and safe.
engine = create_engine(_DB_URL, future=True)


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, connection_record):  # noqa: ANN001
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA busy_timeout = 2000;")
    cursor.close()


SessionWriter = sessionmaker(bind=engine, future=True)


def _reader_engine():
    """A second engine pointed at the same file, with query_only enforced
    at connect-time — read-only isn't just convention here, it's a PRAGMA
    the connection itself refuses to violate."""

    reader_engine = create_engine(_DB_URL, future=True)

    @event.listens_for(reader_engine, "connect")
    def _set_reader_pragmas(dbapi_connection, connection_record):  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA busy_timeout = 2000;")
        cursor.execute("PRAGMA query_only = ON;")
        cursor.close()

    return reader_engine


reader_engine = _reader_engine()
SessionReader = sessionmaker(bind=reader_engine, future=True)


def init_db() -> None:
    """Create all tables. Fine to call every startup — no-op if they
    already exist. Alembic takes over for real schema changes later."""
    from storage.models import Base

    Base.metadata.create_all(engine)
