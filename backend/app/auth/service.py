from datetime import UTC, datetime, timedelta
from uuid import UUID

from jose import JWTError
from sqlmodel import Session, select

from app.auth.models import AuthToken, AuthTokenPurpose
from app.auth.schemas import TokenPair
from app.common.exceptions import bad_request, unauthorized
from app.core.config import get_settings
from app.core.email import send_password_reset_email
from app.core.security import (
    TokenType,
    create_access_token,
    create_plain_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.users.models import User
from app.users.service import create_user, get_user_by_email, get_user_by_username


def _now() -> datetime:
    return datetime.now(UTC)


def build_token_pair(session: Session, user: User) -> TokenPair:
    subject = str(user.id)
    refresh_token = create_refresh_token(subject)
    store_auth_token(
        session,
        user=user,
        plain_token=refresh_token,
        purpose=AuthTokenPurpose.REFRESH,
        expires_at=_now() + timedelta(days=get_settings().refresh_token_expire_days),
    )
    return TokenPair(
        access_token=create_access_token(subject),
        refresh_token=refresh_token,
    )


def store_auth_token(
    session: Session,
    *,
    user: User,
    plain_token: str,
    purpose: AuthTokenPurpose,
    expires_at: datetime,
) -> AuthToken:
    auth_token = AuthToken(
        user_id=user.id,
        token_hash=hash_token(plain_token),
        purpose=purpose,
        expires_at=expires_at,
    )
    session.add(auth_token)
    session.commit()
    session.refresh(auth_token)
    return auth_token


def create_email_confirmation_token(session: Session, user: User) -> str:
    token = create_plain_token()
    store_auth_token(
        session,
        user=user,
        plain_token=token,
        purpose=AuthTokenPurpose.EMAIL_CONFIRMATION,
        expires_at=_now() + timedelta(hours=get_settings().email_confirmation_token_expire_hours),
    )
    return token


def create_password_reset_token(session: Session, user: User) -> str:
    token = create_plain_token()
    store_auth_token(
        session,
        user=user,
        plain_token=token,
        purpose=AuthTokenPurpose.PASSWORD_RESET,
        expires_at=_now() + timedelta(minutes=get_settings().password_reset_token_expire_minutes),
    )
    return token


def _get_active_auth_token(
    session: Session,
    *,
    plain_token: str,
    purpose: AuthTokenPurpose,
) -> AuthToken:
    statement = select(AuthToken).where(
        AuthToken.token_hash == hash_token(plain_token),
        AuthToken.purpose == purpose,
    )
    auth_token = session.exec(statement).first()
    if not auth_token or not auth_token.is_active:
        raise bad_request("Invalid or expired token")
    return auth_token


def _mark_token_used(session: Session, auth_token: AuthToken) -> None:
    auth_token.used_at = _now()
    session.add(auth_token)
    session.commit()


def _revoke_token(session: Session, auth_token: AuthToken) -> None:
    auth_token.revoked_at = _now()
    session.add(auth_token)
    session.commit()


def _revoke_user_refresh_tokens(session: Session, user: User) -> None:
    statement = select(AuthToken).where(
        AuthToken.user_id == user.id,
        AuthToken.purpose == AuthTokenPurpose.REFRESH,
        AuthToken.used_at.is_(None),
        AuthToken.revoked_at.is_(None),
    )
    active_tokens = session.exec(statement).all()
    for auth_token in active_tokens:
        auth_token.revoked_at = _now()
        session.add(auth_token)


def register_user(
    session: Session,
    *,
    email: str,
    password: str,
    display_name: str,
    username: str | None = None,
) -> User:
    if get_user_by_email(session, email):
        raise bad_request("User with this email already exists")

    if username and get_user_by_username(session, username):
        raise bad_request("User with this username already exists")

    return create_user(
        session,
        email=email,
        password=password,
        display_name=display_name,
        username=username,
    )


def get_or_create_oauth_user(
    session: Session,
    *,
    email: str,
    display_name: str,
    avatar_url: str | None = None,
) -> User:
    user = get_user_by_email(session, email)
    if user:
        if avatar_url and not user.avatar_url:
            user.avatar_url = avatar_url
            user.updated_at = _now()
            session.add(user)
            session.commit()
            session.refresh(user)
        return user

    user = User(
        email=email.lower(),
        display_name=display_name,
        avatar_url=avatar_url,
        password_hash=hash_password(create_plain_token()),
        is_verified=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def authenticate_user(session: Session, *, email: str, password: str) -> User:
    user = get_user_by_email(session, email)
    if not user or not verify_password(password, user.password_hash):
        raise unauthorized("Invalid email or password")

    if not user.is_active:
        raise unauthorized("User is inactive")

    return user


def refresh_tokens(session: Session, refresh_token: str) -> TokenPair:
    try:
        payload = decode_token(refresh_token)
        user_id = UUID(payload["sub"])
        token_type = payload.get("type")
    except (JWTError, KeyError, ValueError):
        raise unauthorized()

    if token_type != TokenType.REFRESH.value:
        raise unauthorized("Invalid token type")

    stored_token = _get_active_auth_token(
        session,
        plain_token=refresh_token,
        purpose=AuthTokenPurpose.REFRESH,
    )
    user = session.get(User, user_id)
    if not user or not user.is_active or user.id != stored_token.user_id:
        raise unauthorized()

    _revoke_token(session, stored_token)
    return build_token_pair(session, user)


def logout_user(session: Session, refresh_token: str) -> None:
    stored_token = _get_active_auth_token(
        session,
        plain_token=refresh_token,
        purpose=AuthTokenPurpose.REFRESH,
    )
    _revoke_token(session, stored_token)


def confirm_email(session: Session, token: str) -> User:
    stored_token = _get_active_auth_token(
        session,
        plain_token=token,
        purpose=AuthTokenPurpose.EMAIL_CONFIRMATION,
    )
    user = session.get(User, stored_token.user_id)
    if not user or not user.is_active:
        raise bad_request("Invalid or expired token")

    user.is_verified = True
    user.updated_at = _now()
    session.add(user)
    _mark_token_used(session, stored_token)
    session.refresh(user)
    return user


def resend_email_confirmation(session: Session, email: str) -> str | None:
    user = get_user_by_email(session, email)
    if not user or not user.is_active or user.is_verified:
        return None
    token = create_email_confirmation_token(session, user)
    return token


def request_password_reset(session: Session, email: str) -> str | None:
    user = get_user_by_email(session, email)
    if not user or not user.is_active:
        return None
    token = create_password_reset_token(session, user)
    send_password_reset_email(user.email, token)
    return token


def reset_password(session: Session, *, token: str, new_password: str) -> None:
    stored_token = _get_active_auth_token(
        session,
        plain_token=token,
        purpose=AuthTokenPurpose.PASSWORD_RESET,
    )
    user = session.get(User, stored_token.user_id)
    if not user or not user.is_active:
        raise bad_request("Invalid or expired token")

    user.password_hash = hash_password(new_password)
    user.updated_at = _now()
    session.add(user)
    _revoke_user_refresh_tokens(session, user)
    _mark_token_used(session, stored_token)


def change_password(
    session: Session,
    *,
    user: User,
    current_password: str,
    new_password: str,
) -> None:
    if not verify_password(current_password, user.password_hash):
        raise bad_request("Current password is incorrect")

    user.password_hash = hash_password(new_password)
    user.updated_at = _now()
    session.add(user)
    _revoke_user_refresh_tokens(session, user)
    session.commit()
