from pydantic import BaseModel

from app.files.schemas import FileAssetPublic


class AudioTranscriptionResponse(BaseModel):
    text: str
    language: str | None
    duration: float | None = None
    file: FileAssetPublic
