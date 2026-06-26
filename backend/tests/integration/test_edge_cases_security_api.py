from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import rate_limit_state
from tests.conftest import auth_headers, register_user


def test_duplicate_registration_and_protected_route_security_headers(client: TestClient) -> None:
    register_user(client, email="edge@example.com", display_name="Edge User")

    duplicate = client.post(
        "/api/v1/auth/register",
        json={
            "email": "edge@example.com",
            "password": "password123",
            "display_name": "Edge User",
        },
    )
    assert duplicate.status_code == 400
    assert duplicate.headers["X-Content-Type-Options"] == "nosniff"
    assert duplicate.headers["X-Frame-Options"] == "DENY"

    protected = client.get("/api/v1/users/me")
    assert protected.status_code == 401
    assert protected.headers["X-Content-Type-Options"] == "nosniff"


def test_rate_limit_uses_forwarded_ip_and_returns_retry_after(client: TestClient) -> None:
    settings = get_settings()
    original_requests = settings.rate_limit_requests
    original_window = settings.rate_limit_window_seconds
    settings.rate_limit_requests = 2
    settings.rate_limit_window_seconds = 30
    rate_limit_state.clear()

    try:
        headers = {"X-Forwarded-For": "203.0.113.10"}
        assert client.get("/api/v1/auth/login-options", headers=headers).status_code == 200
        assert client.get("/api/v1/auth/login-options", headers=headers).status_code == 200

        limited = client.get("/api/v1/auth/login-options", headers=headers)
        assert limited.status_code == 429
        assert limited.json()["detail"] == "Too many requests"
        assert limited.headers["Retry-After"] == "30"
        assert limited.headers["X-Content-Type-Options"] == "nosniff"
    finally:
        settings.rate_limit_requests = original_requests
        settings.rate_limit_window_seconds = original_window
        rate_limit_state.clear()


def test_blocks_prevent_direct_chat(client: TestClient) -> None:
    alice = register_user(client, email="block-alice@example.com", display_name="Alice")
    bob = register_user(client, email="block-bob@example.com", display_name="Bob")
    alice_headers = auth_headers(alice)
    bob_headers = auth_headers(bob)

    blocked = client.post(f"/api/v1/settings/blocks/{bob['user']['id']}", headers=alice_headers)
    assert blocked.status_code == 200

    chat = client.post(
        "/api/v1/chats/direct",
        headers=bob_headers,
        json={"user_id": alice["user"]["id"]},
    )
    assert chat.status_code == 403


def test_notification_settings_can_disable_new_message_notifications(client: TestClient) -> None:
    alice = register_user(client, email="notify-alice@example.com", display_name="Alice")
    bob = register_user(client, email="notify-bob@example.com", display_name="Bob")
    alice_headers = auth_headers(alice)
    bob_headers = auth_headers(bob)

    settings_response = client.patch(
        "/api/v1/settings/notifications",
        headers=bob_headers,
        json={"new_messages": False},
    )
    assert settings_response.status_code == 200
    assert settings_response.json()["new_messages"] is False

    chat = client.post(
        "/api/v1/chats/direct",
        headers=alice_headers,
        json={"user_id": bob["user"]["id"]},
    )
    assert chat.status_code == 201

    message = client.post(
        f"/api/v1/chats/{chat.json()['id']}/messages",
        headers=alice_headers,
        json={"text": "This should not create a new-message notification"},
    )
    assert message.status_code == 201

    notifications = client.get("/api/v1/notifications", headers=bob_headers)
    assert notifications.status_code == 200
    assert notifications.json()["unread_count"] == 0


def test_reactions_are_idempotent_and_removable(client: TestClient) -> None:
    alice = register_user(client, email="react-alice@example.com", display_name="Alice")
    bob = register_user(client, email="react-bob@example.com", display_name="Bob")
    alice_headers = auth_headers(alice)
    bob_headers = auth_headers(bob)

    chat = client.post(
        "/api/v1/chats/direct",
        headers=alice_headers,
        json={"user_id": bob["user"]["id"]},
    )
    message = client.post(
        f"/api/v1/chats/{chat.json()['id']}/messages",
        headers=alice_headers,
        json={"text": "React to this"},
    )
    message_id = message.json()["id"]

    first = client.post(f"/api/v1/messages/{message_id}/reactions", headers=bob_headers, json={"emoji": "👍"})
    second = client.post(f"/api/v1/messages/{message_id}/reactions", headers=bob_headers, json={"emoji": "👍"})
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    reactions = client.get(f"/api/v1/messages/{message_id}/reactions", headers=alice_headers)
    assert reactions.status_code == 200
    assert len(reactions.json()) == 1

    removed = client.request("DELETE", f"/api/v1/messages/{message_id}/reactions", headers=bob_headers, json={"emoji": "👍"})
    assert removed.status_code == 200
    assert client.get(f"/api/v1/messages/{message_id}/reactions", headers=alice_headers).json() == []


def test_mentions_create_notification_when_new_message_notifications_are_disabled(client: TestClient) -> None:
    alice = register_user(client, email="mention-alice@example.com", display_name="Alice")
    bob = register_user(client, email="mention-bob@example.com", display_name="Bob")
    alice_headers = auth_headers(alice)
    bob_headers = auth_headers(bob)

    username = client.patch("/api/v1/users/me", headers=bob_headers, json={"username": "bob_mention"})
    assert username.status_code == 200

    client.patch("/api/v1/settings/notifications", headers=bob_headers, json={"new_messages": False})
    chat = client.post(
        "/api/v1/chats/direct",
        headers=alice_headers,
        json={"user_id": bob["user"]["id"]},
    )
    message = client.post(
        f"/api/v1/chats/{chat.json()['id']}/messages",
        headers=alice_headers,
        json={"text": "Hey @bob_mention, check this"},
    )
    assert message.status_code == 201

    notifications = client.get("/api/v1/notifications", headers=bob_headers)
    assert notifications.status_code == 200
    assert notifications.json()["unread_count"] == 1
    assert notifications.json()["items"][0]["type"] == "mention"
