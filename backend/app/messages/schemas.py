from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.messages.models import MessageType
from app.users.schemas import UserPublic


class MessageCreate(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    type: MessageType = MessageType.TEXT
    attachment_url: str | None = Field(default=None, max_length=500)
    attachment_mime_type: str | None = Field(default=None, max_length=120)
    attachment_name: str | None = Field(default=None, max_length=255)
    attachment_size: int | None = None
    reply_to_id: UUID | None = None


class MessageUpdate(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class MessageReactionCreate(BaseModel):
    emoji: str = Field(min_length=1, max_length=32)


class MessageReactionPublic(BaseModel):
    id: UUID
    message_id: UUID
    user_id: UUID
    user: UserPublic | None = None
    emoji: str
    created_at: datetime


class MessagePublic(BaseModel):
    id: UUID
    chat_id: UUID
    sender_id: UUID
    sender: UserPublic | None = None
    text: str
    type: MessageType
    attachment_url: str | None
    attachment_mime_type: str | None
    attachment_name: str | None
    attachment_size: int | None
    reply_to_id: UUID | None
    created_at: datetime
    updated_at: datetime
    edited_at: datetime | None
    deleted_at: datetime | None
