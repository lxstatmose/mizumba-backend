from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings


settings = get_settings()
engine = create_engine(settings.database_url, echo=settings.debug)


def create_db_and_tables() -> None:
    # Import models before creating metadata so SQLModel knows all tables.
    from app.auth import models  # noqa: F401
    from app.channels import models  # noqa: F401
    from app.chats import models  # noqa: F401
    from app.files import models  # noqa: F401
    from app.messages import models  # noqa: F401
    from app.notifications import models  # noqa: F401
    from app.privacy import models  # noqa: F401
    from app.users import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
