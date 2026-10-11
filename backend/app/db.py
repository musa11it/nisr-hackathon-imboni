"""Database engine with safe MySQL initialisation and a documented SQLite fallback.

* Never creates users, changes passwords, or drops anything.
* Creates the configured MySQL database only with ``CREATE DATABASE IF NOT EXISTS``
  and a backtick-quoted identifier (the name ``nisr-hachathon`` contains a hyphen).
* If MySQL is unreachable and the fallback is enabled, switches to SQLite and
  reports why via ``db_status()`` (without echoing credentials).
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import ROOT, get_settings

log = logging.getLogger("imboni.db")


class Base(DeclarativeBase):
    pass


_state: dict = {"engine": None, "backend": None, "fallback_reason": None}
SessionLocal = sessionmaker(autoflush=False, expire_on_commit=False)

_SAFE_DB_NAME = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")


def quote_mysql_identifier(name: str) -> str:
    """Backtick-quote a MySQL identifier after validating it (no injection possible)."""
    if not _SAFE_DB_NAME.match(name):
        raise ValueError("Database name may only contain letters, digits, '_' and '-'")
    return f"`{name}`"


def _sqlite_url(url: str) -> str:
    # make relative sqlite paths relative to the project root, not the CWD
    u = make_url(url)
    if u.drivername.startswith("sqlite") and u.database and not Path(u.database).is_absolute():
        path = (ROOT / u.database).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{path.as_posix()}"
    return url


def _redact(exc: Exception) -> str:
    msg = str(exc).split("\n")[0]
    return re.sub(r"//[^@/]+@", "//***@", msg)[:200]


def _mysql_engine(url: str) -> Engine:
    u = make_url(url)
    s = get_settings()
    if s.db_create_database and u.database:
        server = create_engine(u.set(database=None), pool_pre_ping=True)
        with server.connect() as conn:
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {quote_mysql_identifier(u.database)} "
                              "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
        server.dispose()
    eng = create_engine(u, pool_pre_ping=True, pool_recycle=1800)
    with eng.connect() as conn:
        conn.execute(text("SELECT 1"))
    return eng


def init_engine() -> Engine:
    if _state["engine"] is not None:
        return _state["engine"]
    s = get_settings()
    url = s.database_url
    try:
        if url.startswith("mysql"):
            eng, backend = _mysql_engine(url), "mysql"
        else:
            eng, backend = create_engine(_sqlite_url(url), connect_args={"check_same_thread": False}), "sqlite"
    except Exception as exc:
        if not s.db_fallback_enabled:
            raise
        reason = _redact(exc)
        log.warning("Primary database unavailable (%s); falling back to SQLite", reason)
        eng = create_engine(_sqlite_url(s.db_fallback_url), connect_args={"check_same_thread": False})
        backend, _state["fallback_reason"] = "sqlite-fallback", reason
    _state.update(engine=eng, backend=backend)
    SessionLocal.configure(bind=eng)
    from . import models  # noqa: F401  (register tables)
    Base.metadata.create_all(eng)
    _additive_migrations(eng)
    return eng


# Columns added after the first release: (table, column, DDL type). Only ever ADDs — never drops or alters.
_ADDED_COLUMNS = [("scenarios", "delete_token_hash", "VARCHAR(64) NULL")]


def _additive_migrations(eng: Engine) -> None:
    insp = inspect(eng)
    for table, column, ddl in _ADDED_COLUMNS:
        if table in insp.get_table_names() and column not in {c["name"] for c in insp.get_columns(table)}:
            with eng.begin() as conn:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
            log.info("added column %s.%s", table, column)


def db_status() -> dict:
    eng = _state["engine"]
    ok = False
    if eng is not None:
        try:
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            ok = True
        except Exception:
            ok = False
    return {"backend": _state["backend"], "connected": ok, "fallback_reason": _state["fallback_reason"]}


def reset_engine_for_tests() -> None:
    if _state["engine"] is not None:
        _state["engine"].dispose()
    _state.update(engine=None, backend=None, fallback_reason=None)
