from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class NotificationType(StrEnum):
    NEW_MESSAGE = "new_message"
    ADDED_TO_GROUP = "added_to_group"
    MENTION = "mention"
    REACTION = "reaction"
    NEW_FOLLOWER = "new_follower"
    CHANNEL_UPDATE = "channel_update"


class Notification(SQLModel, table=True):
    __tablename__ = "notifications"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    actor_id: UUID | None = Field(default=None, foreign_key="users.id", index=True)
    chat_id: UUID | None = Field(default=None, foreign_key="chats.id", index=True)
    message_id: UUID | None = Field(default=None, foreign_key="messages.id", index=True)
    type: NotificationType = Field(index=True)
    title: str = Field(max_length=160)
    body: str = Field(max_length=500)
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON))
    is_read: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)
