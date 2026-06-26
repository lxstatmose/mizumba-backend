from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import Session, func, select

from app.chats.models import Chat, ChatMember, ChatMemberRole, ChatType
from app.chats.schemas import ChatDetail, ChatMemberPublic, ChatSummary
from app.common.exceptions import bad_request, forbidden, not_found
from app.messages.models import Message
from app.messages.schemas import MessagePublic
from app.notifications.service import create_added_to_group_notification
from app.privacy.service import ensure_users_can_direct_message
from app.users.models import User
from app.users.service import get_user_by_id


def get_chat_by_id(session: Session, chat_id: UUID) -> Chat | None:
    return session.get(Chat, chat_id)


def get_chat_member(session: Session, chat_id: UUID, user_id: UUID) -> ChatMember | None:
    statement = select(ChatMember).where(ChatMember.chat_id == chat_id, ChatMember.user_id == user_id)
    return session.exec(statement).first()


def require_chat_member(session: Session, chat_id: UUID, user: User) -> ChatMember:
    member = get_chat_member(session, chat_id, user.id)
    if not member:
        raise forbidden("You are not a member of this chat")
    return member


def require_chat_admin(session: Session, chat_id: UUID, user: User) -> ChatMember:
    member = require_chat_member(session, chat_id, user)
    if member.role not in {ChatMemberRole.OWNER, ChatMemberRole.ADMIN}:
        raise forbidden("Only chat admins can perform this action")
    return member


def _get_members(session: Session, chat_id: UUID) -> list[ChatMember]:
    statement = select(ChatMember).where(ChatMember.chat_id == chat_id).order_by(ChatMember.joined_at)
    return list(session.exec(statement).all())


def get_chat_member_user_ids(session: Session, chat_id: UUID) -> list[UUID]:
    return [member.user_id for member in _get_members(session, chat_id)]


def get_user_chat_peer_ids(session: Session, user: User) -> list[UUID]:
    statement = (
        select(ChatMember.user_id)
        .join(Chat, Chat.id == ChatMember.chat_id)
        .where(
            Chat.id.in_(select(ChatMember.chat_id).where(ChatMember.user_id == user.id)),
            ChatMember.user_id != user.id,
        )
    )
    return list(set(session.exec(statement).all()))


def _get_latest_message(session: Session, chat: Chat) -> Message | None:
    if chat.last_message_id:
        message = session.get(Message, chat.last_message_id)
        if message:
            return message

    statement = (
        select(Message)
        .where(Message.chat_id == chat.id, Message.deleted_at.is_(None))
        .order_by(Message.created_at.desc())
    )
    return session.exec(statement).first()


def _message_to_public(session: Session, message: Message | None) -> MessagePublic | None:
    if not message:
        return None

    sender = get_user_by_id(session, message.sender_id)
    return MessagePublic(
        id=message.id,
        chat_id=message.chat_id,
        sender_id=message.sender_id,
        sender=sender,
        text=message.text,
        type=message.type,
        attachment_url=message.attachment_url,
        attachment_mime_type=message.attachment_mime_type,
        attachment_name=message.attachment_name,
        attachment_size=message.attachment_size,
        reply_to_id=message.reply_to_id,
        created_at=message.created_at,
        updated_at=message.updated_at,
        edited_at=message.edited_at,
        deleted_at=message.deleted_at,
    )


def _get_unread_count(session: Session, chat_id: UUID, member: ChatMember) -> int:
    statement = select(func.count(Message.id)).where(
        Message.chat_id == chat_id,
        Message.sender_id != member.user_id,
        Message.deleted_at.is_(None),
    )
    if member.last_read_at:
        statement = statement.where(Message.created_at > member.last_read_at)

    return session.exec(statement).one()


def _get_members_count(session: Session, chat_id: UUID) -> int:
    statement = select(func.count(ChatMember.id)).where(ChatMember.chat_id == chat_id)
    return session.exec(statement).one()


def _get_direct_companion(session: Session, chat_id: UUID, current_user: User) -> User | None:
    statement = select(ChatMember).where(
        ChatMember.chat_id == chat_id,
        ChatMember.user_id != current_user.id,
    )
    companion_member = session.exec(statement).first()
    if not companion_member:
        return None
    return get_user_by_id(session, companion_member.user_id)


def build_chat_summary(session: Session, chat: Chat, current_user: User) -> ChatSummary:
    member = require_chat_member(session, chat.id, current_user)
    title = chat.title
    avatar_url = chat.avatar_url

    if chat.type == ChatType.DIRECT:
        companion = _get_direct_companion(session, chat.id, current_user)
        if companion:
            title = companion.display_name
            avatar_url = companion.avatar_url

    return ChatSummary(
        id=chat.id,
        type=chat.type,
        title=title,
        avatar_url=avatar_url,
        last_message=_message_to_public(session, _get_latest_message(session, chat)),
        unread_count=_get_unread_count(session, chat.id, member),
        members_count=_get_members_count(session, chat.id),
        updated_at=chat.updated_at,
    )


def build_chat_detail(session: Session, chat: Chat, current_user: User) -> ChatDetail:
    summary = build_chat_summary(session, chat, current_user)
    members: list[ChatMemberPublic] = []

    for member in _get_members(session, chat.id):
        user = get_user_by_id(session, member.user_id)
        if not user:
            continue
        members.append(
            ChatMemberPublic(
                user=user,
                role=member.role,
                joined_at=member.joined_at,
                last_read_at=member.last_read_at,
                muted=member.muted,
            )
        )

    return ChatDetail(**summary.model_dump(), members=members)


def list_user_chats(session: Session, user: User) -> list[ChatSummary]:
    statement = (
        select(Chat)
        .join(ChatMember, ChatMember.chat_id == Chat.id)
        .where(ChatMember.user_id == user.id)
        .order_by(Chat.updated_at.desc())
    )
    chats = session.exec(statement).all()
    return [build_chat_summary(session, chat, user) for chat in chats]


def get_chat_detail(session: Session, chat_id: UUID, user: User) -> ChatDetail:
    chat = get_chat_by_id(session, chat_id)
    if not chat:
        raise not_found("Chat not found")
    return build_chat_detail(session, chat, user)


def find_direct_chat(session: Session, first_user_id: UUID, second_user_id: UUID) -> Chat | None:
    first_chat_ids = select(ChatMember.chat_id).where(ChatMember.user_id == first_user_id)
    statement = (
        select(Chat)
        .join(ChatMember, ChatMember.chat_id == Chat.id)
        .where(
            Chat.type == ChatType.DIRECT,
            Chat.id.in_(first_chat_ids),
            ChatMember.user_id == second_user_id,
        )
    )
    return session.exec(statement).first()


def create_direct_chat(session: Session, current_user: User, target_user_id: UUID) -> ChatDetail:
    if current_user.id == target_user_id:
        raise bad_request("Cannot create direct chat with yourself")

    target_user = get_user_by_id(session, target_user_id)
    if not target_user or not target_user.is_active:
        raise not_found("User not found")
    ensure_users_can_direct_message(session, sender=current_user, recipient=target_user)

    existing_chat = find_direct_chat(session, current_user.id, target_user_id)
    if existing_chat:
        return build_chat_detail(session, existing_chat, current_user)

    chat = Chat(type=ChatType.DIRECT, created_by_id=current_user.id)
    session.add(chat)
    session.commit()
    session.refresh(chat)

    session.add(ChatMember(chat_id=chat.id, user_id=current_user.id, role=ChatMemberRole.OWNER))
    session.add(ChatMember(chat_id=chat.id, user_id=target_user.id, role=ChatMemberRole.MEMBER))
    session.commit()
    session.refresh(chat)
    return build_chat_detail(session, chat, current_user)


def create_group_chat(
    session: Session,
    current_user: User,
    *,
    title: str,
    member_ids: list[UUID],
    avatar_url: str | None = None,
) -> ChatDetail:
    unique_member_ids = {current_user.id, *member_ids}
    users_by_id: dict[UUID, User] = {}
    for user_id in unique_member_ids:
        user = get_user_by_id(session, user_id)
        if not user or not user.is_active:
            raise not_found(f"User {user_id} not found")
        users_by_id[user_id] = user

    chat = Chat(
        type=ChatType.GROUP,
        title=title.strip(),
        avatar_url=avatar_url.strip() if avatar_url else None,
        created_by_id=current_user.id,
    )
    session.add(chat)
    session.commit()
    session.refresh(chat)

    for user_id in users_by_id:
        role = ChatMemberRole.OWNER if user_id == current_user.id else ChatMemberRole.MEMBER
        session.add(ChatMember(chat_id=chat.id, user_id=user_id, role=role))

    session.commit()
    for user_id in users_by_id:
        if user_id == current_user.id:
            continue
        create_added_to_group_notification(
            session,
            user_id=user_id,
            actor=current_user,
            chat_id=chat.id,
            group_title=chat.title or "group chat",
        )
    session.refresh(chat)
    return build_chat_detail(session, chat, current_user)


def add_chat_member(
    session: Session,
    *,
    chat_id: UUID,
    current_user: User,
    user_id: UUID,
    role: ChatMemberRole,
) -> ChatDetail:
    chat = get_chat_by_id(session, chat_id)
    if not chat:
        raise not_found("Chat not found")
    if chat.type == ChatType.DIRECT:
        raise bad_request("Cannot add members to direct chat")

    require_chat_admin(session, chat_id, current_user)
    user = get_user_by_id(session, user_id)
    if not user or not user.is_active:
        raise not_found("User not found")
    if get_chat_member(session, chat_id, user_id):
        raise bad_request("User is already a chat member")

    session.add(ChatMember(chat_id=chat_id, user_id=user_id, role=role))
    chat.updated_at = datetime.now(UTC)
    session.add(chat)
    session.commit()
    create_added_to_group_notification(
        session,
        user_id=user_id,
        actor=current_user,
        chat_id=chat.id,
        group_title=chat.title or "group chat",
    )
    session.refresh(chat)
    return build_chat_detail(session, chat, current_user)


def remove_chat_member(
    session: Session,
    *,
    chat_id: UUID,
    current_user: User,
    user_id: UUID,
) -> ChatDetail:
    chat = get_chat_by_id(session, chat_id)
    if not chat:
        raise not_found("Chat not found")
    if chat.type == ChatType.DIRECT:
        raise bad_request("Cannot remove members from direct chat")

    current_member = require_chat_member(session, chat_id, current_user)
    target_member = get_chat_member(session, chat_id, user_id)
    if not target_member:
        raise not_found("Chat member not found")

    if current_user.id != user_id and current_member.role not in {ChatMemberRole.OWNER, ChatMemberRole.ADMIN}:
        raise forbidden("Only chat admins can remove other members")
    if target_member.role == ChatMemberRole.OWNER and current_user.id != user_id:
        raise forbidden("Cannot remove chat owner")

    session.delete(target_member)
    chat.updated_at = datetime.now(UTC)
    session.add(chat)
    session.commit()
    session.refresh(chat)
    return build_chat_detail(session, chat, current_user)


def mark_chat_read(
    session: Session,
    *,
    chat_id: UUID,
    current_user: User,
    message_id: UUID | None = None,
) -> ChatSummary:
    chat = get_chat_by_id(session, chat_id)
    if not chat:
        raise not_found("Chat not found")

    member = require_chat_member(session, chat_id, current_user)
    if message_id:
        message = session.get(Message, message_id)
        if not message or message.chat_id != chat_id:
            raise not_found("Message not found")
        member.last_read_at = message.created_at
    else:
        member.last_read_at = datetime.now(UTC)

    session.add(member)
    session.commit()
    return build_chat_summary(session, chat, current_user)
