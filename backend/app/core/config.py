from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MiZumBA API"
    app_env: str = "local"
    debug: bool = True

    api_v1_prefix: str = "/api/v1"
    frontend_origin: str = "http://localhost:5173"
    public_base_url: str = "http://localhost:8000"

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/mizumba"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret_key: str = Field(default="change-me-before-production")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    email_confirmation_token_expire_hours: int = 24
    password_reset_token_expire_minutes: int = 30
    upload_dir: str = "uploads"
    max_upload_size_mb: int = 10
    max_audio_upload_size_mb: int = 25
    enable_whisper_transcription: bool = False
    whisper_model_name: str = "base"
    whisper_default_language: str | None = None
    google_client_id: str | None = None
    apple_client_id: str | None = None

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str = "noreply@mizumba.app"
    smtp_use_tls: bool = True

    storage_provider: str = "local"
    s3_bucket: str | None = None
    s3_region: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    cloudinary_cloud_name: str | None = None
    cloudinary_api_key: str | None = None
    cloudinary_api_secret: str | None = None

    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60

    default_country_code: str = "DEFAULT"
    auth_provider_rules_json: dict[str, dict[str, bool]] = Field(
        default_factory=lambda: {
            "DEFAULT": {"google": True, "apple": True},
            "RU": {"google": False, "apple": False},
        }
    )

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origin.split(",") if origin.strip()]

    @property
    def auth_provider_rules(self) -> dict[str, dict[str, bool]]:
        rules: Any = self.auth_provider_rules_json
        if isinstance(rules, dict):
            return rules
        return {"DEFAULT": {"google": True, "apple": True}}


@lru_cache
def get_settings() -> Settings:
    return Settings()
