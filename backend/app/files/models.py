from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class FileAssetKind(StrEnum):
    AVATAR = "avatar"
    AUDIO = "audio"
    IMAGE = "image"
    FILE = "file"
    CHANNEL_COVER = "channel_cover"


class FileAsset(SQLModel, table=True):
    __tablename__ = "file_assets"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    owner_id: UUID = Field(foreign_key="users.id", index=True)
    kind: FileAssetKind = Field(index=True)
    original_filename: str = Field(max_length=255)
    stored_filename: str = Field(max_length=255)
    storage_path: str = Field(max_length=500)
    url: str = Field(max_length=500)
    mime_type: str = Field(max_length=120)
    size_bytes: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)
