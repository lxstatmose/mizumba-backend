from uuid import UUID

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlmodel import Session

from app.common.exceptions import unauthorized
from app.core.config import get_settings
from app.core.database import get_session
from app.core.security import TokenType, decode_token
from app.users.models import User
from app.users.service import get_user_by_id


settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/login")


def get_user_from_access_token(session: Session, token: str) -> User:
    try:
        payload = decode_token(token)
        user_id = UUID(payload["sub"])
        token_type = payload.get("type")
    except (JWTError, KeyError, ValueError):
        raise unauthorized()

    if token_type != TokenType.ACCESS.value:
        raise unauthorized("Invalid token type")

    user = get_user_by_id(session, user_id)
    if not user or not user.is_active:
        raise unauthorized()

    return user


def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> User:
    return get_user_from_access_token(session, token)
