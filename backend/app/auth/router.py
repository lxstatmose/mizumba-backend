from fastapi import APIRouter, Depends, Request, status
from sqlmodel import Session

from app.auth.dependencies import get_current_user
from app.auth.schemas import (
    AuthResponse,
    ChangePasswordRequest,
    EmailConfirmationRequest,
    EmailConfirmationTokenResponse,
    ForgotPasswordRequest,
    LoginOptionsResponse,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    OAuthProviderRequest,
    PasswordResetTokenResponse,
    RefreshTokenRequest,
    RegisterRequest,
    ResendEmailConfirmationRequest,
    ResetPasswordRequest,
    TokenPair,
)
from app.auth.service import (
    authenticate_user,
    build_token_pair,
    change_password,
    confirm_email,
    create_email_confirmation_token,
    get_or_create_oauth_user,
    logout_user,
    refresh_tokens,
    register_user,
    request_password_reset,
    resend_email_confirmation,
    reset_password,
)
from app.core.config import get_settings
from app.core.database import get_session
from app.core.email import send_confirmation_email
from app.geo.service import get_auth_provider_options, get_country_code_from_request
from app.auth.oauth import verify_apple_id_token, verify_google_id_token
from app.users.models import User
from app.users.schemas import UserPublic


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, session: Session = Depends(get_session)) -> AuthResponse:
    user = register_user(
        session,
        email=payload.email,
        password=payload.password,
        display_name=payload.display_name,
        username=payload.username,
    )
    confirmation_token = create_email_confirmation_token(session, user)
    send_confirmation_email(user.email, confirmation_token)
    settings = get_settings()
    return AuthResponse(
        user=user,
        tokens=build_token_pair(session, user),
        email_confirmation_token=confirmation_token if settings.debug else None,
    )


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, session: Session = Depends(get_session)) -> AuthResponse:
    user = authenticate_user(session, email=payload.email, password=payload.password)
    return AuthResponse(user=user, tokens=build_token_pair(session, user))


@router.post("/oauth/google", response_model=AuthResponse)
def google_oauth(payload: OAuthProviderRequest, session: Session = Depends(get_session)) -> AuthResponse:
    profile = verify_google_id_token(payload.id_token)
    user = get_or_create_oauth_user(session, **profile)
    return AuthResponse(user=user, tokens=build_token_pair(session, user))


@router.post("/oauth/apple", response_model=AuthResponse)
def apple_oauth(payload: OAuthProviderRequest, session: Session = Depends(get_session)) -> AuthResponse:
    profile = verify_apple_id_token(payload.id_token)
    user = get_or_create_oauth_user(session, **profile)
    return AuthResponse(user=user, tokens=build_token_pair(session, user))


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshTokenRequest, session: Session = Depends(get_session)) -> TokenPair:
    return refresh_tokens(session, payload.refresh_token)


@router.post("/logout", response_model=MessageResponse)
def logout(payload: LogoutRequest, session: Session = Depends(get_session)) -> MessageResponse:
    logout_user(session, payload.refresh_token)
    return MessageResponse(message="Logged out successfully")


@router.post("/confirm-email", response_model=UserPublic)
def confirm_email_address(
    payload: EmailConfirmationRequest,
    session: Session = Depends(get_session),
) -> User:
    return confirm_email(session, payload.token)


@router.post("/resend-confirmation", response_model=EmailConfirmationTokenResponse)
def resend_confirmation(
    payload: ResendEmailConfirmationRequest,
    session: Session = Depends(get_session),
) -> EmailConfirmationTokenResponse:
    token = resend_email_confirmation(session, payload.email)
    if token:
        send_confirmation_email(payload.email, token)
    settings = get_settings()
    return EmailConfirmationTokenResponse(
        message="If the account exists and is not verified, a confirmation email was sent",
        email_confirmation_token=token if settings.debug else None,
    )


@router.post("/forgot-password", response_model=PasswordResetTokenResponse)
def forgot_password(
    payload: ForgotPasswordRequest,
    session: Session = Depends(get_session),
) -> PasswordResetTokenResponse:
    token = request_password_reset(session, payload.email)
    settings = get_settings()
    return PasswordResetTokenResponse(
        message="If the account exists, a password reset email was sent",
        password_reset_token=token if settings.debug else None,
    )


@router.post("/reset-password", response_model=MessageResponse)
def reset_account_password(
    payload: ResetPasswordRequest,
    session: Session = Depends(get_session),
) -> MessageResponse:
    reset_password(session, token=payload.token, new_password=payload.new_password)
    return MessageResponse(message="Password has been reset successfully")


@router.post("/change-password", response_model=MessageResponse)
def change_account_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> MessageResponse:
    change_password(
        session,
        user=current_user,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    return MessageResponse(message="Password has been changed successfully")


@router.get("/login-options", response_model=LoginOptionsResponse)
def login_options(request: Request) -> LoginOptionsResponse:
    country_code = get_country_code_from_request(request)
    options = get_auth_provider_options(country_code)
    return LoginOptionsResponse(
        email_password=True,
        google=options.get("google", True),
        apple=options.get("apple", True),
        country_code=country_code,
    )
