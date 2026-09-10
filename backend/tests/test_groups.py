"""Study group CRUD plus join/leave membership rules."""

from fastapi.testclient import TestClient

from tests.conftest import make_group, register


def test_create_group_adds_owner_as_member(client: TestClient, alice: dict) -> None:
    group = make_group(client, alice["headers"])
    assert group["owner"]["username"] == "alice"
    assert group["member_count"] == 1
    assert [member["username"] for member in group["members"]] == ["alice"]
    assert group["is_full"] is False


def test_create_group_requires_auth(client: TestClient) -> None:
    response = client.post(
        "/api/groups",
        json={"name": "Ghost group", "description": "", "course_code": "CS400", "capacity": 4},
    )
    assert response.status_code == 401


def test_join_group(client: TestClient, alice: dict, bob: dict) -> None:
    group = make_group(client, alice["headers"])
    response = client.post(f"/api/groups/{group['id']}/members", headers=bob["headers"])
    assert response.status_code == 201
    assert response.json()["member_count"] == 2


def test_cannot_join_twice(client: TestClient, alice: dict, bob: dict) -> None:
    group = make_group(client, alice["headers"])
    client.post(f"/api/groups/{group['id']}/members", headers=bob["headers"])
    second = client.post(f"/api/groups/{group['id']}/members", headers=bob["headers"])
    assert second.status_code == 409


def test_cannot_join_a_full_group(client: TestClient, alice: dict, bob: dict) -> None:
    group = make_group(client, alice["headers"], capacity=2)
    assert client.post(
        f"/api/groups/{group['id']}/members", headers=bob["headers"]
    ).status_code == 201

    carol = register(client, "carol")
    response = client.post(f"/api/groups/{group['id']}/members", headers=carol["headers"])
    assert response.status_code == 409
    assert response.json()["detail"] == "This group is full"


def test_leave_group(client: TestClient, alice: dict, bob: dict) -> None:
    group = make_group(client, alice["headers"])
    client.post(f"/api/groups/{group['id']}/members", headers=bob["headers"])

    assert client.delete(
        f"/api/groups/{group['id']}/members/me", headers=bob["headers"]
    ).status_code == 204
    assert client.get(f"/api/groups/{group['id']}").json()["member_count"] == 1


def test_owner_cannot_leave_their_own_group(client: TestClient, alice: dict) -> None:
    group = make_group(client, alice["headers"])
    response = client.delete(f"/api/groups/{group['id']}/members/me", headers=alice["headers"])
    assert response.status_code == 400


def test_leaving_a_group_you_are_not_in_is_404(client: TestClient, alice: dict, bob: dict) -> None:
    group = make_group(client, alice["headers"])
    response = client.delete(f"/api/groups/{group['id']}/members/me", headers=bob["headers"])
    assert response.status_code == 404


def test_only_owner_can_update(client: TestClient, alice: dict, bob: dict) -> None:
    group = make_group(client, alice["headers"])
    assert client.patch(
        f"/api/groups/{group['id']}", json={"location": "Union South"}, headers=bob["headers"]
    ).status_code == 403

    ok = client.patch(
        f"/api/groups/{group['id']}", json={"location": "Union South"}, headers=alice["headers"]
    )
    assert ok.status_code == 200
    assert ok.json()["location"] == "Union South"


def test_capacity_cannot_drop_below_member_count(client: TestClient, alice: dict, bob: dict) -> None:
    group = make_group(client, alice["headers"], capacity=5)
    carol = register(client, "carol")
    client.post(f"/api/groups/{group['id']}/members", headers=bob["headers"])
    client.post(f"/api/groups/{group['id']}/members", headers=carol["headers"])

    ok = client.patch(
        f"/api/groups/{group['id']}", json={"capacity": 3}, headers=alice["headers"]
    )
    assert ok.status_code == 200  # exactly the 3 current members

    too_small = client.patch(
        f"/api/groups/{group['id']}", json={"capacity": 2}, headers=alice["headers"]
    )
    assert too_small.status_code == 400


def test_only_owner_can_delete(client: TestClient, alice: dict, bob: dict) -> None:
    group = make_group(client, alice["headers"])
    assert client.delete(f"/api/groups/{group['id']}", headers=bob["headers"]).status_code == 403
    assert client.delete(f"/api/groups/{group['id']}", headers=alice["headers"]).status_code == 204
    assert client.get(f"/api/groups/{group['id']}").status_code == 404


def test_filter_groups_by_course_and_space(client: TestClient, alice: dict, bob: dict) -> None:
    make_group(client, alice["headers"], name="CS 537 crew", course_code="CS537", capacity=2)
    make_group(client, alice["headers"], name="CS 400 crew", course_code="CS400", capacity=5)

    by_course = client.get("/api/groups", params={"course_code": "CS537"}).json()
    assert by_course["total"] == 1

    full_group_id = by_course["items"][0]["id"]
    client.post(f"/api/groups/{full_group_id}/members", headers=bob["headers"])

    with_space = client.get("/api/groups", params={"has_space": True}).json()
    assert full_group_id not in {item["id"] for item in with_space["items"]}


def test_my_groups_lists_owned_and_joined(client: TestClient, alice: dict, bob: dict) -> None:
    owned = make_group(client, alice["headers"], name="Owned by bob's friend")
    joined = make_group(client, alice["headers"], name="Second group")
    client.post(f"/api/groups/{joined['id']}/members", headers=bob["headers"])

    alice_groups = client.get("/api/users/me/groups", headers=alice["headers"]).json()
    assert {group["id"] for group in alice_groups} == {owned["id"], joined["id"]}

    bob_groups = client.get("/api/users/me/groups", headers=bob["headers"]).json()
    assert {group["id"] for group in bob_groups} == {joined["id"]}
