from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    username: str | None
    display_name: str
    avatar_url: str | None
    bio: str | None
    is_verified: bool
    is_online: bool
    last_seen_at: datetime | None
    created_at: datetime


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=50)
    display_name: str | None = Field(default=None, min_length=2, max_length=100)
    avatar_url: str | None = Field(default=None, max_length=500)
    bio: str | None = Field(default=None, max_length=500)


class ProfileStats(BaseModel):
    messages_count: int = 0
    groups_count: int = 0
    channels_count: int = 0


class UserProfile(BaseModel):
    user: UserPublic
    stats: ProfileStats
