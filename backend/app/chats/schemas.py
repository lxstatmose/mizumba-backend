from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.chats.models import ChatMemberRole, ChatType
from app.messages.schemas import MessagePublic
from app.users.schemas import UserPublic


class DirectChatCreate(BaseModel):
    user_id: UUID


class GroupChatCreate(BaseModel):
    title: str = Field(min_length=2, max_length=100)
    member_ids: list[UUID] = Field(min_length=1)
    avatar_url: str | None = Field(default=None, max_length=500)


class ChatMemberAdd(BaseModel):
    user_id: UUID
    role: ChatMemberRole = ChatMemberRole.MEMBER


class ChatReadRequest(BaseModel):
    message_id: UUID | None = None


class ChatMemberPublic(BaseModel):
    user: UserPublic
    role: ChatMemberRole
    joined_at: datetime
    last_read_at: datetime | None
    muted: bool


class ChatSummary(BaseModel):
    id: UUID
    type: ChatType
    title: str | None
    avatar_url: str | None
    last_message: MessagePublic | None
    unread_count: int
    members_count: int
    updated_at: datetime


class ChatDetail(ChatSummary):
    members: list[ChatMemberPublic]
