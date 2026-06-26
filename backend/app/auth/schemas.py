from pydantic import BaseModel, EmailStr, Field

from app.users.schemas import UserPublic


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=2, max_length=100)
    username: str | None = Field(default=None, min_length=3, max_length=50)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class OAuthProviderRequest(BaseModel):
    id_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthResponse(BaseModel):
    user: UserPublic
    tokens: TokenPair
    email_confirmation_token: str | None = None


class LoginOptionsResponse(BaseModel):
    email_password: bool = True
    google: bool
    apple: bool
    country_code: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class MessageResponse(BaseModel):
    message: str


class EmailConfirmationRequest(BaseModel):
    token: str


class ResendEmailConfirmationRequest(BaseModel):
    email: EmailStr


class EmailConfirmationTokenResponse(BaseModel):
    message: str
    email_confirmation_token: str | None = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class PasswordResetTokenResponse(BaseModel):
    message: str
    password_reset_token: str | None = None


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
