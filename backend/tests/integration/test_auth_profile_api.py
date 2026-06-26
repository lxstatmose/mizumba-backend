from fastapi.testclient import TestClient

from tests.conftest import auth_headers, register_user


def test_register_login_profile_and_change_password(client: TestClient) -> None:
    auth = register_user(client, email="auth@example.com", display_name="Auth User")
    headers = auth_headers(auth)

    me = client.get("/api/v1/users/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "auth@example.com"

    patched = client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={"username": "AuthUser", "bio": "Hello"},
    )
    assert patched.status_code == 200
    assert patched.json()["username"] == "authuser"
    assert patched.json()["bio"] == "Hello"

    changed = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "password123", "new_password": "newpassword123"},
    )
    assert changed.status_code == 200

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "auth@example.com", "password": "newpassword123"},
    )
    assert login.status_code == 200


def test_login_options_country_rules(client: TestClient) -> None:
    response = client.get("/api/v1/auth/login-options", headers={"X-Country-Code": "RU"})

    assert response.status_code == 200
    assert response.json()["google"] is False
    assert response.json()["apple"] is False
