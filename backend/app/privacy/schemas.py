from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.privacy.models import DirectMessagePolicy
from app.users.schemas import UserPublic


class PrivacySettingsUpdate(BaseModel):
    direct_messages: DirectMessagePolicy | None = None
    show_online_status: bool | None = None


class PrivacySettingsPublic(BaseModel):
    user_id: UUID
    direct_messages: DirectMessagePolicy
    show_online_status: bool
    updated_at: datetime


class NotificationSettingsUpdate(BaseModel):
    new_messages: bool | None = None
    mentions: bool | None = None
    reactions: bool | None = None
    group_invites: bool | None = None
    channel_updates: bool | None = None


class NotificationSettingsPublic(BaseModel):
    user_id: UUID
    new_messages: bool
    mentions: bool
    reactions: bool
    group_invites: bool
    channel_updates: bool
    updated_at: datetime


class BlockedUserPublic(BaseModel):
    id: UUID
    blocked_user: UserPublic
    created_at: datetime
