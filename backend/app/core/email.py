import smtplib
from email.message import EmailMessage

from app.core.config import get_settings


def send_email(*, to_email: str, subject: str, body: str) -> bool:
    settings = get_settings()
    if not settings.smtp_host:
        return False

    message = EmailMessage()
    message["From"] = settings.smtp_from_email
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        if settings.smtp_username and settings.smtp_password:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)
    return True


def send_confirmation_email(email: str, token: str) -> bool:
    return send_email(
        to_email=email,
        subject="Confirm your MiZumBA email",
        body=f"Use this token to confirm your email: {token}",
    )


def send_password_reset_email(email: str, token: str) -> bool:
    return send_email(
        to_email=email,
        subject="Reset your MiZumBA password",
        body=f"Use this token to reset your password: {token}",
    )
