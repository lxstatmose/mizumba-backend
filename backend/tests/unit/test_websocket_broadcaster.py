from uuid import uuid4

import pytest

import app.websocket.broadcaster as broadcaster
from app.websocket.manager import WebSocketManager


class FakeSocket:
    def __init__(self) -> None:
        self.accepted = False
        self.events: list[dict] = []

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, event: dict) -> None:
        self.events.append(event)


class FailingRedis:
    async def publish(self, *args, **kwargs) -> None:
        raise RuntimeError("redis unavailable")


@pytest.mark.asyncio
async def test_publish_to_user_falls_back_to_local_manager(monkeypatch) -> None:
    test_manager = WebSocketManager()
    user_id = uuid4()
    socket = FakeSocket()
    await test_manager.connect(user_id, socket)

    monkeypatch.setattr(broadcaster, "manager", test_manager)
    monkeypatch.setattr(broadcaster, "get_redis_client", lambda: FailingRedis())

    await broadcaster.publish_to_user(user_id, {"type": "test.event", "payload": {}})

    assert socket.events == [{"type": "test.event", "payload": {}}]
