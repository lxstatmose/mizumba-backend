from io import BytesIO
from pathlib import Path

import pytest
from fastapi import UploadFile
from sqlmodel import Session

from app.auth.service import register_user
from app.common.exceptions import bad_request
from app.core.config import get_settings
from app.files.models import FileAssetKind
from app.files.service import save_upload_file


def _upload(filename: str, content_type: str, body: bytes = b"file") -> UploadFile:
    upload = UploadFile(filename=filename, file=BytesIO(body))
    upload.headers = {"content-type": content_type}
    return upload


def test_save_avatar_file(db_session: Session, tmp_path: Path) -> None:
    settings = get_settings()
    original_upload_dir = settings.upload_dir
    settings.upload_dir = str(tmp_path)
    user = register_user(
        db_session,
        email="file@example.com",
        password="password123",
        display_name="File User",
    )

    asset = save_upload_file(
        db_session,
        current_user=user,
        upload=_upload("avatar.png", "image/png", b"image"),
        kind=FileAssetKind.AVATAR,
    )

    assert asset.kind == FileAssetKind.AVATAR
    assert asset.mime_type == "image/png"
    assert Path(asset.storage_path).exists()
    settings.upload_dir = original_upload_dir


def test_reject_invalid_avatar_mime_type(db_session: Session) -> None:
    user = register_user(
        db_session,
        email="invalid-file@example.com",
        password="password123",
        display_name="File User",
    )

    with pytest.raises(type(bad_request("bad"))):
        save_upload_file(
            db_session,
            current_user=user,
            upload=_upload("avatar.txt", "text/plain", b"text"),
            kind=FileAssetKind.AVATAR,
        )
