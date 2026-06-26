from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class DirectMessagePolicy(StrEnum):
    EVERYONE = "everyone"
    NOBODY = "nobody"


class BlockedUser(SQLModel, table=True):
    __tablename__ = "blocked_users"
    __table_args__ = (UniqueConstraint("blocker_id", "blocked_id", name="uq_blocked_user"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    blocker_id: UUID = Field(foreign_key="users.id", index=True)
    blocked_id: UUID = Field(foreign_key="users.id", index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)


class UserPrivacySettings(SQLModel, table=True):
    __tablename__ = "user_privacy_settings"

    user_id: UUID = Field(foreign_key="users.id", primary_key=True, index=True)
    direct_messages: DirectMessagePolicy = Field(default=DirectMessagePolicy.EVERYONE)
    show_online_status: bool = True
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class UserNotificationSettings(SQLModel, table=True):
    __tablename__ = "user_notification_settings"

    user_id: UUID = Field(foreign_key="users.id", primary_key=True, index=True)
    new_messages: bool = True
    mentions: bool = True
    reactions: bool = True
    group_invites: bool = True
    channel_updates: bool = True
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
