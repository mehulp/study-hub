import os
import subprocess
import sys

# Point the whole app at the test database *before* anything under app/ is
# imported below — app/db.py reads DATABASE_URL from the environment at
# import time, and python-dotenv's load_dotenv() never overrides a variable
# that's already set, so setting it here wins over .env.
TEST_DATABASE_URL = (
    "postgresql+psycopg://study_hub:study_hub_dev_password"
    "@localhost:5432/study_hub_test"
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import sessionmaker

from app.db import engine, get_db
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def _migrate_test_db():
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
    yield


@pytest.fixture()
def db_session():
    connection = engine.connect()
    outer_transaction = connection.begin()

    Session = sessionmaker(bind=connection)
    session = Session()

    # Route code calls session.commit() as part of normal request handling
    # (see main.py), possibly more than once per test (e.g. login, then
    # refresh, then logout). A plain commit would end outer_transaction
    # early, so every commit is nested inside a SAVEPOINT instead — only the
    # savepoint ends, the outer transaction survives. This listener restarts
    # a fresh SAVEPOINT immediately after each one ends, so a second (or
    # third) commit in the same test stays nested too.
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
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
