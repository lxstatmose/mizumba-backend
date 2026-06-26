from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.channels.models import ChannelCategory, ChannelSubscriberRole
from app.users.schemas import UserPublic


class ChannelCreate(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    slug: str | None = Field(default=None, min_length=3, max_length=80)
    description: str = Field(min_length=1, max_length=500)
    cover_url: str | None = Field(default=None, max_length=500)
    category: ChannelCategory = ChannelCategory.GENERAL
    is_public: bool = True


class ChannelUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, min_length=1, max_length=500)
    cover_url: str | None = Field(default=None, max_length=500)
    category: ChannelCategory | None = None
    is_public: bool | None = None


class ChannelPostCreate(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    image_url: str | None = Field(default=None, max_length=500)


class ChannelPostUpdate(BaseModel):
    text: str | None = Field(default=None, min_length=1, max_length=4000)
    image_url: str | None = Field(default=None, max_length=500)


class ChannelPostPublic(BaseModel):
    id: UUID
    channel_id: UUID
    author_id: UUID
    author: UserPublic | None = None
    text: str
    image_url: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class ChannelSubscriberPublic(BaseModel):
    user: UserPublic
    role: ChannelSubscriberRole
    subscribed_at: datetime
    muted: bool


class ChannelSummary(BaseModel):
    id: UUID
    title: str
    slug: str
    description: str
    cover_url: str | None
    category: ChannelCategory
    is_public: bool
    is_subscribed: bool
    current_user_role: ChannelSubscriberRole | None
    subscribers_count: int
    last_post: ChannelPostPublic | None
    created_at: datetime
    updated_at: datetime


class ChannelDetail(ChannelSummary):
    subscribers: list[ChannelSubscriberPublic]
