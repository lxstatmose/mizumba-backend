from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.auth.dependencies import get_current_user
from app.channels.models import Channel, ChannelSubscriber
from app.chats.models import Chat, ChatMember
from app.core.database import get_session
from app.messages.models import Message
from app.search.schemas import SearchItem, SearchResponse
from app.users.models import User


router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
def search(
    q: str = Query(min_length=2, max_length=100),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> SearchResponse:
    pattern = f"%{q.strip()}%"

    users = session.exec(
        select(User)
        .where(User.is_active.is_(True))
        .where((User.display_name.ilike(pattern)) | (User.username.ilike(pattern)) | (User.email.ilike(pattern)))
        .limit(10)
    ).all()

    chats = session.exec(
        select(Chat)
        .join(ChatMember, Chat.id == ChatMember.chat_id)
        .where(ChatMember.user_id == current_user.id)
        .where(Chat.title.ilike(pattern))
        .limit(10)
    ).all()

    messages = session.exec(
        select(Message)
        .join(ChatMember, Message.chat_id == ChatMember.chat_id)
        .where(ChatMember.user_id == current_user.id)
        .where(Message.deleted_at.is_(None))
        .where(Message.text.ilike(pattern))
        .order_by(Message.created_at.desc())
        .limit(10)
    ).all()

    channels = session.exec(
        select(Channel)
        .outerjoin(ChannelSubscriber, Channel.id == ChannelSubscriber.channel_id)
        .where((Channel.is_public.is_(True)) | (ChannelSubscriber.user_id == current_user.id))
        .where((Channel.title.ilike(pattern)) | (Channel.slug.ilike(pattern)) | (Channel.description.ilike(pattern)))
        .limit(10)
    ).all()

    return SearchResponse(
        users=[
            SearchItem(
                id=user.id,
                type="user",
                title=user.display_name,
                subtitle=user.username or user.email,
                url=user.avatar_url,
            )
            for user in users
        ],
        chats=[
            SearchItem(id=chat.id, type="chat", title=chat.title or "Direct chat", url=chat.avatar_url)
            for chat in chats
        ],
        messages=[
            SearchItem(
                id=message.id,
                type="message",
                title=message.text[:120],
                subtitle=str(message.chat_id),
            )
            for message in messages
        ],
        channels=[
            SearchItem(
                id=channel.id,
                type="channel",
                title=channel.title,
                subtitle=f"@{channel.slug}",
                url=channel.cover_url,
            )
            for channel in channels
        ],
    )
