from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.auth.dependencies import get_current_user
from app.auth.schemas import MessageResponse
from app.core.database import get_session
from app.messages.schemas import MessagePublic, MessageReactionCreate, MessageReactionPublic, MessageUpdate
from app.messages.service import (
    add_message_reaction,
    delete_message,
    list_message_reactions,
    remove_message_reaction,
    update_message,
)
from app.users.models import User


router = APIRouter(prefix="/messages", tags=["messages"])


@router.patch("/{message_id}", response_model=MessagePublic)
def edit_message(
    message_id: UUID,
    payload: MessageUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> MessagePublic:
    return update_message(
        session,
        message_id=message_id,
        current_user=current_user,
        text=payload.text,
    )


@router.delete("/{message_id}", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def remove_message(
    message_id: UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> MessageResponse:
    delete_message(session, message_id=message_id, current_user=current_user)
    return MessageResponse(message="Message deleted successfully")


@router.get("/{message_id}/reactions", response_model=list[MessageReactionPublic])
def get_reactions(
    message_id: UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[MessageReactionPublic]:
    return list_message_reactions(session, message_id=message_id, current_user=current_user)


@router.post("/{message_id}/reactions", response_model=MessageReactionPublic, status_code=status.HTTP_201_CREATED)
def react_to_message(
    message_id: UUID,
    payload: MessageReactionCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> MessageReactionPublic:
    return add_message_reaction(
        session,
        message_id=message_id,
        current_user=current_user,
        emoji=payload.emoji,
    )


@router.delete("/{message_id}/reactions", response_model=MessageResponse)
def delete_reaction(
    message_id: UUID,
    payload: MessageReactionCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> MessageResponse:
    remove_message_reaction(
        session,
        message_id=message_id,
        current_user=current_user,
        emoji=payload.emoji,
    )
    return MessageResponse(message="Reaction removed successfully")
