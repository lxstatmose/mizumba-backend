from fastapi.testclient import TestClient

from app.core.config import get_settings
from tests.conftest import auth_headers, register_user


def test_channels_posts_and_file_upload_api(client: TestClient) -> None:
    owner = register_user(client, email="owner@example.com", display_name="Owner")
    subscriber = register_user(client, email="subscriber@example.com", display_name="Subscriber")
    owner_headers = auth_headers(owner)
    subscriber_headers = auth_headers(subscriber)

    avatar = client.post(
        "/api/v1/files/avatar",
        headers=owner_headers,
        files={"upload": ("avatar.png", b"image", "image/png")},
    )
    assert avatar.status_code == 200
    assert avatar.json()["avatar_url"].endswith(".png")

    channel = client.post(
        "/api/v1/channels",
        headers=owner_headers,
        json={
            "title": "Tech News Daily",
            "slug": "tech-news-daily",
            "description": "Tech updates",
            "category": "technology",
        },
    )
    assert channel.status_code == 200
    channel_id = channel.json()["id"]

    subscribed = client.post(f"/api/v1/channels/{channel_id}/subscribe", headers=subscriber_headers)
    assert subscribed.status_code == 200
    assert subscribed.json()["is_subscribed"] is True

    post = client.post(
        f"/api/v1/channels/{channel_id}/posts",
        headers=owner_headers,
        json={"text": "New launch"},
    )
    assert post.status_code == 200
    assert post.json()["text"] == "New launch"

    notifications = client.get("/api/v1/notifications", headers=subscriber_headers)
    assert notifications.status_code == 200
    assert notifications.json()["items"][0]["type"] == "channel_update"


def test_audio_transcribe_api_with_fake_whisper_model(client: TestClient, monkeypatch) -> None:
    class FakeWhisperModel:
        def transcribe(self, path: str, language: str | None = None) -> dict:
            return {"text": "hello from audio", "language": language or "en", "duration": 1.25}

    monkeypatch.setattr(
        "app.audio.service._load_whisper_model",
        lambda model_name: FakeWhisperModel(),
    )
    settings = get_settings()
    original_value = settings.enable_whisper_transcription
    settings.enable_whisper_transcription = True
    auth = register_user(client, email="audio-api@example.com", display_name="Audio User")

    try:
        response = client.post(
            "/api/v1/audio/transcribe",
            headers=auth_headers(auth),
            files={"upload": ("voice.webm", b"audio", "audio/webm")},
            data={"language": "en"},
        )
    finally:
        settings.enable_whisper_transcription = original_value

    assert response.status_code == 200
    assert response.json()["text"] == "hello from audio"
    assert response.json()["file"]["kind"] == "audio"


def test_audio_transcribe_returns_503_when_whisper_is_disabled(client: TestClient) -> None:
    auth = register_user(client, email="audio-disabled@example.com", display_name="Audio Disabled")

    response = client.post(
        "/api/v1/audio/transcribe",
        headers=auth_headers(auth),
        files={"upload": ("voice.webm", b"audio", "audio/webm")},
        data={"language": "en"},
    )

    assert response.status_code == 503
    assert "disabled" in response.json()["detail"].lower()
