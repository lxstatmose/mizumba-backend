from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.notifications.models import NotificationType
from app.users.schemas import UserPublic


class NotificationPublic(BaseModel):
    id: UUID
    user_id: UUID
    actor_id: UUID | None
    actor: UserPublic | None = None
    chat_id: UUID | None
    message_id: UUID | None
    type: NotificationType
    title: str
    body: str
    payload: dict
    is_read: bool
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: list[NotificationPublic]
    unread_count: int
