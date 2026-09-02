import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

_GATEWAY_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _GATEWAY_DIR.parent.parent
_AUTH_DIR = _GATEWAY_DIR.parent / "auth"
_AUTH_VENV_PYTHON = _AUTH_DIR / "venv" / "bin" / "python"

TEST_DATABASE_URL = (
    "postgresql+psycopg://bookmarks_hub:bookmarks_hub_dev_password"
    "@localhost:5432/bookmarks_hub_test"
)
AUTH_TEST_PORT = 8011
AUTH_TEST_URL = f"http://127.0.0.1:{AUTH_TEST_PORT}"

# Gateway's app reads AUTH_SERVICE_URL at import time (main.py) and fetches
# the JWKS from it during its startup lifespan, so this must be set, and the
# real Auth subprocess must already be reachable, before app.main is
# imported below.
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
def auth_service():
    """Runs the real Auth service as a subprocess, against the dedicated
    test database, for the whole test session — same reasoning as Decision
    #27 for Auth's own tests: Gateway's job IS the integration, so a stub
    backend would only prove Gateway's assumptions about Auth are
    internally consistent, not that the real thing actually works."""
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


@pytest.fixture()
def client():
    from app.main import app  # imported here, after AUTH_SERVICE_URL is set above

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def _clean_auth_test_db():
    # The Auth subprocess owns real, actually-committed transactions of its
    # own — Gateway's tests have no session to roll back (unlike Auth's own
    # tests, see services/auth/tests/conftest.py), so cleanup here means
    # actually deleting the rows each test created.
    yield
    subprocess.run(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "postgres",
            "psql",
            "-U",
            "bookmarks_hub",
            "-d",
            "bookmarks_hub_test",
            "-c",
            "TRUNCATE auth.users, auth.refresh_tokens CASCADE;",
        ],
        cwd=_REPO_ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
