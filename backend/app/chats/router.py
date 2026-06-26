from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.auth.dependencies import get_current_user
from app.chats.schemas import (
    ChatDetail,
    ChatMemberAdd,
    ChatReadRequest,
    ChatSummary,
    DirectChatCreate,
    GroupChatCreate,
)
from app.chats.service import (
    add_chat_member,
    create_direct_chat,
    create_group_chat,
    get_chat_detail,
    list_user_chats,
    mark_chat_read,
    remove_chat_member,
)
from app.core.database import get_session
from app.messages.schemas import MessageCreate, MessagePublic
from app.messages.service import create_message, list_chat_messages
from app.users.models import User


router = APIRouter(prefix="/chats", tags=["chats"])


@router.get("", response_model=list[ChatSummary])
def list_chats(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[ChatSummary]:
    return list_user_chats(session, current_user)


@router.post("/direct", response_model=ChatDetail, status_code=status.HTTP_201_CREATED)
def create_direct(
    payload: DirectChatCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ChatDetail:
    return create_direct_chat(session, current_user, payload.user_id)


@router.post("/group", response_model=ChatDetail, status_code=status.HTTP_201_CREATED)
def create_group(
    payload: GroupChatCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ChatDetail:
    return create_group_chat(
        session,
        current_user,
        title=payload.title,
        member_ids=payload.member_ids,
        avatar_url=payload.avatar_url,
    )


@router.get("/{chat_id}", response_model=ChatDetail)
def get_chat(
    chat_id: UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ChatDetail:
    return get_chat_detail(session, chat_id, current_user)


@router.post("/{chat_id}/members", response_model=ChatDetail)
def add_member(
    chat_id: UUID,
    payload: ChatMemberAdd,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ChatDetail:
    return add_chat_member(
        session,
        chat_id=chat_id,
        current_user=current_user,
        user_id=payload.user_id,
        role=payload.role,
    )


@router.delete("/{chat_id}/members/{user_id}", response_model=ChatDetail)
def remove_member(
    chat_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ChatDetail:
    return remove_chat_member(session, chat_id=chat_id, current_user=current_user, user_id=user_id)


@router.post("/{chat_id}/read", response_model=ChatSummary)
def mark_read(
    chat_id: UUID,
    payload: ChatReadRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ChatSummary:
    return mark_chat_read(
        session,
        chat_id=chat_id,
        current_user=current_user,
        message_id=payload.message_id,
    )


@router.get("/{chat_id}/messages", response_model=list[MessagePublic])
def get_messages(
    chat_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    before_message_id: UUID | None = None,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[MessagePublic]:
    return list_chat_messages(
        session,
        chat_id=chat_id,
        current_user=current_user,
        limit=limit,
        before_message_id=before_message_id,
    )


@router.post("/{chat_id}/messages", response_model=MessagePublic, status_code=status.HTTP_201_CREATED)
def send_message(
    chat_id: UUID,
    payload: MessageCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> MessagePublic:
    return create_message(
        session,
        chat_id=chat_id,
        current_user=current_user,
        text=payload.text,
        message_type=payload.type,
        attachment_url=payload.attachment_url,
        attachment_mime_type=payload.attachment_mime_type,
        attachment_name=payload.attachment_name,
        attachment_size=payload.attachment_size,
        reply_to_id=payload.reply_to_id,
    )
