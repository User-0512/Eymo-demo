"""
Authentication endpoint tests.

Uses the shared TestClient and database fixtures from conftest.py.
"""
from tests.conftest import client


def test_register_user():
    response = client.post(
        "/auth/register",
        json={"username": "testuser", "email": "test@example.com", "password": "password123"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "hashed_password" not in data  # Should not return password


def test_register_duplicate_user():
    client.post(
        "/auth/register",
        json={"username": "testuser", "email": "test@example.com", "password": "password123"}
    )
    # Duplicate username
    response = client.post(
        "/auth/register",
        json={"username": "testuser", "email": "other@example.com", "password": "password123"}
    )
    assert response.status_code == 400

    # Duplicate email
    response = client.post(
        "/auth/register",
        json={"username": "otheruser", "email": "test@example.com", "password": "password123"}
    )
    assert response.status_code == 400


def test_login_user():
    # Register first
    client.post(
        "/auth/register",
        json={"username": "loginuser", "email": "login@example.com", "password": "password123"}
    )

    # Login (OAuth2 uses form data)
    response = client.post(
        "/auth/login",
        data={"username": "loginuser", "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_get_current_user():
    # Register and login
    client.post(
        "/auth/register",
        json={"username": "meuser", "email": "me@example.com", "password": "password123"}
    )
    login_res = client.post(
        "/auth/login",
        data={"username": "meuser", "password": "password123"}
    )
    token = login_res.json()["access_token"]

    # Get Me
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "meuser"


def test_refresh_token():
    # Register and login
    client.post(
        "/auth/register",
        json={"username": "refreshuser", "email": "refresh@example.com", "password": "password123"}
    )
    login_res = client.post(
        "/auth/login",
        data={"username": "refreshuser", "password": "password123"}
    )
    refresh_token = login_res.json()["refresh_token"]

    # Refresh
    response = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data

