from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class ChannelCategory(StrEnum):
    DESIGN = "design"
    TECHNOLOGY = "technology"
    PROGRAMMING = "programming"
    GENERAL = "general"


class ChannelSubscriberRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    SUBSCRIBER = "subscriber"


class Channel(SQLModel, table=True):
    __tablename__ = "channels"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    title: str = Field(max_length=120)
    slug: str = Field(index=True, unique=True, max_length=80)
    description: str = Field(max_length=500)
    cover_url: str | None = Field(default=None, max_length=500)
    category: ChannelCategory = Field(default=ChannelCategory.GENERAL, index=True)
    created_by_id: UUID = Field(foreign_key="users.id", index=True)
    is_public: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ChannelSubscriber(SQLModel, table=True):
    __tablename__ = "channel_subscribers"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    channel_id: UUID = Field(foreign_key="channels.id", index=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    role: ChannelSubscriberRole = Field(default=ChannelSubscriberRole.SUBSCRIBER, index=True)
    subscribed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    muted: bool = False


class ChannelPost(SQLModel, table=True):
    __tablename__ = "channel_posts"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    channel_id: UUID = Field(foreign_key="channels.id", index=True)
    author_id: UUID = Field(foreign_key="users.id", index=True)
    text: str = Field(max_length=4000)
    image_url: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    deleted_at: datetime | None = None
