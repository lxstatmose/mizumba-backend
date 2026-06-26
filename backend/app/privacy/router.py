from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.auth.dependencies import get_current_user
from app.auth.schemas import MessageResponse
from app.core.database import get_session
from app.privacy.schemas import (
    BlockedUserPublic,
    NotificationSettingsPublic,
    NotificationSettingsUpdate,
    PrivacySettingsPublic,
    PrivacySettingsUpdate,
)
from app.privacy.service import (
    block_user,
    get_notification_settings,
    get_privacy_settings,
    list_blocked_users,
    unblock_user,
    update_notification_settings,
    update_privacy_settings,
)
from app.users.models import User


router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/privacy", response_model=PrivacySettingsPublic)
def read_privacy_settings(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> PrivacySettingsPublic:
    return get_privacy_settings(session, current_user)


@router.patch("/privacy", response_model=PrivacySettingsPublic)
def change_privacy_settings(
    payload: PrivacySettingsUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> PrivacySettingsPublic:
    return update_privacy_settings(
        session,
        current_user,
        direct_messages=payload.direct_messages,
        show_online_status=payload.show_online_status,
    )


@router.get("/notifications", response_model=NotificationSettingsPublic)
def read_notification_settings(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> NotificationSettingsPublic:
    return get_notification_settings(session, current_user.id)


@router.patch("/notifications", response_model=NotificationSettingsPublic)
def change_notification_settings(
    payload: NotificationSettingsUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> NotificationSettingsPublic:
    return update_notification_settings(session, current_user, updates=payload.model_dump())


@router.get("/blocks", response_model=list[BlockedUserPublic])
def read_blocked_users(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[BlockedUserPublic]:
    return list_blocked_users(session, current_user)


@router.post("/blocks/{user_id}", response_model=MessageResponse)
def block_account(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> MessageResponse:
    block_user(session, user=current_user, blocked_user_id=user_id)
    return MessageResponse(message="User blocked successfully")


@router.delete("/blocks/{user_id}", response_model=MessageResponse)
def unblock_account(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> MessageResponse:
    unblock_user(session, user=current_user, blocked_user_id=user_id)
    return MessageResponse(message="User unblocked successfully")
