from fastapi.testclient import TestClient

from tests.conftest import auth_headers, register_user


def test_chat_message_unread_and_notifications_api(client: TestClient) -> None:
    alice = register_user(client, email="alice@example.com", display_name="Alice")
    bob = register_user(client, email="bob@example.com", display_name="Bob")
    alice_headers = auth_headers(alice)
    bob_headers = auth_headers(bob)

    chat_response = client.post(
        "/api/v1/chats/direct",
        headers=alice_headers,
        json={"user_id": bob["user"]["id"]},
    )
    assert chat_response.status_code == 201
    chat_id = chat_response.json()["id"]

    message_response = client.post(
        f"/api/v1/chats/{chat_id}/messages",
        headers=alice_headers,
        json={"text": "Hello Bob"},
    )
    assert message_response.status_code == 201
    message_id = message_response.json()["id"]

    bob_chats = client.get("/api/v1/chats", headers=bob_headers)
    assert bob_chats.status_code == 200
    assert bob_chats.json()[0]["unread_count"] == 1

    notifications = client.get("/api/v1/notifications", headers=bob_headers)
    assert notifications.status_code == 200
    assert notifications.json()["unread_count"] == 1
    notification_id = notifications.json()["items"][0]["id"]

    marked_notification = client.post(
        f"/api/v1/notifications/{notification_id}/read",
        headers=bob_headers,
    )
    assert marked_notification.status_code == 200
    assert marked_notification.json()["is_read"] is True

    read_response = client.post(
        f"/api/v1/chats/{chat_id}/read",
        headers=bob_headers,
        json={"message_id": message_id},
    )
    assert read_response.status_code == 200
    assert read_response.json()["unread_count"] == 0

    messages = client.get(f"/api/v1/chats/{chat_id}/messages", headers=bob_headers)
    assert messages.status_code == 200
    assert messages.json()[0]["text"] == "Hello Bob"
