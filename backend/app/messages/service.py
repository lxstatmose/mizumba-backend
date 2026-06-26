import re
from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import Session, select

from app.chats.models import Chat
from app.chats.service import get_chat_member_user_ids, require_chat_member
from app.common.exceptions import forbidden, not_found
from app.messages.models import Message, MessageReaction, MessageType
from app.messages.schemas import MessagePublic, MessageReactionPublic
from app.notifications.service import (
    create_mention_notification,
    create_new_message_notifications,
    create_reaction_notification,
)
from app.users.models import User
from app.users.service import get_user_by_id, get_user_by_username


def message_to_public(session: Session, message: Message) -> MessagePublic:
    return MessagePublic(
        id=message.id,
        chat_id=message.chat_id,
        sender_id=message.sender_id,
        sender=get_user_by_id(session, message.sender_id),
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


def reaction_to_public(session: Session, reaction: MessageReaction) -> MessageReactionPublic:
    return MessageReactionPublic(
        id=reaction.id,
        message_id=reaction.message_id,
        user_id=reaction.user_id,
        user=get_user_by_id(session, reaction.user_id),
        emoji=reaction.emoji,
        created_at=reaction.created_at,
    )


def _create_mention_notifications(session: Session, *, message: Message, actor: User) -> None:
    usernames = {match.group(1).lower() for match in re.finditer(r"@([a-zA-Z0-9_]{3,50})", message.text)}
    if not usernames:
        return

    member_ids = set(get_chat_member_user_ids(session, message.chat_id))
    for username in usernames:
        mentioned_user = get_user_by_username(session, username)
        if mentioned_user and mentioned_user.id in member_ids and mentioned_user.id != actor.id:
            create_mention_notification(
                session,
                user_id=mentioned_user.id,
                actor=actor,
                chat_id=message.chat_id,
                message_id=message.id,
            )


def list_chat_messages(
    session: Session,
    *,
    chat_id: UUID,
    current_user: User,
    limit: int = 50,
    before_message_id: UUID | None = None,
) -> list[MessagePublic]:
    require_chat_member(session, chat_id, current_user)

    statement = select(Message).where(Message.chat_id == chat_id)
    if before_message_id:
        before_message = session.get(Message, before_message_id)
        if not before_message or before_message.chat_id != chat_id:
            raise not_found("Message not found")
        statement = statement.where(Message.created_at < before_message.created_at)

    statement = statement.order_by(Message.created_at.desc()).limit(limit)
    messages = list(session.exec(statement).all())
    messages.reverse()
    return [message_to_public(session, message) for message in messages]


def create_message(
    session: Session,
    *,
    chat_id: UUID,
    current_user: User,
    text: str,
    message_type: MessageType = MessageType.TEXT,
    attachment_url: str | None = None,
    attachment_mime_type: str | None = None,
    attachment_name: str | None = None,
    attachment_size: int | None = None,
    reply_to_id: UUID | None = None,
) -> MessagePublic:
    chat = session.get(Chat, chat_id)
    if not chat:
        raise not_found("Chat not found")
    require_chat_member(session, chat_id, current_user)

    if reply_to_id:
        reply_to = session.get(Message, reply_to_id)
        if not reply_to or reply_to.chat_id != chat_id:
            raise not_found("Reply message not found")

    now = datetime.now(UTC)
    message = Message(
        chat_id=chat_id,
        sender_id=current_user.id,
        text=text.strip(),
        type=message_type,
        attachment_url=attachment_url,
        attachment_mime_type=attachment_mime_type,
        attachment_name=attachment_name,
        attachment_size=attachment_size,
        reply_to_id=reply_to_id,
        created_at=now,
        updated_at=now,
    )
    session.add(message)
    session.commit()
    session.refresh(message)

    chat.last_message_id = message.id
    chat.updated_at = now
    session.add(chat)
    session.commit()
    session.refresh(message)
    create_new_message_notifications(
        session,
        recipient_ids=get_chat_member_user_ids(session, chat_id),
        actor=current_user,
        chat_id=chat_id,
        message_id=message.id,
        text=message.text,
    )
    _create_mention_notifications(session, message=message, actor=current_user)
    return message_to_public(session, message)


def get_message_for_user(session: Session, message_id: UUID, current_user: User) -> Message:
    message = session.get(Message, message_id)
    if not message:
        raise not_found("Message not found")
    require_chat_member(session, message.chat_id, current_user)
    return message


def update_message(
    session: Session,
    *,
    message_id: UUID,
    current_user: User,
    text: str,
) -> MessagePublic:
    message = get_message_for_user(session, message_id, current_user)
    if message.sender_id != current_user.id:
        raise forbidden("Only sender can edit message")
    if message.deleted_at:
        raise not_found("Message not found")

    now = datetime.now(UTC)
    message.text = text.strip()
    message.edited_at = now
    message.updated_at = now
    session.add(message)
    session.commit()
    session.refresh(message)
    return message_to_public(session, message)


def delete_message(session: Session, *, message_id: UUID, current_user: User) -> None:
    message = get_message_for_user(session, message_id, current_user)
    if message.sender_id != current_user.id:
        raise forbidden("Only sender can delete message")
    if message.deleted_at:
        return

    now = datetime.now(UTC)
    message.deleted_at = now
    message.updated_at = now
    session.add(message)
    session.commit()


def list_message_reactions(session: Session, *, message_id: UUID, current_user: User) -> list[MessageReactionPublic]:
    message = get_message_for_user(session, message_id, current_user)
    statement = select(MessageReaction).where(MessageReaction.message_id == message.id)
    return [reaction_to_public(session, reaction) for reaction in session.exec(statement).all()]


def add_message_reaction(
    session: Session,
    *,
    message_id: UUID,
    current_user: User,
    emoji: str,
) -> MessageReactionPublic:
    message = get_message_for_user(session, message_id, current_user)
    statement = select(MessageReaction).where(
        MessageReaction.message_id == message.id,
        MessageReaction.user_id == current_user.id,
        MessageReaction.emoji == emoji,
    )
    reaction = session.exec(statement).first()
    if not reaction:
        reaction = MessageReaction(message_id=message.id, user_id=current_user.id, emoji=emoji)
        session.add(reaction)
        session.commit()
        session.refresh(reaction)
        create_reaction_notification(
            session,
            user_id=message.sender_id,
            actor=current_user,
            chat_id=message.chat_id,
            message_id=message.id,
            emoji=emoji,
        )
    return reaction_to_public(session, reaction)


def remove_message_reaction(
    session: Session,
    *,
    message_id: UUID,
    current_user: User,
    emoji: str,
) -> None:
    message = get_message_for_user(session, message_id, current_user)
    statement = select(MessageReaction).where(
        MessageReaction.message_id == message.id,
        MessageReaction.user_id == current_user.id,
        MessageReaction.emoji == emoji,
    )
    reaction = session.exec(statement).first()
    if reaction:
        session.delete(reaction)
        session.commit()
