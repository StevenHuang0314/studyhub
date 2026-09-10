"""Registration, login and token handling."""

from fastapi.testclient import TestClient

from tests.conftest import register


def test_register_returns_token_and_user(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={"email": "New@Wisc.edu", "username": "newbie", "password": "password123"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == "new@wisc.edu"  # emails are normalized to lowercase
    assert "password" not in response.text and "hashed" not in response.text


def test_register_rejects_duplicate_email(client: TestClient) -> None:
    register(client, "dupe")
    response = client.post(
        "/api/auth/register",
        json={"email": "dupe@wisc.edu", "username": "someone_else", "password": "password123"},
    )
    assert response.status_code == 409
    assert "email" in response.json()["detail"]


def test_register_rejects_duplicate_username(client: TestClient) -> None:
    register(client, "taken")
    response = client.post(
        "/api/auth/register",
        json={"email": "other@wisc.edu", "username": "taken", "password": "password123"},
    )
    assert response.status_code == 409
    assert "username" in response.json()["detail"]


def test_register_rejects_short_password(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={"email": "short@wisc.edu", "username": "shorty", "password": "abc"},
    )
    assert response.status_code == 422


def test_login_with_correct_password(client: TestClient, alice: dict) -> None:
    response = client.post(
        "/api/auth/login", json={"email": "alice@wisc.edu", "password": "password123"}
    )
    assert response.status_code == 200
    assert response.json()["user"]["username"] == "alice"


def test_login_with_wrong_password_is_401(client: TestClient, alice: dict) -> None:
    response = client.post(
        "/api/auth/login", json={"email": "alice@wisc.edu", "password": "wrong-password"}
    )
    assert response.status_code == 401


def test_login_with_unknown_email_is_401(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login", json={"email": "ghost@wisc.edu", "password": "password123"}
    )
    assert response.status_code == 401


def test_oauth2_form_login_works(client: TestClient, alice: dict) -> None:
    """The form endpoint backing the Swagger "Authorize" button."""
    response = client.post(
        "/api/auth/token",
        data={"username": "alice@wisc.edu", "password": "password123"},
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_me_requires_a_token(client: TestClient) -> None:
    assert client.get("/api/auth/me").status_code == 401


def test_me_rejects_a_garbage_token(client: TestClient) -> None:
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert response.status_code == 401


def test_me_returns_the_signed_in_user(client: TestClient, alice: dict) -> None:
    response = client.get("/api/auth/me", headers=alice["headers"])
    assert response.status_code == 200
    assert response.json()["username"] == "alice"


def test_update_profile(client: TestClient, alice: dict) -> None:
    response = client.patch(
        "/api/auth/me", json={"bio": "Sophomore, CS major."}, headers=alice["headers"]
    )
    assert response.status_code == 200
    assert response.json()["bio"] == "Sophomore, CS major."


def test_cannot_take_someone_elses_username(client: TestClient, alice: dict, bob: dict) -> None:
    response = client.patch("/api/auth/me", json={"username": "bob"}, headers=alice["headers"])
    assert response.status_code == 409
