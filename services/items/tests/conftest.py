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

_ITEMS_DIR = Path(__file__).resolve().parent.parent
_AUTH_DIR = _ITEMS_DIR.parent / "auth"
_AUTH_VENV_PYTHON = _AUTH_DIR / "venv" / "bin" / "python"

TEST_DATABASE_URL = (
    "postgresql+psycopg://study_hub:study_hub_dev_password"
    "@localhost:5432/study_hub_test"
)
AUTH_TEST_PORT = 8012
AUTH_TEST_URL = f"http://127.0.0.1:{AUTH_TEST_PORT}"

# Items reads both DATABASE_URL (app/db.py) and AUTH_SERVICE_URL (app/auth.py)
# from the environment at import time, so both must be set before app.main
# is imported below.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["AUTH_SERVICE_URL"] = AUTH_TEST_URL


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
    raise RuntimeError(f"Auth service did not become healthy in time: {last_error}")


@pytest.fixture(scope="session", autouse=True)
def _migrate_items_test_db():
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)


@pytest.fixture(scope="session", autouse=True)
def auth_service():
    """Runs the real Auth service as a subprocess for the whole test
    session. Items needs a genuine Auth to fetch a real JWKS from (its own
    startup lifespan) and to mint real, correctly-signed tokens for testing
    protected endpoints — same reasoning as Gateway's conftest."""
    env = os.environ.copy()
    env["DATABASE_URL"] = TEST_DATABASE_URL

    subprocess.run(
        [str(_AUTH_VENV_PYTHON), "-m", "alembic", "upgrade", "head"],
        cwd=_AUTH_DIR,
        env=env,
        check=True,
    )

    process = subprocess.Popen(
        [
            str(_AUTH_VENV_PYTHON),
            "-m",
            "uvicorn",
            "app.main:app",
            "--port",
            str(AUTH_TEST_PORT),
        ],
        cwd=_AUTH_DIR,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        _wait_until_healthy(f"{AUTH_TEST_URL}/.well-known/jwks.json")
        yield
    finally:
        process.terminate()
        process.wait(timeout=10)


@pytest.fixture(scope="session")
def auth_identity(auth_service):
    """One real user, signed up and logged in against the real Auth
    subprocess once per test session — Items' tests don't care about
    account identity, only that the token's `sub` is a real, consistent
    user id Items can independently verify. Email is unique per session
    (not fixed) so a second test run never collides with a leftover user
    from a prior run that didn't get torn down cleanly."""
    email = f"items-test-user-{uuid.uuid4()}@example.com"
    password = "correcthorsebatterystaple"

    signup_response = httpx.post(
        f"{AUTH_TEST_URL}/signup", json={"email": email, "password": password}
    )
    user_id = signup_response.json()["id"]

    login_response = httpx.post(
        f"{AUTH_TEST_URL}/login", json={"email": email, "password": password}
    )
    access_token = login_response.json()["access_token"]

    yield {"user_id": user_id, "access_token": access_token}

    # Actually deletes the row (not just /logout, which only revokes the
    # refresh token and leaves the account itself behind) — the same
    # docker-compose-exec-psql cleanup pattern Gateway's conftest uses.
    subprocess.run(
        [
            "docker", "compose", "exec", "-T", "postgres",
            "psql", "-U", "study_hub", "-d", "study_hub_test",
            "-c", f"DELETE FROM auth.refresh_tokens WHERE user_id = '{user_id}'; "
                  f"DELETE FROM auth.users WHERE id = '{user_id}';",
        ],
        cwd=_ITEMS_DIR.parent.parent,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


@pytest.fixture()
def auth_headers(auth_identity):
    return {"Authorization": f"Bearer {auth_identity['access_token']}"}


@pytest.fixture(scope="session")
def service_identity(auth_service):
    """Registers a real OAuth client against the real Auth subprocess (via
    the same create_oauth_client.py script used in production, not a
    shortcut) and fetches a real service token — Decision #41's
    client-credentials flow, exercised for real rather than mocked."""
    client_id = f"items-test-client-{uuid.uuid4()}"
    env = os.environ.copy()
    env["DATABASE_URL"] = TEST_DATABASE_URL

    result = subprocess.run(
        [str(_AUTH_VENV_PYTHON), "create_oauth_client.py", client_id, "Items Test Client"],
        cwd=_AUTH_DIR,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    client_secret = next(
        line.split(":", 1)[1].strip()
        for line in result.stdout.splitlines()
        if line.startswith("client_secret:")
    )

    token_response = httpx.post(
        f"{AUTH_TEST_URL}/oauth/token",
        json={"client_id": client_id, "client_secret": client_secret},
    )
    access_token = token_response.json()["access_token"]

    yield {"client_id": client_id, "access_token": access_token}

    subprocess.run(
        [
            "docker", "compose", "exec", "-T", "postgres",
            "psql", "-U", "study_hub", "-d", "study_hub_test",
            "-c", f"DELETE FROM auth.oauth_clients WHERE client_id = '{client_id}';",
        ],
        cwd=_ITEMS_DIR.parent.parent,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


@pytest.fixture()
def service_headers(service_identity):
    return {"Authorization": f"Bearer {service_identity['access_token']}"}


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
def client(db_session, auth_service):
    from app.db import get_db
    from app.main import app

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
