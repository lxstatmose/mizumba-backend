from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import Session, select

from app.channels.models import ChannelSubscriber
from app.chats.models import Chat, ChatMember, ChatType
from app.common.exceptions import bad_request
from app.core.security import hash_password
from app.messages.models import Message
from app.users.models import User
from app.users.schemas import ProfileStats, UserUpdate


def get_user_by_id(session: Session, user_id: UUID) -> User | None:
    return session.get(User, user_id)


def get_user_by_email(session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email.lower())
    return session.exec(statement).first()


def get_user_by_username(session: Session, username: str) -> User | None:
    statement = select(User).where(User.username == username.lower())
    return session.exec(statement).first()


def create_user(
    session: Session,
    *,
    email: str,
    password: str,
    display_name: str,
    username: str | None = None,
) -> User:
    user = User(
        email=email.lower(),
        username=username.lower() if username else None,
        display_name=display_name,
        password_hash=hash_password(password),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def update_user_last_seen(session: Session, user: User) -> User:
    user.is_online = False
    user.last_seen_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def set_user_online(session: Session, user: User) -> User:
    user.is_online = True
    user.updated_at = datetime.now(UTC)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def update_user_profile(session: Session, user: User, payload: UserUpdate) -> User:
    update_data = payload.model_dump(exclude_unset=True)

    if "username" in update_data:
        username = update_data["username"]
        username = username.lower().strip() if username else None
        if username:
            existing_user = get_user_by_username(session, username)
            if existing_user and existing_user.id != user.id:
                raise bad_request("User with this username already exists")
        user.username = username

    if "display_name" in update_data and update_data["display_name"] is not None:
        user.display_name = update_data["display_name"].strip()

    if "avatar_url" in update_data:
        avatar_url = update_data["avatar_url"]
        user.avatar_url = avatar_url.strip() if avatar_url else None

    if "bio" in update_data:
        bio = update_data["bio"]
        user.bio = bio.strip() if bio else None

    user.updated_at = datetime.now(UTC)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def get_profile_stats(session: Session, user: User) -> ProfileStats:
    messages_count = len(
        session.exec(select(Message).where(Message.sender_id == user.id, Message.deleted_at.is_(None))).all()
    )
    groups_count = len(
        session.exec(
            select(Chat)
            .join(ChatMember, ChatMember.chat_id == Chat.id)
            .where(ChatMember.user_id == user.id, Chat.type == ChatType.GROUP)
        ).all()
    )
    channels_count = len(
        session.exec(select(ChannelSubscriber).where(ChannelSubscriber.user_id == user.id)).all()
    )

    return ProfileStats(
        messages_count=messages_count,
        groups_count=groups_count,
        channels_count=channels_count,
    )
