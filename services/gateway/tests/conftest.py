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
_ITEMS_DIR = _GATEWAY_DIR.parent / "items"
_ITEMS_VENV_PYTHON = _ITEMS_DIR / "venv" / "bin" / "python"
_BOARD_DIR = _GATEWAY_DIR.parent / "board"
_BOARD_VENV_PYTHON = _BOARD_DIR / "venv" / "bin" / "python"

TEST_DATABASE_URL = (
    "postgresql+psycopg://bookmarks_hub:bookmarks_hub_dev_password"
    "@localhost:5432/bookmarks_hub_test"
)
AUTH_TEST_PORT = 8011
AUTH_TEST_URL = f"http://127.0.0.1:{AUTH_TEST_PORT}"
ITEMS_TEST_PORT = 8013
ITEMS_TEST_URL = f"http://127.0.0.1:{ITEMS_TEST_PORT}"
BOARD_TEST_PORT = 8018
BOARD_TEST_URL = f"http://127.0.0.1:{BOARD_TEST_PORT}"

# Gateway's app reads AUTH_SERVICE_URL/ITEMS_SERVICE_URL/BOARD_SERVICE_URL at
# import time (main.py) and fetches the JWKS from Auth during its startup
# lifespan, so these must be set, and the real subprocesses reachable,
# before app.main is imported below.
os.environ["AUTH_SERVICE_URL"] = AUTH_TEST_URL
os.environ["ITEMS_SERVICE_URL"] = ITEMS_TEST_URL
os.environ["BOARD_SERVICE_URL"] = BOARD_TEST_URL


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


@pytest.fixture(scope="session", autouse=True)
def items_service(auth_service):
    """Runs the real Items service as a subprocess too — proving Decision
    #31's actual promise (a second backend is just a new routing-table row,
    no change to Gateway's own logic) requires a second real backend to
    route to, not just Auth."""
    env = os.environ.copy()
    env["DATABASE_URL"] = TEST_DATABASE_URL
    env["AUTH_SERVICE_URL"] = AUTH_TEST_URL

    subprocess.run(
        [str(_ITEMS_VENV_PYTHON), "-m", "alembic", "upgrade", "head"],
        cwd=_ITEMS_DIR,
        env=env,
        check=True,
    )

    process = subprocess.Popen(
        [
            str(_ITEMS_VENV_PYTHON),
            "-m",
            "uvicorn",
            "app.main:app",
            "--port",
            str(ITEMS_TEST_PORT),
        ],
        cwd=_ITEMS_DIR,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        _wait_until_healthy(f"{ITEMS_TEST_URL}/docs")
        yield
    finally:
        process.terminate()
        process.wait(timeout=10)


@pytest.fixture(scope="session", autouse=True)
def board_service(auth_service, items_service):
    """Runs the real Board service as a subprocess too — the third proof
    of Decision #31's promise, and Board's add-item path genuinely calls
    Items (Decision #37), so both need to be real here, not stubs."""
    env = os.environ.copy()
    env["DATABASE_URL"] = TEST_DATABASE_URL
    env["AUTH_SERVICE_URL"] = AUTH_TEST_URL
    env["ITEMS_SERVICE_URL"] = ITEMS_TEST_URL

    subprocess.run(
        [str(_BOARD_VENV_PYTHON), "-m", "alembic", "upgrade", "head"],
        cwd=_BOARD_DIR,
        env=env,
        check=True,
    )

    process = subprocess.Popen(
        [
            str(_BOARD_VENV_PYTHON),
            "-m",
            "uvicorn",
            "app.main:app",
            "--port",
            str(BOARD_TEST_PORT),
        ],
        cwd=_BOARD_DIR,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        _wait_until_healthy(f"{BOARD_TEST_URL}/docs")
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
            "TRUNCATE auth.users, auth.refresh_tokens, items.items, board.boards, board.board_items CASCADE;",
        ],
        cwd=_REPO_ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
