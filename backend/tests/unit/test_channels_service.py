from sqlmodel import Session

from app.auth.service import register_user
from app.channels.models import ChannelCategory
from app.channels.service import create_channel, normalize_slug, subscribe_to_channel
from app.notifications.service import list_user_notifications


def test_normalize_slug() -> None:
    assert normalize_slug("Tech News Daily!") == "tech-news-daily"


def test_create_channel_subscribe_and_notify_on_post(db_session: Session) -> None:
    owner = register_user(
        db_session,
        email="owner@example.com",
        password="password123",
        display_name="Owner",
    )
    subscriber = register_user(
        db_session,
        email="subscriber@example.com",
        password="password123",
        display_name="Subscriber",
    )

    channel = create_channel(
        db_session,
        current_user=owner,
        title="Tech News",
        description="Updates",
        category=ChannelCategory.TECHNOLOGY,
    )
    subscribed = subscribe_to_channel(db_session, channel_id=channel.id, current_user=subscriber)

    assert subscribed.is_subscribed is True
    assert subscribed.subscribers_count == 2
    assert list_user_notifications(db_session, user=subscriber) == []
