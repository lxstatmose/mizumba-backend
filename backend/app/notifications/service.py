from uuid import UUID

from sqlmodel import Session, func, select

from app.common.exceptions import not_found
from app.notifications.models import Notification, NotificationType
from app.notifications.schemas import NotificationPublic
from app.privacy.service import should_create_notification
from app.users.models import User
from app.users.service import get_user_by_id


def notification_to_public(session: Session, notification: Notification) -> NotificationPublic:
    actor = get_user_by_id(session, notification.actor_id) if notification.actor_id else None
    return NotificationPublic(
        id=notification.id,
        user_id=notification.user_id,
        actor_id=notification.actor_id,
        actor=actor,
        chat_id=notification.chat_id,
        message_id=notification.message_id,
        type=notification.type,
        title=notification.title,
        body=notification.body,
        payload=notification.payload,
        is_read=notification.is_read,
        created_at=notification.created_at,
    )


def create_notification(
    session: Session,
    *,
    user_id: UUID,
    notification_type: NotificationType,
    title: str,
    body: str,
    actor_id: UUID | None = None,
    chat_id: UUID | None = None,
    message_id: UUID | None = None,
    payload: dict | None = None,
) -> Notification | None:
    if not should_create_notification(session, user_id=user_id, notification_type=notification_type):
        return None
    notification = Notification(
        user_id=user_id,
        actor_id=actor_id,
        chat_id=chat_id,
        message_id=message_id,
        type=notification_type,
        title=title,
        body=body,
        payload=payload or {},
    )
    session.add(notification)
    session.commit()
    session.refresh(notification)
    return notification


def create_new_message_notifications(
    session: Session,
    *,
    recipient_ids: list[UUID],
    actor: User,
    chat_id: UUID,
    message_id: UUID,
    text: str,
) -> list[Notification]:
    notifications: list[Notification] = []
    body = text if len(text) <= 120 else f"{text[:117]}..."
    for recipient_id in set(recipient_ids):
        if recipient_id == actor.id:
            continue
        notification = create_notification(
            session,
            user_id=recipient_id,
            actor_id=actor.id,
            chat_id=chat_id,
            message_id=message_id,
            notification_type=NotificationType.NEW_MESSAGE,
            title=f"{actor.display_name} sent you a message",
            body=body,
            payload={"chat_id": str(chat_id), "message_id": str(message_id)},
        )
        if notification:
            notifications.append(notification)
    return notifications


def create_added_to_group_notification(
    session: Session,
    *,
    user_id: UUID,
    actor: User,
    chat_id: UUID,
    group_title: str,
) -> Notification:
    return create_notification(
        session,
        user_id=user_id,
        actor_id=actor.id,
        chat_id=chat_id,
        notification_type=NotificationType.ADDED_TO_GROUP,
        title=f"{actor.display_name} added you to {group_title}",
        body="You were added to a group chat",
        payload={"chat_id": str(chat_id)},
    )


def create_mention_notification(
    session: Session,
    *,
    user_id: UUID,
    actor: User,
    chat_id: UUID,
    message_id: UUID,
) -> Notification:
    return create_notification(
        session,
        user_id=user_id,
        actor_id=actor.id,
        chat_id=chat_id,
        message_id=message_id,
        notification_type=NotificationType.MENTION,
        title=f"{actor.display_name} mentioned you",
        body="You were mentioned in a message",
        payload={"chat_id": str(chat_id), "message_id": str(message_id)},
    )


def create_reaction_notification(
    session: Session,
    *,
    user_id: UUID,
    actor: User,
    chat_id: UUID,
    message_id: UUID,
    emoji: str,
) -> Notification | None:
    if user_id == actor.id:
        return None
    return create_notification(
        session,
        user_id=user_id,
        actor_id=actor.id,
        chat_id=chat_id,
        message_id=message_id,
        notification_type=NotificationType.REACTION,
        title=f"{actor.display_name} reacted to your message",
        body=emoji,
        payload={"chat_id": str(chat_id), "message_id": str(message_id), "emoji": emoji},
    )


def list_user_notifications(
    session: Session,
    *,
    user: User,
    limit: int = 50,
    unread_only: bool = False,
) -> list[NotificationPublic]:
    statement = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        statement = statement.where(Notification.is_read.is_(False))

    statement = statement.order_by(Notification.created_at.desc()).limit(limit)
    notifications = session.exec(statement).all()
    return [notification_to_public(session, notification) for notification in notifications]


def get_unread_notifications_count(session: Session, user: User) -> int:
    statement = select(func.count(Notification.id)).where(
        Notification.user_id == user.id,
        Notification.is_read.is_(False),
    )
    return session.exec(statement).one()


def get_notifications_for_message(session: Session, message_id: UUID) -> list[NotificationPublic]:
    statement = select(Notification).where(Notification.message_id == message_id)
    notifications = session.exec(statement).all()
    return [notification_to_public(session, notification) for notification in notifications]


def mark_notification_read(
    session: Session,
    *,
    user: User,
    notification_id: UUID,
) -> NotificationPublic:
    notification = session.get(Notification, notification_id)
    if not notification or notification.user_id != user.id:
        raise not_found("Notification not found")

    notification.is_read = True
    session.add(notification)
    session.commit()
    session.refresh(notification)
    return notification_to_public(session, notification)


def mark_all_notifications_read(session: Session, user: User) -> None:
    statement = select(Notification).where(
        Notification.user_id == user.id,
        Notification.is_read.is_(False),
    )
    notifications = session.exec(statement).all()
    for notification in notifications:
        notification.is_read = True
        session.add(notification)
    session.commit()


def delete_notification(session: Session, *, user: User, notification_id: UUID) -> None:
    notification = session.get(Notification, notification_id)
    if not notification or notification.user_id != user.id:
        raise not_found("Notification not found")

    session.delete(notification)
    session.commit()
