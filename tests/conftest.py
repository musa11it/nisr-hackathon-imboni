import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Tests always use an isolated SQLite database, never the developer's MySQL.
_TMP_DB = ROOT / "data" / "test_imboni.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB.as_posix()}"
os.environ["DB_FALLBACK_ENABLED"] = "false"
os.environ["APP_ENV"] = "development"


@pytest.fixture(scope="session")
def store():
    from backend.app.store import get_store
    return get_store()


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from backend.app.main import app
    if _TMP_DB.exists():
        _TMP_DB.unlink()
    with TestClient(app) as c:
        yield c
    from backend.app.db import reset_engine_for_tests
    reset_engine_for_tests()
    if _TMP_DB.exists():
        _TMP_DB.unlink()
