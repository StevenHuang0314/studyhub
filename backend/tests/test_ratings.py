"""Rating rules: one per user per note, no self-rating, and correct aggregation."""

from fastapi.testclient import TestClient

from tests.conftest import make_note, register


def test_rate_a_note(client: TestClient, alice: dict, bob: dict) -> None:
    note = make_note(client, alice["headers"])
    response = client.put(
        f"/api/notes/{note['id']}/ratings",
        json={"score": 5, "comment": "Great breakdown."},
        headers=bob["headers"],
    )
    assert response.status_code == 200
    body = response.json()
    assert body["score"] == 5
    assert body["user"]["username"] == "bob"


def test_rating_requires_auth(client: TestClient, alice: dict) -> None:
    note = make_note(client, alice["headers"])
    response = client.put(f"/api/notes/{note['id']}/ratings", json={"score": 4})
    assert response.status_code == 401


def test_cannot_rate_your_own_note(client: TestClient, alice: dict) -> None:
    note = make_note(client, alice["headers"])
    response = client.put(
        f"/api/notes/{note['id']}/ratings", json={"score": 5}, headers=alice["headers"]
    )
    assert response.status_code == 400


def test_score_must_be_between_1_and_5(client: TestClient, alice: dict, bob: dict) -> None:
    note = make_note(client, alice["headers"])
    for bad_score in (0, 6, -3):
        response = client.put(
            f"/api/notes/{note['id']}/ratings",
            json={"score": bad_score},
            headers=bob["headers"],
        )
        assert response.status_code == 422


def test_rating_twice_updates_instead_of_duplicating(
    client: TestClient, alice: dict, bob: dict
) -> None:
    note = make_note(client, alice["headers"])
    client.put(f"/api/notes/{note['id']}/ratings", json={"score": 2}, headers=bob["headers"])
    client.put(
        f"/api/notes/{note['id']}/ratings",
        json={"score": 5, "comment": "Changed my mind."},
        headers=bob["headers"],
    )

    ratings = client.get(f"/api/notes/{note['id']}/ratings").json()
    assert len(ratings) == 1
    assert ratings[0]["score"] == 5
    assert ratings[0]["comment"] == "Changed my mind."


def test_average_rating_is_computed(client: TestClient, alice: dict, bob: dict) -> None:
    note = make_note(client, alice["headers"])
    carol = register(client, "carol")

    client.put(f"/api/notes/{note['id']}/ratings", json={"score": 4}, headers=bob["headers"])
    client.put(f"/api/notes/{note['id']}/ratings", json={"score": 5}, headers=carol["headers"])

    detail = client.get(f"/api/notes/{note['id']}").json()
    assert detail["average_rating"] == 4.5
    assert detail["rating_count"] == 2

    listed = client.get("/api/notes").json()["items"][0]
    assert listed["average_rating"] == 4.5
    assert listed["rating_count"] == 2


def test_delete_my_rating(client: TestClient, alice: dict, bob: dict) -> None:
    note = make_note(client, alice["headers"])
    client.put(f"/api/notes/{note['id']}/ratings", json={"score": 3}, headers=bob["headers"])

    assert client.delete(
        f"/api/notes/{note['id']}/ratings/me", headers=bob["headers"]
    ).status_code == 204
    assert client.get(f"/api/notes/{note['id']}").json()["rating_count"] == 0


def test_deleting_a_rating_you_never_left_is_404(client: TestClient, alice: dict, bob: dict) -> None:
    note = make_note(client, alice["headers"])
    response = client.delete(f"/api/notes/{note['id']}/ratings/me", headers=bob["headers"])
    assert response.status_code == 404


def test_deleting_a_note_removes_its_ratings(client: TestClient, alice: dict, bob: dict) -> None:
    note = make_note(client, alice["headers"])
    client.put(f"/api/notes/{note['id']}/ratings", json={"score": 5}, headers=bob["headers"])

    client.delete(f"/api/notes/{note['id']}", headers=alice["headers"])
    assert client.get(f"/api/notes/{note['id']}/ratings").status_code == 404


def test_sort_by_top_rated(client: TestClient, alice: dict, bob: dict) -> None:
    good = make_note(client, alice["headers"], title="Excellent notes")
    okay = make_note(client, alice["headers"], title="Okay notes")

    client.put(f"/api/notes/{good['id']}/ratings", json={"score": 5}, headers=bob["headers"])
    client.put(f"/api/notes/{okay['id']}/ratings", json={"score": 2}, headers=bob["headers"])

    items = client.get("/api/notes", params={"sort": "top_rated"}).json()["items"]
    assert items[0]["title"] == "Excellent notes"
