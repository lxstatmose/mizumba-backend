from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class MessageType(StrEnum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    SYSTEM = "system"


class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    chat_id: UUID = Field(foreign_key="chats.id", index=True)
    sender_id: UUID = Field(foreign_key="users.id", index=True)
    text: str = Field(max_length=4000)
    type: MessageType = Field(default=MessageType.TEXT, index=True)
    attachment_url: str | None = Field(default=None, max_length=500)
    attachment_mime_type: str | None = Field(default=None, max_length=120)
    attachment_name: str | None = Field(default=None, max_length=255)
    attachment_size: int | None = None
    reply_to_id: UUID | None = Field(default=None, foreign_key="messages.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    edited_at: datetime | None = None
    deleted_at: datetime | None = None


class MessageReaction(SQLModel, table=True):
    __tablename__ = "message_reactions"
    __table_args__ = (UniqueConstraint("message_id", "user_id", "emoji", name="uq_message_reaction"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    message_id: UUID = Field(foreign_key="messages.id", index=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    emoji: str = Field(max_length=32)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)
