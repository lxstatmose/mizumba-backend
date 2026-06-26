from collections.abc import Generator
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import app.auth.models  # noqa: F401
import app.channels.models  # noqa: F401
import app.chats.models  # noqa: F401
import app.files.models  # noqa: F401
import app.messages.models  # noqa: F401
import app.notifications.models  # noqa: F401
import app.privacy.models  # noqa: F401
import app.users.models  # noqa: F401
from app.core.config import get_settings
from app.core.database import get_session
from app.main import app, rate_limit_state


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture()
def client(db_session: Session, tmp_path: Path) -> Generator[TestClient, None, None]:
    settings = get_settings()
    original_upload_dir = settings.upload_dir
    settings.upload_dir = str(tmp_path / "uploads")
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    rate_limit_state.clear()

    def override_get_session() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    rate_limit_state.clear()
    settings.upload_dir = original_upload_dir


def register_user(
    client: TestClient,
    *,
    email: str = "user@example.com",
    password: str = "password123",
    display_name: str = "Test User",
) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "display_name": display_name,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth_headers(auth_response: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {auth_response['tokens']['access_token']}"}
