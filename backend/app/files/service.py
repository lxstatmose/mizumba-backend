import re
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlmodel import Session

from app.common.exceptions import bad_request
from app.core.config import get_settings
from app.files.models import FileAsset, FileAssetKind
from app.files.storage import upload_to_cloud_if_configured
from app.users.models import User


IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
AUDIO_MIME_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/wav",
    "audio/x-wav",
    "audio/webm",
    "audio/ogg",
    "audio/aac",
    "audio/m4a",
}
FILE_MIME_TYPES = {
    "application/pdf",
    "application/zip",
    "text/plain",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _sanitize_filename(filename: str) -> str:
    filename = Path(filename).name
    filename = re.sub(r"[^a-zA-Z0-9._-]+", "-", filename).strip(".-")
    return filename or "upload"


def _validate_mime_type(kind: FileAssetKind, mime_type: str) -> None:
    if kind in {FileAssetKind.AVATAR, FileAssetKind.IMAGE, FileAssetKind.CHANNEL_COVER}:
        if mime_type not in IMAGE_MIME_TYPES:
            raise bad_request("Only JPEG, PNG, WEBP and GIF images are allowed")
    elif kind == FileAssetKind.AUDIO:
        if mime_type not in AUDIO_MIME_TYPES:
            raise bad_request("Only MP3, MP4, WAV, WEBM, OGG, AAC and M4A audio files are allowed")
    elif kind == FileAssetKind.FILE and mime_type not in IMAGE_MIME_TYPES | AUDIO_MIME_TYPES | FILE_MIME_TYPES:
        raise bad_request("This file type is not allowed")


def _kind_folder(kind: FileAssetKind) -> str:
    return {
        FileAssetKind.AVATAR: "avatars",
        FileAssetKind.AUDIO: "audio",
        FileAssetKind.IMAGE: "images",
        FileAssetKind.FILE: "files",
        FileAssetKind.CHANNEL_COVER: "channel-covers",
    }[kind]


def save_upload_file(
    session: Session,
    *,
    current_user: User,
    upload: UploadFile,
    kind: FileAssetKind,
) -> FileAsset:
    settings = get_settings()
    mime_type = upload.content_type or "application/octet-stream"
    _validate_mime_type(kind, mime_type)

    original_filename = _sanitize_filename(upload.filename or "upload")
    extension = Path(original_filename).suffix.lower()
    stored_filename = f"{uuid4().hex}{extension}"
    folder = _kind_folder(kind)
    upload_dir = Path(settings.upload_dir) / folder
    upload_dir.mkdir(parents=True, exist_ok=True)
    storage_path = upload_dir / stored_filename

    max_size_mb = settings.max_audio_upload_size_mb if kind == FileAssetKind.AUDIO else settings.max_upload_size_mb
    max_size = max_size_mb * 1024 * 1024
    size = 0
    with storage_path.open("wb") as destination:
        while chunk := upload.file.read(1024 * 1024):
            size += len(chunk)
            if size > max_size:
                destination.close()
                storage_path.unlink(missing_ok=True)
                raise bad_request(f"File is too large. Max size is {max_size_mb} MB")
            destination.write(chunk)

    cloud_url = upload_to_cloud_if_configured(
        local_path=storage_path,
        folder=folder,
        stored_filename=stored_filename,
        mime_type=mime_type,
    )
    url = cloud_url or f"{settings.public_base_url}/uploads/{folder}/{stored_filename}"
    asset = FileAsset(
        owner_id=current_user.id,
        kind=kind,
        original_filename=original_filename,
        stored_filename=stored_filename,
        storage_path=str(storage_path),
        url=url,
        mime_type=mime_type,
        size_bytes=size,
    )
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset
