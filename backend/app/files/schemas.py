from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.files.models import FileAssetKind


class FileAssetPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    kind: FileAssetKind
    original_filename: str
    url: str
    mime_type: str
    size_bytes: int
    created_at: datetime
