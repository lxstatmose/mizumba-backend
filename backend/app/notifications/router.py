from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.auth.dependencies import get_current_user
from app.auth.schemas import MessageResponse
from app.core.database import get_session
from app.notifications.schemas import NotificationListResponse, NotificationPublic
from app.notifications.service import (
    delete_notification,
    get_unread_notifications_count,
    list_user_notifications,
    mark_all_notifications_read,
    mark_notification_read,
)
from app.users.models import User


router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    limit: int = Query(default=50, ge=1, le=100),
    unread_only: bool = False,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> NotificationListResponse:
    return NotificationListResponse(
        items=list_user_notifications(
            session,
            user=current_user,
            limit=limit,
            unread_only=unread_only,
        ),
        unread_count=get_unread_notifications_count(session, current_user),
    )


@router.post("/read-all", response_model=MessageResponse)
def read_all_notifications(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> MessageResponse:
    mark_all_notifications_read(session, current_user)
    return MessageResponse(message="All notifications were marked as read")


@router.post("/{notification_id}/read", response_model=NotificationPublic)
def read_notification(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> NotificationPublic:
    return mark_notification_read(session, user=current_user, notification_id=notification_id)


@router.delete("/{notification_id}", response_model=MessageResponse)
def remove_notification(
    notification_id: UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> MessageResponse:
    delete_notification(session, user=current_user, notification_id=notification_id)
    return MessageResponse(message="Notification deleted successfully")
