from fastapi import APIRouter, Depends, File, UploadFile
from sqlmodel import Session

from app.auth.dependencies import get_current_user
from app.core.database import get_session
from app.files.models import FileAssetKind
from app.files.schemas import FileAssetPublic
from app.files.service import save_upload_file
from app.users.models import User
from app.users.schemas import UserPublic


router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload", response_model=FileAssetPublic)
def upload_file(
    kind: FileAssetKind = FileAssetKind.FILE,
    upload: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> FileAssetPublic:
    return save_upload_file(session, current_user=current_user, upload=upload, kind=kind)


@router.post("/avatar", response_model=UserPublic)
def upload_avatar(
    upload: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> User:
    asset = save_upload_file(
        session,
        current_user=current_user,
        upload=upload,
        kind=FileAssetKind.AVATAR,
    )
    current_user.avatar_url = asset.url
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user


@router.post("/channel-cover", response_model=FileAssetPublic)
def upload_channel_cover(
    upload: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> FileAssetPublic:
    return save_upload_file(
        session,
        current_user=current_user,
        upload=upload,
        kind=FileAssetKind.CHANNEL_COVER,
    )
