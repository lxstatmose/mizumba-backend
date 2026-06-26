from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class ChatType(StrEnum):
    DIRECT = "direct"
    GROUP = "group"


class ChatMemberRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class Chat(SQLModel, table=True):
    __tablename__ = "chats"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    type: ChatType = Field(index=True)
    title: str | None = Field(default=None, max_length=100)
    avatar_url: str | None = Field(default=None, max_length=500)
    created_by_id: UUID = Field(foreign_key="users.id", index=True)
    last_message_id: UUID | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ChatMember(SQLModel, table=True):
    __tablename__ = "chat_members"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    chat_id: UUID = Field(foreign_key="chats.id", index=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    role: ChatMemberRole = Field(default=ChatMemberRole.MEMBER, index=True)
    joined_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_read_at: datetime | None = None
    muted: bool = False
