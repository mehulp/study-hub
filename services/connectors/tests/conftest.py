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

_CONNECTORS_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _CONNECTORS_DIR.parent.parent
_AUTH_DIR = _CONNECTORS_DIR.parent / "auth"
_AUTH_VENV_PYTHON = _AUTH_DIR / "venv" / "bin" / "python"
_ITEMS_DIR = _CONNECTORS_DIR.parent / "items"
_ITEMS_VENV_PYTHON = _ITEMS_DIR / "venv" / "bin" / "python"

TEST_DATABASE_URL = (
    "postgresql+psycopg://study_hub:study_hub_dev_password"
    "@localhost:5432/study_hub_test"
)
AUTH_TEST_PORT = 8019
AUTH_TEST_URL = f"http://127.0.0.1:{AUTH_TEST_PORT}"
ITEMS_TEST_PORT = 8020
ITEMS_TEST_URL = f"http://127.0.0.1:{ITEMS_TEST_PORT}"

# Connectors reads DATABASE_URL, AUTH_SERVICE_URL, ITEMS_SERVICE_URL, and its
# own OAUTH_CLIENT_ID/SECRET at import time, so all must be set before
# app.main is imported below. The client_id/secret are set once the fixture
# below actually registers a client — see _register_test_client.
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
def _migrate_connectors_test_db():
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)


@pytest.fixture(scope="session", autouse=True)
def auth_service():
    """Real Auth subprocess — Connectors needs genuinely signed user tokens
    (for /connections) and a real /oauth/token endpoint (for its own
    service credentials), same reasoning as every other service's conftest."""
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
    """Real Items subprocess — sync genuinely calls Items' ingest, so this
    has to be the real thing, same reasoning as Board's conftest."""
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


@pytest.fixture(scope="session", autouse=True)
def oauth_client(auth_service):
    """Registers Connectors' own OAuth client against the real Auth
    subprocess (via create_oauth_client.py, same tool used in production —
    Decision #8's reasoning) and points Connectors' own env at it, before
    app.main is ever imported."""
    client_id = f"connectors-test-client-{uuid.uuid4()}"
    env = os.environ.copy()
    env["DATABASE_URL"] = TEST_DATABASE_URL

    result = subprocess.run(
        [str(_AUTH_VENV_PYTHON), "create_oauth_client.py", client_id, "Connectors Test Client"],
        cwd=_AUTH_DIR, env=env, check=True, capture_output=True, text=True,
    )
    client_secret = next(
        line.split(":", 1)[1].strip()
        for line in result.stdout.splitlines()
        if line.startswith("client_secret:")
    )

    os.environ["OAUTH_CLIENT_ID"] = client_id
    os.environ["OAUTH_CLIENT_SECRET"] = client_secret

    yield {"client_id": client_id, "client_secret": client_secret}

    subprocess.run(
        [
            "docker", "compose", "exec", "-T", "postgres",
            "psql", "-U", "study_hub", "-d", "study_hub_test",
            "-c", f"DELETE FROM auth.oauth_clients WHERE client_id = '{client_id}';",
        ],
        cwd=_REPO_ROOT, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def _create_real_user() -> dict:
    email = f"connectors-test-user-{uuid.uuid4()}@example.com"
    password = "correcthorsebatterystaple"

    signup = httpx.post(f"{AUTH_TEST_URL}/signup", json={"email": email, "password": password})
    user_id = signup.json()["id"]
    login = httpx.post(f"{AUTH_TEST_URL}/login", json={"email": email, "password": password})
    access_token = login.json()["access_token"]

    return {"user_id": user_id, "access_token": access_token}


def _delete_user(user_id: str) -> None:
    subprocess.run(
        [
            "docker", "compose", "exec", "-T", "postgres",
            "psql", "-U", "study_hub", "-d", "study_hub_test",
            "-c", f"DELETE FROM items.items WHERE owner_user_id = '{user_id}'; "
                  f"DELETE FROM auth.refresh_tokens WHERE user_id = '{user_id}'; "
                  f"DELETE FROM auth.users WHERE id = '{user_id}';",
        ],
        cwd=_REPO_ROOT, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


@pytest.fixture(scope="session")
def owner_identity(auth_service, items_service, oauth_client):
    identity = _create_real_user()
    yield identity
    _delete_user(identity["user_id"])


@pytest.fixture()
def owner_headers(owner_identity):
    return {"Authorization": f"Bearer {owner_identity['access_token']}"}


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
