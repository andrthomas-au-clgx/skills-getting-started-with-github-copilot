from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from src.app import activities, app


@pytest.fixture(autouse=True)
def restore_participants() -> Iterator[None]:
    original_participants = {
        activity_name: activity["participants"][:]
        for activity_name, activity in activities.items()
    }
    yield
    for activity_name, participants in original_participants.items():
        activities[activity_name]["participants"][:] = participants


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_get_activities_returns_activity_data(client: TestClient) -> None:
    response = client.get("/activities")

    assert response.status_code == 200
    assert "Chess Club" in response.json()
    assert response.json()["Chess Club"]["participants"] == activities["Chess Club"]["participants"]


def test_root_redirects_to_static_index(client: TestClient) -> None:
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


def test_signup_adds_student_to_activity(client: TestClient) -> None:
    email = "new.student@mergington.edu"

    response = client.post("/activities/Chess Club/signup", params={"email": email})

    assert response.status_code == 200
    assert response.json() == {"message": f"Signed up {email} for Chess Club"}
    assert email in activities["Chess Club"]["participants"]


def test_signup_returns_not_found_for_unknown_activity(client: TestClient) -> None:
    response = client.post(
        "/activities/Unknown Club/signup",
        params={"email": "new.student@mergington.edu"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}


def test_signup_returns_bad_request_for_duplicate_student(client: TestClient) -> None:
    email = activities["Chess Club"]["participants"][0]

    response = client.post("/activities/Chess Club/signup", params={"email": email})

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Student already signed up for this activity"
    }


def test_signup_requires_email(client: TestClient) -> None:
    response = client.post("/activities/Chess Club/signup")

    assert response.status_code == 422


def test_unregister_removes_student_from_activity(client: TestClient) -> None:
    email = activities["Chess Club"]["participants"][0]

    response = client.delete("/activities/Chess Club/signup", params={"email": email})

    assert response.status_code == 200
    assert response.json() == {"message": f"Unregistered {email} from Chess Club"}
    assert email not in activities["Chess Club"]["participants"]


def test_unregister_returns_not_found_for_unknown_activity(client: TestClient) -> None:
    response = client.delete(
        "/activities/Unknown Club/signup",
        params={"email": "student@mergington.edu"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}


def test_unregister_returns_not_found_for_non_member(client: TestClient) -> None:
    response = client.delete(
        "/activities/Chess Club/signup",
        params={"email": "not-enrolled@mergington.edu"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Student not signed up for this activity"}


def test_delete_participant_alias_unregisters_student(client: TestClient) -> None:
    email = activities["Chess Club"]["participants"][0]

    response = client.delete(
        "/activities/Chess Club/participants",
        params={"email": email},
    )

    assert response.status_code == 200
    assert email not in activities["Chess Club"]["participants"]