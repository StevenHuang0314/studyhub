"""Note CRUD, ownership rules, search, filtering and pagination."""

from fastapi.testclient import TestClient

from tests.conftest import make_note


def test_create_note_requires_auth(client: TestClient) -> None:
    response = client.post(
        "/api/notes",
        json={"title": "Anonymous notes", "content": "...", "course_code": "CS400"},
    )
    assert response.status_code == 401


def test_create_note(client: TestClient, alice: dict) -> None:
    note = make_note(client, alice["headers"], tags=["Trees", " trees ", "exam-prep"])
    assert note["author"]["username"] == "alice"
    assert note["course_code"] == "CS400"
    assert note["tags"] == ["trees", "exam-prep"]  # lowercased and de-duplicated
    assert note["average_rating"] is None
    assert note["rating_count"] == 0


def test_course_code_is_normalized(client: TestClient, alice: dict) -> None:
    note = make_note(client, alice["headers"], course_code=" cs 537 ")
    assert note["course_code"] == "CS537"


def test_get_note(client: TestClient, alice: dict) -> None:
    created = make_note(client, alice["headers"])
    response = client.get(f"/api/notes/{created['id']}")
    assert response.status_code == 200
    assert response.json()["title"] == created["title"]


def test_get_missing_note_is_404(client: TestClient) -> None:
    assert client.get("/api/notes/9999").status_code == 404


def test_update_own_note(client: TestClient, alice: dict) -> None:
    note = make_note(client, alice["headers"])
    response = client.patch(
        f"/api/notes/{note['id']}",
        json={"title": "Binary search, even more carefully"},
        headers=alice["headers"],
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Binary search, even more carefully"
    assert response.json()["content"] == note["content"]  # untouched fields survive a PATCH


def test_cannot_update_someone_elses_note(client: TestClient, alice: dict, bob: dict) -> None:
    note = make_note(client, alice["headers"])
    response = client.patch(
        f"/api/notes/{note['id']}", json={"title": "Hijacked"}, headers=bob["headers"]
    )
    assert response.status_code == 403


def test_delete_own_note(client: TestClient, alice: dict) -> None:
    note = make_note(client, alice["headers"])
    assert client.delete(f"/api/notes/{note['id']}", headers=alice["headers"]).status_code == 204
    assert client.get(f"/api/notes/{note['id']}").status_code == 404


def test_cannot_delete_someone_elses_note(client: TestClient, alice: dict, bob: dict) -> None:
    note = make_note(client, alice["headers"])
    assert client.delete(f"/api/notes/{note['id']}", headers=bob["headers"]).status_code == 403


def test_search_matches_title_and_body(client: TestClient, alice: dict) -> None:
    make_note(client, alice["headers"], title="Graph traversal notes", content="BFS and DFS")
    make_note(client, alice["headers"], title="Sorting notes", content="Quicksort partitioning")

    by_title = client.get("/api/notes", params={"search": "graph"}).json()
    assert by_title["total"] == 1
    assert by_title["items"][0]["title"] == "Graph traversal notes"

    by_body = client.get("/api/notes", params={"search": "quicksort"}).json()
    assert by_body["total"] == 1


def test_filter_by_course_and_tag(client: TestClient, alice: dict) -> None:
    make_note(client, alice["headers"], title="OS scheduling", course_code="CS537", tags=["mlfq"])
    make_note(client, alice["headers"], title="Tree rotations", course_code="CS400", tags=["trees"])

    by_course = client.get("/api/notes", params={"course_code": "cs537"}).json()
    assert by_course["total"] == 1
    assert by_course["items"][0]["title"] == "OS scheduling"

    by_tag = client.get("/api/notes", params={"tag": "trees"}).json()
    assert by_tag["total"] == 1


def test_pagination_reports_total(client: TestClient, alice: dict) -> None:
    for index in range(5):
        make_note(client, alice["headers"], title=f"Lecture {index} notes")

    page = client.get("/api/notes", params={"skip": 0, "limit": 2}).json()
    assert page["total"] == 5
    assert len(page["items"]) == 2

    second_page = client.get("/api/notes", params={"skip": 2, "limit": 2}).json()
    assert {item["id"] for item in page["items"]}.isdisjoint(
        {item["id"] for item in second_page["items"]}
    )


def test_course_code_list(client: TestClient, alice: dict) -> None:
    make_note(client, alice["headers"], course_code="CS400")
    make_note(client, alice["headers"], course_code="CS537")
    make_note(client, alice["headers"], course_code="CS400")

    response = client.get("/api/notes/courses")
    assert response.status_code == 200
    assert response.json() == ["CS400", "CS537"]


def test_my_notes_endpoint(client: TestClient, alice: dict, bob: dict) -> None:
    make_note(client, alice["headers"], title="Alice's notes")
    make_note(client, bob["headers"], title="Bob's notes")

    response = client.get("/api/users/me/notes", headers=alice["headers"])
    assert response.status_code == 200
    assert [note["title"] for note in response.json()] == ["Alice's notes"]
