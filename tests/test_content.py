"""
Content CRUD endpoint tests.

Uses the shared TestClient and database fixtures from conftest.py.
External services (moderation, embeddings, rules) are mocked.
"""
import pytest
from unittest.mock import patch

from tests.conftest import client


@pytest.fixture
def auth_headers():
    """Register and login a user, returning Authorization headers."""
    client.post(
        "/auth/register",
        json={"username": "contentuser", "email": "content@example.com", "password": "password123"}
    )
    res = client.post(
        "/auth/login",
        data={"username": "contentuser", "password": "password123"}
    )
    token = res.json().get("access_token")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_other():
    """A second user for authorization testing."""
    client.post(
        "/auth/register",
        json={"username": "otheruser", "email": "other@example.com", "password": "password123"}
    )
    res = client.post(
        "/auth/login",
        data={"username": "otheruser", "password": "password123"}
    )
    token = res.json().get("access_token")
    return {"Authorization": f"Bearer {token}"}


@patch("services.api.app.routers.content.classify_content")
@patch("services.api.app.routers.content.generate_embedding")
@patch("services.api.app.routers.content.passes_basic_rules")
def test_create_content(mock_rules, mock_embed, mock_classify, auth_headers):
    mock_rules.return_value = True
    mock_classify.return_value = {"status": "approved", "subject_tag": "Math"}
    mock_embed.return_value = [0.1] * 384

    response = client.post(
        "/content/",
        json={
            "text": "1 + 1 = 2",
            "content_type": "text",
            "difficulty": "beginner"
        },
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["text"] == "1 + 1 = 2"
    assert data["subject_tag"] == "Math"
    assert data["difficulty"] == "beginner"
    assert data["moderation_status"] == "approved"


@patch("services.api.app.routers.content.classify_content")
@patch("services.api.app.routers.content.generate_embedding")
@patch("services.api.app.routers.content.passes_basic_rules")
def test_get_content(mock_rules, mock_embed, mock_classify, auth_headers):
    mock_rules.return_value = True
    mock_classify.return_value = {"status": "approved", "subject_tag": "Science"}
    mock_embed.return_value = [0.1] * 384

    res = client.post("/content/", json={"text": "E=mc^2"}, headers=auth_headers)
    content_id = res.json()["id"]

    response = client.get(f"/content/{content_id}")
    assert response.status_code == 200
    assert response.json()["text"] == "E=mc^2"


@patch("services.api.app.routers.content.classify_content")
@patch("services.api.app.routers.content.generate_embedding")
@patch("services.api.app.routers.content.passes_basic_rules")
def test_update_content_author_only(mock_rules, mock_embed, mock_classify, auth_headers, auth_headers_other):
    mock_rules.return_value = True
    mock_classify.return_value = {"status": "approved", "subject_tag": "Science"}
    mock_embed.return_value = [0.1] * 384

    res = client.post("/content/", json={"text": "Initial text"}, headers=auth_headers)
    content_id = res.json()["id"]

    # Try updating with other user
    response = client.put(
        f"/content/{content_id}",
        json={"text": "Hacked text"},
        headers=auth_headers_other
    )
    assert response.status_code == 403

    # Update with author
    response = client.put(
        f"/content/{content_id}",
        json={"text": "Updated text"},
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["text"] == "Updated text"


@patch("services.api.app.routers.content.classify_content")
@patch("services.api.app.routers.content.generate_embedding")
@patch("services.api.app.routers.content.passes_basic_rules")
def test_delete_content(mock_rules, mock_embed, mock_classify, auth_headers, auth_headers_other):
    mock_rules.return_value = True
    mock_classify.return_value = {"status": "approved", "subject_tag": "History"}
    mock_embed.return_value = [0.1] * 384

    res = client.post("/content/", json={"text": "History fact"}, headers=auth_headers)
    content_id = res.json()["id"]

    # Other user delete
    response = client.delete(f"/content/{content_id}", headers=auth_headers_other)
    assert response.status_code == 403

    # Author delete
    response = client.delete(f"/content/{content_id}", headers=auth_headers)
    assert response.status_code == 204

    # Verify deleted
    response = client.get(f"/content/{content_id}")
    assert response.status_code == 404

