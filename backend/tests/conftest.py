"""Pytest fixtures: a throwaway in-memory database and an authenticated client."""

import os

# Point the app's own engine at an in-memory database before app modules read
# their settings, so running the suite never touches the development studyhub.db.
os.environ["DATABASE_URL"] = "sqlite://"

from collections.abc import Generator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """A fresh in-memory SQLite database per test.

    StaticPool keeps every connection pointed at the same in-memory database,
    which is what makes ":memory:" usable across the request thread pool.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def register(client: TestClient, username: str = "student", password: str = "password123") -> dict:
    """Create an account and return {'token', 'headers', 'user'}."""
    response = client.post(
        "/api/auth/register",
        json={"email": f"{username}@wisc.edu", "username": username, "password": password},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return {
        "token": body["access_token"],
        "headers": {"Authorization": f"Bearer {body['access_token']}"},
        "user": body["user"],
    }


@pytest.fixture
def alice(client: TestClient) -> dict:
    return register(client, "alice")


@pytest.fixture
def bob(client: TestClient) -> dict:
    return register(client, "bob")


def make_note(client: TestClient, headers: dict, **overrides) -> dict:
    payload = {
        "title": "Binary search, carefully",
        "content": "Off-by-one errors and how to avoid them.",
        "course_code": "CS400",
        "tags": ["algorithms"],
    }
    payload.update(overrides)
    response = client.post("/api/notes", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def make_group(client: TestClient, headers: dict, **overrides) -> dict:
    payload = {
        "name": "CS 400 Sunday sessions",
        "description": "Weekly problem set review.",
        "course_code": "CS400",
        "capacity": 3,
    }
    payload.update(overrides)
    response = client.post("/api/groups", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()
