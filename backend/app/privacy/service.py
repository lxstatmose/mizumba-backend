from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import Session, select

from app.common.exceptions import bad_request, forbidden, not_found
from app.notifications.models import NotificationType
from app.privacy.models import (
    BlockedUser,
    DirectMessagePolicy,
    UserNotificationSettings,
    UserPrivacySettings,
)
from app.privacy.schemas import BlockedUserPublic
from app.users.models import User
from app.users.service import get_user_by_id


def get_privacy_settings(session: Session, user: User) -> UserPrivacySettings:
    settings = session.get(UserPrivacySettings, user.id)
    if settings:
        return settings
    settings = UserPrivacySettings(user_id=user.id)
    session.add(settings)
    session.commit()
    session.refresh(settings)
    return settings


def update_privacy_settings(
    session: Session,
    user: User,
    *,
    direct_messages: DirectMessagePolicy | None = None,
    show_online_status: bool | None = None,
) -> UserPrivacySettings:
    settings = get_privacy_settings(session, user)
    if direct_messages is not None:
        settings.direct_messages = direct_messages
    if show_online_status is not None:
        settings.show_online_status = show_online_status
    settings.updated_at = datetime.now(UTC)
    session.add(settings)
    session.commit()
    session.refresh(settings)
    return settings


def get_notification_settings(session: Session, user_id: UUID) -> UserNotificationSettings:
    settings = session.get(UserNotificationSettings, user_id)
    if settings:
        return settings
    settings = UserNotificationSettings(user_id=user_id)
    session.add(settings)
    session.commit()
    session.refresh(settings)
    return settings


def update_notification_settings(
    session: Session,
    user: User,
    *,
    updates: dict[str, bool | None],
) -> UserNotificationSettings:
    settings = get_notification_settings(session, user.id)
    for field, value in updates.items():
        if value is not None:
            setattr(settings, field, value)
    settings.updated_at = datetime.now(UTC)
    session.add(settings)
    session.commit()
    session.refresh(settings)
    return settings


def is_user_blocked(session: Session, *, first_user_id: UUID, second_user_id: UUID) -> bool:
    statement = select(BlockedUser).where(
        (
            (BlockedUser.blocker_id == first_user_id)
            & (BlockedUser.blocked_id == second_user_id)
        )
        | (
            (BlockedUser.blocker_id == second_user_id)
            & (BlockedUser.blocked_id == first_user_id)
        )
    )
    return session.exec(statement).first() is not None


def ensure_users_can_direct_message(session: Session, *, sender: User, recipient: User) -> None:
    if is_user_blocked(session, first_user_id=sender.id, second_user_id=recipient.id):
        raise forbidden("You cannot interact with this user")
    privacy = get_privacy_settings(session, recipient)
    if privacy.direct_messages == DirectMessagePolicy.NOBODY:
        raise forbidden("This user does not accept direct messages")


def list_blocked_users(session: Session, user: User) -> list[BlockedUserPublic]:
    statement = select(BlockedUser).where(BlockedUser.blocker_id == user.id).order_by(BlockedUser.created_at.desc())
    blocked_items = session.exec(statement).all()
    result: list[BlockedUserPublic] = []
    for item in blocked_items:
        blocked_user = get_user_by_id(session, item.blocked_id)
        if blocked_user:
            result.append(BlockedUserPublic(id=item.id, blocked_user=blocked_user, created_at=item.created_at))
    return result


def block_user(session: Session, *, user: User, blocked_user_id: UUID) -> None:
    if user.id == blocked_user_id:
        raise bad_request("Cannot block yourself")
    blocked_user = get_user_by_id(session, blocked_user_id)
    if not blocked_user or not blocked_user.is_active:
        raise not_found("User not found")
    statement = select(BlockedUser).where(
        BlockedUser.blocker_id == user.id,
        BlockedUser.blocked_id == blocked_user_id,
    )
    if session.exec(statement).first():
        return
    session.add(BlockedUser(blocker_id=user.id, blocked_id=blocked_user_id))
    session.commit()


def unblock_user(session: Session, *, user: User, blocked_user_id: UUID) -> None:
    statement = select(BlockedUser).where(
        BlockedUser.blocker_id == user.id,
        BlockedUser.blocked_id == blocked_user_id,
    )
    blocked = session.exec(statement).first()
    if blocked:
        session.delete(blocked)
        session.commit()


def should_create_notification(session: Session, *, user_id: UUID, notification_type: NotificationType) -> bool:
    settings = get_notification_settings(session, user_id)
    if notification_type == NotificationType.NEW_MESSAGE:
        return settings.new_messages
    if notification_type == NotificationType.MENTION:
        return settings.mentions
    if notification_type == NotificationType.REACTION:
        return settings.reactions
    if notification_type == NotificationType.ADDED_TO_GROUP:
        return settings.group_invites
    if notification_type == NotificationType.CHANNEL_UPDATE:
        return settings.channel_updates
    return True
