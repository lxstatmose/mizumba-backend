from collections import defaultdict
from uuid import UUID

from fastapi import WebSocket


class WebSocketManager:
    def __init__(self) -> None:
        self._connections: dict[UUID, set[WebSocket]] = defaultdict(set)

    async def connect(self, user_id: UUID, websocket: WebSocket) -> bool:
        was_offline = not self._connections[user_id]
        await websocket.accept()
        self._connections[user_id].add(websocket)
        return was_offline

    def disconnect(self, user_id: UUID, websocket: WebSocket) -> bool:
        connections = self._connections.get(user_id)
        if not connections:
            return True

        connections.discard(websocket)
        if connections:
            return False

        self._connections.pop(user_id, None)
        return True

    def is_online(self, user_id: UUID) -> bool:
        return bool(self._connections.get(user_id))

    async def send_to_user(self, user_id: UUID, event: dict) -> None:
        connections = list(self._connections.get(user_id, set()))
        for websocket in connections:
            await websocket.send_json(event)

    async def send_to_users(self, user_ids: list[UUID] | set[UUID], event: dict) -> None:
        for user_id in set(user_ids):
            await self.send_to_user(user_id, event)


manager = WebSocketManager()
