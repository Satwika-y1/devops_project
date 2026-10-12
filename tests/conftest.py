"""Shared pytest setup: every test uses its own temporary database."""
import os
import sys
import tempfile

# Point the module-level `app` at a throw-away DB *before* app.py is imported,
# so importing it never creates or touches the real instance/food.db.
_IMPORT_DB = os.path.join(tempfile.mkdtemp(), "import_check.db")
os.environ["DATABASE_PATH"] = _IMPORT_DB

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from app import create_app  # noqa: E402


@pytest.fixture()
def app(tmp_path):
    db_file = tmp_path / "test_food.db"
    flask_app = create_app({"TESTING": True, "DATABASE": str(db_file), "SECRET_KEY": "test-secret"})
    yield flask_app


@pytest.fixture()
def client(app):
    return app.test_client()
