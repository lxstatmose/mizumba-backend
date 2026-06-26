from pathlib import Path
import sys

from sqlmodel import Session

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from app.channels.models import ChannelCategory  # noqa: E402
from app.channels.service import create_channel, create_channel_post, get_channel_by_slug  # noqa: E402
from app.chats.service import create_direct_chat  # noqa: E402
from app.core.database import create_db_and_tables, engine  # noqa: E402
from app.messages.service import create_message  # noqa: E402
from app.users.models import User  # noqa: E402
from app.users.service import create_user, get_user_by_email  # noqa: E402


DEMO_USERS = [
    {
        "email": "demo-alice@mizumba.app",
        "password": "demoPassword123",
        "display_name": "Alice Demo",
        "username": "alice_demo",
    },
    {
        "email": "demo-bob@mizumba.app",
        "password": "demoPassword123",
        "display_name": "Bob Demo",
        "username": "bob_demo",
    },
]


def get_or_create_demo_user(session: Session, data: dict[str, str]) -> User:
    user = get_user_by_email(session, data["email"])
    if user:
        return user
    user = create_user(
        session,
        email=data["email"],
        password=data["password"],
        display_name=data["display_name"],
        username=data["username"],
    )
    user.is_verified = True
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def seed() -> None:
    create_db_and_tables()
    with Session(engine) as session:
        alice = get_or_create_demo_user(session, DEMO_USERS[0])
        bob = get_or_create_demo_user(session, DEMO_USERS[1])

        chat = create_direct_chat(session, alice, bob.id)
        if not chat.last_message:
            create_message(
                session,
                chat_id=chat.id,
                current_user=alice,
                text="Привет! Это демо-чат для проверки фронта.",
            )
            create_message(
                session,
                chat_id=chat.id,
                current_user=bob,
                text="Отлично, можно тестировать realtime и историю сообщений.",
            )

        channel = get_channel_by_slug(session, "demo-news")
        if not channel:
            channel = create_channel(
                session,
                current_user=alice,
                title="Demo News",
                slug="demo-news",
                description="Демо-канал для проверки ленты и подписок.",
                category=ChannelCategory.GENERAL,
            )
            create_channel_post(
                session,
                channel_id=channel.id,
                current_user=alice,
                text="Первый демо-пост. Если видишь его на фронте, интеграция работает.",
            )

    print("Demo data created")
    print("Users:")
    for user in DEMO_USERS:
        print(f"- {user['email']} / {user['password']}")


if __name__ == "__main__":
    seed()
