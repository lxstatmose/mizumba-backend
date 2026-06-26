import re
from datetime import UTC, datetime
from uuid import UUID

from sqlmodel import Session, func, select

from app.channels.models import Channel, ChannelCategory, ChannelPost, ChannelSubscriber, ChannelSubscriberRole
from app.channels.schemas import (
    ChannelDetail,
    ChannelPostPublic,
    ChannelSubscriberPublic,
    ChannelSummary,
    ChannelUpdate,
)
from app.common.exceptions import bad_request, forbidden, not_found
from app.notifications.models import NotificationType
from app.notifications.service import create_notification
from app.users.models import User
from app.users.service import get_user_by_id


def normalize_slug(value: str) -> str:
    slug = value.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    if not slug:
        raise bad_request("Channel slug is invalid")
    return slug


def get_channel_by_id(session: Session, channel_id: UUID) -> Channel | None:
    return session.get(Channel, channel_id)


def get_channel_by_slug(session: Session, slug: str) -> Channel | None:
    statement = select(Channel).where(Channel.slug == normalize_slug(slug))
    return session.exec(statement).first()


def get_channel_subscriber(session: Session, channel_id: UUID, user_id: UUID) -> ChannelSubscriber | None:
    statement = select(ChannelSubscriber).where(
        ChannelSubscriber.channel_id == channel_id,
        ChannelSubscriber.user_id == user_id,
    )
    return session.exec(statement).first()


def require_channel_subscriber(session: Session, channel: Channel, user: User) -> ChannelSubscriber:
    subscriber = get_channel_subscriber(session, channel.id, user.id)
    if not subscriber:
        raise forbidden("You are not subscribed to this channel")
    return subscriber


def require_channel_admin(session: Session, channel: Channel, user: User) -> ChannelSubscriber:
    subscriber = require_channel_subscriber(session, channel, user)
    if subscriber.role not in {ChannelSubscriberRole.OWNER, ChannelSubscriberRole.ADMIN}:
        raise forbidden("Only channel admins can perform this action")
    return subscriber


def _subscribers_count(session: Session, channel_id: UUID) -> int:
    statement = select(func.count(ChannelSubscriber.id)).where(ChannelSubscriber.channel_id == channel_id)
    return session.exec(statement).one()


def _get_last_post(session: Session, channel_id: UUID) -> ChannelPost | None:
    statement = (
        select(ChannelPost)
        .where(ChannelPost.channel_id == channel_id, ChannelPost.deleted_at.is_(None))
        .order_by(ChannelPost.created_at.desc())
    )
    return session.exec(statement).first()


def _post_to_public(session: Session, post: ChannelPost | None) -> ChannelPostPublic | None:
    if not post:
        return None
    return ChannelPostPublic(
        id=post.id,
        channel_id=post.channel_id,
        author_id=post.author_id,
        author=get_user_by_id(session, post.author_id),
        text=post.text,
        image_url=post.image_url,
        created_at=post.created_at,
        updated_at=post.updated_at,
        deleted_at=post.deleted_at,
    )


def build_channel_summary(session: Session, channel: Channel, current_user: User | None) -> ChannelSummary:
    subscriber = get_channel_subscriber(session, channel.id, current_user.id) if current_user else None
    return ChannelSummary(
        id=channel.id,
        title=channel.title,
        slug=channel.slug,
        description=channel.description,
        cover_url=channel.cover_url,
        category=channel.category,
        is_public=channel.is_public,
        is_subscribed=subscriber is not None,
        current_user_role=subscriber.role if subscriber else None,
        subscribers_count=_subscribers_count(session, channel.id),
        last_post=_post_to_public(session, _get_last_post(session, channel.id)),
        created_at=channel.created_at,
        updated_at=channel.updated_at,
    )


def build_channel_detail(session: Session, channel: Channel, current_user: User | None) -> ChannelDetail:
    summary = build_channel_summary(session, channel, current_user)
    statement = select(ChannelSubscriber).where(ChannelSubscriber.channel_id == channel.id)
    subscribers: list[ChannelSubscriberPublic] = []
    for subscriber in session.exec(statement).all():
        user = get_user_by_id(session, subscriber.user_id)
        if not user:
            continue
        subscribers.append(
            ChannelSubscriberPublic(
                user=user,
                role=subscriber.role,
                subscribed_at=subscriber.subscribed_at,
                muted=subscriber.muted,
            )
        )
    return ChannelDetail(**summary.model_dump(), subscribers=subscribers)


def list_channels(
    session: Session,
    *,
    current_user: User,
    category: ChannelCategory | None = None,
    query: str | None = None,
) -> list[ChannelSummary]:
    statement = select(Channel).where(Channel.is_public.is_(True))
    if category:
        statement = statement.where(Channel.category == category)
    if query:
        like_query = f"%{query.strip()}%"
        statement = statement.where(Channel.title.ilike(like_query))

    statement = statement.order_by(Channel.updated_at.desc())
    channels = session.exec(statement).all()
    return [build_channel_summary(session, channel, current_user) for channel in channels]


def create_channel(
    session: Session,
    *,
    current_user: User,
    title: str,
    description: str,
    slug: str | None = None,
    cover_url: str | None = None,
    category: ChannelCategory,
    is_public: bool = True,
) -> ChannelDetail:
    normalized_slug = normalize_slug(slug or title)
    if get_channel_by_slug(session, normalized_slug):
        raise bad_request("Channel with this slug already exists")

    now = datetime.now(UTC)
    channel = Channel(
        title=title.strip(),
        slug=normalized_slug,
        description=description.strip(),
        cover_url=cover_url.strip() if cover_url else None,
        category=category,
        created_by_id=current_user.id,
        is_public=is_public,
        created_at=now,
        updated_at=now,
    )
    session.add(channel)
    session.commit()
    session.refresh(channel)

    session.add(
        ChannelSubscriber(
            channel_id=channel.id,
            user_id=current_user.id,
            role=ChannelSubscriberRole.OWNER,
        )
    )
    session.commit()
    session.refresh(channel)
    return build_channel_detail(session, channel, current_user)


def get_channel_detail(session: Session, *, channel_id: UUID, current_user: User) -> ChannelDetail:
    channel = get_channel_by_id(session, channel_id)
    if not channel:
        raise not_found("Channel not found")
    if not channel.is_public:
        require_channel_subscriber(session, channel, current_user)
    return build_channel_detail(session, channel, current_user)


def update_channel(
    session: Session,
    *,
    channel_id: UUID,
    current_user: User,
    payload: ChannelUpdate,
) -> ChannelDetail:
    channel = get_channel_by_id(session, channel_id)
    if not channel:
        raise not_found("Channel not found")
    require_channel_admin(session, channel, current_user)

    update_data = payload.model_dump(exclude_unset=True)
    if "title" in update_data and update_data["title"] is not None:
        channel.title = update_data["title"].strip()
    if "description" in update_data and update_data["description"] is not None:
        channel.description = update_data["description"].strip()
    if "cover_url" in update_data:
        cover_url = update_data["cover_url"]
        channel.cover_url = cover_url.strip() if cover_url else None
    if "category" in update_data and update_data["category"] is not None:
        channel.category = update_data["category"]
    if "is_public" in update_data and update_data["is_public"] is not None:
        channel.is_public = update_data["is_public"]

    channel.updated_at = datetime.now(UTC)
    session.add(channel)
    session.commit()
    session.refresh(channel)
    return build_channel_detail(session, channel, current_user)


def subscribe_to_channel(session: Session, *, channel_id: UUID, current_user: User) -> ChannelDetail:
    channel = get_channel_by_id(session, channel_id)
    if not channel:
        raise not_found("Channel not found")
    if get_channel_subscriber(session, channel_id, current_user.id):
        return build_channel_detail(session, channel, current_user)

    session.add(ChannelSubscriber(channel_id=channel_id, user_id=current_user.id))
    session.commit()
    session.refresh(channel)
    return build_channel_detail(session, channel, current_user)


def unsubscribe_from_channel(session: Session, *, channel_id: UUID, current_user: User) -> ChannelSummary:
    channel = get_channel_by_id(session, channel_id)
    if not channel:
        raise not_found("Channel not found")
    subscriber = get_channel_subscriber(session, channel_id, current_user.id)
    if not subscriber:
        return build_channel_summary(session, channel, current_user)
    if subscriber.role == ChannelSubscriberRole.OWNER:
        raise bad_request("Channel owner cannot unsubscribe")

    session.delete(subscriber)
    session.commit()
    session.refresh(channel)
    return build_channel_summary(session, channel, current_user)


def list_channel_posts(
    session: Session,
    *,
    channel_id: UUID,
    current_user: User,
    limit: int = 50,
) -> list[ChannelPostPublic]:
    channel = get_channel_by_id(session, channel_id)
    if not channel:
        raise not_found("Channel not found")
    if not channel.is_public:
        require_channel_subscriber(session, channel, current_user)

    statement = (
        select(ChannelPost)
        .where(ChannelPost.channel_id == channel_id, ChannelPost.deleted_at.is_(None))
        .order_by(ChannelPost.created_at.desc())
        .limit(limit)
    )
    posts = list(session.exec(statement).all())
    posts.reverse()
    return [_post_to_public(session, post) for post in posts if post]


def create_channel_post(
    session: Session,
    *,
    channel_id: UUID,
    current_user: User,
    text: str,
    image_url: str | None = None,
) -> ChannelPostPublic:
    channel = get_channel_by_id(session, channel_id)
    if not channel:
        raise not_found("Channel not found")
    require_channel_admin(session, channel, current_user)

    now = datetime.now(UTC)
    post = ChannelPost(
        channel_id=channel_id,
        author_id=current_user.id,
        text=text.strip(),
        image_url=image_url.strip() if image_url else None,
        created_at=now,
        updated_at=now,
    )
    session.add(post)
    channel.updated_at = now
    session.add(channel)
    session.commit()
    session.refresh(post)

    notify_channel_subscribers(session, channel=channel, actor=current_user, post=post)
    return _post_to_public(session, post)


def notify_channel_subscribers(
    session: Session,
    *,
    channel: Channel,
    actor: User,
    post: ChannelPost,
) -> None:
    statement = select(ChannelSubscriber).where(
        ChannelSubscriber.channel_id == channel.id,
        ChannelSubscriber.user_id != actor.id,
        ChannelSubscriber.muted.is_(False),
    )
    subscribers = session.exec(statement).all()
    body = post.text if len(post.text) <= 120 else f"{post.text[:117]}..."
    for subscriber in subscribers:
        create_notification(
            session,
            user_id=subscriber.user_id,
            actor_id=actor.id,
            notification_type=NotificationType.CHANNEL_UPDATE,
            title=f"New post in {channel.title}",
            body=body,
            payload={"channel_id": str(channel.id), "post_id": str(post.id)},
        )
