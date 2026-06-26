from fastapi.testclient import TestClient

from tests.conftest import auth_headers, register_user


def test_full_messenger_mvp_flow(client: TestClient) -> None:
    alice = register_user(client, email="e2e-alice@example.com", display_name="Alice")
    bob = register_user(client, email="e2e-bob@example.com", display_name="Bob")
    alice_headers = auth_headers(alice)
    bob_headers = auth_headers(bob)

    chat = client.post(
        "/api/v1/chats/direct",
        headers=alice_headers,
        json={"user_id": bob["user"]["id"]},
    )
    assert chat.status_code == 201
    chat_id = chat.json()["id"]

    uploaded = client.post(
        "/api/v1/files/upload",
        headers=alice_headers,
        data={"kind": "image"},
        files={"upload": ("photo.png", b"image", "image/png")},
    )
    assert uploaded.status_code == 200
    asset = uploaded.json()

    message = client.post(
        f"/api/v1/chats/{chat_id}/messages",
        headers=alice_headers,
        json={
            "text": "Photo for you",
            "type": "image",
            "attachment_url": asset["url"],
            "attachment_mime_type": asset["mime_type"],
            "attachment_name": asset["original_filename"],
            "attachment_size": asset["size_bytes"],
        },
    )
    assert message.status_code == 201
    message_id = message.json()["id"]
    assert message.json()["attachment_url"] == asset["url"]

    bob_notifications = client.get("/api/v1/notifications", headers=bob_headers)
    assert bob_notifications.status_code == 200
    assert bob_notifications.json()["unread_count"] == 1

    read = client.post(
        f"/api/v1/chats/{chat_id}/read",
        headers=bob_headers,
        json={"message_id": message_id},
    )
    assert read.status_code == 200
    assert read.json()["unread_count"] == 0

    channel = client.post(
        "/api/v1/channels",
        headers=alice_headers,
        json={
            "title": "Design Inspiration",
            "slug": "design-inspiration",
            "description": "Daily design ideas",
            "category": "design",
        },
    )
    assert channel.status_code == 200
    channel_id = channel.json()["id"]

    subscribed = client.post(f"/api/v1/channels/{channel_id}/subscribe", headers=bob_headers)
    assert subscribed.status_code == 200

    post = client.post(
        f"/api/v1/channels/{channel_id}/posts",
        headers=alice_headers,
        json={"text": "New brand assets uploaded"},
    )
    assert post.status_code == 200

    bob_profile = client.get("/api/v1/users/me/profile", headers=bob_headers)
    assert bob_profile.status_code == 200
    assert bob_profile.json()["stats"]["channels_count"] == 1
