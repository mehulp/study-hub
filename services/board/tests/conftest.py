import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import sessionmaker

_BOARD_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BOARD_DIR.parent.parent
_AUTH_DIR = _BOARD_DIR.parent / "auth"
_AUTH_VENV_PYTHON = _AUTH_DIR / "venv" / "bin" / "python"
_ITEMS_DIR = _BOARD_DIR.parent / "items"
_ITEMS_VENV_PYTHON = _ITEMS_DIR / "venv" / "bin" / "python"

TEST_DATABASE_URL = (
    "postgresql+psycopg://bookmarks_hub:bookmarks_hub_dev_password"
    "@localhost:5432/bookmarks_hub_test"
)
AUTH_TEST_PORT = 8016
AUTH_TEST_URL = f"http://127.0.0.1:{AUTH_TEST_PORT}"
ITEMS_TEST_PORT = 8017
ITEMS_TEST_URL = f"http://127.0.0.1:{ITEMS_TEST_PORT}"

# Board reads DATABASE_URL (app/db.py), AUTH_SERVICE_URL and
# ITEMS_SERVICE_URL (app/auth.py, app/items_client.py) at import time, so
# all three must be set before app.main is imported below.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["AUTH_SERVICE_URL"] = AUTH_TEST_URL
os.environ["ITEMS_SERVICE_URL"] = ITEMS_TEST_URL


def _wait_until_healthy(url: str, timeout: float = 15.0) -> None:
    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        try:
            response = httpx.get(url, timeout=1.0)
            if response.status_code == 200:
                return
        except httpx.HTTPError as exc:
            last_error = exc
        time.sleep(0.2)
    raise RuntimeError(f"Service did not become healthy in time: {last_error}")


@pytest.fixture(scope="session", autouse=True)
def _migrate_board_test_db():
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)


@pytest.fixture(scope="session", autouse=True)
def auth_service():
    """Real Auth subprocess — Board needs genuinely signed tokens (its own
    JWT verification is real, Decision #30), same reasoning as Items'/
    Gateway's conftest."""
    env = os.environ.copy()
    env["DATABASE_URL"] = TEST_DATABASE_URL

    subprocess.run(
        [str(_AUTH_VENV_PYTHON), "-m", "alembic", "upgrade", "head"],
        cwd=_AUTH_DIR, env=env, check=True,
    )
    process = subprocess.Popen(
        [str(_AUTH_VENV_PYTHON), "-m", "uvicorn", "app.main:app", "--port", str(AUTH_TEST_PORT)],
        cwd=_AUTH_DIR, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        _wait_until_healthy(f"{AUTH_TEST_URL}/.well-known/jwks.json")
        yield
    finally:
        process.terminate()
        process.wait(timeout=10)


@pytest.fixture(scope="session", autouse=True)
def items_service(auth_service):
    """Real Items subprocess — Board's add-item endpoint genuinely calls
    Items (Decision #37), so this has to be the real thing, not a stub."""
    env = os.environ.copy()
    env["DATABASE_URL"] = TEST_DATABASE_URL
    env["AUTH_SERVICE_URL"] = AUTH_TEST_URL

    subprocess.run(
        [str(_ITEMS_VENV_PYTHON), "-m", "alembic", "upgrade", "head"],
        cwd=_ITEMS_DIR, env=env, check=True,
    )
    process = subprocess.Popen(
        [str(_ITEMS_VENV_PYTHON), "-m", "uvicorn", "app.main:app", "--port", str(ITEMS_TEST_PORT)],
        cwd=_ITEMS_DIR, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        _wait_until_healthy(f"{ITEMS_TEST_URL}/docs")
        yield
    finally:
        process.terminate()
        process.wait(timeout=10)


def _create_real_user() -> dict:
    email = f"board-test-user-{uuid.uuid4()}@example.com"
    password = "correcthorsebatterystaple"

    signup = httpx.post(f"{AUTH_TEST_URL}/signup", json={"email": email, "password": password})
    user_id = signup.json()["id"]
    login = httpx.post(f"{AUTH_TEST_URL}/login", json={"email": email, "password": password})
    access_token = login.json()["access_token"]

    return {"user_id": user_id, "access_token": access_token, "email": email}


def _delete_user(user_id: str) -> None:
    subprocess.run(
        [
            "docker", "compose", "exec", "-T", "postgres",
            "psql", "-U", "bookmarks_hub", "-d", "bookmarks_hub_test",
            "-c", f"DELETE FROM items.items WHERE owner_user_id = '{user_id}'; "
                  f"DELETE FROM auth.refresh_tokens WHERE user_id = '{user_id}'; "
                  f"DELETE FROM auth.users WHERE id = '{user_id}';",
        ],
        cwd=_REPO_ROOT, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


@pytest.fixture(scope="session")
def owner_identity(auth_service, items_service):
    identity = _create_real_user()
    yield identity
    _delete_user(identity["user_id"])


@pytest.fixture()
def owner_headers(owner_identity):
    return {"Authorization": f"Bearer {owner_identity['access_token']}"}


@pytest.fixture()
def other_user():
    """A second real user, fresh per test — used for ownership-boundary
    tests. Function-scoped (not session) since not every test needs one."""
    identity = _create_real_user()
    yield identity
    _delete_user(identity["user_id"])


@pytest.fixture()
def other_headers(other_user):
    return {"Authorization": f"Bearer {other_user['access_token']}"}


@pytest.fixture()
def ingested_item(owner_identity):
    """A real item, ingested through the real Items subprocess, owned by
    owner_identity — what add-item tests attach to a board."""
    response = httpx.post(
        f"{ITEMS_TEST_URL}/",
        json={
            "source": "chrome",
            "external_id": str(uuid.uuid4()),
            "title": "Test Item",
            "url": "https://example.com",
            "favicon_url": "https://example.com/favicon.ico",
            "saved_at": "2026-01-01T00:00:00Z",
        },
        headers={"Authorization": f"Bearer {owner_identity['access_token']}"},
    )
    return response.json()


@pytest.fixture()
def db_session():
    from app.db import engine

    connection = engine.connect()
    outer_transaction = connection.begin()

    Session = sessionmaker(bind=connection)
    session = Session()
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(session, transaction):
        if not connection.in_nested_transaction():
            connection.begin_nested()

    yield session

    session.close()
    outer_transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    from app.db import get_db
    from app.main import app

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
